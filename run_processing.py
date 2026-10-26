"""Orquestador de processing: corre cada modulo de src/processing (lee los
crudos que ingestion ya subio, los limpia/consolida y sube un CSV por
dimension a 02_limpias) y registra la corrida en Google Sheets.

Separado de run_pipeline.py a proposito: ingestion (01_crudas) y processing
(02_limpias) son etapas distintas del pipeline (ver CLAUDE.md seccion 2). Se
puede correr a mano o con el workflow "Run Pipeline" de GitHub Actions, que
(rama Pruebas-de-ajuste) corre ingestion y despues este script en un solo
disparo manual.

Si un modulo falla en cualquier variable termina con codigo 1 (despues de
subir las variables que si salieron bien): antes varios modulos solo
imprimian "[!]" y la corrida quedaba en OK."""
import importlib
import pkgutil
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from src import processing
from src.sheets import append_log_row

load_dotenv()

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def discover_processing_modules():
    names = []
    for _, name, is_pkg in pkgutil.iter_modules(processing.__path__):
        if is_pkg or name.startswith("_"):
            continue
        names.append(name)
    return names


def run():
    started = datetime.now(timezone.utc)
    modules_run = []
    errors = {}

    for name in discover_processing_modules():
        module = importlib.import_module(f"src.processing.{name}")
        if not hasattr(module, "run"):
            print(f"[skip] src/processing/{name}.py no define run(), se ignora.")
            continue

        print(f"[run] src/processing/{name}.py")
        try:
            module.run()
            modules_run.append(name)
        except Exception as exc:
            errors[name] = repr(exc)
            print(f"[error] {name}: {exc}", file=sys.stderr)

    append_log_row(
        started=started,
        finished=datetime.now(timezone.utc),
        modules_run=modules_run,
        errors=errors,
        tab_name="processing_log",
    )

    if errors:
        print(f"Processing termino con errores: {errors}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing OK. Modulos ejecutados: {modules_run or '(ninguno todavia)'}")


if __name__ == "__main__":
    run()
