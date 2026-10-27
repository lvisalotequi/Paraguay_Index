#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: bid_proyectos                                                        #
# DETALLE: pide a la API CKAN del BID los proyectos con cntry_nm = Paraguay y  #
#   sube el JSON crudo a Drive. NO pondera por la cuota de capital de EE.UU.:  #
#   eso es trabajo de src/processing/.                                         #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_financiero_oficial.py                            #
# SALIDA: un JSON por dia (bid_proyectos_paraguay_{fecha}.json) en             #
#   01_crudas/<dimension>_crudas/bid_proyectos/                                #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import json
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo



# Parametros -------------------------------------------------------------------

# API CKAN del portal de datos abiertos del BID (data.iadb.org), dataset
# "idb-projects-dataset". El filtro por pais lo aplica la propia API: no hace falta
# bajar el listado global de unos 28.000 proyectos del BID.
URL_API          = "https://data.iadb.org/api/3/action/datastore_search"
RESOURCE_ID      = "814b7b54-477a-4c25-b3bf-6be05412069d"  # EN - IDB Projects List
FILTRO_PAIS      = {"cntry_nm": "Paraguay"}
FILAS_POR_PEDIDO = 5000  # el total de proyectos de Paraguay (unos 940) entra en un solo pedido

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "1_Compromiso_financiero_oficial"
FUENTE      = "bid_proyectos"
DESCRIPCION = "Proyectos del BID en Paraguay (insumo para desembolsos multilaterales atribuibles a EE.UU.)"
URL_FUENTE  = "https://data.iadb.org"



# Funciones auxiliares ---------------------------------------------------------


def _pedir_proyectos():
    params = {
        "resource_id": RESOURCE_ID,
        "filters": json.dumps(FILTRO_PAIS),
        "limit": FILAS_POR_PEDIDO,
    }
    resp = requests.get(URL_API, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        raise RuntimeError(f"La API de data.iadb.org devolvio un error: {data}")

    # validacion de contrato: si Paraguay tiene mas proyectos que FILAS_POR_PEDIDO,
    # la respuesta vendria cortada y no se sube un archivo incompleto
    resultado = data["result"]
    total = resultado.get("total", 0)
    registros = resultado.get("records", [])
    if len(registros) < total:
        raise RuntimeError(
            f"La API tiene {total} proyectos de Paraguay pero solo se "
            f"pidieron {FILAS_POR_PEDIDO} filas - subir FILAS_POR_PEDIDO."
        )
    return resultado



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre del archivo del dia

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"bid_proyectos_paraguay_{fecha}.json"

    # 2. idempotente por dia: si ya se corrio hoy, no se vuelve a pedir

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    # 3. pide los proyectos y sube el JSON crudo, sin transformarlo

    resultado = _pedir_proyectos()
    contenido = json.dumps(resultado, ensure_ascii=False, indent=2).encode("utf-8")

    subir_archivo(contenido, nombre, carpeta_id, mime_type="application/json")

    # 4. validacion: dice que se subio

    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
