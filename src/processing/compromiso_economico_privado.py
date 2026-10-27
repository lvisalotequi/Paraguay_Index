#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 02/09/2026                                                #
# NOMBRE: compromiso_economico_privado                                         #
# DETALLE: lleva a trimestres las 5 fuentes de la dimension 3 y deja 6         #
#   variables: exportaciones, importaciones, inversion directa del BCP,        #
#   remesas y posicion de inversion de BEA (todas en USD sin escalar) y        #
#   turismo receptivo del INE (cantidad). NO consulta ninguna API: lee solo    #
#   los crudos de Drive.                                                       #
#                                                                              #
# CORRE DESPUES DE: ingestion de bcp_comercio_exterior, bcp_inversion_directa, #
#   bcp_remesas_familiares, bea_inversion_directa e ine_turismo_receptivo      #
#   (src/ingestion/)                                                           #
# SALIDA: un CSV por variable (6) en                                           #
#   02_limpias/3_Compromiso_economico_privado_limpias/<variable>/              #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import json
import re
import unicodedata

import pandas as pd

from src.drive import descargar_archivo, listar_archivos, resolve_ingestion_folder
from src.processing._common import reescalar, subir_variable



# Parametros -------------------------------------------------------------------

# Carpetas de Drive: las crudas las escribe ingestion y las limpias este modulo.
DIMENSION_CRUDA  = "3_Compromiso_economico_privado"
DIMENSION_LIMPIA = "3_Compromiso_economico_privado_limpias"

ANIO_MINIMO = 2015

NUMERO_TRIM = {"I": 1, "II": 2, "III": 3, "IV": 4}
MESES_A_TRIM = {
    "Ene": 1, "Feb": 1, "Mar": 1,
    "Abr": 2, "May": 2, "Jun": 2,
    "Jul": 3, "Ago": 3, "Set": 3, "Sep": 3,
    "Oct": 4, "Nov": 4, "Dic": 4,
}

PATRON_BOLETIN_TRIM = re.compile(r"(\d)_?trim_?(\d{4})", re.IGNORECASE)



# Funciones auxiliares ---------------------------------------------------------

# A diferencia de src/ingestion/ (que solo extrae y sube los crudos sin leerlos), este
# modulo SI lee los crudos que ingestion ya subio a Drive, aisla la cifra de EE.UU. de
# cada fuente, arma trimestres a partir del formato nativo de cada una y sube un CSV
# por variable (esquema fijo, ver src/processing/_common.py).
#
# POR QUE TODO EN USD SIN ESCALAR (politica 2026-09-03, a pedido del usuario): las 5
# variables monetarias quedan en la misma unidad entre si aunque la fuente venga en
# miles o millones. Los extractores devuelven el valor tal como viene en el archivo
# crudo, para que cada uno siga describiendo la unidad real de su fuente; el reescalado
# a USD pasa en run(), justo antes de subir cada variable, con reescalar().
#
# De cada fuente se usa el archivo mas reciente que subio ingestion. Cada variable se
# sube por separado, con la fecha de la corrida en el nombre (idempotente por dia).


def _clave_boletin(archivo):
    """Orden cronologico real de un boletin del BCP ("..._al_2_Trim_2026.xlsx"):
    (anio, trimestre). El orden alfabetico por nombre elegia mal (4_Trim_2025
    quedaba por encima de 1_Trim_2026). Sin patron reconocible va al final de
    la fila (0, 0, nombre)."""
    match = PATRON_BOLETIN_TRIM.search(archivo["name"])
    if not match:
        return (0, 0, archivo["name"])
    return (int(match.group(2)), int(match.group(1)), archivo["name"])


def _archivo_mas_reciente(dimension, fuente, prefijo_nombre=None, clave=None):
    """Devuelve (nombre, bytes) del archivo mas reciente (por nombre, orden
    alfabetico - sirve para nombres con fecha ISO como los de bea) de una
    carpeta de ingestion. Si prefijo_nombre esta dado, filtra primero por
    archivos cuyo nombre empiece con ese prefijo (case-insensitive) - para
    carpetas que tienen archivos de mas de un formato/fuente historica."""
    carpeta_id = resolve_ingestion_folder(dimension, fuente)
    archivos = listar_archivos(carpeta_id)
    if prefijo_nombre:
        archivos = [a for a in archivos if a["name"].lower().startswith(prefijo_nombre.lower())]
    if not archivos:
        raise RuntimeError(f"No hay archivos en {dimension}/{fuente} (prefijo={prefijo_nombre!r})")
    archivo = sorted(archivos, key=clave or (lambda a: a["name"]))[-1]
    return archivo["name"], descargar_archivo(archivo["id"])


def _mapear_columnas_trimestre(fila_anio, fila_trim):
    """A partir de la fila de anios (con huecos - solo la primera columna de
    cada anio esta poblada, hay que rellenar hacia adelante) y la fila de
    trimestres (I/II/III/IV, vacia en las columnas de TOTAL anual), arma
    {(anio, trimestre): columna}."""
    anios = fila_anio.ffill()
    mapeo = {}
    for col, trim in fila_trim.items():
        if trim == "l":  # typo real del BCP: el trimestre "I" viene tipeado
            trim = "I"   # como una ele minuscula en varios anios (ej. 2015, 2016)
        if trim not in NUMERO_TRIM or pd.isna(anios[col]):
            continue
        # el rotulo del anio no siempre es el numero solo - la hoja de
        # importaciones antepone "Anio " (ej. "Anio 1961") y los anios
        # recientes vienen marcados como preliminares (ej. "2025*")
        match_anio = re.search(r"(\d{4})", str(anios[col]))
        if not match_anio:
            continue
        mapeo[(int(match_anio.group(1)), NUMERO_TRIM[trim])] = col
    return mapeo


def _sin_acentos(texto):
    """Quita tildes/diacriticos para comparar nombres de pais sin depender
    de que el BCP los escriba siempre igual (ej. 'America' vs 'América')."""
    return (
        unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").strip().upper()
    )


def _extraer_fila_pais_trimestral(df, fila_anio_idx, fila_trim_idx, fila_pais):
    """Extrae {(anio, trimestre): valor} de una hoja con el patron BCP de
    encabezado (fila de anios + fila de trimestres arriba de los datos) y
    la columna 0 con el nombre del pais/producto."""

    # 1. mapea cada (anio, trimestre) a su columna
    mapeo_cols = _mapear_columnas_trimestre(df.iloc[fila_anio_idx], df.iloc[fila_trim_idx])

    # 2. ubica la fila del pais, comparando sin tildes
    nombres = df[0].astype(str).map(_sin_acentos)
    idx = nombres[nombres == _sin_acentos(fila_pais)].index
    if len(idx) == 0:
        raise RuntimeError(f"No se encontro la fila {fila_pais!r} (columna 0)")
    fila = df.iloc[idx[0]]

    # 3. toma el valor de cada trimestre desde ANIO_MINIMO, sin los vacios
    return {
        clave: fila[col]
        for clave, col in mapeo_cols.items()
        if clave[0] >= ANIO_MINIMO and pd.notna(fila[col])
    }



# Comercio exterior (BCP) ------------------------------------------------------

# Entrada: el Boletin de Comercio Exterior del BCP (bcp_comercio_exterior), un unico
# Excel con la serie completa. Las hojas "Exp. por paises" e "Imp. por paises" ya traen
# el desglose TRIMESTRAL desde 1994.
#
# Salida: exportaciones e importaciones, de la fila "Estados Unidos de America". Nativo
# en miles de USD FOB; run() las lleva a USD.


def _extraer_comercio_exterior():
    """Devuelve (exportaciones, importaciones), cada una {(anio,trim): valor
    nativo en miles de USD FOB - el reescalado a USD pasa en run()}."""

    # 1. toma el boletin mas reciente por (anio, trimestre) del nombre, no alfabetico
    _, contenido = _archivo_mas_reciente(
        DIMENSION_CRUDA, "bcp_comercio_exterior", prefijo_nombre="boletin", clave=_clave_boletin
    )
    xls = pd.ExcelFile(io.BytesIO(contenido))

    # 2. extrae la fila de EE.UU. de cada hoja
    exportaciones = _extraer_fila_pais_trimestral(
        xls.parse("Exp. por países", header=None), fila_anio_idx=4, fila_trim_idx=6,
        fila_pais="Estados Unidos de América",
    )
    importaciones = _extraer_fila_pais_trimestral(
        xls.parse("Imp. por países", header=None), fila_anio_idx=4, fila_trim_idx=6,
        fila_pais="Estados Unidos de América",
    )
    return exportaciones, importaciones



# Inversion directa (BCP) ------------------------------------------------------

# Entrada: el Anexo Estadistico del BCP (bcp_inversion_directa), "Cuadro 4. Flujos de
# Inversion Directa por residencia del inversionista", ya TRIMESTRAL.
#
# Salida: inversion_directa_bcp, de la fila "ESTADOS UNIDOS". Nativo en USD, no en
# miles: el propio archivo lo aclara en el titulo del cuadro.
#
# HUECO REAL Y A PROPOSITO EN 2025 (validado el 2026-09-21): el anexo mas reciente
# ("Anexo_estadistico...1995_-_2024.xlsx", publicado el 2025-10-23) llega solo hasta
# 2024. El BCP publica el desglose por pais (Cuadro 4) en octubre del anio siguiente,
# una vez validada la informacion de empresas no financieras (nota tecnica del
# 2025-07-25). El dato de 2025 deberia estar en octubre de 2026, y la funcion ya esta
# lista para recogerlo sola: toma siempre el archivo mas reciente de Drive, asi que basta
# con correr src/ingestion/bcp_inversion_directa.py y despues este modulo, sin tocar
# codigo.
#
# POR QUE 2025 NO SE PROYECTA: se probaron 3 metodos contra los valores YA CONOCIDOS de
# 2023 y 2024 (backtest): tendencia de crecimiento interanual, % historico de EE.UU.
# sobre el total de Paraguay (incluido un 12,5% fijo) y el delta interanual de la
# posicion de EE.UU. que reporta BEA (bea_inversion_directa, que si tiene 2025). Los tres
# fallaron por completo, con un error de entre 400% y 4200%: el flujo de EE.UU. es chico
# y de signo variable (lo dominan eventos puntuales de una sola empresa, como una
# repatriacion de capital, no una tendencia), y los tres metodos asumen un resultado
# positivo. Se descarto proyectar y se deja 2025 como falta real hasta que el BCP
# publique el dato: un hueco visible es mejor que un numero con un error esperado de
# varios cientos por ciento.


def _extraer_inversion_directa_bcp():
    """Devuelve {(anio,trim): usd} de flujos de IED de EE.UU. hacia Paraguay (BCP)."""
    _, contenido = _archivo_mas_reciente(DIMENSION_CRUDA, "bcp_inversion_directa")
    xls = pd.ExcelFile(io.BytesIO(contenido))
    df = xls.parse("Cuadro 4", header=None)
    return _extraer_fila_pais_trimestral(df, fila_anio_idx=9, fila_trim_idx=10, fila_pais="ESTADOS UNIDOS")



# Remesas familiares (BCP) -----------------------------------------------------

# Entrada: el Excel unico de remesas familiares del BCP (bcp_remesas_familiares), con
# desglose MENSUAL.
#
# Salida: remesas, de la columna "EE.UU." (dentro de "America del Norte"), sumando los 3
# meses de cada trimestre. Nativo en miles de USD; run() las lleva a USD.


def _extraer_remesas():
    """Devuelve {(anio,trim): valor nativo en miles de USD} sumando los 3
    meses de cada trimestre - el reescalado a USD pasa en run()."""

    # 1. lee la hoja del Excel mas reciente
    _, contenido = _archivo_mas_reciente(DIMENSION_CRUDA, "bcp_remesas_familiares")
    df = pd.read_excel(io.BytesIO(contenido), header=None, sheet_name="Hoja1")

    # 2. recorre las filas: cada anio abre un bloque y cada mes suma a su trimestre
    col_eeuu = 5  # fila 9 ('America del Norte') / fila 10 ('EE.UU.'), ver el comentario de la seccion
    acumulado = {}
    anio_actual = None
    for i in range(11, len(df)):
        etiqueta = df.iat[i, 0]
        if pd.isna(etiqueta):
            continue
        etiqueta = str(etiqueta).strip()

        match_anio = re.match(r"^(\d{4})\b", etiqueta)
        if match_anio:
            anio_actual = int(match_anio.group(1))
            continue  # fila de TOTAL anual, no un mes - no sumar (evitar duplicar)

        trimestre = MESES_A_TRIM.get(etiqueta[:3])
        valor = df.iat[i, col_eeuu]
        if trimestre is None or anio_actual is None or pd.isna(valor):
            continue
        if anio_actual < ANIO_MINIMO:
            continue

        clave = (anio_actual, trimestre)
        acumulado[clave] = acumulado.get(clave, 0.0) + float(valor)

    return acumulado



# Inversion directa (BEA) ------------------------------------------------------

# Entrada: el JSON diario de la API de BEA (bea_inversion_directa), serie ANUAL: la API
# no ofrece corte trimestral por pais (ver el modulo de ingestion). Se usa el archivo
# diario mas reciente.
#
# Salida: bea_inversion_directa, de la serie "U.S. Direct Investment Position Abroad on a
# Historical-Cost Basis". Nativo en millones de USD; run() la lleva a USD.
#
# POR QUE EL MISMO VALOR EN LOS 4 TRIMESTRES: el valor anual se repite en cada trimestre
# de ese anio. NO es una medicion trimestral real: la fuente simplemente no tiene ese
# detalle.


def _extraer_bea_posicion():
    """Devuelve {(anio,trim): valor nativo en millones de USD} repitiendo el
    valor ANUAL de BEA en los 4 trimestres de ese anio (ver el comentario de
    la seccion - no hay corte trimestral por pais en esta fuente). El
    reescalado a USD pasa en run()."""

    # 1. lee el JSON mas reciente
    _, contenido = _archivo_mas_reciente(DIMENSION_CRUDA, "bea_inversion_directa")
    data = json.loads(contenido)
    filas = data["BEAAPI"]["Results"]["Data"]

    # 2. se queda con la serie de posicion y los anios desde ANIO_MINIMO
    serie = "U.S. Direct Investment Position Abroad on a Historical-Cost Basis"
    valores_por_anio = {}
    for fila in filas:
        if fila["SeriesName"] != serie:
            continue
        valor_bruto = fila["DataValue"]
        if valor_bruto in ("(D)", "(*)", "(NA)", ""):
            continue  # dato suprimido por confidencialidad (BEA) o no disponible
        anio = int(fila["Year"])
        if anio < ANIO_MINIMO:
            continue
        valores_por_anio[anio] = float(valor_bruto.replace(",", ""))

    # 3. repite el valor anual en los 4 trimestres
    resultado = {}
    for anio, valor in valores_por_anio.items():
        for trim in (1, 2, 3, 4):
            resultado[(anio, trim)] = valor
    return resultado



# Turismo receptivo (INE) ------------------------------------------------------

# Entrada: un unico Excel del INE (ine_turismo_receptivo), una fila por anio con el total
# y los 12 meses de turistas de EE.UU. que ingresaron a Paraguay (ver
# src/ingestion/ine_turismo_receptivo.py).
#
# Salida: turismo_receptivo_eeuu, sumando los 3 meses de cada trimestre. Es tipo
# "cantidad": no es monetario y no se reescala.
#
# POR QUE 2016 SE ESTIMA Y COMO: 2016 no existe en la fuente original (investigado a
# fondo, ver el docstring de ingestion). Se completa con un PROMEDIO ARITMETICO SIMPLE,
# mes a mes, de 2015 y 2017 (_estimar_2016_turismo). Decision tomada con datos reales el
# 2026-09-28: se comparo contra la media geometrica mes a mes (raiz de 2015 por 2017) y la
# diferencia es minima (0,79% en el total anual). Ademas se corrio un backtest con las 6
# tripletas de anios consecutivos ya conocidos (2017-2018-2019, ..., 2022-2023-2024). En
# la unica tripleta realmente comparable, sin shock externo (2017+2019 para 2018), el
# resultado es casi un empate, pero en las 5 que tocan la caida de COVID-19 el aritmetico
# fue consistentemente mas robusto: la media geometrica es muy sensible a los meses con
# valores muy bajos o en cero, que sobran en 2020-2021. Se eligio el aritmetico por ser
# igual de bueno en el caso limpio y mas robusto en general.
#
# LIMITE: es una estimacion, no un dato real. El esquema fijo de 02_limpias (trimestre,
# anio, trimestre_num, valor, unidad) no tiene lugar para marcarlo, asi que queda
# documentado aca y en DICCIONARIO_VARIABLES.md, no en el dato mismo.

MESES_ORDEN = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]


def _estimar_2016_turismo(serie_por_anio):
    """Devuelve los 12 valores mensuales de 2016 - promedio aritmetico
    simple, mes a mes, de 2015 y 2017. Ver el comentario de la seccion para
    la justificacion completa (comparacion contra la media geometrica +
    backtest con datos reales, 2026-09-28)."""
    meses_2015 = serie_por_anio[2015]
    meses_2017 = serie_por_anio[2017]
    return [(a + b) / 2 for a, b in zip(meses_2015, meses_2017)]


def _extraer_turismo_receptivo():
    """Devuelve {(anio,trim): cantidad} de turistas de EE.UU. que
    ingresaron a Paraguay, sumando los 3 meses de cada trimestre. Incluye
    2016 estimado (ver `_estimar_2016_turismo()` y el comentario de la
    seccion)."""

    # 1. lee el Excel mas reciente y arma la serie mensual de cada anio, con 2016 estimado
    _, contenido = _archivo_mas_reciente(DIMENSION_CRUDA, "ine_turismo_receptivo")
    df = pd.read_excel(io.BytesIO(contenido))

    serie_por_anio = {int(fila["anio"]): [fila[m] for m in MESES_ORDEN] for _, fila in df.iterrows()}
    serie_por_anio[2016] = _estimar_2016_turismo(serie_por_anio)

    # 2. suma los 3 meses de cada trimestre, desde ANIO_MINIMO
    resultado = {}
    for anio, meses in serie_por_anio.items():
        if anio < ANIO_MINIMO:
            continue
        for trim in (1, 2, 3, 4):
            valores_trim = meses[(trim - 1) * 3: trim * 3]
            resultado[(anio, trim)] = sum(valores_trim)
    return resultado



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. avisa que dimension procesa
    print(f"[{DIMENSION_LIMPIA}]")
    errores = []

    # 2. comercio exterior: exportaciones e importaciones, de miles de USD a USD;
    # una fuente que falla no frena a las otras
    try:
        exportaciones, importaciones = _extraer_comercio_exterior()
        subir_variable(DIMENSION_LIMPIA, "exportaciones", reescalar(exportaciones, 1_000), "USD")
        subir_variable(DIMENSION_LIMPIA, "importaciones", reescalar(importaciones, 1_000), "USD")
    except Exception as exc:  # noqa: BLE001
        errores.append(("comercio_exterior", repr(exc)))
        print(f"    [!] comercio_exterior: {exc!r}")

    # 3. inversion directa del BCP: ya viene en USD
    try:
        subir_variable(DIMENSION_LIMPIA, "inversion_directa_bcp", _extraer_inversion_directa_bcp(), "USD")
    except Exception as exc:  # noqa: BLE001
        errores.append(("inversion_directa_bcp", repr(exc)))
        print(f"    [!] inversion_directa_bcp: {exc!r}")

    # 4. remesas: de miles de USD a USD
    try:
        subir_variable(DIMENSION_LIMPIA, "remesas", reescalar(_extraer_remesas(), 1_000), "USD")
    except Exception as exc:  # noqa: BLE001
        errores.append(("remesas", repr(exc)))
        print(f"    [!] remesas: {exc!r}")

    # 5. posicion de inversion directa de BEA: de millones de USD a USD
    try:
        subir_variable(
            DIMENSION_LIMPIA, "bea_inversion_directa", reescalar(_extraer_bea_posicion(), 1_000_000), "USD"
        )
    except Exception as exc:  # noqa: BLE001
        errores.append(("bea_inversion_directa", repr(exc)))
        print(f"    [!] bea_inversion_directa: {exc!r}")

    # 6. turismo receptivo: es una cantidad, no se reescala
    try:
        subir_variable(DIMENSION_LIMPIA, "turismo_receptivo_eeuu", _extraer_turismo_receptivo(), "cantidad")
    except Exception as exc:  # noqa: BLE001
        errores.append(("turismo_receptivo_eeuu", repr(exc)))
        print(f"    [!] turismo_receptivo_eeuu: {exc!r}")

    # 7. validacion: se intentaron todas las variables y se subieron las que salieron bien;
    # recien ahora se avisa del resto, para que la corrida quede en rojo y no figure como
    # OK con variables sin actualizar
    if errores:
        raise RuntimeError(f"Fallaron {len(errores)} fuentes de {DIMENSION_LIMPIA}: {errores}")


if __name__ == "__main__":
    run()
