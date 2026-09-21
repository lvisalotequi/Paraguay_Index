"""
Limpieza/consolidacion de la dimension 1 (Compromiso financiero oficial) en
un CSV trimestral por variable, en USD sin escalar (mismo patron y misma
politica de unidades/salida que src/processing/compromiso_economico_privado.py
y src/processing/_common.py - ver esos modulos para el detalle de la
convencion general: una carpeta por variable, esquema fijo trimestre/anio/
trimestre_num/valor/unidad).

Fuentes y como se tratan (confirmado con datos reales el 2026-09-03):
    - fa_gov_asistencia_oficial (un JSON por año+medida, ya filtrado a
      Paraguay): se suma `current_amount` de todas las actividades de cada
      año, por separado para Obligations y Disbursements. La fuente no
      tiene fecha mas fina que el año fiscal (`fiscal_year`) - el mismo
      total anual se repite en los 4 trimestres de ese año, igual que
      bea_inversion_directa en la dimension 3.
    - usaspending_obligaciones (un ZIP por año, con 4 CSV adentro): se usan
      los dos CSV "PrimeTransactions" (Contracts y Assistance - las
      transacciones en si, no los subawards), sumando
      `federal_action_obligation` por trimestre segun `action_date`. A
      diferencia de fa_gov, esta SI tiene fecha de transaccion real -
      trimestral autentico.
    - dfc_proyectos_activos (Excel unico, todos los paises, hoja
      "Project Data"): se filtra a `Country == "Paraguay"` y se suma
      `Committed` por `Fiscal Year`. Muy pocos proyectos en total (~4
      historicos) - sin fecha mas fina que el año, se repite en los 4
      trimestres como fa_gov.
    - exim_autorizaciones (CSV unico, ya filtrado a Paraguay): se filtra a
      `Decision == "Approved"` (se excluyen autorizaciones declinadas - hoy
      es un filtro inerte, las 60 filas de Paraguay ya vienen todas
      "Approved", pero se deja por si alguna vez aparece una declinada) y se
      suman DOS columnas por trimestre segun `Decision Date`, mismo patron
      que fa_gov obligado/desembolsado: `exim_autorizado` (`Approved/
      Declined Amount`, el valor de cara de la autorizacion) y
      `exim_desembolsado` (`Disbursed/Shipped Amount`, lo que realmente se
      desembolso - para Guarantee - o se embarco - para Insurance - bajo esa
      autorizacion). Trimestral autentico. Las 4 operaciones canceladas
      (`Deal Cancelled == "Yes"`) ya vienen con monto $0 en el propio
      archivo de EXIM, no requieren ajuste aparte.

      **Piloto Insurance vs Guarantee (2026-09-21, a pedido del usuario -
      "quisiera ver si tienen comportamientos distintos... para decidir si
      conviene separarlos"): se investigo separarlos y se decidio NO
      hacerlo, con evidencia.** Los dos `Program` que existen para Paraguay
      (Insurance y Guarantee - no hay Loan ni Working Capital) se comportan
      de forma casi opuesta: correlacion practicamente nula o levemente
      negativa (Spearman sobre cambios trimestrales -0.15, igual criterio
      que usa la etapa de construccion del indice para evaluar redundancia),
      coocurren en el mismo trimestre solo 4.5% de las veces (22.7% solo
      Insurance, 25% solo Guarantee, 47.7% ninguno), y hay un cambio de
      regimen real: Insurance domino 2017-2020 (100%/100%/42%/79% del total
      anual) y desde 2021 EXIM le da a Paraguay casi exclusivamente
      Guarantees (60%-100% del total anual 2021-2025). Tambien difieren en
      tamaño promedio de operacion (Insurance ~USD 2.46M, Guarantee ~USD
      1.35M) y en cuanto de lo aprobado se desembolsa/embarca (Guarantee
      94.3%, Insurance 70.5%). Toda esta evidencia apunta a que SON series
      con comportamiento distinto, no redundantes entre si.

      **Por que igual se decidio no separarlas**: al turnarse en vez de
      superponerse, la serie COMBINADA tiene actividad en 23 de 44
      trimestres (desde 2015), contra apenas 12 (Insurance sola) y 13
      (Guarantee sola) si se separan - separar convertiria una variable ya
      razonable en dos series de eventos raros, el mismo problema que ya
      esta documentado y sin resolver para la dimension 2 (ver CLAUDE.md,
      pendiente #6). La combinada ademas es MENOS volatil que cualquiera de
      las dos por separado (coeficiente de variacion anual 0.91 vs 1.34 de
      Insurance y 0.99 de Guarantee) - justamente por el efecto de que se
      turnan. Se prioriza tener una serie utilizable para el indice sobre
      preservar la distincion Insurance/Guarantee, aunque esa distincion sea
      real. Si en el futuro se necesita esa distincion (ej. para leer la
      composicion del compromiso de EXIM, no para el indice en si), estos
      numeros de referencia ya estan calculados y no hace falta repetir el
      piloto.
    - bid_proyectos / bancomundial_proyectos (JSON diario, ya filtrado a
      Paraguay - se usa el archivo mas reciente subido por ingestion): se
      suma el monto aprobado de cada proyecto por trimestre segun su fecha
      de aprobacion (`apprvl_dt` en BID, `boardapprovaldate` en Banco
      Mundial). **Es el monto total aprobado del proyecto, NO ponderado
      por la cuota de capital de EE.UU. en cada banco** - ese calculo
      queda pendiente (ver CLAUDE.md seccion 7), esta columna es un
      proxy de "actividad multilateral" en general, no una cifra
      atribuible a EE.UU. todavia.

Rango: ANIO_MINIMO en adelante. Cada variable se sube por separado, con la
fecha de la corrida en el nombre (idempotente por dia) - no escribe nada a
disco local.
"""
import io
import json
import zipfile

import pandas as pd

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos
from src.processing._common import subir_variable

DIMENSION_CRUDA = "1_Compromiso_financiero_oficial"
DIMENSION_LIMPIA = "1_Compromiso_financiero_oficial_limpias"

ANIO_MINIMO = 2015


def _archivos(fuente):
    return listar_archivos(FOLDER_IDS[(DIMENSION_CRUDA, fuente)])


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
    los 4 trimestres (para fuentes sin fecha mas fina que el año)."""
    return {(anio, trim): valor for anio, valor in valores_por_anio.items() for trim in (1, 2, 3, 4)}


def _extraer_fa_gov():
    """Devuelve (obligaciones, desembolsos), cada una {(anio,trim): usd}
    repitiendo el total anual en los 4 trimestres (ver docstring)."""
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

    return _repetir_en_trimestres(totales["Obligations"]), _repetir_en_trimestres(totales["Disbursements"])


def _extraer_usaspending():
    """Devuelve {(anio,trim): usd} sumando `federal_action_obligation` de
    las transacciones (Contracts + Assistance) por trimestre de `action_date`."""
    acumulado = {}
    for archivo in _archivos("usaspending_obligaciones"):
        contenido = descargar_archivo(archivo["id"])
        z = zipfile.ZipFile(io.BytesIO(contenido))
        for nombre in z.namelist():
            if "PrimeTransactions" not in nombre:
                continue
            df = pd.read_csv(z.open(nombre), usecols=["action_date", "federal_action_obligation"])
            parcial = _sumar_por_trimestre(df["action_date"], df["federal_action_obligation"])
            for clave, valor in parcial.items():
                acumulado[clave] = acumulado.get(clave, 0.0) + valor
    return acumulado


def _extraer_dfc():
    """Devuelve {(anio,trim): usd} sumando `Committed` de proyectos de
    Paraguay por `Fiscal Year`, repitiendo el total en los 4 trimestres
    (ver docstring - muy pocos proyectos, sin fecha mas fina que el año)."""
    _, contenido = _archivo_mas_reciente_por_nombre("dfc_proyectos_activos")
    df = pd.read_excel(io.BytesIO(contenido), sheet_name="Project Data", header=1)
    py = df[df["Country"] == "Paraguay"]
    por_anio = py.groupby("Fiscal Year")["Committed"].sum()
    por_anio = por_anio[por_anio.index >= ANIO_MINIMO]
    return _repetir_en_trimestres(por_anio.to_dict())


def _extraer_exim():
    """Devuelve (autorizado, desembolsado), cada una {(anio,trim): usd},
    sumando `Approved/Declined Amount` y `Disbursed/Shipped Amount` de
    autorizaciones con `Decision == "Approved"`, por trimestre de
    `Decision Date` - ver el docstring del modulo para el piloto que
    decidio no separar por Program (Insurance/Guarantee)."""
    _, contenido = _archivo_mas_reciente_por_nombre("exim_autorizaciones")
    df = pd.read_csv(io.BytesIO(contenido))
    aprobadas = df[df["Decision"] == "Approved"]
    autorizado = _sumar_por_trimestre(aprobadas["Decision Date"], aprobadas["Approved/Declined Amount"])
    desembolsado = _sumar_por_trimestre(aprobadas["Decision Date"], aprobadas["Disbursed/Shipped Amount"])
    return autorizado, desembolsado


def _extraer_bid():
    """Devuelve {(anio,trim): usd} sumando el monto originalmente aprobado
    de cada proyecto (`orig_apprvd_useq_amnt`) por trimestre de `apprvl_dt`.
    NO esta ponderado por la cuota de capital de EE.UU. (ver docstring)."""
    _, contenido = _archivo_mas_reciente_por_nombre("bid_proyectos")
    registros = json.loads(contenido)["records"]
    df = pd.DataFrame(registros)
    return _sumar_por_trimestre(df["apprvl_dt"], df["orig_apprvd_useq_amnt"])


def _extraer_bancomundial():
    """Devuelve {(anio,trim): usd} sumando el monto total del proyecto
    (`totalamt`) por trimestre de `boardapprovaldate`. NO esta ponderado
    por la cuota de capital de EE.UU. (ver docstring)."""
    _, contenido = _archivo_mas_reciente_por_nombre("bancomundial_proyectos")
    proyectos = json.loads(contenido)["projects"].values()
    df = pd.DataFrame(proyectos)
    return _sumar_por_trimestre(df["boardapprovaldate"], df["totalamt"])


def _archivo_mas_reciente_por_nombre(fuente):
    archivos = _archivos(fuente)
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    return archivo["name"], descargar_archivo(archivo["id"])


def run():
    print(f"[{DIMENSION_LIMPIA}]")
    fuentes = []

    try:
        obligaciones_fa, desembolsos_fa = _extraer_fa_gov()
        fuentes.append(("fa_gov_obligaciones", obligaciones_fa))
        fuentes.append(("fa_gov_desembolsos", desembolsos_fa))
    except Exception as exc:  # noqa: BLE001
        print(f"    [!] fa_gov_asistencia_oficial: {exc!r}")

    try:
        autorizado_exim, desembolsado_exim = _extraer_exim()
        fuentes.append(("exim_autorizado", autorizado_exim))
        fuentes.append(("exim_desembolsado", desembolsado_exim))
    except Exception as exc:  # noqa: BLE001
        print(f"    [!] exim_autorizaciones: {exc!r}")

    for nombre_variable, extraer in (
        ("usaspending_obligaciones", _extraer_usaspending),
        ("dfc_comprometido", _extraer_dfc),
        ("bid_proyectos_aprobados", _extraer_bid),
        ("bancomundial_proyectos_aprobados", _extraer_bancomundial),
    ):
        try:
            fuentes.append((nombre_variable, extraer()))
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] {nombre_variable}: {exc!r}")

    # todas estas fuentes ya vienen nativamente en USD (no miles/millones),
    # a diferencia de la dimension 3 - no hace falta reescalar
    for nombre_variable, valores in fuentes:
        subir_variable(DIMENSION_LIMPIA, nombre_variable, valores, "USD")


if __name__ == "__main__":
    run()
