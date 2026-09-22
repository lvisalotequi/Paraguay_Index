"""
Noticias del MRE de Paraguay clasificadas por mencion y bilateralidad con EE.UU.
Ministerio de Relaciones Exteriores de Paraguay (Cancilleria)

Fuente: archivo de noticias del MRE (mre.gov.py/archivo-de-noticias/) +
capturas historicas de Wayback Machine, procesado por mre_scraping/ (ver ese
directorio, no este modulo). Es la contraparte del lado paraguayo de
ustr_consejo_comercio_inversion.py/congreso_menciones_paraguay.py (que miden
actividad diplomatica/legislativa del lado de EE.UU.): esta fuente mide
cuanto reporta la propia Cancilleria paraguaya de la relacion con EE.UU.

Por que este modulo es distinto al resto de src/ingestion/ (misma excepcion
que gdelt_proxy_b.py con gdelt_extraction/): el scraping de mre_scraping/ no
es una llamada liviana a una API - recorre el indice CDX de Wayback Machine y
descarga cada noticia individualmente con demora entre pedidos, tarda horas
para el rango completo 2015-2025. No tiene sentido correrlo en GitHub
Actions. Por eso corre a mano, localmente, desde mre_scraping/; este modulo
SOLO sube a Drive lo que esa carpeta ya produjo
(mre_scraping/output/noticias_clasificadas.csv y manifiesto.json). Si esa
carpeta no existe en la maquina donde corre (ej. en Actions, donde
mre_scraping/output/ esta en .gitignore y nunca se clona), el modulo imprime
un aviso y no sube nada - no es un error, es el comportamiento esperado.

El scraping original devuelve 403 en el sitio actual con requests normal
(bloqueo por huella TLS) - mre_scraping/scraper_mre.py ya usa curl_cffi con
impersonate="chrome" para pasarlo (ver mre_scraping/README.md).
"""
from datetime import datetime, timezone
from pathlib import Path

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

DIMENSION = "2_Actividad_gubernamental_y_diplomatica"
FUENTE = "mre_menciones_eeuu"
DESCRIPCION = "Noticias del MRE de Paraguay clasificadas por mención y bilateralidad con EE.UU. — sube lo que mre_scraping/ ya produjo localmente"
URL_FUENTE = "https://www.mre.gov.py/archivo-de-noticias/"

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_OUTPUT_DIR = REPO_ROOT / "mre_scraping" / "output"

ARCHIVOS_A_SUBIR = ("noticias_clasificadas.csv", "manifiesto.json")


def run():
    if not LOCAL_OUTPUT_DIR.is_dir():
        print(f"[{FUENTE}] sin extraccion local en esta maquina ({LOCAL_OUTPUT_DIR}), no hay nada que subir.")
        return

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    nuevos, existentes, faltantes = [], [], []
    for nombre_local in ARCHIVOS_A_SUBIR:
        path = LOCAL_OUTPUT_DIR / nombre_local
        if not path.is_file():
            faltantes.append(nombre_local)
            continue
        nombre_drive = f"{path.stem}_{fecha}{path.suffix}"
        if existe_archivo(nombre_drive, carpeta_id):
            existentes.append(nombre_drive)
            continue
        mime = "application/json" if path.suffix == ".json" else "text/csv"
        subir_archivo(path.read_bytes(), nombre_drive, carpeta_id, mime_type=mime)
        nuevos.append(nombre_drive)

    if faltantes:
        print(f"[{FUENTE}] [!] faltan en {LOCAL_OUTPUT_DIR}: {faltantes}")
    print(f"[{FUENTE}] {len(nuevos)} nuevos, {len(existentes)} ya existian (Drive: {DIMENSION}/{FUENTE})")


if __name__ == "__main__":
    run()
