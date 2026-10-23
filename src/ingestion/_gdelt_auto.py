"""Extraccion automatica de GDELT (regla proxy B) con la cuenta de servicio.

Prefijo `_`: helper de `gdelt_proxy_b.py`, no un modulo de ingestion.

Que resuelve: hasta ahora la extraccion contra BigQuery corria SOLO a mano, en
una maquina con `gcloud auth application-default login` personal y con una
carpeta `output/` local que guardaba los CSV, los recibos y el libro de consumo.
Nada de eso existe en GitHub Actions. Este helper hace lo mismo con la cuenta
de servicio y guardando todo en Drive y en el Sheet de auditoria:

  - Que meses faltan: se deduce de los nombres `monthly_AAAA-MM_AAAA-MM.csv` que
    ya estan en la carpeta de Drive (esos archivos son la fuente de verdad de
    lo ya extraido). Faltan los meses entre feb-2015 y el ultimo mes completo
    (con DIAS_DE_MARGEN de espera) que ningun archivo cubre.
  - Consulta: el SQL sale de `gdelt_extraction/` (mismo codigo y misma
    configuracion que la extraccion local, asi la serie es continua y el SQL de
    un mes tiene el mismo hash que el de una corrida manual).
  - Registro de consumo: cada consulta agrega una fila a la pestana
    `gdelt_registro` del Sheet de auditoria (reemplaza al `*.complete.json` y al
    `query_usage_ledger.json` locales). El tope mensual se calcula sobre esa
    pestana.
  - Sin recibos locales: el `job_id` es deterministico (mes + hash del SQL). Si
    una corrida se corta despues de enviar la consulta, la siguiente encuentra
    el job (Conflict) y recupera su resultado, sin volver a facturar.
  - Seguridad heredada: tope por consulta (`maximum_bytes_billed`), tope por
    corrida y tope mensual de `historical_workflow_config.json`, y verificacion
    de que el proyecto NO tenga facturacion antes y despues de cada consulta
    (falla cerrada: si no se puede confirmar, no se consulta nada).

Requisito unico del lado de Google Cloud (una vez): la cuenta de servicio
necesita poder LEER la facturacion del proyecto para esa verificacion. Hace
falta habilitar la API "Cloud Billing" en el proyecto y darle a la cuenta un rol
de lectura (por ejemplo "Browser"). No necesita ni debe tener permisos de
administracion de facturacion. Sin eso, la extraccion se detiene con un mensaje
que lo explica y el resto del pipeline sigue.
"""
import calendar
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.sheets import agregar_filas, leer_pestana

REPO_ROOT = Path(__file__).resolve().parents[2]
CARPETA_EXTRACTOR = REPO_ROOT / "gdelt_extraction"
CONFIG = CARPETA_EXTRACTOR / "historical_workflow_config.json"

PERFIL = "proxy_b_metrics"
GIB = 1024**3
INICIO_GDELT = date(2015, 2, 1)  # GDELT 2.0 arranca el 2015-02-19; el primer mes extraible es feb-2015
DIAS_DE_MARGEN = 3  # un mes se extrae recien cuando pasaron N dias de su cierre (rezago de carga de GDELT)

PATRON_ARCHIVO_MENSUAL = re.compile(r"^monthly_(\d{4})-(\d{2})_(\d{4})-(\d{2})\.csv$")

TAB_REGISTRO = "gdelt_registro"
ENCABEZADO_REGISTRO = [
    "timestamp_utc", "mes", "job_id", "bytes_procesados", "bytes_facturados",
    "gib_facturados", "mes_calendario", "sql_sha256", "origen", "estado",
]


def _extractor():
    """Importa gdelt_extraction/bilateral_media_extractor (carpeta sin paquete)."""
    if str(CARPETA_EXTRACTOR) not in sys.path:
        sys.path.insert(0, str(CARPETA_EXTRACTOR))
    import bilateral_media_extractor

    return bilateral_media_extractor


def cargar_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


# ----------------------------------------------------------- que meses faltan

def meses_cubiertos(nombres):
    """Conjunto de 'AAAA-MM' cubiertos por los archivos monthly_*.csv (cada uno
    cubre un rango de meses, ambos extremos incluidos)."""
    cubiertos = set()
    for nombre in nombres:
        match = PATRON_ARCHIVO_MENSUAL.match(nombre)
        if not match:
            continue
        anio, mes, anio_fin, mes_fin = (int(g) for g in match.groups())
        cursor = date(anio, mes, 1)
        fin = date(anio_fin, mes_fin, 1)
        while cursor <= fin:
            cubiertos.add(cursor.strftime("%Y-%m"))
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    return cubiertos


def ultimo_mes_extraible(hoy):
    """Ultimo mes cerrado hace al menos DIAS_DE_MARGEN dias."""
    primero = hoy.replace(day=1)
    anterior = (primero - timedelta(days=1)).replace(day=1)  # mes previo al de hoy
    if (hoy - primero).days < DIAS_DE_MARGEN:
        return (anterior - timedelta(days=1)).replace(day=1)
    return anterior


def meses_faltantes(cubiertos, hoy):
    """Meses (date, dia 1) entre feb-2015 y el ultimo extraible que ningun archivo cubre."""
    ultimo = ultimo_mes_extraible(hoy)
    faltantes = []
    cursor = INICIO_GDELT
    while cursor <= ultimo:
        if cursor.strftime("%Y-%m") not in cubiertos:
            faltantes.append(cursor)
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    return faltantes


# ---------------------------------------------------------- registro de consumo

def gib_usados_en_el_mes(registro, mes_calendario):
    total = 0.0
    for fila in registro:
        if str(fila.get("mes_calendario", "")) == mes_calendario:
            try:
                total += float(fila.get("gib_facturados") or 0)
            except (TypeError, ValueError):
                continue
    return total


def fila_de_registro(mes, job_id, procesados, facturados, sql_sha, origen, estado, ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    return [
        ahora.isoformat(timespec="seconds"), mes, job_id, int(procesados), int(facturados),
        round(int(facturados) / GIB, 4), ahora.strftime("%Y-%m"), sql_sha, origen, estado,
    ]


# ------------------------------------------------------------------ BigQuery

def verificar_sin_facturacion(project):
    """Falla cerrada: si no se puede confirmar que el proyecto no tiene cuenta de
    facturacion, no se consulta nada. Reusa la verificacion del extractor local."""
    try:
        _extractor().require_unbilled_project(project)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"No se pudo confirmar que el proyecto {project} no tenga facturacion ({exc}). "
            "Sin esa confirmacion no se consulta nada. En Google Cloud: habilitar la API "
            "'Cloud Billing' en el proyecto y dar a la cuenta de servicio un rol de lectura "
            "(por ejemplo 'Browser'), nunca de administracion de facturacion."
        ) from exc


def tope_de_la_consulta(estimado, tope_por_consulta):
    """Mismo calculo que el extractor local: la estimacion redondeada hacia
    arriba al MiB (minimo 10 MiB), sin pasar del tope por consulta."""
    return min(tope_por_consulta, max(10 * 1024**2, math.ceil(estimado / 1024**2) * 1024**2))


def extraer_mes(client, ventana, sql, tope, location):
    """Ejecuta la consulta de un mes con job_id deterministico. Devuelve
    (csv_bytes, bytes_procesados, bytes_facturados, job_id, recuperado)."""
    import pandas as pd
    from google.api_core.exceptions import Conflict
    from google.cloud import bigquery

    sql_sha = hashlib.sha256(sql.encode()).hexdigest()
    job_id = f"gdelt_regla_b_{ventana.label.replace('-', '_')}_{sql_sha[:12]}"
    config = bigquery.QueryJobConfig(
        maximum_bytes_billed=tope,
        use_query_cache=True,
        labels={"project": "py_us_media", "month": ventana.label.replace("-", "_")},
    )
    recuperado = False
    try:
        job = client.query(sql, job_config=config, job_id=job_id, job_retry=None)
    except Conflict:
        # una corrida anterior ya envio esta misma consulta (y se corto antes de
        # guardar el resultado): se recupera, no se vuelve a facturar
        job = client.get_job(job_id, location=location)
        recuperado = True

    frame = job.result().to_dataframe(create_bqstorage_client=False)
    procesados = int(job.total_bytes_processed or 0)
    facturados = int(job.total_bytes_billed or 0)
    frame["query_bytes_processed"] = procesados
    frame["query_bytes_billed"] = facturados
    frame = frame.sort_values(["month", "source_country"])
    return frame.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"), procesados, facturados, job_id, recuperado


def nombre_archivo_mensual(ventana):
    return f"monthly_{ventana.label}_{ventana.label}.csv"


# ------------------------------------------------------------- orquestacion

def actualizar(subir, nombres_en_drive, hoy=None, client=None):
    """Extrae los meses que faltan y los entrega con `subir(nombre, bytes)`.

    Devuelve (meses_subidos, meses_pendientes). `meses_pendientes` son los que
    quedaron para otra corrida por alcanzar un tope (consumo mensual o por corrida).
    Lanza RuntimeError si no se puede verificar la facturacion o si una consulta falla.
    """
    hoy = hoy or datetime.now(timezone.utc).date()
    faltantes = meses_faltantes(meses_cubiertos(nombres_en_drive), hoy)
    if not faltantes:
        print(f"[gdelt_proxy_b] sin meses pendientes: Drive cubre hasta {ultimo_mes_extraible(hoy):%Y-%m}.")
        return [], []

    config = cargar_config()
    tope_consulta = int(config["per_query_gib"] * GIB)
    tope_corrida = int(config["per_run_gib"] * GIB)
    tope_mensual = int(config["monthly_ledger_gib"] * GIB)
    project, location = config["project"], config["location"]
    extractor = _extractor()

    registro = leer_pestana(TAB_REGISTRO)
    mes_calendario = datetime.now(timezone.utc).strftime("%Y-%m")
    usado_mes = int(gib_usados_en_el_mes(registro, mes_calendario) * GIB)

    if client is None:
        from google.cloud import bigquery

        client = bigquery.Client(project=project, location=location)

    print(f"[gdelt_proxy_b] meses por extraer: {[m.strftime('%Y-%m') for m in faltantes]}")
    verificar_sin_facturacion(project)

    from google.cloud import bigquery

    subidos, pendientes = [], []
    reservado_corrida = 0
    for indice, inicio in enumerate(faltantes):
        ventana = next(iter(extractor.month_windows(inicio, inicio)))
        sql = extractor.build_gdelt_sql(ventana, PERFIL)
        sql_sha = hashlib.sha256(sql.encode()).hexdigest()

        # estimacion gratuita (dry run) y chequeo de topes ANTES de gastar nada
        estimado = int(client.query(
            sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        ).total_bytes_processed)
        if estimado > tope_consulta:
            raise RuntimeError(f"{ventana.label}: la estimacion ({estimado / GIB:.2f} GiB) supera el tope por consulta")
        tope = tope_de_la_consulta(estimado, tope_consulta)
        if reservado_corrida + tope > tope_corrida:
            print(f"[gdelt_proxy_b] tope por corrida ({config['per_run_gib']} GiB): el resto queda para la proxima corrida.")
            pendientes = [m.strftime("%Y-%m") for m in faltantes[indice:]]
            break
        if usado_mes + reservado_corrida + tope > tope_mensual:
            print(f"[gdelt_proxy_b] tope mensual ({config['monthly_ledger_gib']} GiB) alcanzado: el resto queda para el mes siguiente.")
            pendientes = [m.strftime("%Y-%m") for m in faltantes[indice:]]
            break
        reservado_corrida += tope

        verificar_sin_facturacion(project)
        contenido, procesados, facturados, job_id, recuperado = extraer_mes(client, ventana, sql, tope, location)

        # primero el registro (el consumo es real aunque la subida falle), despues el archivo
        agregar_filas(
            TAB_REGISTRO, ENCABEZADO_REGISTRO,
            [fila_de_registro(ventana.label, job_id, procesados, facturados, sql_sha,
                              "github_actions", "recuperado" if recuperado else "completado")],
        )
        subir(nombre_archivo_mensual(ventana), contenido)
        subidos.append(ventana.label)
        print(f"[gdelt_proxy_b] {ventana.label}: {facturados / GIB:.3f} GiB facturados, subido a Drive.")
        verificar_sin_facturacion(project)

    return subidos, pendientes


def sembrar_registro_desde_ledger_local(ruta_ledger=None):
    """Una sola vez: copia a `gdelt_registro` el historial de consultas del
    `query_usage_ledger.json` local, para que el registro del Sheet arranque con
    todo lo ya consumido (en especial el consumo del mes en curso). Devuelve
    cuantas filas agrego. No duplica jobs que ya esten en la pestana."""
    ruta = Path(ruta_ledger) if ruta_ledger else CARPETA_EXTRACTOR / "output" / "query_usage_ledger.json"
    ledger = json.loads(ruta.read_text(encoding="utf-8"))
    ya_registrados = {str(f.get("job_id")) for f in leer_pestana(TAB_REGISTRO)}
    filas = []
    for entrada in ledger["entries"]:
        if entrada["job_id"] in ya_registrados:
            continue
        completado = datetime.fromisoformat(entrada["completed_at"])
        filas.append(fila_de_registro(
            entrada.get("window") or "", entrada["job_id"], entrada.get("bytes_processed") or 0,
            entrada["bytes_billed"], entrada.get("sql_sha256") or "", "local_historico", "completado",
            ahora=completado.astimezone(timezone.utc),
        ))
    agregar_filas(TAB_REGISTRO, ENCABEZADO_REGISTRO, filas)
    return len(filas)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    if "--sembrar" in sys.argv:
        print(f"filas agregadas a {TAB_REGISTRO}: {sembrar_registro_desde_ledger_local()}")
    else:
        print("uso: python -m src.ingestion._gdelt_auto --sembrar")
