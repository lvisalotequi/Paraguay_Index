"""
Noticias del MRE de Paraguay clasificadas por mencion y bilateralidad con EE.UU.
Ministerio de Relaciones Exteriores de Paraguay (Cancilleria)

Fuente: archivo de noticias del MRE (mre.gov.py/archivo-de-noticias/) +
capturas historicas de Wayback Machine, procesado por mre_scraping/ (ver ese
directorio). Es la contraparte del lado paraguayo de
ustr_consejo_comercio_inversion.py/congreso_menciones_paraguay.py (que miden
actividad diplomatica/legislativa del lado de EE.UU.): esta fuente mide
cuanto reporta la propia Cancilleria paraguaya de la relacion con EE.UU.

Como funciona (cambio de la rama Pruebas-de-ajuste, 2026-10-23): la
recoleccion COMPLETA 2015-2025 (9.304 URL, ~5 h, sobre todo Wayback) se hizo
una sola vez y vive en Drive como `noticias_clasificadas_*.csv`. Antes, para
sumar noticias nuevas habia que volver a correr el scraping a mano en una
maquina local. Ahora cada corrida (local o GitHub Actions):

  1. Si existe la carpeta local `mre_scraping/output/` (corrida manual), sube
     sus archivos como siempre.
  2. Baja de Drive el ultimo `noticias_clasificadas_*.csv`, recorre el archivo
     actual del MRE desde la primera pagina y se detiene al encontrar una
     racha de noticias ya conocidas (`mre_scraping/actualizar_incremental.py`);
     descarga y clasifica solo lo nuevo, re-evalua el periodo de las noticias de
     2026 que la corrida original dejo como `fuera_periodo` y reintenta las
     `error_descarga`. Si hubo cambios, sube el archivo completo actualizado
     (y un manifiesto) con la fecha de hoy. Tarda minutos, no horas.

Si el sitio del MRE no responde (bloqueo o caida) devuelve "omitido" en vez de
fallar: el ultimo archivo subido sigue vigente. Si no hay archivo base en Drive
(Drive nuevo) tambien se omite: la carga inicial completa sigue siendo la
corrida manual de mre_scraping/ (ver su README).
"""
import csv
import io
import json
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.drive import (
    descargar_archivo,
    existe_archivo,
    listar_archivos,
    resolve_ingestion_folder,
    subir_archivo,
    subir_si_cambio,
)

DIMENSION = "2_Actividad_gubernamental_y_diplomatica"
FUENTE = "mre_menciones_eeuu"
DESCRIPCION = "Noticias del MRE de Paraguay clasificadas por mención y bilateralidad con EE.UU. — actualiza de forma incremental las noticias nuevas del archivo actual"
URL_FUENTE = "https://www.mre.gov.py/archivo-de-noticias/"

REPO_ROOT = Path(__file__).resolve().parents[2]
CARPETA_SCRAPER = REPO_ROOT / "mre_scraping"
LOCAL_OUTPUT_DIR = CARPETA_SCRAPER / "output"

ARCHIVOS_A_SUBIR = ("noticias_clasificadas.csv", "manifiesto.json")
PREFIJO_BASE = "noticias_clasificadas_"


def _subir_salida_local(carpeta_id, fecha):
    """Comportamiento anterior: sube lo que dejo una corrida manual de mre_scraping/."""
    if not LOCAL_OUTPUT_DIR.is_dir():
        return

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
    print(f"[{FUENTE}] salida local: {len(nuevos)} nuevos, {len(existentes)} ya existian (Drive: {DIMENSION}/{FUENTE})")


def _base_en_drive(carpeta_id):
    """(nombre, filas) del ultimo noticias_clasificadas_*.csv de Drive, o None."""
    candidatos = [a for a in listar_archivos(carpeta_id) if a["name"].startswith(PREFIJO_BASE) and a["name"].endswith(".csv")]
    if not candidatos:
        return None
    ultimo = sorted(candidatos, key=lambda a: a["name"])[-1]
    contenido = descargar_archivo(ultimo["id"]).decode("utf-8-sig")
    csv.field_size_limit(2**31 - 1)
    return ultimo["name"], list(csv.DictReader(io.StringIO(contenido, newline="")))


def _manifiesto(filas, resumen, desde, hasta):
    validas = [f for f in filas if f.get("estado") == "ok"]
    con_mencion = [f for f in validas if str(f.get("menciona_eeuu")) == "1"]
    return {
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "origen": "actualizacion incremental (mre_scraping/actualizar_incremental.py)",
        "periodo": {"desde": desde, "hasta": hasta},
        "resumen_de_la_corrida": resumen,
        "registros_unicos": len(filas),
        "estados": dict(sorted(Counter(f.get("estado") for f in filas).items())),
        "noticias_validas": len(validas),
        "noticias_con_mencion_eeuu": len(con_mencion),
        "total_menciones_eeuu": sum(int(f.get("numero_menciones_eeuu") or 0) for f in con_mencion),
    }


def _actualizar_incremental(carpeta_id, fecha):
    base = _base_en_drive(carpeta_id)
    if base is None:
        return "omitido: no hay un noticias_clasificadas_*.csv base en Drive (la carga inicial completa es la corrida manual de mre_scraping/)"
    nombre_base, previas = base

    # mre_scraping/ no es un paquete: se agrega a la ruta de busqueda
    if str(CARPETA_SCRAPER) not in sys.path:
        sys.path.insert(0, str(CARPETA_SCRAPER))
    import actualizar_incremental as incremental

    with tempfile.TemporaryDirectory() as cache:
        try:
            filas, resumen = incremental.actualizar(previas, cache)
        except incremental.SitioNoAccesible as exc:
            print(f"[{FUENTE}] [!] {exc}")
            return "omitido: el sitio del MRE no respondio (el ultimo archivo subido sigue vigente)"

    cambios = resumen["agregadas"] + resumen["errores_resueltos"] + resumen["reevaluadas_por_periodo"]
    print(f"[{FUENTE}] base '{nombre_base}': {resumen}")
    if not cambios:
        print(f"[{FUENTE}] sin cambios respecto de la base, no se sube nada.")
        return None

    campos = incremental.columnas(previas)
    buffer = io.StringIO(newline="")
    escritor = csv.DictWriter(buffer, fieldnames=campos, extrasaction="ignore")
    escritor.writeheader()
    escritor.writerows(filas)
    contenido_csv = buffer.getvalue().encode("utf-8-sig")

    anio_actual = datetime.now(timezone.utc).year
    manifiesto = json.dumps(_manifiesto(filas, resumen, incremental.ANIO_MINIMO, anio_actual), ensure_ascii=False, indent=2).encode("utf-8")

    r_csv = subir_si_cambio(contenido_csv, f"{PREFIJO_BASE}{fecha}.csv", carpeta_id, mime_type="text/csv")
    r_man = subir_si_cambio(manifiesto, f"manifiesto_{fecha}.json", carpeta_id, mime_type="application/json")
    print(f"[{FUENTE}] noticias_clasificadas_{fecha}.csv: {r_csv}; manifiesto_{fecha}.json: {r_man} ({len(filas)} noticias).")
    return None


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    _subir_salida_local(carpeta_id, fecha)
    return _actualizar_incremental(carpeta_id, fecha)


if __name__ == "__main__":
    run()
