"""
Limpieza/consolidacion de la dimension 3 (Compromiso economico privado) en
un CSV trimestral por variable.

A diferencia de src/ingestion/ (que SOLO extrae y sube archivos crudos tal
cual, sin leerlos ni transformarlos), este modulo SI lee los archivos
crudos que ingestion ya subio a Drive (01_crudas/3_Compromiso_economico_privado/),
aisla la cifra especifica de EE.UU. de cada fuente, arma trimestres a
partir del formato nativo de cada una, y sube un CSV independiente por
variable (esquema fijo: trimestre, anio, trimestre_num, valor, unidad) a
02_limpias/3_Compromiso_economico_privado_limpias/{variable}/ - ver
src/processing/_common.py para el detalle de esta convencion, compartida
por las 4 dimensiones.

Fuentes y como se tratan (confirmado con datos reales el 2026-09-02):
    - bcp_comercio_exterior (Boletin Comercio Exterior, un unico Excel con
      la serie completa; hojas "Exp. por paises" e "Imp. por paises", ya
      con desglose TRIMESTRAL desde 1994): se toma la fila
      "Estados Unidos de America". Nativo en miles de USD FOB.
    - bcp_inversion_directa (Anexo Estadistico; "Cuadro 4. Flujos de
      Inversion Directa por residencia del inversionista", ya TRIMESTRAL):
      se toma la fila "ESTADOS UNIDOS". Nativo en USD (no miles - el
      propio archivo lo aclara en el titulo del cuadro).
    - bcp_remesas_familiares (Excel unico, desglose MENSUAL): se toma la
      columna "EE.UU." (dentro de "America del Norte") y se suman los 3
      meses de cada trimestre. Nativo en miles de USD.
    - bea_inversion_directa (JSON diario de la API de BEA, serie ANUAL -
      la API no ofrece corte trimestral por pais, ver el modulo de
      ingestion): se toma la serie "U.S. Direct Investment Position Abroad
      on a Historical-Cost Basis". El mismo valor anual se repite en los 4
      trimestres de ese anio - NO es una medicion trimestral real, esta
      fuente simplemente no tiene ese detalle disponible. Nativo en
      millones de USD. Se usa el archivo diario mas reciente subido por
      ingestion.

**Unidades (politica 2026-09-03, a pedido del usuario):** todas las
variables monetarias se suben en USD sin escalar, aunque la fuente nativa
venga en miles o millones - las 5 quedan en la misma unidad entre si. Los
extractores devuelven el valor tal como viene de la fuente (sin reescalar,
para que el docstring de cada uno siga describiendo la unidad real del
archivo crudo); el reescalado a USD pasa en `run()`, justo antes de subir
cada variable con `reescalar()` (ver src/processing/_common.py).

Rango: ANIO_MINIMO en adelante (mismo piso que el resto del proyecto).
Cada variable se sube por separado, con la fecha de la corrida en el
nombre (idempotente por dia) - no escribe nada a disco local.
"""
import io
import json
import re
import unicodedata

import pandas as pd

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos
from src.processing._common import reescalar, subir_variable

DIMENSION_CRUDA = "3_Compromiso_economico_privado"
DIMENSION_LIMPIA = "3_Compromiso_economico_privado_limpias"

ANIO_MINIMO = 2015

NUMERO_TRIM = {"I": 1, "II": 2, "III": 3, "IV": 4}
MESES_A_TRIM = {
    "Ene": 1, "Feb": 1, "Mar": 1,
    "Abr": 2, "May": 2, "Jun": 2,
    "Jul": 3, "Ago": 3, "Set": 3, "Sep": 3,
    "Oct": 4, "Nov": 4, "Dic": 4,
}


def _archivo_mas_reciente(dimension, fuente, prefijo_nombre=None):
    """Devuelve (nombre, bytes) del archivo mas reciente (por nombre, orden
    alfabetico - sirve para nombres con fecha ISO como los de bea) de una
    carpeta de ingestion. Si prefijo_nombre esta dado, filtra primero por
    archivos cuyo nombre empiece con ese prefijo (case-insensitive) - para
    carpetas que tienen archivos de mas de un formato/fuente historica."""
    carpeta_id = FOLDER_IDS[(dimension, fuente)]
    archivos = listar_archivos(carpeta_id)
    if prefijo_nombre:
        archivos = [a for a in archivos if a["name"].lower().startswith(prefijo_nombre.lower())]
    if not archivos:
        raise RuntimeError(f"No hay archivos en {dimension}/{fuente} (prefijo={prefijo_nombre!r})")
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    return archivo["name"], descargar_archivo(archivo["id"])


def _mapear_columnas_trimestre(fila_anio, fila_trim):
    """A partir de la fila de anios (con huecos - solo la primera columna de
    cada anio esta poblada, hay que rellenar hacia adelante) y la fila de
    trimestres (I/II/III/IV, vacia en las columnas de TOTAL anual), arma
    {(anio, trimestre): columna}."""
    anios = fila_anio.ffill()
    mapeo = {}
    for col, trim in fila_trim.items():
        if trim not in NUMERO_TRIM or pd.isna(anios[col]):
            continue
        # el rotulo del anio no siempre es el numero solo - la hoja de
        # importaciones antepone "Año " (ej. "Año 1961") y los anios
        # recientes vienen marcados como preliminares (ej. "2025*")
        match_anio = re.search(r"(\d{4})", str(anios[col]))
        if not match_anio:
            continue
        mapeo[(int(match_anio.group(1)), NUMERO_TRIM[trim])] = col
    return mapeo


def _sin_acentos(texto):
    """Quita tildes/diacriticos para comparar nombres de pais sin depender
    de que el BCP los escriba siempre igual (ej. 'America' vs 'América')."""
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").strip().upper()


def _extraer_fila_pais_trimestral(df, fila_anio_idx, fila_trim_idx, fila_pais):
    """Extrae {(anio, trimestre): valor} de una hoja con el patron BCP de
    encabezado (fila de anios + fila de trimestres arriba de los datos) y
    la columna 0 con el nombre del pais/producto."""
    mapeo_cols = _mapear_columnas_trimestre(df.iloc[fila_anio_idx], df.iloc[fila_trim_idx])
    nombres = df[0].astype(str).map(_sin_acentos)
    idx = nombres[nombres == _sin_acentos(fila_pais)].index
    if len(idx) == 0:
        raise RuntimeError(f"No se encontro la fila {fila_pais!r} (columna 0)")
    fila = df.iloc[idx[0]]

    return {
        clave: fila[col]
        for clave, col in mapeo_cols.items()
        if clave[0] >= ANIO_MINIMO and pd.notna(fila[col])
    }


def _extraer_comercio_exterior():
    """Devuelve (exportaciones, importaciones), cada una {(anio,trim): valor
    nativo en miles de USD FOB - el reescalado a USD pasa en _armar_tabla}."""
    _, contenido = _archivo_mas_reciente(DIMENSION_CRUDA, "bcp_comercio_exterior", prefijo_nombre="boletin")
    xls = pd.ExcelFile(io.BytesIO(contenido))

    exportaciones = _extraer_fila_pais_trimestral(
        xls.parse("Exp. por países", header=None), fila_anio_idx=4, fila_trim_idx=6,
        fila_pais="Estados Unidos de América",
    )
    importaciones = _extraer_fila_pais_trimestral(
        xls.parse("Imp. por países", header=None), fila_anio_idx=4, fila_trim_idx=6,
        fila_pais="Estados Unidos de América",
    )
    return exportaciones, importaciones


def _extraer_inversion_directa_bcp():
    """Devuelve {(anio,trim): usd} de flujos de IED de EE.UU. hacia Paraguay (BCP)."""
    _, contenido = _archivo_mas_reciente(DIMENSION_CRUDA, "bcp_inversion_directa")
    xls = pd.ExcelFile(io.BytesIO(contenido))
    df = xls.parse("Cuadro 4", header=None)
    return _extraer_fila_pais_trimestral(df, fila_anio_idx=9, fila_trim_idx=10, fila_pais="ESTADOS UNIDOS")


def _extraer_remesas():
    """Devuelve {(anio,trim): valor nativo en miles de USD} sumando los 3
    meses de cada trimestre - el reescalado a USD pasa en _armar_tabla."""
    _, contenido = _archivo_mas_reciente(DIMENSION_CRUDA, "bcp_remesas_familiares")
    df = pd.read_excel(io.BytesIO(contenido), header=None, sheet_name="Hoja1")

    col_eeuu = 5  # fila 9 ('América del Norte') / fila 10 ('EE.UU.') - ver docstring
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


def _extraer_bea_posicion():
    """Devuelve {(anio,trim): valor nativo en millones de USD} repitiendo el
    valor ANUAL de BEA en los 4 trimestres de ese anio (ver docstring - no
    hay corte trimestral por pais en esta fuente). El reescalado a USD pasa
    en _armar_tabla."""
    _, contenido = _archivo_mas_reciente(DIMENSION_CRUDA, "bea_inversion_directa")
    data = json.loads(contenido)
    filas = data["BEAAPI"]["Results"]["Data"]

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

    resultado = {}
    for anio, valor in valores_por_anio.items():
        for trim in (1, 2, 3, 4):
            resultado[(anio, trim)] = valor
    return resultado


def run():
    print(f"[{DIMENSION_LIMPIA}]")
    errores = []

    try:
        exportaciones, importaciones = _extraer_comercio_exterior()
        subir_variable(DIMENSION_LIMPIA, "exportaciones", reescalar(exportaciones, 1_000), "USD")
        subir_variable(DIMENSION_LIMPIA, "importaciones", reescalar(importaciones, 1_000), "USD")
    except Exception as exc:  # noqa: BLE001
        errores.append(("comercio_exterior", repr(exc)))
        print(f"    [!] comercio_exterior: {exc!r}")

    try:
        subir_variable(DIMENSION_LIMPIA, "inversion_directa_bcp", _extraer_inversion_directa_bcp(), "USD")
    except Exception as exc:  # noqa: BLE001
        errores.append(("inversion_directa_bcp", repr(exc)))
        print(f"    [!] inversion_directa_bcp: {exc!r}")

    try:
        subir_variable(DIMENSION_LIMPIA, "remesas", reescalar(_extraer_remesas(), 1_000), "USD")
    except Exception as exc:  # noqa: BLE001
        errores.append(("remesas", repr(exc)))
        print(f"    [!] remesas: {exc!r}")

    try:
        subir_variable(DIMENSION_LIMPIA, "bea_inversion_directa", reescalar(_extraer_bea_posicion(), 1_000_000), "USD")
    except Exception as exc:  # noqa: BLE001
        errores.append(("bea_inversion_directa", repr(exc)))
        print(f"    [!] bea_inversion_directa: {exc!r}")

    if errores and len(errores) == 4:
        raise RuntimeError(f"Fallaron todas las fuentes de {DIMENSION_LIMPIA}: {errores}")


if __name__ == "__main__":
    run()
