"""
Extraccion de datos de Inversion Extranjera Directa (ID)
Banco Central del Paraguay (BCP)

Fuente: https://www.bcp.gov.py/web/institucional/-inversion-directa-id-

Que hace: descarga EN MEMORIA el anexo estadistico de Inversion Directa (un
unico Excel con varios cuadros: flujos y saldos por componentes, por
residencia del inversionista -incluye una fila "ESTADOS UNIDOS" con datos
trimestrales- y por actividad economica) y lo sube a la carpeta de Drive de
la dimension correspondiente. No lo lee, no lo transforma, no aisla la fila
de EE.UU. - eso es trabajo de una etapa posterior (clean/integracion), que
todavia no existe en este repo. Es idempotente: si ya existe un archivo con
ese nombre en Drive, lo saltea.

Nota: el BCP publica un unico archivo con toda la serie (no uno por anio).
El nombre incluye el rango de anios (ej. "...1995 - 2024.xlsx") y cambia
cuando el BCP actualiza el anexo, asi que cada actualizacion sube como
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

URL_PAGINA = "https://www.bcp.gov.py/web/institucional/-inversion-directa-id-"

DIMENSION = "3.Compromiso_economico_privado"
FUENTE = "bcp_inversion_directa"


def _obtener_archivo():
    """Devuelve (nombre_de_archivo, url) del anexo publicado en la pagina."""
    soup = obtener_html(URL_PAGINA)

    link = soup.select_one('a[href*="/documents/"]')
    if not link:
        raise RuntimeError("No se encontro ningun link de documento en la pagina")

    url = urljoin(URL_BASE, link["href"])
    original = nombre_desde_url(url)  # ej. "Anexo estadistico de Inversion Directa (ID) 1995 - 2024.xlsx"
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
