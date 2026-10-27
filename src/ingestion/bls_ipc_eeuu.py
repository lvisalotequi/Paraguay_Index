#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 22/09/2026                                                #
# NOMBRE: bls_ipc_eeuu                                                         #
# DETALLE: pide a la API publica del BLS la serie mensual del IPC de EE.UU.    #
#   (CUUR0000SA0) desde 2015, en tramos de 10 anios, y sube el JSON crudo de   #
#   cada tramo a Drive. Es un insumo transversal para deflactar, no una        #
#   variable de las 4 dimensiones. NO lo convierte a CSV ni promedia por       #
#   trimestre: eso es de src/processing/.                                      #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/insumos_indice.py                                           #
# SALIDA: un JSON por tramo (CUUR0000SA0_{desde}_{hasta}.json) en              #
#   insumos_indice_crudas/bls_ipc_eeuu/                                        #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import json
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_si_cambio



# Parametros -------------------------------------------------------------------

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "insumos_indice"
FUENTE      = "bls_ipc_eeuu"
DESCRIPCION = (
    "Índice de Precios al Consumidor de EE.UU. (BLS, serie CUUR0000SA0) — "
    "insumo para deflactar variables monetarias del índice"
)
URL_FUENTE  = "https://data.bls.gov/timeseries/CUUR0000SA0"

# La fuente es la API publica de series de tiempo del BLS (sin API key), serie
# CUUR0000SA0: IPC de EE.UU., todos los consumidores urbanos, no desestacionalizado
# (https://data.bls.gov/timeseries/CUUR0000SA0).
#
# Se pide la serie MENSUAL completa desde ANIO_MINIMO hasta el anio en curso y se sube
# el JSON crudo de cada tramo tal cual lo devuelve la API, sin convertirlo a CSV ni
# promediar a trimestre. Esa transformacion es trabajo de quien lo consuma despues
# (hoy src/analysis_index/indice_version_1/04_construccion_indice.qmd, que hasta el
# 2026-09-22 lo pedia en tiempo de render en vez de leerlo de Drive; ver pendiente #7
# de CLAUDE.md). Mismo criterio que fa_gov_asistencia_oficial.py, bid_proyectos.py y
# bancomundial_proyectos.py: el JSON crudo de la API es la fuente de verdad, no se
# transforma en ingestion.
#
# NO ES UNA VARIABLE de ninguna de las 4 dimensiones: es un insumo transversal
# (deflactor de precios) que usa la etapa de construccion del indice para expresar
# series monetarias en dolares constantes. Por eso vive en la pseudo-dimension
# insumos_indice y no en 1_Compromiso_financiero_oficial ni en ninguna de las 4 reales
# (ver tambien ine_poblacion_paraguay.py, el otro insumo transversal, para poblacion).
SERIE_IPC   = "CUUR0000SA0"
ANIO_MINIMO = 2015
URL_API     = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# POR QUE SE PIDE EN TRAMOS DE 10 ANIOS: la API publica del BLS, sin credencial,
# limita cada consulta a 10 anios de una serie. Los tramos se arman dinamicamente
# desde ANIO_MINIMO hasta el anio en curso (no hardcodeados como tuplas fijas, a
# diferencia del primer uso de esto en el .qmd) para que agregar un anio nuevo no
# requiera tocar este archivo.
TRAMO_MAXIMO_ANIOS = 10  # limite de la API publica del BLS sin API key



# Funciones auxiliares ---------------------------------------------------------


def _tramos_de_anios(anio_desde, anio_hasta):
    """Parte [anio_desde, anio_hasta] en tramos de a lo sumo
    TRAMO_MAXIMO_ANIOS, calculado dinamicamente segun el año en curso - asi
    agregar un año nuevo no requiere editar tuplas fijas en el codigo."""
    tramos = []
    inicio = anio_desde
    while inicio <= anio_hasta:
        fin = min(inicio + TRAMO_MAXIMO_ANIOS - 1, anio_hasta)
        tramos.append((inicio, fin))
        inicio = fin + 1
    return tramos


def _pedir_tramo(anio_desde, anio_hasta):
    resp = requests.post(
        URL_API,
        data=json.dumps({
            "seriesid": [SERIE_IPC],
            "startyear": str(anio_desde),
            "endyear": str(anio_hasta),
        }),
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y el anio en curso

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    anio_actual = datetime.now(timezone.utc).year

    # 2. arma los tramos. Los cerrados no cambian; el ULTIMO (el que incluye el anio en
    # curso) se pide siempre y se reemplaza si el BLS publico meses nuevos (antes
    # quedaba congelado con el IPC del dia de la primera corrida)

    tramos = _tramos_de_anios(ANIO_MINIMO, anio_actual)
    nuevos, actualizados, existentes = [], [], []
    for indice, (anio_desde, anio_hasta) in enumerate(tramos):
        nombre = f"{SERIE_IPC}_{anio_desde}_{anio_hasta}.json"
        es_ultimo = indice == len(tramos) - 1
        if not es_ultimo and existe_archivo(nombre, carpeta_id):
            existentes.append(nombre)
            continue

        # pide el tramo y sube el JSON crudo, que se reemplaza solo si cambio
        contenido = _pedir_tramo(anio_desde, anio_hasta)
        resultado = subir_si_cambio(contenido, nombre, carpeta_id, mime_type="application/json")
        if resultado == "nuevo":
            nuevos.append(nombre)
        elif resultado == "actualizado":
            actualizados.append(nombre)
        else:
            existentes.append(nombre)

    # 3. validacion: resumen de la corrida

    print(
        f"[{FUENTE}] {len(nuevos)} nuevos, {len(actualizados)} actualizados, {len(existentes)} sin cambios "
        f"(Drive: {DIMENSION}/{FUENTE})"
    )


if __name__ == "__main__":
    run()
