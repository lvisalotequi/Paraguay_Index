"""
Indice de Precios al Consumidor de EE.UU. (deflactor)
U.S. Bureau of Labor Statistics (BLS)

Fuente: API publica de series de tiempo del BLS (sin API key), serie
`CUUR0000SA0` (IPC de EE.UU., todos los consumidores urbanos, no
desestacionalizado) - https://data.bls.gov/timeseries/CUUR0000SA0

Que hace: pide la serie MENSUAL completa desde ANIO_MINIMO hasta el año en
curso y sube el JSON crudo de cada tramo tal cual lo devuelve la API, sin
convertirlo a CSV ni promediar a trimestre (esa transformacion es trabajo de
quien lo consuma despues - hoy `src/analysis_index/indice_version_1/04_construccion_indice.qmd`,
que hasta el 2026-09-22 lo pedia en tiempo de render en vez de leerlo de
Drive; ver pendiente #7 de CLAUDE.md). Mismo criterio que
fa_gov_asistencia_oficial.py/bid_proyectos.py/bancomundial_proyectos.py: el
JSON crudo de la API es la fuente de verdad, no se transforma en ingestion.

**Por que se pide en tramos de 10 años**: la API publica del BLS, sin
credencial, limita cada consulta a 10 años de una serie. Se arman los tramos
dinamicamente desde ANIO_MINIMO hasta el año en curso (no hardcodeados como
tuplas fijas, a diferencia del primer uso de esto en el .qmd) para que
agregar un año nuevo no requiera tocar este archivo.

**No es una variable de ninguna de las 4 dimensiones**: es un insumo
transversal (deflactor de precios) que usa la etapa de construccion del
indice para expresar series monetarias en dolares constantes - por eso vive
en la pseudo-dimension `insumos_indice`, no en `1_Compromiso_financiero_oficial`
ni ninguna otra de las 4 reales (ver tambien ine_poblacion_paraguay.py, el
otro insumo transversal, para poblacion).
"""
import json
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

DIMENSION = "insumos_indice"
FUENTE = "bls_ipc_eeuu"
DESCRIPCION = "Índice de Precios al Consumidor de EE.UU. (BLS, serie CUUR0000SA0) — insumo para deflactar variables monetarias del índice"
URL_FUENTE = "https://data.bls.gov/timeseries/CUUR0000SA0"

SERIE_IPC = "CUUR0000SA0"
ANIO_MINIMO = 2015
URL_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
TRAMO_MAXIMO_ANIOS = 10  # limite de la API publica del BLS sin API key


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


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    anio_actual = datetime.now(timezone.utc).year

    nuevos, existentes = [], []
    for anio_desde, anio_hasta in _tramos_de_anios(ANIO_MINIMO, anio_actual):
        nombre = f"{SERIE_IPC}_{anio_desde}_{anio_hasta}.json"
        if existe_archivo(nombre, carpeta_id):
            existentes.append(nombre)
            continue
        contenido = _pedir_tramo(anio_desde, anio_hasta)
        subir_archivo(contenido, nombre, carpeta_id, mime_type="application/json")
        nuevos.append(nombre)

    print(f"[{FUENTE}] {len(nuevos)} nuevos, {len(existentes)} ya existian (Drive: {DIMENSION}/{FUENTE})")


if __name__ == "__main__":
    run()
