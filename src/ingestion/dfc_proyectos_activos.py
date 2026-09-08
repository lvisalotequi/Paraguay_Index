"""
Extraccion de Financiamiento y Garantias Activas de DFC en Paraguay
U.S. International Development Finance Corporation (DFC)

Fuente: https://www.dfc.gov/our-impact/transaction-data (la pagina de
"Active Projects" que lista el portal es un buscador en JS sin archivo
descargable; el Excel real esta en esta otra pagina).

Que hace: descarga EN MEMORIA el Excel "DFC Annual Project Data" (todos los
proyectos activos de DFC, global) y lo sube tal cual a Drive. No lo filtra:
a diferencia de otras fuentes globales de esta dimension, este archivo pesa
poco (~300 KB), así que no hace falta filtrar a Paraguay antes de subir -
filtrar por pais es trabajo de una etapa posterior.

Nota: el dato de DFC se publica ANUAL (fiscal year), no mensual como se
pidio originalmente - es el corte mas frecuente que DFC publica como
archivo descargable.

Es idempotente: si el archivo ya existe en Drive (mismo nombre = mismo
fiscal year), no se vuelve a subir.
"""
import re
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_BASE = "https://www.dfc.gov"
URL_PAGINA = "https://www.dfc.gov/our-impact/transaction-data"

DIMENSION = "1_Compromiso_financiero_oficial"
FUENTE = "dfc_proyectos_activos"
DESCRIPCION = "Proyectos de financiamiento y garantías activas de DFC (global, se filtra a Paraguay en una etapa posterior)"
URL_FUENTE = URL_PAGINA


def _obtener_archivo():
    """Devuelve (nombre_de_archivo, url) del Excel de proyectos, tal como lo nombra DFC."""
    resp = requests.get(URL_PAGINA, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Hay dos .xlsx en la pagina (proyectos y sub-proyectos de fondos de inversion);
    # el que queremos es el que NO tiene "Subproject" en el nombre.
    candidatos = [
        a
        for a in soup.select('a[href*=".xlsx"]')
        if "subproject" not in a["href"].lower()
    ]
    if not candidatos:
        raise RuntimeError("No se encontro ningun link a un .xlsx (no-subproject) en la pagina")
    link = candidatos[0]

    url = urljoin(URL_BASE, link["href"])
    nombre_original = unquote(url.rsplit("/", 1)[-1].split("?")[0])
    nombre = re.sub(r"[^\w\-.]+", "_", nombre_original)
    return nombre, url


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nombre, url = _obtener_archivo()

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    subir_archivo(
        resp.content,
        nombre,
        carpeta_id,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
