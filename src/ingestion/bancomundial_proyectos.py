"""
Extraccion de proyectos del Banco Mundial en Paraguay
World Bank Projects API

Fuente: https://search.worldbank.org/api/v3/projects (API publica, sin key)
Pagina de referencia: https://projects.bancomundial.org/es/projects-operations/projects-summary?countrycode_exact=PY

Que hace: pide todos los proyectos del Banco Mundial con countrycode_exact=PY
(filtrado a Paraguay por la propia API - no hace falta bajar el catalogo
global de proyectos) y sube el JSON crudo a Drive. No lo transforma.

Fuente complementaria a bid_proyectos.py: sirve de insumo para "Desembolsos
multilaterales atribuibles a EE.UU." (BID + Banco Mundial, ponderados por
cuota de capital de EE.UU.) - el ponderado por cuota de capital es trabajo
de una etapa posterior, aca solo se extraen los proyectos crudos.

Es idempotente por dia: si ya se corrio hoy, no se vuelve a pedir.
"""
import json
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_API = "https://search.worldbank.org/api/v3/projects"
PAIS = "PY"
FILAS_POR_PEDIDO = 200  # el total de proyectos de Paraguay entra en un solo pedido

DIMENSION = "1.Compromiso_financiero_oficial"
FUENTE = "bancomundial_proyectos"


def _pedir_proyectos():
    params = {"format": "json", "countrycode_exact": PAIS, "rows": FILAS_POR_PEDIDO}
    resp = requests.get(URL_API, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    total = int(data.get("total", 0))
    proyectos = data.get("projects", {})
    if len(proyectos) < total:
        raise RuntimeError(
            f"La API tiene {total} proyectos pero solo se pidieron "
            f"{FILAS_POR_PEDIDO} filas - subir FILAS_POR_PEDIDO."
        )
    return data


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"bancomundial_proyectos_paraguay_{fecha}.json"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    data = _pedir_proyectos()
    contenido = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    subir_archivo(contenido, nombre, carpeta_id, mime_type="application/json")
    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
