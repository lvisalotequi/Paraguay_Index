#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: bcp_comercio_exterior                                                #
# DETALLE: descarga en memoria el Boletin de Comercio Exterior del BCP (un     #
#   Excel con la serie 1961-actualidad, con exportaciones e importaciones por  #
#   pais socio) y lo sube a Drive. NO lo lee ni aisla la fila de EE.UU.: eso   #
#   es trabajo de src/processing/. Si el sitio bloquea, devuelve omitido.      #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_economico_privado.py                             #
# SALIDA: el Boletin con su nombre saneado (Boletin_..._N_Trim_AAAA.xlsx) en   #
#   01_crudas/<dimension>_crudas/bcp_comercio_exterior/                        #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import re
from urllib.parse import urljoin

from src.drive import resolve_ingestion_folder, subir_si_cambio
from src.ingestion._bloqueo import SitioBloqueado, omitido_por_bloqueo
from src.ingestion._bcp_common import (
    URL_BASE,
    descargar_bytes,
    limpiar_nombre_archivo,
    mime_de,
    nombre_desde_url,
    obtener_html,
)



# Parametros -------------------------------------------------------------------

# La fuente es la seccion "Boletin Comercio Exterior" de esta pagina del BCP. El
# Boletin es un unico Excel con la serie completa 1961-actualidad; entre sus hojas
# estan "Exp. por paises" e "Imp. por paises" (exportaciones e importaciones de
# Paraguay por pais socio), con desglose TRIMESTRAL desde 1994 y una fila "Estados
# Unidos de America".
#
# El BCP publica un unico archivo con toda la serie, no uno por anio. El nombre
# incluye el rango (por ejemplo "...1961 al 2 Trim 2026.xlsx") y cambia cada vez que
# el BCP lo actualiza, asi que cada actualizacion sube como archivo nuevo en vez de
# sobreescribir el anterior (mismo patron que bcp_inversion_directa.py y
# bcp_remesas_familiares.py).
#
# CAMBIO DE FUENTE (2026-09-02, a pedido del usuario): reemplaza la fuente anterior
# de este modulo (un listado de archivos por anio en .../importaciones-partidas-p,
# desglosado por PARTIDA ARANCELARIA, es decir por producto y no por pais socio, asi
# que no tenia ninguna cifra de comercio con EE.UU. y era inutil para processing).
# Confirmado con datos reales el mismo dia: la hoja "Exp./Imp. por paises" de este
# boletin tiene columnas trimestrales (I-IV) por cada anio desde 1994, mas una
# columna TOTAL anual: cubre de sobra el rango 2015-actualidad del proyecto.
URL_PAGINA = "https://www.bcp.gov.py/web/institucional/comercio-externo-comex-mensual"

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "3_Compromiso_economico_privado"
FUENTE      = "bcp_comercio_exterior"
DESCRIPCION = "Comercio exterior de Paraguay por país socio (incluye EE.UU.), trimestral desde 1994"
URL_FUENTE  = URL_PAGINA

# La pagina publica varios documentos (arancel nacional, link a SICEX, "Cuadros de
# Comercio Exterior" y el Boletin en si): se filtra por el que tiene "Boletin
# Comercio Exterior" en el nombre. A veces la pagina deja mas de un link con ese
# nombre (una version vieja en cache junto a la actual): se elige la de anio y
# trimestre mas reciente segun el propio nombre del archivo, no el orden en que
# aparecen en la pagina. Este patron busca "N trim AAAA" (o "N Trim AAAA") en la
# URL o en el nombre.
PATRON_TRIM_ANIO = re.compile(r"(\d+)\s*\+?trim\+?\s*(\d{4})", re.IGNORECASE)



# Funciones auxiliares ---------------------------------------------------------


def _es_boletin(href):
    href_baja = href.lower()
    return "bolet" in href_baja and "comercio" in href_baja and "exterior" in href_baja


def _obtener_archivo():
    """Devuelve (nombre_de_archivo, url) del Boletin mas reciente publicado en la pagina."""
    soup = obtener_html(URL_PAGINA)

    # 1. junta los links a boletines, con su (anio, trimestre) como clave de orden
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

    # 2. se queda con el de anio y trimestre mas reciente y arma el nombre de archivo
    _, url = max(candidatos, key=lambda c: c[0])
    original = nombre_desde_url(url)
    base, extension = original.rsplit(".", 1)
    nombre = f"{limpiar_nombre_archivo(base)}.{extension.lower()}"
    return nombre, url



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive de esta fuente

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)

    # 2. encuentra y descarga el Boletin vigente. No lo lee ni lo transforma.
    try:
        nombre, url = _obtener_archivo()

        # se descarga siempre y se compara por contenido (md5): si el BCP republica
        # el archivo CON EL MISMO NOMBRE, la version vieja ya no queda congelada
        extension = nombre.rsplit(".", 1)[1]
        contenido = descargar_bytes(url)
    except SitioBloqueado as exc:
        # bcp.gov.py bloquea algunos runners de Actions: no es un error de
        # datos, el ultimo archivo de Drive sigue vigente (ver _bloqueo.py)
        return omitido_por_bloqueo(FUENTE, "bcp.gov.py", exc)

    # 3. sube el archivo; se reemplaza solo si el contenido cambio

    resultado = subir_si_cambio(contenido, nombre, carpeta_id, mime_type=mime_de(extension))

    # 4. validacion: dice que paso con el archivo

    print(f"[{FUENTE}] '{nombre}': {resultado} (Drive: {DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
