"""
Interes de busqueda digital en Google (Google Trends) para un conjunto FIJO
de terminos ligados a la relacion bilateral Paraguay-EE.UU.

Complementa a gdelt_proxy_b.py (dimension 4): GDELT mide cobertura
mediatica (oferta de noticias), esto mide demanda (cuanto busca
activamente el publico de EE.UU.) - no verificado todavia si son
redundantes entre si (a diferencia de la comparacion TIF/USTR, que si se
hizo antes de construir esa variable) - queda pendiente una vez esta
variable este validada con datos reales.

Fuente: no hay API oficial de Google Trends. Se usa `pytrends`, una
libreria NO oficial que scrapea el mismo endpoint que usa la interfaz web
de trends.google.com. Dos problemas reales encontrados al probarla
(2026-09-22):
- La version instalada (4.9.2) rompe con `urllib3>=2.0` si se le pasan
  `retries`/`backoff_factor` a `TrendReq` (usa el parametro
  `method_whitelist`, renombrado a `allowed_methods` hace varias versiones
  de urllib3) - por eso este modulo NO usa esos parametros y maneja
  reintentos a mano.
- El timeout por default (2 segundos) es demasiado corto para esta red -
  se pasa uno explicito mas largo.

**Riesgo operativo no resuelto, documentado a proposito**: Google bloquea o
limita agresivamente el scraping no oficial, mas todavia desde IPs
compartidas como las de GitHub Actions - mismo tipo de riesgo que ya tiene
`state_gov_tias_paraguay.py` con la busqueda de DuckDuckGo. Si las
consultas fallan (incluidos los reintentos), el modulo no sube nada y
avisa por consola - no rompe el pipeline.

**Decisiones tomadas, verificadas con datos reales antes de decidir (ver
DICCIONARIO_VARIABLES.md para el detalle completo del analisis)**:
1. Filtro geografico `geo=US`, no global - se comparo el indice sumado
   2015-2025 de los 3 terminos bajo ambos filtros y el numero cambia de
   forma real (ej. "Paraguay trade": 768 EE.UU. vs 964 global). Se eligio
   `US` por ser la unica opcion consistente con la convencion central del
   proyecto (aislar la señal especificamente EE.UU.-Paraguay) - "global"
   mezclaria busquedas del propio Paraguay sobre si mismo.
2. Lista de terminos `Paraguay trade` / `Paraguay tariffs` / `Paraguay
   embassy` - **FIJA, no se puede modificar sin invalidar la serie
   historica**. Motivo tecnico: Google Trends normaliza los terminos de
   una misma consulta 0-100 RELATIVOS ENTRE SI (segun cual tuvo mas
   busquedas en todo el rango pedido), no cada uno con su propia escala -
   confirmado con datos reales. Agregar o sacar un termino mas adelante
   reescala retroactivamente el significado de toda la serie de los demas
   terminos ya publicados. Se probaron 9 terminos candidatos con datos
   reales antes de elegir estos 3 (ver diccionario) - en particular se
   descarto "Paraguay visa" pese a tener la mejor cobertura de todos
   (91.7% de los meses con dato) por ser conceptualmente ambiguo (mide
   intencion de viaje, no necesariamente atencion a la relacion
   bilateral), y se mantuvo "Paraguay tariffs" pese a ser disperso (3.8%
   de los meses) porque sus picos coinciden con hechos reales de politica
   comercial, no con ruido.

Sube un Excel (una fila por mes, una columna por termino) a Drive. Es
idempotente por dia.
"""
import io
import time
from datetime import datetime, timezone

import pandas as pd
from pytrends.request import TrendReq

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

DIMENSION = "4_Visibilidad_mediatica_y_relevancia_publica"
FUENTE = "google_trends_paraguay"
DESCRIPCION = (
    "Interes de busqueda en Google (EE.UU.) para terminos ligados a la relacion "
    "bilateral Paraguay-EE.UU. (Paraguay trade / tariffs / embassy)"
)
URL_FUENTE = "https://trends.google.com/trends/explore?geo=US&q=Paraguay%20trade,Paraguay%20tariffs,Paraguay%20embassy"

ANIO_MINIMO = 2015
GEO = "US"
# Lista FIJA - ver docstring del modulo y DICCIONARIO_VARIABLES.md antes de tocar esto.
TERMINOS = ["Paraguay trade", "Paraguay tariffs", "Paraguay embassy"]

INTENTOS = 3
ESPERA_ENTRE_INTENTOS_SEG = 20


def _pedir_interes_con_reintentos():
    """Pide interest_over_time() a Google Trends, reintentando ante fallos
    transitorios (rate limiting es el modo de fallo esperado, no una
    excepcion rara) - ver docstring del modulo, riesgo documentado a
    proposito, no resuelto."""
    hoy = datetime.now(timezone.utc)
    timeframe = f"{ANIO_MINIMO}-01-01 {hoy.strftime('%Y-%m-%d')}"

    ultimo_error = None
    for intento in range(1, INTENTOS + 1):
        try:
            # sin retries/backoff_factor: rompe con la version de urllib3
            # instalada (ver docstring del modulo).
            pytrends = TrendReq(hl="en-US", tz=360, timeout=(15, 30))
            pytrends.build_payload(TERMINOS, timeframe=timeframe, geo=GEO)
            df = pytrends.interest_over_time()
            if df.empty:
                raise RuntimeError("Google Trends devolvio una respuesta vacia")
            return df
        except Exception as exc:  # noqa: BLE001
            ultimo_error = exc
            print(f"    [!] intento {intento}/{INTENTOS} fallo: {exc!r}")
            if intento < INTENTOS:
                time.sleep(ESPERA_ENTRE_INTENTOS_SEG)

    raise RuntimeError(f"no se pudo obtener datos de Google Trends tras {INTENTOS} intentos") from ultimo_error


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"google_trends_paraguay_{fecha_hoy}.xlsx"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    try:
        df = _pedir_interes_con_reintentos()
    except Exception as exc:  # noqa: BLE001
        print(f"[{FUENTE}] [!] no se pudo obtener datos de Google Trends esta corrida: {exc!r}")
        return

    df = df.reset_index().rename(columns={"date": "fecha"})
    df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(df)} meses, {df['fecha'].min()} a {df['fecha'].max()}, geo={GEO}."
    )


if __name__ == "__main__":
    run()
