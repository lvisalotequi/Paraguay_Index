#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: bcp_inversion_directa                                                #
# DETALLE: descarga en memoria el anexo estadistico de Inversion Directa del   #
#   BCP (un Excel con flujos y saldos por pais del inversionista) y lo sube a  #
#   Drive. NO lo lee ni aisla la fila de EE.UU.: eso es trabajo de             #
#   src/processing/. Si el sitio bloquea, devuelve omitido.                    #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_economico_privado.py                             #
# SALIDA: el anexo con su nombre saneado (Anexo_..._ID_1995_-_AAAA.xlsx) en    #
#   01_crudas/<dimension>_crudas/bcp_inversion_directa/                        #
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

# La fuente es el anexo estadistico de Inversion Directa (ID): un unico Excel con
# varios cuadros (flujos y saldos por componentes, por residencia del inversionista
# y por actividad economica). El cuadro por residencia incluye una fila "ESTADOS
# UNIDOS" con datos trimestrales.
#
# El BCP publica un unico archivo con toda la serie, no uno por anio. El nombre
# incluye el rango de anios (por ejemplo "...1995 - 2024.xlsx") y cambia cuando el
# BCP actualiza el anexo, asi que cada actualizacion sube como archivo nuevo en vez
# de sobreescribir el anterior.
URL_PAGINA = "https://www.bcp.gov.py/web/institucional/-inversion-directa-id-"

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "3_Compromiso_economico_privado"
FUENTE      = "bcp_inversion_directa"
DESCRIPCION = "Inversión Extranjera Directa en Paraguay por país de origen (incluye EE.UU.), trimestral"
URL_FUENTE  = URL_PAGINA



# Funciones auxiliares ---------------------------------------------------------


def _obtener_archivo():
    """Devuelve (nombre_de_archivo, url) del anexo publicado en la pagina."""
    soup = obtener_html(URL_PAGINA)

    # el anexo es el unico documento de la pagina
    link = soup.select_one('a[href*="/documents/"]')
    if not link:
        raise RuntimeError("No se encontro ningun link de documento en la pagina")

    url = urljoin(URL_BASE, link["href"])
    original = nombre_desde_url(url)  # ej. "Anexo estadistico de Inversion Directa (ID) 1995 - 2024.xlsx"
    base, extension = original.rsplit(".", 1)
    nombre = f"{limpiar_nombre_archivo(base)}.{extension.lower()}"
    return nombre, url



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive de esta fuente

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)

    # 2. encuentra y descarga el anexo vigente. No lo lee ni aisla la fila de EE.UU.:
    # eso es trabajo de src/processing/.
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
