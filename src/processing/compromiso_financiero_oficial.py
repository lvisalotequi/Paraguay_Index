#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 03/09/2026                                                #
# NOMBRE: compromiso_financiero_oficial                                        #
# DETALLE: lleva a trimestres las 6 fuentes de la dimension 1                  #
#   (ForeignAssistance.gov, USAspending, DFC, EXIM, BID y Banco Mundial) y     #
#   deja 11 variables en USD sin escalar, salvo los proyectos vigentes de DFC, #
#   que son una cantidad. BID y Banco Mundial incluyen una variante ponderada  #
#   por la cuota de EE.UU. NO consulta ninguna API: lee solo los crudos de     #
#   Drive.                                                                     #
#                                                                              #
# CORRE DESPUES DE: ingestion de las 6 fuentes y de cuota_capital_bid y        #
#   cuota_capital_bancomundial (src/ingestion/)                                #
# SALIDA: un CSV por variable (11) en                                          #
#   02_limpias/1_Compromiso_financiero_oficial_limpias/<variable>/             #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import json
import zipfile
from datetime import datetime, timezone

import pandas as pd

from src.drive import descargar_archivo, listar_archivos, resolve_ingestion_folder
from src.processing._common import subir_variable



# Parametros -------------------------------------------------------------------

# Carpetas de Drive: las crudas las escribe ingestion y las limpias este modulo.
DIMENSION_CRUDA  = "1_Compromiso_financiero_oficial"
DIMENSION_LIMPIA = "1_Compromiso_financiero_oficial_limpias"

ANIO_MINIMO = 2015



# Funciones auxiliares ---------------------------------------------------------

# Mismo patron y misma politica de unidades y salida que compromiso_economico_privado.py
# y _common.py: una carpeta por variable y esquema fijo (trimestre, anio, trimestre_num,
# valor, unidad). A diferencia de la dimension 3, todas las fuentes monetarias ya vienen
# nativamente en USD (no en miles ni millones), asi que no hace falta reescalar.
#
# De cada fuente se usa el archivo mas reciente que subio ingestion. Cada variable se
# sube por separado, con la fecha de la corrida en el nombre (idempotente por dia).


def _archivos(fuente):
    return listar_archivos(resolve_ingestion_folder(DIMENSION_CRUDA, fuente))


def _sumar_por_trimestre(fechas, montos):
    """A partir de dos Series alineadas (fecha, monto), devuelve
    {(anio,trim): suma} - fechas invalidas/faltantes o < ANIO_MINIMO se
    ignoran, montos no numericos tambien."""
    fechas = pd.to_datetime(fechas, errors="coerce")
    montos = pd.to_numeric(montos, errors="coerce")
    df = pd.DataFrame({"fecha": fechas, "monto": montos}).dropna()
    df = df[df["fecha"].dt.year >= ANIO_MINIMO]

    acumulado = {}
    for fecha, monto in zip(df["fecha"], df["monto"]):
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        acumulado[clave] = acumulado.get(clave, 0.0) + float(monto)
    return acumulado


def _repetir_en_trimestres(valores_por_anio):
    """{anio: valor} -> {(anio,trim): valor} repitiendo el mismo valor en
    los 4 trimestres (para fuentes sin fecha mas fina que el anio)."""
    return {(anio, trim): valor for anio, valor in valores_por_anio.items() for trim in (1, 2, 3, 4)}



# ForeignAssistance.gov --------------------------------------------------------

# Entrada: un JSON por anio y medida (fa_gov_asistencia_oficial), ya filtrado a Paraguay.
#
# Salida: fa_gov_obligaciones y fa_gov_desembolsos. Se suma `current_amount` de todas las
# actividades de cada anio, por separado para Obligations y Disbursements. La fuente no
# tiene fecha mas fina que el anio fiscal (`fiscal_year`): el mismo total anual se repite
# en los 4 trimestres, igual que bea_inversion_directa en la dimension 3.


def _extraer_fa_gov():
    """Devuelve (obligaciones, desembolsos), cada una {(anio,trim): usd}
    repitiendo el total anual en los 4 trimestres (ver el comentario de la
    seccion)."""

    # 1. lee un JSON por anio y medida y suma el monto de todas sus actividades
    archivos = _archivos("fa_gov_asistencia_oficial")
    totales = {"Obligations": {}, "Disbursements": {}}

    for archivo in archivos:
        # nombre: "PRY_{medida}_{anio}.json"
        partes = archivo["name"].removesuffix(".json").split("_")
        medida, anio = partes[1], int(partes[2])
        if anio < ANIO_MINIMO or medida not in totales:
            continue
        filas = json.loads(descargar_archivo(archivo["id"]))
        totales[medida][anio] = sum(f.get("current_amount") or 0 for f in filas)

    # 2. repite cada total anual en los 4 trimestres
    return _repetir_en_trimestres(totales["Obligations"]), _repetir_en_trimestres(totales["Disbursements"])



# USAspending ------------------------------------------------------------------

# Entrada: un ZIP por anio (usaspending_obligaciones) con 4 CSV adentro. Se usan los dos
# CSV "PrimeTransactions" (Contracts y Assistance: las transacciones en si, no los
# subawards).
#
# Salida: usaspending_obligaciones, la suma de `federal_action_obligation` por trimestre
# de `action_date`. A diferencia de fa_gov, esta fuente SI tiene fecha de transaccion
# real: es trimestral autentico.
#
# POR QUE ASSISTANCE SE FILTRA (2026-09-28, a pedido del usuario: "excluir toda la
# asistencia extranjera, quedarnos con el resto"): para no duplicar lo que ya miden
# fa_gov_obligaciones y fa_gov_desembolsos. Se mantienen todas las transacciones de
# Contracts y solo las de Assistance de tres agencias, listadas abajo.
#
# Agencias cuyas filas de Assistance se MANTIENEN: no son asistencia extranjera pese a
# estar clasificadas como "Assistance" por USAspending. Son pagos de beneficios
# individuales (jubilacion, pension, compensacion por discapacidad) de EE.UU. a personas
# que residen en Paraguay: nada que ver con cooperacion bilateral, ni se solapan con lo
# que reporta fa_gov (que solo trackea programas de USAID y del Departamento de Estado,
# no beneficios individuales). Verificado con datos reales 2015-2026, por
# `awarding_agency_name`:
#   Social Security Administration      $29.600.411 (417 transacciones)
#   Railroad Retirement Board              $209.718 (219 transacciones)
#   Department of Veterans Affairs         $566.102 (74 transacciones -
#     "Pension to Veterans...", "Veterans Compensation for Service-Connected
#     Disability...", "Post-9/11 Veterans Educational Assistance")
# Todas las demas agencias que aparecen en Assistance para Paraguay SI son asistencia
# extranjera propiamente dicha y quedan excluidas:
#   Agency for International Development   $70.797.374
#   Department of State                     $24.084.099
#   Department of Agriculture               $14.710.573 (Food for Progress)
#   Inter-American Foundation                $3.968.504
#   Department of Health and Human Services  $3.536.686 (salud publica global)
#   Department of the Interior               $1.218.990 (conservacion/vida silvestre)
AGENCIAS_NO_ASISTENCIA_EXTRANJERA = (
    "Social Security Administration",
    "Railroad Retirement Board",
    "Department of Veterans Affairs",
)


def _extraer_usaspending():
    """Devuelve {(anio,trim): usd} sumando `federal_action_obligation` por
    trimestre de `action_date`, de:
    - TODAS las transacciones de Contracts (compras directas del gobierno
      de EE.UU. con desempenio en Paraguay - no se solapan con fa_gov).
    - Solo las transacciones de Assistance cuya `awarding_agency_name` esta
      en AGENCIAS_NO_ASISTENCIA_EXTRANJERA (ver esa constante para el
      detalle completo). El resto de Assistance (USAID, Departamento de
      Estado, y otros programas de cooperacion/ayuda internacional) se
      excluye a proposito porque ya lo mide `fa_gov_obligaciones`/
      `fa_gov_desembolsos` - sumarlo aca duplicaria esa plata."""

    # 1. abre el ZIP de cada anio y toma los CSV de transacciones
    acumulado = {}
    for archivo in _archivos("usaspending_obligaciones"):
        contenido = descargar_archivo(archivo["id"])
        z = zipfile.ZipFile(io.BytesIO(contenido))
        for nombre in z.namelist():
            if "Contracts_PrimeTransactions" in nombre:
                df = pd.read_csv(z.open(nombre), usecols=["action_date", "federal_action_obligation"])
            elif "Assistance_PrimeTransactions" in nombre:
                df = pd.read_csv(
                    z.open(nombre),
                    usecols=["action_date", "federal_action_obligation", "awarding_agency_name"],
                )
                df = df[df["awarding_agency_name"].isin(AGENCIAS_NO_ASISTENCIA_EXTRANJERA)]
            else:
                continue

            # 2. suma cada CSV por trimestre y lo acumula al total
            parcial = _sumar_por_trimestre(df["action_date"], df["federal_action_obligation"])
            for clave, valor in parcial.items():
                acumulado[clave] = acumulado.get(clave, 0.0) + valor
    return acumulado



# DFC --------------------------------------------------------------------------

# Entrada: un Excel unico de DFC (dfc_proyectos_activos), todos los paises, hoja "Project
# Data". Se filtra a `Country == "Paraguay"`.
#
# Salida: dos variables.
#   - dfc_comprometido: `Committed` por `Fiscal Year`, repetido en los 4 trimestres como
#     fa_gov (sin fecha mas fina que el anio).
#   - dfc_proyectos_vigentes: stock acumulado de proyectos vigentes, usando `Estimated
#     Term (Years)` para dar de baja el proyecto al vencer (ver _acumular_vigencia_dfc).
#
# POR QUE UN STOCK DE VIGENCIA (2026-09-21, a pedido del usuario): con solo 4 proyectos
# en 8 anios, un conteo de proyectos nuevos por trimestre queda casi todo en cero, el
# mismo problema ya documentado para USTR y TIAS antes de pasar a stock.
#
# LIMITE HEREDADO DE LA FUENTE: son pocos proyectos (~4 historicos) y el archivo es
# "Active Project Data", una foto de lo vigente hoy y no un historico completo. Un
# proyecto viejo que ya cerro no aparece nunca, ni siquiera para los trimestres en que si
# estuvo vigente. El 2026-09-21 el usuario sospecho que la transicion OPIC a DFC de 2019
# podia haber perdido datos de Paraguay anteriores a 2018. Se descarto esa hipotesis con
# evidencia: el archivo global SI conserva 511 proyectos de otros paises originados antes
# de 2018 y aun vigentes, de las 3 agencias predecesoras (OPIC, Legacy USAID y DCA), asi
# que la transicion no pierde datos. La ausencia de proyectos viejos de Paraguay se
# explica mas probablemente por el vencimiento natural de prestamos previos que por un
# error de la fuente.


def _acumular_vigencia_dfc(fiscal_years, terminos):
    """Devuelve {(anio,trim): cantidad de proyectos vigentes}. Cada proyecto
    se considera vigente desde el trimestre 1 de su `Fiscal Year` hasta el
    trimestre 4 del anio (`Fiscal Year` + `Estimated Term (Years)`) - a
    diferencia de state_gov_tias_vigentes (que acumula sin bajas porque no
    hay dato de vencimiento), aca SI hay una duracion estimada por proyecto
    y se usa para dar de baja el proyecto vencido, no solo para sumar.
    Aproximado por partida doble: el trimestre exacto dentro del Fiscal Year
    no se conoce (solo el anio), y "Estimated Term" es una estimacion de DFC,
    no una fecha de vencimiento contractual real."""

    # 1. arma la ventana de vigencia (trimestre inicial, trimestre final) de cada proyecto
    ventanas = []
    for anio_inicio, term in zip(fiscal_years, terminos):
        if pd.isna(anio_inicio):
            continue
        anio_inicio = int(anio_inicio)
        term = int(term) if pd.notna(term) else 0
        ventanas.append(((anio_inicio, 1), (anio_inicio + term, 4)))

    if not ventanas:
        return {}

    # 2. recorre los trimestres desde el primer proyecto hasta el actual
    anio, trim = min(v[0] for v in ventanas)
    hoy = datetime.now(timezone.utc)
    ultimo_trim = (hoy.year, (hoy.month - 1) // 3 + 1)

    # 3. en cada trimestre cuenta los proyectos cuya ventana lo incluye
    resultado = {}
    while (anio, trim) <= ultimo_trim:
        resultado[(anio, trim)] = sum(1 for inicio, fin in ventanas if inicio <= (anio, trim) <= fin)
        trim += 1
        if trim > 4:
            trim = 1
            anio += 1
    return resultado


def _extraer_dfc():
    """Devuelve (comprometido, proyectos_vigentes): `comprometido` es
    {(anio,trim): usd} sumando `Committed` de proyectos de Paraguay por
    `Fiscal Year` y repitiendo el total en los 4 trimestres;
    `proyectos_vigentes` es {(anio,trim): cantidad}, el stock acumulado de
    proyectos vigentes (ver `_acumular_vigencia_dfc` y el comentario de la
    seccion para sus limites)."""

    # 1. lee la hoja y filtra a Paraguay
    _, contenido = _archivo_mas_reciente_por_nombre("dfc_proyectos_activos")
    df = pd.read_excel(io.BytesIO(contenido), sheet_name="Project Data", header=1)
    py = df[df["Country"] == "Paraguay"].copy()
    py["Fiscal Year"] = pd.to_numeric(py["Fiscal Year"], errors="coerce")

    # 2. suma lo comprometido por anio fiscal y lo repite en los 4 trimestres
    por_anio = py[py["Fiscal Year"] >= ANIO_MINIMO].groupby("Fiscal Year")["Committed"].sum()
    comprometido = _repetir_en_trimestres(por_anio.to_dict())

    # 3. arma el stock de proyectos vigentes
    proyectos_vigentes = _acumular_vigencia_dfc(py["Fiscal Year"], py["Estimated Term (Years)"])
    return comprometido, proyectos_vigentes



# EXIM -------------------------------------------------------------------------

# Entrada: un CSV unico de EXIM (exim_autorizaciones), ya filtrado a Paraguay. Se filtra a
# `Decision == "Approved"` (se excluyen las declinadas). Hoy es un filtro inerte: las 60
# filas de Paraguay ya vienen todas "Approved", pero se deja por si alguna vez aparece una
# declinada. Las 4 operaciones canceladas (`Deal Cancelled == "Yes"`) ya vienen con monto
# $0 en el propio archivo de EXIM, no requieren ajuste aparte.
#
# Salida: dos variables por trimestre de `Decision Date`, el mismo patron que fa_gov
# obligado y desembolsado. Es trimestral autentico.
#   - exim_autorizado: `Approved/Declined Amount`, el valor de cara de la autorizacion.
#   - exim_desembolsado: `Disbursed/Shipped Amount`, lo que realmente se desembolso (en
#     Guarantee) o se embarco (en Insurance) bajo esa autorizacion.
#
# POR QUE NO SE SEPARA POR PROGRAMA (piloto Insurance vs Guarantee, 2026-09-21, a pedido
# del usuario: "quisiera ver si tienen comportamientos distintos... para decidir si
# conviene separarlos"). Se investigo y se decidio NO separarlos, con evidencia. Los dos
# `Program` que existen para Paraguay (Insurance y Guarantee; no hay Loan ni Working
# Capital) se comportan de forma casi opuesta:
#   - correlacion casi nula o levemente negativa (Spearman sobre cambios trimestrales
#     -0.15, el mismo criterio que usa la etapa de construccion del indice para evaluar
#     redundancia);
#   - coocurren en el mismo trimestre solo el 4.5% de las veces (22.7% solo Insurance,
#     25% solo Guarantee, 47.7% ninguno);
#   - hay un cambio de regimen real: Insurance domino 2017-2020 (100%, 100%, 42% y 79% del
#     total anual) y desde 2021 EXIM le da a Paraguay casi solo Guarantees (60% a 100% del
#     total anual 2021-2025);
#   - difieren en tamanio promedio de operacion (Insurance ~USD 2.46M, Guarantee ~USD
#     1.35M) y en cuanto de lo aprobado se desembolsa o embarca (Guarantee 94.3%,
#     Insurance 70.5%).
# Toda esa evidencia apunta a que SON series con comportamiento distinto, no redundantes.
#
# Pero igual se decidio no separarlas: al turnarse en vez de superponerse, la serie
# COMBINADA tiene actividad en 23 de 44 trimestres (desde 2015), contra apenas 12
# (Insurance sola) y 13 (Guarantee sola). Separar convertiria una variable ya razonable
# en dos series de eventos raros, el mismo problema documentado y sin resolver para la
# dimension 2 (ver CLAUDE.md, pendiente #6). La combinada ademas es MENOS volatil que
# cualquiera de las dos (coeficiente de variacion anual 0.91 contra 1.34 de Insurance y
# 0.99 de Guarantee), justamente porque se turnan. Se priorizo tener una serie utilizable
# para el indice sobre preservar una distincion que es real. Si en el futuro se necesita
# esa distincion (por ejemplo para leer la composicion del compromiso de EXIM, no para el
# indice), estos numeros ya estan calculados y no hace falta repetir el piloto.


def _extraer_exim():
    """Devuelve (autorizado, desembolsado), cada una {(anio,trim): usd},
    sumando `Approved/Declined Amount` y `Disbursed/Shipped Amount` de
    autorizaciones con `Decision == "Approved"`, por trimestre de
    `Decision Date` - ver el comentario de la seccion para el piloto que
    decidio no separar por Program (Insurance/Guarantee)."""
    _, contenido = _archivo_mas_reciente_por_nombre("exim_autorizaciones")
    df = pd.read_csv(io.BytesIO(contenido))
    aprobadas = df[df["Decision"] == "Approved"]
    autorizado = _sumar_por_trimestre(aprobadas["Decision Date"], aprobadas["Approved/Declined Amount"])
    desembolsado = _sumar_por_trimestre(aprobadas["Decision Date"], aprobadas["Disbursed/Shipped Amount"])
    return autorizado, desembolsado



# BID --------------------------------------------------------------------------

# Entrada: el JSON diario de bid_proyectos, ya filtrado a Paraguay (se usa el archivo mas
# reciente), y el % de capital de EE.UU. que sube cuota_capital_bid.
#
# Salida: dos variables, por trimestre de la fecha de aprobacion (`apprvl_dt`).
#   - bid_proyectos_aprobados: el monto originalmente aprobado de CADA proyecto
#     (`orig_apprvd_useq_amnt`), sin distinguir tipo de operacion. Es una cifra de
#     "actividad multilateral" general, no atribuible a EE.UU. por si sola.
#   - bid_proyectos_atribuible_eeuu: la porcion de lo aprobado ponderada por la cuota de
#     capital de EE.UU. en el BID (hoy 30.006%), aplicada SOLO a los registros financiados
#     con Capital Ordinario (`OPERTYP_CAPITAL_ORDINARIO_BID`: "Loan Operation" y
#     "Container"). El % se lee del archivo mas reciente de cuota_capital_bid, no esta
#     hardcodeado aca, para que una futura actualizacion en ingestion se propague sola.
#
# POR QUE SOLO ESOS DOS TIPOS (investigado el 2026-09-21, ver tambien
# DICCIONARIO_VARIABLES.md): el 69% de los 940 registros de Paraguay son "Technical
# Cooperation", financiada en su mayoria por fondos fiduciarios especificos (confirmado un
# caso real financiado por el Fund for Special Operations) que NO salen de Capital
# Ordinario. Aplicarles el mismo 30% que a un prestamo hubiera sido inventar un numero:
# un fondo fiduciario de otro pais tiene 0% de EE.UU., no 30%. El dataset de
# bid_proyectos.py no identifica el fondo exacto de cada Cooperacion Tecnica (esa info
# vive en la pagina de cada proyecto, y revisarla una por una no es practico). Quedan
# deliberadamente fuera del calculo ponderado: Technical Cooperation, Multilateral
# Investment Fund/IDB Lab, IDB Invest (entidad legal separada, cuota propia sin investigar
# todavia), Garantias y Equity. Por eso `atribuible_eeuu` es un piso (minimo atribuible),
# no el total real, que seria mas alto si se lograran clasificar esas otras categorias.

OPERTYP_CAPITAL_ORDINARIO_BID = ("Loan Operation", "Container")


def _cuota_capital_bid_eeuu():
    """Devuelve el % de capital/poder de voto de EE.UU. en el BID, leido
    del archivo mas reciente que subio `cuota_capital_bid.py` (no
    hardcodeado aca, para que una futura actualizacion del valor en
    ingestion se propague sola sin tocar este archivo)."""
    _, contenido = _archivo_mas_reciente_por_nombre("cuota_capital_bid")
    df = pd.read_csv(io.BytesIO(contenido))
    fila = df[df["pais"] == "Estados Unidos"].iloc[0]
    return float(fila["porcentaje_capital_voto"])


def _extraer_bid():
    """Devuelve (aprobado, atribuible_eeuu), cada una {(anio,trim): usd}
    (ver el comentario de la seccion para la definicion de cada una y por
    que `atribuible_eeuu` solo cubre Capital Ordinario)."""

    # 1. lee el JSON mas reciente y suma lo aprobado por trimestre
    _, contenido = _archivo_mas_reciente_por_nombre("bid_proyectos")
    registros = json.loads(contenido)["records"]
    df = pd.DataFrame(registros)

    aprobado = _sumar_por_trimestre(df["apprvl_dt"], df["orig_apprvd_useq_amnt"])

    # 2. suma solo lo de Capital Ordinario y lo pondera por la cuota de EE.UU.
    capital_ordinario = df[df["opertyp_nm"].isin(OPERTYP_CAPITAL_ORDINARIO_BID)]
    aprobado_capital_ordinario = _sumar_por_trimestre(
        capital_ordinario["apprvl_dt"], capital_ordinario["orig_apprvd_useq_amnt"]
    )
    pct_eeuu = _cuota_capital_bid_eeuu()
    atribuible_eeuu = {
        clave: valor * pct_eeuu / 100 for clave, valor in aprobado_capital_ordinario.items()
    }

    return aprobado, atribuible_eeuu



# Banco Mundial ----------------------------------------------------------------

# Entrada: el JSON diario de bancomundial_proyectos, ya filtrado a Paraguay (se usa el
# archivo mas reciente), y la serie anual de % de poder de voto de EE.UU. en el IBRD que
# sube cuota_capital_bancomundial.
#
# Salida: dos variables, por trimestre de `boardapprovaldate`.
#   - bancomundial_proyectos_aprobados: el monto total del proyecto (`totalamt`), sin
#     ponderar. Es una cifra de "actividad multilateral" general.
#   - bancomundial_proyectos_atribuible_eeuu: lo aprobado ponderado por la cuota de poder
#     de voto de EE.UU. en el IBRD DEL ANIO DE APROBACION de cada proyecto. A diferencia
#     del BID no es una constante: la cuota de EE.UU. en el IBRD si cambio de verdad entre
#     2015 y 2026 (ver cuota_capital_bancomundial.py).
#
# POR QUE SE APLICA A TODO SIN EXCLUIR TIPOS (a diferencia del BID): los proyectos de
# Paraguay son 100% IBRD y cero IDA (`idacommamt` da 0 en las 133 filas, confirmado el
# 2026-09-21), asi que no hay categorias con otra estructura de capital que excluir.
#
# POR QUE SE ARRASTRA EL ULTIMO VALOR EN LOS ANIOS SIN DATO: el historico de
# cuota_capital_bancomundial.py no tiene dato exacto para 2015, 2017, 2020, 2021 y 2026
# (al 2026-09-22). Para esos anios se usa el % del anio confirmado mas cercano, hacia
# adelante o, si el proyecto es anterior al primer anio con dato, hacia atras. Es el mismo
# criterio de repetir el ultimo valor conocido que el proyecto usa para otras fuentes
# anuales (fa_gov, bea_inversion_directa).


def _cuota_capital_bancomundial_por_anio():
    """Devuelve {anio_fiscal: porcentaje_voto} leido del archivo mas
    reciente que subio `cuota_capital_bancomundial.py` (historico fijo,
    editado a mano - ver ese modulo para como agregar un anio nuevo)."""
    _, contenido = _archivo_mas_reciente_por_nombre("cuota_capital_bancomundial")
    df = pd.read_csv(io.BytesIO(contenido))
    df = df[df["pais"] == "Estados Unidos"]
    return dict(zip(df["anio_fiscal"], df["porcentaje_voto"]))


def _extraer_bancomundial():
    """Devuelve (aprobado, atribuible_eeuu), cada una {(anio,trim): usd}
    (ver el comentario de la seccion para la definicion de cada una y para
    el arrastre del % en los anios sin dato)."""

    # 1. lee el JSON mas reciente y suma lo aprobado por trimestre
    _, contenido = _archivo_mas_reciente_por_nombre("bancomundial_proyectos")
    proyectos = json.loads(contenido)["projects"].values()
    df = pd.DataFrame(proyectos)
    df["boardapprovaldate"] = pd.to_datetime(df["boardapprovaldate"], errors="coerce")
    df["totalamt"] = pd.to_numeric(df["totalamt"], errors="coerce")

    aprobado = _sumar_por_trimestre(df["boardapprovaldate"], df["totalamt"])

    # 2. prepara el % de EE.UU. de cada anio, arrastrando el ultimo valor conocido
    pct_por_anio = _cuota_capital_bancomundial_por_anio()
    anios_disponibles = sorted(pct_por_anio)

    def _pct_para_anio(anio):
        anteriores = [a for a in anios_disponibles if a <= anio]
        return pct_por_anio[max(anteriores)] if anteriores else pct_por_anio[min(anios_disponibles)]

    # 3. pondera cada proyecto por el % de su anio de aprobacion y suma por trimestre
    validas = df.dropna(subset=["boardapprovaldate", "totalamt"])
    validas = validas[validas["boardapprovaldate"].dt.year >= ANIO_MINIMO]

    atribuible_eeuu = {}
    for fecha, monto in zip(validas["boardapprovaldate"], validas["totalamt"]):
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        pct = _pct_para_anio(fecha.year)
        atribuible_eeuu[clave] = atribuible_eeuu.get(clave, 0.0) + float(monto) * pct / 100

    return aprobado, atribuible_eeuu



# Lectura del archivo mas reciente ---------------------------------------------

# Las extracciones de DFC, EXIM, BID y Banco Mundial leen con esta funcion. Esta definida
# al final porque se resuelve al llamarla, no al importar el modulo.


def _archivo_mas_reciente_por_nombre(fuente):
    archivos = _archivos(fuente)
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    return archivo["name"], descargar_archivo(archivo["id"])



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. prepara las listas de variables y errores, y el ayudante que corre cada extraccion
    print(f"[{DIMENSION_LIMPIA}]")
    fuentes = []
    errores = []

    def intentar(etiqueta, extraer):
        """Corre una extraccion; si falla la anota (no corta las demas) y
        devuelve None. Los errores se reportan juntos al final de run()."""
        try:
            return extraer()
        except Exception as exc:  # noqa: BLE001
            errores.append((etiqueta, repr(exc)))
            print(f"    [!] {etiqueta}: {exc!r}")
            return None

    # 2. ForeignAssistance.gov: obligaciones y desembolsos
    resultado = intentar("fa_gov_asistencia_oficial", _extraer_fa_gov)
    if resultado:
        fuentes.append(("fa_gov_obligaciones", resultado[0], "USD"))
        fuentes.append(("fa_gov_desembolsos", resultado[1], "USD"))

    # 3. EXIM: autorizado y desembolsado
    resultado = intentar("exim_autorizaciones", _extraer_exim)
    if resultado:
        fuentes.append(("exim_autorizado", resultado[0], "USD"))
        fuentes.append(("exim_desembolsado", resultado[1], "USD"))

    # 4. DFC: comprometido (USD) y proyectos vigentes (cantidad)
    resultado = intentar("dfc_proyectos_activos", _extraer_dfc)
    if resultado:
        fuentes.append(("dfc_comprometido", resultado[0], "USD"))
        fuentes.append(("dfc_proyectos_vigentes", resultado[1], "cantidad"))

    # 5. BID: aprobado y atribuible a EE.UU.
    resultado = intentar("bid_proyectos", _extraer_bid)
    if resultado:
        fuentes.append(("bid_proyectos_aprobados", resultado[0], "USD"))
        fuentes.append(("bid_proyectos_atribuible_eeuu", resultado[1], "USD"))

    # 6. Banco Mundial: aprobado y atribuible a EE.UU.
    resultado = intentar("bancomundial_proyectos", _extraer_bancomundial)
    if resultado:
        fuentes.append(("bancomundial_proyectos_aprobados", resultado[0], "USD"))
        fuentes.append(("bancomundial_proyectos_atribuible_eeuu", resultado[1], "USD"))

    # 7. USAspending: una sola variable
    resultado = intentar("usaspending_obligaciones", _extraer_usaspending)
    if resultado is not None:
        fuentes.append(("usaspending_obligaciones", resultado, "USD"))

    # 8. sube cada variable; todas las monetarias ya vienen en USD, no hace falta reescalar
    for nombre_variable, valores, unidad in fuentes:
        try:
            subir_variable(DIMENSION_LIMPIA, nombre_variable, valores, unidad)
        except Exception as exc:  # noqa: BLE001
            errores.append((nombre_variable, repr(exc)))
            print(f"    [!] {nombre_variable}: {exc!r}")

    # 9. validacion: si fallo alguna variable, termina con error despues de subir las otras
    if errores:
        raise RuntimeError(f"Fallaron {len(errores)} variables de {DIMENSION_LIMPIA}: {errores}")


if __name__ == "__main__":
    run()
