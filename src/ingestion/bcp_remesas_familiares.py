"""
Extraccion de datos de Remesas Familiares
Banco Central del Paraguay (BCP)

Fuente: https://www.bcp.gov.py/remesas-familiares

Que hace: descarga EN MEMORIA el Excel de remesas familiares (ingreso de
divisas, con columna "EE.UU." dentro de America del Norte, desglose
mensual) y lo sube a la carpeta de Drive de la dimension correspondiente. No
lo lee, no lo transforma, no aisla la columna de EE.UU. - eso es trabajo de
una etapa posterior (clean/integracion), que todavia no existe en este
repo. Es idempotente: si ya existe un archivo con ese nombre en Drive, lo
saltea.

Nota: el BCP publica un unico archivo con toda la serie (no uno por anio).
Si el BCP renombra el archivo al actualizarlo, la actualizacion sube como
archivo nuevo en vez de sobreescribir el anterior.
"""
from urllib.parse import urljoin

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo
from src.ingestion._bcp_common import (
    URL_BASE,
    descargar_bytes,
    limpiar_nombre_archivo,
    mime_de,
    nombre_desde_url,
    obtener_html,
)

URL_PAGINA = "https://www.bcp.gov.py/remesas-familiares"

DIMENSION = "3_Compromiso_economico_privado"
FUENTE = "bcp_remesas_familiares"
DESCRIPCION = "Remesas familiares recibidas en Paraguay por país de origen (incluye EE.UU.), mensual"
URL_FUENTE = URL_PAGINA


def _obtener_archivo():
    """Devuelve (nombre_de_archivo, url) del Excel publicado en la pagina."""
    soup = obtener_html(URL_PAGINA)

    link = soup.select_one('a[href*="/documents/"]')
    if not link:
        raise RuntimeError("No se encontro ningun link de documento en la pagina")

    url = urljoin(URL_BASE, link["href"])
    original = nombre_desde_url(url)  # ej. "Remesas familiares.xlsx"
    base, extension = original.rsplit(".", 1)
    nombre = f"{limpiar_nombre_archivo(base)}.{extension.lower()}"
    return nombre, url


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nombre, url = _obtener_archivo()

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    extension = nombre.rsplit(".", 1)[1]
    contenido = descargar_bytes(url)
    subir_archivo(contenido, nombre, carpeta_id, mime_type=mime_de(extension))
    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
