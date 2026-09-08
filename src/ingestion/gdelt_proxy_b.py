"""
Cobertura mediatica bilateral Paraguay-EE.UU. via GDELT 2.1 GKG (regla proxy B)

Fuente: GDELT 2.1 GKG en BigQuery, filtrado por coocurrencia geografica PY-US
y senales tematicas (proxy B, version aceptada 2026-08-27 - ver
gdelt_extraction/proxy_b_config.json). La extraccion en si corre a mano,
localmente, desde gdelt_extraction/ (historical_campaign.py) - no aca.

Por que este modulo es distinto al resto de src/ingestion/: la extraccion
via BigQuery consume cuota mensual del sandbox y necesita un login OAuth
personal (gcloud auth application-default login) para verificar que la
facturacion siga deshabilitada antes de cada consulta. Automatizarla cada
12 horas en GitHub Actions no tiene sentido (no hay login humano ahi, y
fundiria la cuota gratuita en poco tiempo). Este modulo NO extrae nada: solo
toma los CSV que la extraccion local ya produjo en
gdelt_extraction/output/historical_rule_b/proxy_b_metrics/ y los sube a
Drive, igual que cualquier otra fuente. Si esa carpeta no existe en la
maquina donde corre (por ejemplo en Actions, donde gdelt_extraction/output/
esta en .gitignore y nunca se clona), no hay nada que subir y listo.
"""
from pathlib import Path

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

DIMENSION = "4_Visibilidad_mediatica_y_relevancia_publica"
FUENTE = "gdelt_proxy_b"
DESCRIPCION = "Cobertura mediática bilateral Paraguay-EE.UU. vía GDELT (regla proxy B) — sube lo que gdelt_extraction/ ya produjo localmente"
URL_FUENTE = "https://www.gdeltproject.org"

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_OUTPUT_DIR = REPO_ROOT / "gdelt_extraction" / "output" / "historical_rule_b" / "proxy_b_metrics"


def _archivos_a_subir(carpeta_local):
    nombres = sorted(p.name for p in carpeta_local.glob("monthly_*.csv"))
    nombres += sorted(p.name for p in carpeta_local.glob("historical_processed_*.csv"))
    return [carpeta_local / nombre for nombre in nombres]


def run():
    if not LOCAL_OUTPUT_DIR.is_dir():
        print(f"[{FUENTE}] sin extraccion local en esta maquina ({LOCAL_OUTPUT_DIR}), no hay nada que subir.")
        return

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nuevos, existentes = [], []
    for path in _archivos_a_subir(LOCAL_OUTPUT_DIR):
        if existe_archivo(path.name, carpeta_id):
            existentes.append(path.name)
            continue
        subir_archivo(path.read_bytes(), path.name, carpeta_id, mime_type="text/csv")
        nuevos.append(path.name)

    print(f"[{FUENTE}] {len(nuevos)} nuevos, {len(existentes)} ya existian (Drive: {DIMENSION}/{FUENTE})")


if __name__ == "__main__":
    run()
