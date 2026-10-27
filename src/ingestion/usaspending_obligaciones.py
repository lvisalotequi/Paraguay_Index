#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: usaspending_obligaciones                                             #
# DETALLE: pide a USAspending.gov un export masivo por anio (prime awards y    #
#   sub-awards, todos los tipos) filtrado a Paraguay, espera a que se genere y #
#   sube el ZIP crudo a Drive. NO lo abre ni lo transforma: sumar las          #
#   obligaciones por trimestre es trabajo de src/processing/.                  #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_financiero_oficial.py                            #
# SALIDA: un ZIP por anio (usaspending_paraguay_{anio}.zip) en                 #
#   01_crudas/<dimension>_crudas/usaspending_obligaciones/                     #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import time
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_si_cambio



# Parametros -------------------------------------------------------------------

# Descarga masiva de USAspending (API publica, sin clave). El endpoint solo
# acepta rangos de fecha de hasta 1 anio por pedido: por eso se pide anio por
# anio y no todo el rango de una vez.
URL_BULK_DOWNLOAD = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
URL_STATUS        = "https://api.usaspending.gov/api/v2/download/status"

PAIS        = "PRY"  # filtra a Paraguay en la propia API (place_of_performance)
ANIO_MINIMO = 2015

# Los anios cerrados se piden una sola vez. Los ultimos ANIOS_A_REFRESCAR se piden
# SIEMPRE y se reemplazan en Drive si cambiaron (subir_si_cambio), mismo criterio
# que fa_gov_asistencia_oficial.py. El nombre del archivo no cambia, asi que
# processing, que suma todos los ZIP de la carpeta, no cuenta un anio dos veces.
ANIOS_A_REFRESCAR = 2  # el anio en curso y el anterior (datos aun en revision)

# Todos los tipos de prime award. El endpoint de busqueda paginada solo permite un
# grupo por pedido, pero bulk_download acepta todos juntos.
PRIME_AWARD_TYPES = [
    "A", "B", "C", "D",
    "IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E",
    "02", "03", "04", "05", "06", "07", "08", "09", "10", "11",
]
SUB_AWARD_TYPES = ["grant", "procurement"]

# El export es asincrono: se pide, se consulta el estado cada POLL_INTERVAL_SEG y
# se descarga cuando esta listo. 20 minutos sobran: el tamano tipico por pais y
# por anio es chico. Si se achica, un export lento falla con TimeoutError.
POLL_INTERVAL_SEG = 15
POLL_TIMEOUT_SEG  = 20 * 60  # 20 minutos

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "1_Compromiso_financiero_oficial"
FUENTE      = "usaspending_obligaciones"
DESCRIPCION = "Obligaciones y desembolsos de fondos federales de EE.UU. vinculados a Paraguay, por año"
URL_FUENTE  = "https://www.usaspending.gov"



# Funciones auxiliares ---------------------------------------------------------


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

        # listo: devuelve la url; fallido o cancelado: corta con el mensaje de la API
        if estado == "finished":
            return data["file_url"]
        if estado in ("failed", "cancelled"):
            raise RuntimeError(f"USAspending fallo al generar {file_name}: {data.get('message')}")

        time.sleep(POLL_INTERVAL_SEG)

    raise TimeoutError(f"USAspending no genero {file_name} en {POLL_TIMEOUT_SEG}s")



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive de esta fuente y el anio en curso

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    anio_actual = datetime.now(timezone.utc).year

    # 2. recorre cada anio y anota que paso con cada archivo

    nuevos, actualizados, existentes, errores = [], [], [], []
    for anio in range(ANIO_MINIMO, anio_actual + 1):
        nombre = f"usaspending_paraguay_{anio}.zip"
        refrescar = anio > anio_actual - ANIOS_A_REFRESCAR

        # un anio cerrado que ya esta en Drive no se vuelve a pedir
        if not refrescar and existe_archivo(nombre, carpeta_id):
            existentes.append(nombre)
            continue

        # pide el export, espera a que se genere y sube el ZIP crudo
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

    # 3. validacion: resumen de la corrida; un anio fallido corta con error

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
