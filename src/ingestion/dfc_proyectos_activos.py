#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: dfc_proyectos_activos                                                #
# DETALLE: descarga en memoria el Excel "DFC Annual Project Data" (todos los   #
#   proyectos activos de DFC, global) y lo sube tal cual a Drive. NO filtra a  #
#   Paraguay: el archivo pesa unos 300 KB y filtrar es trabajo de              #
#   src/processing/.                                                           #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_financiero_oficial.py                            #
# SALIDA: el Excel de DFC con su nombre original saneado en                    #
#   01_crudas/<dimension>_crudas/dfc_proyectos_activos/                        #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import re
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

from src.drive import resolve_ingestion_folder, subir_si_cambio



# Parametros -------------------------------------------------------------------

# El Excel real esta en esta pagina. La de "Active Projects" que lista el portal
# es un buscador en JavaScript, sin archivo descargable.
URL_BASE   = "https://www.dfc.gov"
URL_PAGINA = "https://www.dfc.gov/our-impact/transaction-data"

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "1_Compromiso_financiero_oficial"
FUENTE      = "dfc_proyectos_activos"
DESCRIPCION = (
    "Proyectos de financiamiento y garantías activas de DFC "
    "(global, se filtra a Paraguay en una etapa posterior)"
)
URL_FUENTE  = URL_PAGINA



# Funciones auxiliares ---------------------------------------------------------


def _obtener_archivo():
    """Devuelve (nombre_de_archivo, url) del Excel de proyectos, tal como lo nombra DFC."""
    resp = requests.get(URL_PAGINA, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Hay dos .xlsx en la pagina (proyectos y sub-proyectos de fondos de inversion);
    # el que queremos es el que NO tiene "Subproject" en el nombre.
    candidatos = [
        a
        for a in soup.select('a[href*=".xlsx"]')
        if "subproject" not in a["href"].lower()
    ]
    if not candidatos:
        raise RuntimeError("No se encontro ningun link a un .xlsx (no-subproject) en la pagina")
    link = candidatos[0]

    # el nombre sale de la URL, sin la parte de consulta y con caracteres seguros
    url = urljoin(URL_BASE, link["href"])
    nombre_original = unquote(url.rsplit("/", 1)[-1].split("?")[0])
    nombre = re.sub(r"[^\w\-.]+", "_", nombre_original)
    return nombre, url



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y encuentra el Excel vigente en la pagina

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nombre, url = _obtener_archivo()

    # 2. descarga el Excel entero (son unos 300 KB, global): NO se filtra a Paraguay
    # aca. Se baja SIEMPRE y se compara por contenido, porque DFC republica el Excel
    # con el mismo nombre y antes la primera version quedaba congelada.

    resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    # 3. sube el archivo; se reemplaza solo si el contenido cambio

    resultado = subir_si_cambio(
        resp.content,
        nombre,
        carpeta_id,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # 4. validacion: dice que paso con el archivo

    print(f"[{FUENTE}] '{nombre}': {resultado} (Drive: {DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
