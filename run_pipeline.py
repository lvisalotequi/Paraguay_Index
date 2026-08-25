"""Pipeline maestro: corre cada modulo de src/ingestion y registra la corrida en Google Sheets."""
import importlib
import pkgutil
import sys
from datetime import datetime, timezone

from src import ingestion
from src.sheets import append_log_row, write_dataframe


def discover_ingestion_modules():
    names = []
    for _, name, is_pkg in pkgutil.iter_modules(ingestion.__path__):
        if is_pkg or name.startswith("_"):
            continue
        names.append(name)
    return names


def run():
    started = datetime.now(timezone.utc)
    results = {}
    errors = {}

    for name in discover_ingestion_modules():
        module = importlib.import_module(f"src.ingestion.{name}")
        if not hasattr(module, "run"):
            print(f"[skip] src/ingestion/{name}.py no define run(), se ignora.")
            continue
        print(f"[run] src/ingestion/{name}.py")
        try:
            results[name] = module.run()
        except Exception as exc:
            errors[name] = repr(exc)
            print(f"[error] {name}: {exc}", file=sys.stderr)

    for name, df in results.items():
        print(f"[sheets] escribiendo pestana '{name}'")
        write_dataframe(name, df)

    append_log_row(
        started=started,
        finished=datetime.now(timezone.utc),
        modules_run=list(results.keys()),
        errors=errors,
    )

    if errors:
        print(f"Pipeline termino con errores: {errors}", file=sys.stderr)
        sys.exit(1)

    print(f"Pipeline OK. Modulos de ingestion ejecutados: {list(results.keys()) or '(ninguno todavia)'}")


if __name__ == "__main__":
    run()
