"""
Extraccion de Obligaciones y Desembolsos de fondos federales de EE.UU. vinculados a Paraguay
USAspending.gov

Fuente: https://api.usaspending.gov/ (API publica, sin key), endpoint de
descarga masiva /api/v2/bulk_download/awards/

Que hace: para cada anio desde ANIO_MINIMO hasta el actual, pide un export
masivo (prime awards + sub-awards, todos los tipos) filtrado a
place_of_performance country=PRY -ya filtrado a Paraguay por la propia API-
espera a que el archivo se genere (proceso asincrono: se pide, se consulta
el estado, se descarga cuando esta listo) y sube el ZIP crudo a Drive. No
lo transforma.

Nota tecnica: el endpoint de descarga masiva de USAspending solo acepta
rangos de fecha de hasta 1 anio por pedido, por eso se pide anio por anio
en vez de todo el rango de una vez.

Es idempotente por anio para los anios cerrados: una vez subidos, no se
vuelven a pedir. Los ultimos ANIOS_A_REFRESCAR anios se piden siempre y se
reemplazan en Drive (subir_si_cambio) - mismo criterio que
fa_gov_asistencia_oficial.py. El nombre del archivo no cambia, asi que
processing, que suma todos los ZIP de la carpeta, no cuenta un año dos veces.
"""
import time
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_si_cambio

URL_BULK_DOWNLOAD = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
URL_STATUS = "https://api.usaspending.gov/api/v2/download/status"

PAIS = "PRY"
ANIO_MINIMO = 2015
ANIOS_A_REFRESCAR = 2  # el año en curso y el anterior se piden siempre (datos aun en revision)

# Todos los tipos de prime award (BID solo permite un grupo por pedido en el
# endpoint de busqueda paginada, pero bulk_download si acepta todos juntos).
PRIME_AWARD_TYPES = [
    "A", "B", "C", "D",
    "IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E",
    "02", "03", "04", "05", "06", "07", "08", "09", "10", "11",
]
SUB_AWARD_TYPES = ["grant", "procurement"]

POLL_INTERVAL_SEG = 15
POLL_TIMEOUT_SEG = 20 * 60  # 20 minutos - el tamano tipico por pais/anio es chico

DIMENSION = "1_Compromiso_financiero_oficial"
FUENTE = "usaspending_obligaciones"
DESCRIPCION = "Obligaciones y desembolsos de fondos federales de EE.UU. vinculados a Paraguay, por año"
URL_FUENTE = "https://www.usaspending.gov"


def _pedir_descarga(anio):
    """Inicia la generacion del archivo para un anio. Devuelve (file_name, file_url)."""
    body = {
        "filters": {
            "prime_award_types": PRIME_AWARD_TYPES,
            "sub_award_types": SUB_AWARD_TYPES,
            "place_of_performance_locations": [{"country": PAIS}],
            "date_range": {"start_date": f"{anio}-01-01", "end_date": f"{anio}-12-31"},
            "date_type": "action_date",
        },
        "columns": [],
    }
    resp = requests.post(URL_BULK_DOWNLOAD, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["file_name"], data["file_url"]


def _esperar_archivo(file_name):
    """Pollea el estado hasta que el archivo este listo. Devuelve la url final."""
    inicio = time.monotonic()
    while time.monotonic() - inicio < POLL_TIMEOUT_SEG:
        resp = requests.get(URL_STATUS, params={"file_name": file_name}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        estado = data.get("status")

        if estado == "finished":
            return data["file_url"]
        if estado in ("failed", "cancelled"):
            raise RuntimeError(f"USAspending fallo al generar {file_name}: {data.get('message')}")

        time.sleep(POLL_INTERVAL_SEG)

    raise TimeoutError(f"USAspending no genero {file_name} en {POLL_TIMEOUT_SEG}s")


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    anio_actual = datetime.now(timezone.utc).year

    nuevos, actualizados, existentes, errores = [], [], [], []
    for anio in range(ANIO_MINIMO, anio_actual + 1):
        nombre = f"usaspending_paraguay_{anio}.zip"
        refrescar = anio > anio_actual - ANIOS_A_REFRESCAR
        if not refrescar and existe_archivo(nombre, carpeta_id):
            existentes.append(nombre)
            continue

        try:
            file_name, file_url = _pedir_descarga(anio)
            file_url = _esperar_archivo(file_name)

            contenido = requests.get(file_url, timeout=120).content
            resultado = subir_si_cambio(contenido, nombre, carpeta_id, mime_type="application/zip")
        except Exception as exc:  # noqa: BLE001
            errores.append((nombre, repr(exc)))
            continue

        if resultado == "nuevo":
            nuevos.append(nombre)
        elif resultado == "actualizado":
            actualizados.append(nombre)
        else:
            existentes.append(nombre)

    print(
        f"[{FUENTE}] {len(nuevos)} nuevos, {len(actualizados)} actualizados, {len(existentes)} sin cambios, "
        f"{len(errores)} errores (Drive: {DIMENSION}/{FUENTE})"
    )
    for nombre, err in errores:
        print(f"    [!] {nombre}: {err}")

    if errores:
        raise RuntimeError(f"{len(errores)} archivos fallaron: {errores}")


if __name__ == "__main__":
    run()
