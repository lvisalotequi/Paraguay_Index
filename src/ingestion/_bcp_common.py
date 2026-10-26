"""Helpers compartidos por los modulos de ingestion que leen bcp.gov.py.

El sitio del BCP esta detras de Cloudflare: `requests` normal da 403 (bloquea
por huella TLS, no por headers). Se usa `curl_cffi` con impersonate="chrome"
para pasar el challenge. Aun asi, desde los runners de GitHub Actions el sitio
responde 403 en algunas corridas (visto 2026-10-26): `obtener_html()` y
`descargar_bytes()` reintentan, y si el bloqueo sigue lanzan `SitioBloqueado`
con el diagnostico (URL, `cf-mitigated`, `server`) para que el modulo devuelva
"omitido" y conserve el ultimo archivo de Drive (ver `_bloqueo.py`).

Prefijo `_`: este archivo no es un modulo de ingestion en si (run_pipeline.py
lo ignora), es un helper que importan los que sí lo son.
"""
import re
import time
import unicodedata
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests

from src.ingestion._bloqueo import SitioBloqueado, comprobar

URL_BASE = "https://www.bcp.gov.py"
IMPERSONATE = "chrome"
INTENTOS_BLOQUEO = 2  # un segundo intento por si el bloqueo era momentaneo
ESPERA_BLOQUEO = 20  # segundos entre intentos

MIME_POR_EXTENSION = {
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xlsb": "application/vnd.ms-excel.sheet.binary.macroenabled.12",
    "csv": "text/csv",
}


def limpiar_nombre_archivo(texto):
    """Convierte un titulo en un nombre de archivo seguro (sin tildes/espacios raros)."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^\w\-]+", "_", texto).strip("_")
    return texto


def nombre_desde_url(url):
    """Extrae y decodifica el nombre de archivo de una URL de documentos del
    BCP (formato .../{id}/{nombre}.ext/{uuid}?t=...) - la extension no queda
    al final de la URL, asi que no se puede usar os.path.basename."""
    for segmento in urlparse(url).path.split("/"):
        if re.search(r"\.(xlsx|xlsb|xls|csv)$", segmento, re.IGNORECASE):
            return unquote(segmento)
    raise RuntimeError(f"No se pudo extraer el nombre de archivo de: {url}")


def _pedir(url, timeout):
    """GET con reintento ante bloqueo. Otros errores HTTP salen sin reintentar."""
    for intento in range(1, INTENTOS_BLOQUEO + 1):
        resp = requests.get(url, impersonate=IMPERSONATE, timeout=timeout)
        try:
            comprobar(resp)
            return resp
        except SitioBloqueado:
            if intento == INTENTOS_BLOQUEO:
                raise
            print(f"    [!] bloqueo en el intento {intento}/{INTENTOS_BLOQUEO}; reintento en {ESPERA_BLOQUEO} s")
            time.sleep(ESPERA_BLOQUEO)


def obtener_html(url, timeout=30):
    return BeautifulSoup(_pedir(url, timeout).text, "html.parser")


def descargar_bytes(url, timeout=60):
    return _pedir(url, timeout).content


def mime_de(extension):
    return MIME_POR_EXTENSION.get(extension.lower(), "application/octet-stream")
