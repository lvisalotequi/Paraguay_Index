#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: exim_autorizaciones                                                  #
# DETALLE: descarga en memoria el CSV completo de autorizaciones de EXIM       #
#   (global, unos 19 MB) y sube a Drive SOLO las filas con Country = Paraguay. #
#   Es la unica fuente que filtra filas antes de subir: no hay API que pida    #
#   solo Paraguay. NO transforma ninguna columna.                              #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_financiero_oficial.py                            #
# SALIDA: un CSV por trimestre fiscal (paraguay_data-gov_fyAA-qN.csv) en       #
#   01_crudas/<dimension>_crudas/exim_autorizaciones/                          #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import re
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo



# Parametros -------------------------------------------------------------------

# El CSV real esta hosteado en img.exim.gov; el catalogo de data.gov solo lo linka.
# Se publica por TRIMESTRE fiscal (el nombre lleva "fyXX-qN"), no mensual: es el
# corte mas frecuente que EXIM ofrece como archivo descargable.
URL_CATALOGO = "https://catalog.data.gov/dataset/authorizations-from-10-01-2006-thru-06-30-2025"

# Es la unica fuente de src/ingestion/ que filtra filas antes de subir: el archivo
# de origen no tiene una API que pida solo Paraguay, y el dump completo (unos 19 MB,
# todos los paises) es demasiado grande para guardarlo entero en Drive sin
# necesidad. El resto de las columnas queda intacto, sin transformar. Hoy son unas
# 60 filas de Paraguay sobre unas 52.700.
PAIS = "Paraguay"

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "1_Compromiso_financiero_oficial"
FUENTE      = "exim_autorizaciones"
DESCRIPCION = "Autorizaciones de EXIM Bank vinculadas a Paraguay, por trimestre fiscal"
URL_FUENTE  = URL_CATALOGO



# Funciones auxiliares ---------------------------------------------------------


def _obtener_url_csv():
    resp = requests.get(URL_CATALOGO, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # el catalogo linka un unico .csv
    link = soup.select_one('a[href$=".csv"]')
    if not link:
        raise RuntimeError("No se encontro ningun link a un .csv en el catalogo de data.gov")

    return urljoin(URL_CATALOGO, link["href"])



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y encuentra la URL del CSV vigente

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    url_csv = _obtener_url_csv()

    # 2. arma el nombre del archivo: el trimestre fiscal sale del nombre original
    # data-gov_fy26-q2.csv -> paraguay_data-gov_fy26-q2.csv

    nombre_original = url_csv.rsplit("/", 1)[-1]  # ej. "data-gov_fy26-q2.csv"
    nombre = "paraguay_" + re.sub(r"[^\w\-.]+", "_", nombre_original)

    # 3. idempotente: si ese trimestre ya esta en Drive, no se vuelve a descargar

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    # 4. descarga el CSV completo y se queda solo con las filas de Paraguay

    resp = requests.get(url_csv, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    df = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig", low_memory=False)
    df_paraguay = df[df["Country"] == PAIS]

    # 5. sube el recorte a Drive

    contenido = df_paraguay.to_csv(index=False).encode("utf-8-sig")
    subir_archivo(contenido, nombre, carpeta_id, mime_type="text/csv")

    # 6. validacion: cuantas filas eran de Paraguay sobre el total

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(df_paraguay)} de {len(df)} filas totales eran de Paraguay."
    )


if __name__ == "__main__":
    run()
