"""Pipeline maestro: corre cada modulo de src/ingestion (solo extraccion, cada uno
guarda sus datos crudos en su propia carpeta) y registra la corrida en Google Sheets."""
import importlib
import pkgutil
import sys
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv

from src import ingestion
from src.sheets import append_log_row, write_dataframe

# Carga GOOGLE_APPLICATION_CREDENTIALS, SHEET_ID, BEA_API_KEY, etc. desde un
# .env local si existe. En GitHub Actions no hay .env (las variables ya
# vienen de los secrets del workflow) - load_dotenv() no hace nada en ese caso.
load_dotenv()

# En Windows, la consola a veces usa un codec (cp1252) que no soporta los
# emojis de las rutas de la Unidad compartida (DATA_ROOT) y print() explota
# con UnicodeEncodeError. Se reconfigura a UTF-8 si el stream lo permite.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def discover_ingestion_modules():
    names = []
    for _, name, is_pkg in pkgutil.iter_modules(ingestion.__path__):
        if is_pkg or name.startswith("_"):
            continue
        names.append(name)
    return names


def run():
    started = datetime.now(timezone.utc)
    modules_run = []
    errors = {}
    catalogo = []

    for name in discover_ingestion_modules():
        module = importlib.import_module(f"src.ingestion.{name}")
        if not hasattr(module, "run"):
            print(f"[skip] src/ingestion/{name}.py no define run(), se ignora.")
            continue

        print(f"[run] src/ingestion/{name}.py")
        try:
            module.run()
            modules_run.append(name)
            estado = "OK"
        except Exception as exc:
            errors[name] = repr(exc)
            print(f"[error] {name}: {exc}", file=sys.stderr)
            estado = "ERROR"

        # Trazabilidad: de donde sale cada fuente, aunque esta corrida haya
        # fallado - asi el catalogo no pierde una fila por un error puntual.
        catalogo.append(
            {
                "fuente": name,
                "dimension": getattr(module, "DIMENSION", ""),
                "descripcion": getattr(module, "DESCRIPCION", ""),
                "url_fuente": getattr(module, "URL_FUENTE", ""),
                "estado_ultima_corrida": estado,
                "ultima_corrida_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

    if catalogo:
        df_catalogo = pd.DataFrame(catalogo).sort_values(["dimension", "fuente"])
        write_dataframe("catalogo_fuentes", df_catalogo)

    append_log_row(
        started=started,
        finished=datetime.now(timezone.utc),
        modules_run=modules_run,
        errors=errors,
    )

    if errors:
        print(f"Pipeline termino con errores: {errors}", file=sys.stderr)
        sys.exit(1)

    print(f"Pipeline OK. Modulos de ingestion ejecutados: {modules_run or '(ninguno todavia)'}")


if __name__ == "__main__":
    run()
