#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 03/09/2026                                                #
# NOMBRE: visibilidad_mediatica_y_relevancia_publica                           #
# DETALLE: lleva a trimestres las dos fuentes de la dimension 4: GDELT proxy B #
#   (articulos y tono ponderado, en 3 variantes BOTH/PY/US) y Google Trends    #
#   (promedio trimestral de 3 terminos fijos). NO consulta ninguna API: lee    #
#   solo los crudos de Drive.                                                  #
#                                                                              #
# CORRE DESPUES DE: ingestion de gdelt_proxy_b y google_trends_paraguay        #
#   (src/ingestion/)                                                           #
# SALIDA: un CSV por variable (9) en                                           #
#   02_limpias/4_Visibilidad_mediatica_y_relevancia_publica_limpias/<variable> #
#   /                                                                          #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io

import pandas as pd

from src.drive import descargar_archivo, listar_archivos, resolve_ingestion_folder
from src.processing._common import subir_variable



# Parametros -------------------------------------------------------------------

# Carpetas de Drive: las crudas las escribe ingestion y las limpias este modulo.
DIMENSION_CRUDA  = "4_Visibilidad_mediatica_y_relevancia_publica"
DIMENSION_LIMPIA = "4_Visibilidad_mediatica_y_relevancia_publica_limpias"
FUENTE           = "gdelt_proxy_b"
FUENTE_TRENDS    = "google_trends_paraguay"

ANIO_MINIMO = 2015

# Nombre de columna en el Excel crudo -> nombre de variable limpia. Lista FIJA (ver el
# docstring de google_trends_paraguay.py): no agregar ni sacar terminos sin revisar
# primero esa justificacion.
TERMINOS_TRENDS = {
    "Paraguay trade": "google_trends_paraguay_trade",
    "Paraguay tariffs": "google_trends_paraguay_tariffs",
    "Paraguay embassy": "google_trends_paraguay_embassy",
}

# Sufijo de cada variante de GDELT. BOTH no lleva sufijo para no romper la carpeta de
# Drive que ya existia con ese nombre.
SUFIJO_VARIABLE = {"BOTH": "", "PY": "_py", "US": "_us"}



# GDELT proxy B ----------------------------------------------------------------

# Entrada: los CSV mensuales que gdelt_proxy_b sube a Drive (ver
# src/ingestion/gdelt_proxy_b.py y gdelt_extraction/ para como se construyen): la
# cobertura mediatica bilateral PY-US segun la regla "proxy B", una fila por
# (mes, source_country).
#
# POR QUE SOLO LOS ARCHIVOS "monthly_": tilan sin huecos ni superposicion todo el rango
# feb-2015 a ene-2026 (confirmado a mano el 2026-09-03 comparando los rangos de fecha
# de cada nombre). "historical_processed_*.csv" queda afuera a proposito: es el
# conglomerado de esos mismos meses, y usarlo ademas de los monthly_ los duplicaria.
#
# POR QUE TRES VARIANTES POR METRICA (politica 2026-09-09, a pedido del usuario): antes
# solo se usaba BOTH y se perdia si la cobertura viene de medios paraguayos o
# estadounidenses. Cada valor de `source_country` da su propia variante:
#   - BOTH: el total de articulos proxy B del mes. No es una tercera categoria de
#     articulos sino la suma de PY y US (verificado el 2026-09-09 contra un CSV real:
#     mes 2026-01, BOTH=241 = PY(238) + US(3)). En gdelt_queries.py, `expanded` hace
#     `CROSS JOIN UNNEST([s.source_country, 'BOTH'])`: cada articulo se cuenta una vez
#     bajo su pais y otra bajo BOTH. El tono de BOTH tampoco es el promedio de PY y US:
#     es el promedio pooled de todos los articulos juntos, asi que con 238 articulos PY
#     y 3 US queda mucho mas cerca del tono de PY que de un promedio 50/50.
#   - PY: solo articulos cuyo dominio de origen esta verificado como paraguayo en el
#     catalogo de fuentes (ver gdelt_extraction/README.md, "PY/US es pais de fuente, no
#     direccion de la interaccion").
#   - US: idem, con dominio verificado como estadounidense.
#
# Salida: dos variables por variante.
#   - gdelt_proxy_articles[_py|_us]: suma de `proxy_articles` de los meses del
#     trimestre, tipo "cantidad".
#   - gdelt_tone_promedio[_py|_us]: promedio de `tone_mean` de esos meses ponderado por
#     `proxy_articles`, para no pesar igual un mes con 0 articulos que uno con 200.
#     Tipo "indice" (tono GDELT, no una unidad monetaria ni un conteo). Un trimestre sin
#     ningun articulo de ese pais no tiene fila: no se rellena con 0.


def _extraer_gdelt():
    """Devuelve {"BOTH"/"PY"/"US": (articulos, tone_ponderado)}, cada una
    {(anio,trim): valor} - tone_ponderado solo tiene clave para los
    trimestres con al menos 1 articulo de ese pais (ver el comentario de la
    seccion para que significa cada uno de los 3)."""

    # 1. lista los CSV mensuales de la carpeta cruda
    carpeta_id = resolve_ingestion_folder(DIMENSION_CRUDA, FUENTE)
    archivos = [a for a in listar_archivos(carpeta_id) if a["name"].startswith("monthly_")]

    # 2. los une y se queda con los meses desde ANIO_MINIMO
    filas = []
    for archivo in archivos:
        contenido = descargar_archivo(archivo["id"])
        filas.append(pd.read_csv(io.BytesIO(contenido)))

    todo = pd.concat(filas, ignore_index=True)
    todo["month"] = pd.to_datetime(todo["month"])
    todo = todo[todo["month"].dt.year >= ANIO_MINIMO]
    todo["trimestre_clave"] = list(zip(todo["month"].dt.year, (todo["month"].dt.month - 1) // 3 + 1))

    # 3. por cada variante de pais, suma los articulos y pondera el tono por trimestre
    resultado = {}
    for pais in SUFIJO_VARIABLE:
        subset = todo[todo["source_country"] == pais]
        articulos, tone_ponderado = {}, {}
        for clave, grupo in subset.groupby("trimestre_clave"):
            total_articulos = int(grupo["proxy_articles"].sum())
            articulos[clave] = total_articulos
            if total_articulos > 0:
                tone_ponderado[clave] = (
                    (grupo["tone_mean"].fillna(0) * grupo["proxy_articles"]).sum() / total_articulos
                )
        resultado[pais] = (articulos, tone_ponderado)

    return resultado



# Google Trends ----------------------------------------------------------------

# Entrada: el Excel que google_trends_paraguay sube a Drive (ver
# src/ingestion/google_trends_paraguay.py para las decisiones de filtro geografico, lista
# fija de terminos y riesgos): indice mensual (0-100, relativo) de 3 terminos fijos.
#
# POR QUE SE PROMEDIA Y NO SE SUMA: es un indice relativo, no un conteo; sumarlo no
# tiene sentido. El trimestre es el promedio simple de sus meses, tipo "indice" (mismo
# tratamiento que gdelt_tone_promedio y no el de gdelt_proxy_articles).
#
# POR QUE SE DESCARTA EL MES isPartial: es el mes en curso, que todavia acumula
# busquedas. Es el mismo criterio que el proyecto aplica a periodos incompletos en
# otras fuentes (por ejemplo el anio fiscal en curso de fa_gov, tratado en la etapa del
# indice).


def _extraer_google_trends():
    """Devuelve {nombre_variable: {(anio,trim): promedio}} para cada uno de
    los 3 terminos fijos - promedio simple de los meses del trimestre
    (indice relativo, no cantidad - ver el comentario de la seccion),
    descartando el mes marcado isPartial (todavia acumulando busquedas)."""

    # 1. toma el Excel mas reciente de la carpeta cruda
    carpeta_id = resolve_ingestion_folder(DIMENSION_CRUDA, FUENTE_TRENDS)
    archivos = listar_archivos(carpeta_id)
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    df = pd.read_excel(io.BytesIO(descargar_archivo(archivo["id"])))

    # 2. descarta el mes parcial y los anios anteriores a ANIO_MINIMO
    df = df[~df["isPartial"]].copy()
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df[df["fecha"].dt.year >= ANIO_MINIMO]
    df["trimestre_clave"] = list(zip(df["fecha"].dt.year, (df["fecha"].dt.month - 1) // 3 + 1))

    # 3. promedia los meses de cada trimestre, termino por termino
    resultado = {}
    for columna_cruda, nombre_variable in TERMINOS_TRENDS.items():
        promedios = {}
        for clave, grupo in df.groupby("trimestre_clave"):
            promedios[clave] = grupo[columna_cruda].mean()
        resultado[nombre_variable] = promedios

    return resultado



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. avisa que dimension procesa
    print(f"[{DIMENSION_LIMPIA}]")
    errores = []

    # 2. GDELT: las 3 variantes de articulos y de tono; una fuente que falla no frena a la otra
    try:
        resultado = _extraer_gdelt()
        for pais, sufijo in SUFIJO_VARIABLE.items():
            articulos, tone_ponderado = resultado[pais]
            subir_variable(DIMENSION_LIMPIA, f"gdelt_proxy_articles{sufijo}", articulos, "cantidad")
            subir_variable(DIMENSION_LIMPIA, f"gdelt_tone_promedio{sufijo}", tone_ponderado, "indice")
    except Exception as exc:  # noqa: BLE001
        errores.append(("gdelt_proxy_b", repr(exc)))
        print(f"    [!] gdelt_proxy_b: {exc!r}")

    # 3. Google Trends: una variable por termino
    try:
        trends = _extraer_google_trends()
        for nombre_variable, valores in trends.items():
            subir_variable(DIMENSION_LIMPIA, nombre_variable, valores, "indice")
    except Exception as exc:  # noqa: BLE001
        errores.append(("google_trends_paraguay", repr(exc)))
        print(f"    [!] google_trends_paraguay: {exc!r}")

    # 4. validacion: si fallo alguna fuente, termina con error despues de subir las otras
    if errores:
        raise RuntimeError(f"Fallaron {len(errores)} fuentes de {DIMENSION_LIMPIA}: {errores}")


if __name__ == "__main__":
    run()
