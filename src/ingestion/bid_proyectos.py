"""
Extraccion de proyectos del BID en Paraguay
Banco Interamericano de Desarrollo (BID) - portal de datos abiertos

Fuente: https://data.iadb.org (API CKAN datastore_search), dataset
"idb-projects-dataset", resource "EN - IDB Projects List"
(814b7b54-477a-4c25-b3bf-6be05412069d).

Que hace: pide los proyectos con cntry_nm=Paraguay (filtrado a Paraguay por
la propia API - no hace falta bajar el listado global de ~28.000 proyectos
del BID) y sube el JSON crudo a Drive. No lo transforma.

Fuente complementaria a bancomundial_proyectos.py: sirve de insumo para
"Desembolsos multilaterales atribuibles a EE.UU." (BID + Banco Mundial,
ponderados por cuota de capital de EE.UU.) - el ponderado por cuota de
capital es trabajo de una etapa posterior, aca solo se extraen los
proyectos crudos.

Es idempotente por dia: si ya se corrio hoy, no se vuelve a pedir.
"""
import json
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_API = "https://data.iadb.org/api/3/action/datastore_search"
RESOURCE_ID = "814b7b54-477a-4c25-b3bf-6be05412069d"  # EN - IDB Projects List
FILTRO_PAIS = {"cntry_nm": "Paraguay"}
FILAS_POR_PEDIDO = 5000  # el total de proyectos de Paraguay (~940) entra en un solo pedido

DIMENSION = "1.Compromiso_financiero_oficial"
FUENTE = "bid_proyectos"


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

    resultado = data["result"]
    total = resultado.get("total", 0)
    registros = resultado.get("records", [])
    if len(registros) < total:
        raise RuntimeError(
            f"La API tiene {total} proyectos de Paraguay pero solo se "
            f"pidieron {FILAS_POR_PEDIDO} filas - subir FILAS_POR_PEDIDO."
        )
    return resultado


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"bid_proyectos_paraguay_{fecha}.json"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    resultado = _pedir_proyectos()
    contenido = json.dumps(resultado, ensure_ascii=False, indent=2).encode("utf-8")

    subir_archivo(contenido, nombre, carpeta_id, mime_type="application/json")
    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
