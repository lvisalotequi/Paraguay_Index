#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: bcp_remesas_familiares                                               #
# DETALLE: descarga en memoria el Excel de remesas familiares del BCP (ingreso #
#   de divisas, con la columna EE.UU. y desglose mensual) y lo sube a Drive.   #
#   NO lo lee ni aisla la columna de EE.UU.: eso es trabajo de                 #
#   src/processing/. Si el sitio bloquea, devuelve omitido.                    #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_economico_privado.py                             #
# SALIDA: Remesas_familiares.xlsx, reemplazado si el contenido cambia, en      #
#   01_crudas/<dimension>_crudas/bcp_remesas_familiares/                       #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
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

# La fuente es el Excel de remesas familiares (ingreso de divisas, con una columna
# "EE.UU." dentro de America del Norte y desglose mensual).
#
# El BCP publica un unico archivo con toda la serie, no uno por anio. Si lo renombra
# al actualizarlo, la actualizacion sube como archivo nuevo en vez de sobreescribir
# el anterior; con el mismo nombre, se reemplaza el contenido si cambio.
URL_PAGINA = "https://www.bcp.gov.py/remesas-familiares"

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "3_Compromiso_economico_privado"
FUENTE      = "bcp_remesas_familiares"
DESCRIPCION = "Remesas familiares recibidas en Paraguay por país de origen (incluye EE.UU.), mensual"
URL_FUENTE  = URL_PAGINA



# Funciones auxiliares ---------------------------------------------------------


def _obtener_archivo():
    """Devuelve (nombre_de_archivo, url) del Excel publicado en la pagina."""
    soup = obtener_html(URL_PAGINA)

    # el Excel es el unico documento de la pagina
    link = soup.select_one('a[href*="/documents/"]')
    if not link:
        raise RuntimeError("No se encontro ningun link de documento en la pagina")

    url = urljoin(URL_BASE, link["href"])
    original = nombre_desde_url(url)  # ej. "Remesas familiares.xlsx"
    base, extension = original.rsplit(".", 1)
    nombre = f"{limpiar_nombre_archivo(base)}.{extension.lower()}"
    return nombre, url



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive de esta fuente

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)

    # 2. encuentra y descarga el Excel vigente. No lo lee ni aisla la columna de
    # EE.UU.: eso es trabajo de src/processing/.
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
