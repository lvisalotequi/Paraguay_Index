"""
Extraccion de Inversion Directa de EE.UU. en Paraguay (USDIA)
Bureau of Economic Analysis (BEA) - Departamento de Comercio de EE.UU.

Fuente: API publica de BEA (https://apps.bea.gov/api/data), dataset MNE
(Multinational Enterprises). Fuente complementaria a bcp_inversion_directa.py
(que trae el mismo tipo de dato, pero registrado del lado paraguayo).

Que hace: pide a la API la posicion/flujos de Inversion Directa de EE.UU.
hacia Paraguay (DirectionOfInvestment=outward, Country=216 -codigo BEA de
Paraguay-, todos los anios disponibles) y sube la respuesta cruda (JSON) tal
cual a Drive. No la parsea, no la transforma - eso es trabajo de una etapa
posterior.

Nota: a diferencia de bcp_inversion_directa.py (trimestral), esta serie de
BEA desagregada por pais viene ANUAL - es el corte mas fino que expone el
dataset MNE para pais, no hay opcion trimestral.

Requiere la variable de entorno BEA_API_KEY (gratuita, se genera en
https://apps.bea.gov/API/signup/ - no se puede automatizar esa alta).
"""
import json
import os
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_API = "https://apps.bea.gov/api/data"
PAIS_PARAGUAY = "216"  # codigo numerico de pais que usa la API de BEA

DIMENSION = "3.Compromiso_economico_privado"
FUENTE = "bea_inversion_directa"


def _pedir_datos():
    api_key = os.environ["BEA_API_KEY"]
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

    error = data.get("BEAAPI", {}).get("Error")
    if error:
        raise RuntimeError(f"BEA API devolvio un error: {error}")

    return data


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"bea_inversion_directa_paraguay_{fecha}.json"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    data = _pedir_datos()
    contenido = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    subir_archivo(contenido, nombre, carpeta_id, mime_type="application/json")
    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
