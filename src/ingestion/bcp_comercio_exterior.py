"""
Extraccion de datos de Comercio Exterior (Serie Detallada)
Banco Central del Paraguay (BCP)

Fuente: https://www.bcp.gov.py/web/institucional/importaciones-partidas-p

Que hace:
    1. Descarga el HTML del listado y extrae todos los archivos disponibles
       (Importacion y Exportacion, todos los anios: 1991 - actualidad). No
       hace falta paginar: la pagina carga todos los enlaces de una sola vez.
    2. Descarga cada archivo (.xls / .xlsx / .xlsb) a data/raw/bcp_comercio_exterior/.
       Es idempotente: si el archivo ya fue descargado en una corrida
       anterior, lo saltea.

Este modulo SOLO extrae y guarda los archivos crudos tal como los publica el
BCP. No los lee, no los transforma ni los consolida en un solo dataset -
eso es trabajo de una etapa posterior (clean/integracion), que todavia no
existe en este repo. Cada modulo de src/ingestion/ se limita a extraccion.

Nota tecnica: el sitio del BCP esta detras de Cloudflare y devuelve 403 con
`requests` normal (bloquea por huella TLS, no por headers). Se usa
`curl_cffi` con impersonate="chrome" para pasar el challenge, igual que en
otras fuentes del equipo que estan detras de Cloudflare.
"""
import os
import re
import time
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests

from src.paths import DATA_ROOT, ruta_larga

URL_BASE = "https://www.bcp.gov.py"
URL_LISTADO = "https://www.bcp.gov.py/web/institucional/importaciones-partidas-p"
CARPETA_DESCARGAS = os.path.join(
    DATA_ROOT, "3.Compromiso_economico_privado", "bcp_comercio_exterior"
)

# Filtrar por tipo: ["Importación"], ["Exportación"] o None para traer ambos
TIPOS_A_INCLUIR = None

# Filtrar por anio(s) exactos, ej: [2023, 2024] o None para no aplicar este filtro
ANIOS_A_INCLUIR = None

# No traer nada anterior a este anio (la serie del BCP arranca en 1991, pero
# para este proyecto solo interesa 2010 en adelante)
ANIO_MINIMO = 2010

IMPERSONATE = "chrome"


def _limpiar_nombre_archivo(texto):
    """Convierte un titulo en un nombre de archivo seguro (sin tildes/espacios raros)."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^\w\-]+", "_", texto).strip("_")
    return texto


def _obtener_listado_archivos():
    """Descarga la pagina del BCP y extrae (titulo, tipo, anio, url, extension)."""
    resp = requests.get(URL_LISTADO, impersonate=IMPERSONATE, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = soup.select("div.list__item.search-item")
    archivos = []

    for item in items:
        titulo_tag = item.select_one(".item__title")
        link_tag = item.select_one(".item__links a[href]")
        if not titulo_tag or not link_tag:
            continue

        titulo = titulo_tag.get_text(strip=True)
        url = urljoin(URL_BASE, link_tag["href"])  # el sitio publica hrefs relativos

        tipo_match = re.search(r"(Importaci[oó]n|Exportaci[oó]n)", titulo, re.IGNORECASE)
        anio_match = re.search(r"(19|20)\d{2}", titulo)
        # La extension queda en medio de la url (.../archivo.xls/<uuid>?t=...),
        # no al final, asi que se busca en cualquier posicion.
        ext_match = re.search(r"\.(xlsx|xlsb|xls|csv)\b", url, re.IGNORECASE)

        if not tipo_match or not anio_match:
            # Fila que no corresponde a un archivo de import/export con anio (raro, se saltea)
            continue

        archivos.append(
            {
                "titulo": titulo,
                "tipo": tipo_match.group(1).capitalize(),
                "anio": int(anio_match.group(0)),
                "url": url,
                "extension": ext_match.group(1).lower() if ext_match else "xls",
            }
        )

    return archivos


def _filtrar_archivos(archivos):
    resultado = archivos
    if TIPOS_A_INCLUIR:
        resultado = [a for a in resultado if a["tipo"] in TIPOS_A_INCLUIR]
    if ANIOS_A_INCLUIR:
        resultado = [a for a in resultado if a["anio"] in ANIOS_A_INCLUIR]
    if ANIO_MINIMO:
        resultado = [a for a in resultado if a["anio"] >= ANIO_MINIMO]
    return resultado


def _descargar_archivo(archivo):
    """Descarga un archivo si todavia no esta en la carpeta. Devuelve (ruta, es_nuevo)."""
    os.makedirs(ruta_larga(CARPETA_DESCARGAS), exist_ok=True)
    nombre = f"{_limpiar_nombre_archivo(archivo['titulo'])}.{archivo['extension']}"
    ruta = os.path.join(CARPETA_DESCARGAS, nombre)

    if os.path.exists(ruta_larga(ruta)):
        return ruta, False  # ya estaba descargado de una corrida anterior

    r = requests.get(archivo["url"], impersonate=IMPERSONATE, timeout=60)
    r.raise_for_status()
    with open(ruta_larga(ruta), "wb") as f:
        f.write(r.content)
    return ruta, True


def run():
    """Descarga a data/raw/bcp_comercio_exterior/ los archivos que todavia no esten ahi."""
    archivos = _filtrar_archivos(_obtener_listado_archivos())
    nuevos, existentes, errores = [], [], []

    for archivo in archivos:
        try:
            ruta, es_nuevo = _descargar_archivo(archivo)
        except Exception as exc:  # noqa: BLE001
            errores.append((archivo["titulo"], repr(exc)))
            continue

        (nuevos if es_nuevo else existentes).append(ruta)
        if es_nuevo:
            time.sleep(0.3)  # pausa breve para no saturar el servidor

    print(
        f"[bcp_comercio_exterior] {len(nuevos)} nuevos, {len(existentes)} ya "
        f"existian, {len(errores)} errores (carpeta: {CARPETA_DESCARGAS})"
    )
    for titulo, err in errores:
        print(f"    [!] {titulo}: {err}")

    if errores and not nuevos and not existentes:
        raise RuntimeError(f"No se pudo descargar ningun archivo: {errores}")


if __name__ == "__main__":
    run()
