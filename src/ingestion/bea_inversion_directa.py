#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: bea_inversion_directa                                                #
# DETALLE: pide a la API del BEA la inversion directa de EE.UU. en Paraguay    #
#   (dataset MNE, anual, todos los anios) y sube la respuesta JSON cruda a     #
#   Drive. NO la parsea ni la transforma: eso es trabajo de src/processing/.   #
#   Requiere BEA_API_KEY.                                                      #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_economico_privado.py                             #
# SALIDA: un JSON por dia (bea_inversion_directa_paraguay_{fecha}.json) en     #
#   01_crudas/<dimension>_crudas/bea_inversion_directa/                        #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import json
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo
from src.entorno import leer_clave



# Parametros -------------------------------------------------------------------

# La fuente es la API publica del BEA (https://apps.bea.gov/api/data), dataset MNE
# (Multinational Enterprises). Es una fuente complementaria a bcp_inversion_directa.py,
# que trae el mismo tipo de dato registrado del lado paraguayo.
#
# A diferencia de bcp_inversion_directa.py (trimestral), esta serie del BEA
# desagregada por pais viene ANUAL: es el corte mas fino que expone el dataset MNE
# para un pais, no hay opcion trimestral.
#
# Requiere BEA_API_KEY (gratuita, se genera en https://apps.bea.gov/API/signup/; no
# se puede automatizar esa alta). leer_clave quita el salto de linea que a veces trae
# el secret.
URL_API       = "https://apps.bea.gov/api/data"
PAIS_PARAGUAY = "216"  # codigo numerico de pais que usa la API de BEA

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "3_Compromiso_economico_privado"
FUENTE      = "bea_inversion_directa"
DESCRIPCION = (
    "Posición de Inversión Directa de EE.UU. en Paraguay, anual "
    "(fuente complementaria del lado de EE.UU.)"
)
URL_FUENTE  = "https://www.bea.gov/data/intl-trade-investment/direct-investment-country-and-industry"



# Funciones auxiliares ---------------------------------------------------------


def _pedir_datos():
    api_key = leer_clave("BEA_API_KEY")
    params = {
        "UserID": api_key,
        "method": "GETDATA",
        "DatasetName": "MNE",
        "DirectionOfInvestment": "outward",  # EE.UU. invirtiendo afuera (USDIA)
        "Classification": "Country",
        "Country": PAIS_PARAGUAY,
        "Industry": "0000",  # total, todas las industrias
        "Year": "all",
        "ResultFormat": "JSON",
    }
    resp = requests.get(URL_API, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # la API devuelve 200 aunque falle: el error viene dentro del JSON
    error = data.get("BEAAPI", {}).get("Error")
    if error:
        raise RuntimeError(f"BEA API devolvio un error: {error}")

    return data



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre del archivo del dia

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"bea_inversion_directa_paraguay_{fecha}.json"

    # 2. idempotente por dia: si ya se corrio hoy, no se vuelve a pedir

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    # 3. pide los datos y sube el JSON crudo, sin parsearlo ni transformarlo

    data = _pedir_datos()
    contenido = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    subir_archivo(contenido, nombre, carpeta_id, mime_type="application/json")

    # 4. validacion: dice que se subio

    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
