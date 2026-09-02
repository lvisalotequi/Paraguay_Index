"""
Extraccion de datos de Comercio Exterior por pais socio (Boletin trimestral)
Banco Central del Paraguay (BCP)

Fuente: https://www.bcp.gov.py/web/institucional/comercio-externo-comex-mensual
(seccion "Boletin Comercio Exterior")

Que hace: descarga EN MEMORIA el Boletin de Comercio Exterior (un unico
Excel con la serie completa 1961-actualidad; entre sus hojas estan
"Exp. por paises" e "Imp. por paises" - exportaciones/importaciones de
Paraguay por pais socio, con desglose TRIMESTRAL desde 1994, con una fila
"Estados Unidos de America") y lo sube a la carpeta de Drive de la
dimension correspondiente. No lo lee, no lo transforma, no aisla la fila
de EE.UU. - eso es trabajo de una etapa posterior (processing/clean). Es
idempotente: si ya existe un archivo con ese nombre en Drive, lo saltea.

Nota (2026-09-02, a pedido del usuario): reemplaza la fuente anterior de
este modulo (listado de archivos por anio en .../importaciones-partidas-p,
desglosado por PARTIDA ARANCELARIA - producto - no por pais socio, asi que
no tenia ninguna cifra especifica de comercio con EE.UU., inutil para la
etapa de processing). Confirmado con datos reales el mismo dia: la hoja
"Exp./Imp. por paises" de este boletin tiene columnas trimestrales (I-IV)
por cada anio desde 1994 en adelante, mas una columna TOTAL anual - cubre
de sobra el rango 2015-actualidad que usa el resto del proyecto.

La pagina publica varios documentos (arancel nacional, link a SICEX,
"Cuadros de Comercio Exterior", y el Boletin en si) - se filtra
especificamente por el que tiene "Boletin Comercio Exterior" en el nombre.
A veces la pagina deja mas de un link con ese nombre (una version vieja en
cache junto a la actual) - se elige la de anio+trimestre mas reciente segun
el propio nombre del archivo, no el orden en que aparecen en la pagina.

El BCP publica un unico archivo con toda la serie (no uno por anio). El
nombre incluye el rango (ej. "...1961 al 2 Trim 2026.xlsx") y cambia cada
vez que el BCP lo actualiza, asi que cada actualizacion sube como archivo
nuevo en vez de sobreescribir el anterior (mismo patron que
bcp_inversion_directa.py / bcp_remesas_familiares.py).
"""
import re
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

URL_PAGINA = "https://www.bcp.gov.py/web/institucional/comercio-externo-comex-mensual"

DIMENSION = "3.Compromiso_economico_privado"
FUENTE = "bcp_comercio_exterior"
DESCRIPCION = "Comercio exterior de Paraguay por país socio (incluye EE.UU.), trimestral desde 1994"
URL_FUENTE = URL_PAGINA

# Busca "N trim AAAA" (o "N Trim AAAA") en la URL/nombre del archivo, para
# poder elegir la version mas reciente si la pagina lista mas de una.
PATRON_TRIM_ANIO = re.compile(r"(\d+)\s*\+?trim\+?\s*(\d{4})", re.IGNORECASE)


def _es_boletin(href):
    href_baja = href.lower()
    return "bolet" in href_baja and "comercio" in href_baja and "exterior" in href_baja


def _obtener_archivo():
    """Devuelve (nombre_de_archivo, url) del Boletin de Comercio Exterior mas reciente publicado en la pagina."""
    soup = obtener_html(URL_PAGINA)

    candidatos = []
    for link in soup.select('a[href*="/documents/"]'):
        href = link["href"]
        if not _es_boletin(href):
            continue
        match = PATRON_TRIM_ANIO.search(href)
        clave = (int(match.group(2)), int(match.group(1))) if match else (0, 0)
        candidatos.append((clave, urljoin(URL_BASE, href)))

    if not candidatos:
        raise RuntimeError("No se encontro ningun link de 'Boletin Comercio Exterior' en la pagina")

    _, url = max(candidatos, key=lambda c: c[0])
    original = nombre_desde_url(url)
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
