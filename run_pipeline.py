"""Pipeline maestro: corre cada modulo de src/ingestion (solo extraccion, cada uno
guarda sus datos crudos en su propia carpeta) y registra la corrida en Google Sheets."""
import importlib
import os
import pkgutil
import sys
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv

from src import ingestion
from src.entorno import instalar_filtro_en_consola, ocultar_claves
from src.ingestion._bloqueo import PREFIJO_OMITIDO_REINTENTABLE
from src.sheets import append_log_row, leer_pestana, write_dataframe

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

# nada de lo que se imprima (ni un traceback) lleva una clave en claro: la URL de
# un HTTPError trae api_key / UserID (ver src/entorno.py)
instalar_filtro_en_consola()


def discover_ingestion_modules():
    names = []
    for _, name, is_pkg in pkgutil.iter_modules(ingestion.__path__):
        if is_pkg or name.startswith("_"):
            continue
        names.append(name)
    return names


def modulos_a_correr():
    """Modulos de ingestion de esta corrida. Con SOLO_MODULOS (lista separada por
    comas) corre solo esos: es el reintento en un segundo job de Actions (otro
    runner, otra IP) de los que fallaron o quedaron bloqueados en el primero."""
    todos = discover_ingestion_modules()
    solo = [m.strip() for m in os.environ.get("SOLO_MODULOS", "").split(",") if m.strip()]
    if not solo:
        return todos, False
    desconocidos = sorted(set(solo) - set(todos))
    if desconocidos:
        raise SystemExit(f"SOLO_MODULOS menciona modulos que no existen: {desconocidos}")
    return [m for m in todos if m in solo], True


def escribir_salida_de_actions(fallidos):
    """Deja la lista de modulos a reintentar en $GITHUB_OUTPUT (solo existe dentro
    de Actions). El workflow la lee para decidir si lanza el segundo job."""
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write("modulos_fallidos=" + ",".join(fallidos) + "\n")


def fusionar_catalogo(catalogo, reintento):
    """Tabla para la pestana catalogo_fuentes. En un reintento solo se corrieron
    algunos modulos: se actualizan sus filas y se conservan las demas, para que
    la pestana (que se reescribe entera) no pierda las fuentes del primer job."""
    df = pd.DataFrame(catalogo)
    if reintento:
        previas = pd.DataFrame(leer_pestana("catalogo_fuentes"))
        if not previas.empty:
            previas = previas[~previas["fuente"].isin(df["fuente"])]
            df = pd.concat([previas, df], ignore_index=True)
    return df.sort_values(["dimension", "fuente"])


def run():
    started = datetime.now(timezone.utc)
    modules_run = []
    errors = {}
    omitidos = {}
    catalogo = []
    fallidos = []  # errores + omitidos por sitio inaccesible: candidatos a reintento

    nombres, reintento = modulos_a_correr()
    sufijo = " (reintento)" if reintento else ""

    for name in nombres:
        module = importlib.import_module(f"src.ingestion.{name}")
        if not hasattr(module, "run"):
            print(f"[skip] src/ingestion/{name}.py no define run(), se ignora.")
            continue

        print(f"[run] src/ingestion/{name}.py")
        try:
            resultado = module.run()
            # convencion: run() puede devolver "omitido: motivo" cuando no pudo
            # traer nada nuevo sin que sea un error (extraccion local ausente,
            # Google bloqueando el scraping). No pone la corrida en rojo, pero
            # tampoco se registra como "OK": queda visible en el log y el catalogo.
            if isinstance(resultado, str) and resultado.startswith("omitido"):
                omitidos[name] = resultado
                modules_run.append(f"{name}{sufijo} (omitido)")
                estado = "OMITIDO"
                if resultado.startswith(PREFIJO_OMITIDO_REINTENTABLE):
                    fallidos.append(name)
            else:
                modules_run.append(f"{name}{sufijo}")
                estado = "OK"
        except Exception as exc:
            errors[f"{name}{sufijo}"] = ocultar_claves(repr(exc))
            fallidos.append(name)
            print(f"[error] {name}: {ocultar_claves(exc)}", file=sys.stderr)
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
        write_dataframe("catalogo_fuentes", fusionar_catalogo(catalogo, reintento))

    append_log_row(
        started=started,
        finished=datetime.now(timezone.utc),
        modules_run=modules_run,
        errors=errors,
    )

    escribir_salida_de_actions(fallidos)

    if errors:
        print(f"Pipeline termino con errores: {errors}", file=sys.stderr)
        sys.exit(1)

    if omitidos:
        print("Modulos omitidos (sin error, pero sin datos nuevos):")
        for nombre, motivo in omitidos.items():
            print(f"    - {nombre}: {motivo}")

    print(f"Pipeline OK. Modulos de ingestion ejecutados: {modules_run or '(ninguno todavia)'}")


if __name__ == "__main__":
    run()
