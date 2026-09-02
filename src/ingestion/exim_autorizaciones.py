"""
Extraccion de Autorizaciones de EXIM vinculadas a Paraguay
Export-Import Bank of the United States (EXIM)

Fuente: https://catalog.data.gov/dataset/authorizations-from-10-01-2006-thru-06-30-2025
(el CSV real esta hosteado en img.exim.gov, el catalogo de data.gov solo linkea a el)

Que hace: descarga EN MEMORIA el CSV completo de autorizaciones de EXIM
(global, todos los paises, ~19 MB) y sube a Drive SOLO las filas donde
Country = Paraguay. A diferencia de las demas fuentes de src/ingestion/,
esta si filtra filas antes de subir: el archivo de origen no tiene una API
que permita pedir solo Paraguay, y el dump completo es demasiado grande
para guardarlo entero en Drive sin necesidad. El resto de las columnas
queda intacto, sin transformar.

Nota: el archivo se publica por TRIMESTRE fiscal (nombre incluye "fyXX-qN"),
no mensual como se pidio originalmente - es el corte mas frecuente que EXIM
publica como archivo descargable.

Es idempotente: si ya existe un archivo con el mismo nombre en Drive
(mismo trimestre publicado), no se vuelve a subir.
"""
import io
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_CATALOGO = "https://catalog.data.gov/dataset/authorizations-from-10-01-2006-thru-06-30-2025"
PAIS = "Paraguay"

DIMENSION = "1.Compromiso_financiero_oficial"
FUENTE = "exim_autorizaciones"
DESCRIPCION = "Autorizaciones de EXIM Bank vinculadas a Paraguay, por trimestre fiscal"
URL_FUENTE = URL_CATALOGO


def _obtener_url_csv():
    resp = requests.get(URL_CATALOGO, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    link = soup.select_one('a[href$=".csv"]')
    if not link:
        raise RuntimeError("No se encontro ningun link a un .csv en el catalogo de data.gov")

    return urljoin(URL_CATALOGO, link["href"])


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    url_csv = _obtener_url_csv()

    nombre_original = url_csv.rsplit("/", 1)[-1]  # ej. "data-gov_fy26-q2.csv"
    nombre = "paraguay_" + re.sub(r"[^\w\-.]+", "_", nombre_original)

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    resp = requests.get(url_csv, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    df = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig", low_memory=False)
    df_paraguay = df[df["Country"] == PAIS]

    contenido = df_paraguay.to_csv(index=False).encode("utf-8-sig")
    subir_archivo(contenido, nombre, carpeta_id, mime_type="text/csv")
    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(df_paraguay)} de {len(df)} filas totales eran de Paraguay."
    )


if __name__ == "__main__":
    run()
