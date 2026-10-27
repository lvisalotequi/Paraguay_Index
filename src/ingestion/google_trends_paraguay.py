#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 22/09/2026                                                #
# NOMBRE: google_trends_paraguay                                               #
# DETALLE: pide a Google Trends (pytrends, no oficial) el interes de busqueda  #
#   en EE.UU. de 3 terminos fijos (Paraguay trade, tariffs y embassy) desde    #
#   2015 y sube un Excel mensual. NO cambia la lista de terminos: Google       #
#   normaliza los terminos entre si. Si Google bloquea, devuelve omitido.      #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/visibilidad_mediatica_y_relevancia_publica.py               #
# SALIDA: un Excel por dia (google_trends_paraguay_{fecha}.xlsx) en            #
#   01_crudas/<dimension>_crudas/google_trends_paraguay/                       #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import time
from datetime import datetime, timezone

import pandas as pd
from pytrends.request import TrendReq

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo



# Parametros -------------------------------------------------------------------

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "4_Visibilidad_mediatica_y_relevancia_publica"
FUENTE      = "google_trends_paraguay"
DESCRIPCION = (
    "Interes de busqueda en Google (EE.UU.) para terminos ligados a la relacion "
    "bilateral Paraguay-EE.UU. (Paraguay trade / tariffs / embassy)"
)
URL_FUENTE  = "https://trends.google.com/trends/explore?geo=US&q=Paraguay%20trade,Paraguay%20tariffs,Paraguay%20embassy"

# Mide el interes de busqueda digital en Google para un conjunto FIJO de terminos
# ligados a la relacion bilateral. Complementa a gdelt_proxy_b.py: GDELT mide
# cobertura mediatica (oferta de noticias) y esto mide demanda (cuanto busca
# activamente el publico de EE.UU.). No se verifico todavia si son redundantes entre
# si (a diferencia de la comparacion TIF/USTR, que si se hizo antes de construir esa
# variable); queda pendiente una vez esta variable este validada con datos reales.
#
# LA FUENTE: no hay API oficial de Google Trends. Se usa pytrends, una libreria NO
# oficial que scrapea el mismo endpoint de la interfaz web de trends.google.com. Dos
# problemas reales encontrados al probarla (2026-09-22):
#   - La version instalada (4.9.2) rompe con urllib3>=2.0 si se le pasan retries o
#     backoff_factor a TrendReq (usa el parametro method_whitelist, renombrado a
#     allowed_methods hace varias versiones de urllib3). Por eso este modulo NO usa
#     esos parametros y maneja los reintentos a mano.
#   - El timeout por defecto (2 segundos) es demasiado corto para esta red: se pasa
#     uno explicito mas largo.
#
# RIESGO OPERATIVO NO RESUELTO, documentado a proposito: Google bloquea o limita
# agresivamente el scraping no oficial, mas todavia desde IPs compartidas como las de
# GitHub Actions (el mismo tipo de riesgo que state_gov_tias_paraguay.py con la
# busqueda de DuckDuckGo). Si las consultas fallan, incluidos los reintentos, el
# modulo no sube nada y avisa por consola: no rompe el pipeline.
#
# DECISIONES TOMADAS, verificadas con datos reales antes de decidir (el detalle del
# analisis esta en DICCIONARIO_VARIABLES.md):
#   1. Filtro geografico geo=US y no global. Se comparo el indice sumado 2015-2025 de
#      los 3 terminos bajo ambos filtros y el numero cambia de forma real (por
#      ejemplo "Paraguay trade": 768 en EE.UU. contra 964 global). Se eligio US por
#      ser la unica opcion consistente con la convencion central del proyecto (aislar
#      la senal especificamente EE.UU.-Paraguay): "global" mezclaria busquedas del
#      propio Paraguay sobre si mismo.
#   2. La lista de terminos es FIJA y NO se puede modificar sin invalidar la serie
#      historica. Motivo tecnico: Google Trends normaliza los terminos de una misma
#      consulta de 0 a 100 RELATIVOS ENTRE SI (segun cual tuvo mas busquedas en todo
#      el rango pedido), no cada uno con su propia escala (confirmado con datos
#      reales). Agregar o sacar un termino mas adelante reescala retroactivamente el
#      significado de toda la serie de los demas ya publicados. Se probaron 9
#      terminos candidatos con datos reales antes de elegir estos 3. En particular se
#      descarto "Paraguay visa" pese a tener la mejor cobertura (91,7 % de los meses
#      con dato) por ser conceptualmente ambiguo (mide intencion de viaje, no
#      necesariamente atencion a la relacion bilateral), y se mantuvo "Paraguay
#      tariffs" pese a ser disperso (3,8 % de los meses) porque sus picos coinciden
#      con hechos reales de politica comercial, no con ruido.
ANIO_MINIMO = 2015
GEO         = "US"

# Lista FIJA: ver el bloque de arriba y DICCIONARIO_VARIABLES.md antes de tocar esto.
TERMINOS = ["Paraguay trade", "Paraguay tariffs", "Paraguay embassy"]

INTENTOS                  = 3
ESPERA_ENTRE_INTENTOS_SEG = 20



# Funciones auxiliares ---------------------------------------------------------


def _pedir_interes_con_reintentos():
    """Pide interest_over_time() a Google Trends, reintentando ante fallos
    transitorios (rate limiting es el modo de fallo esperado, no una
    excepcion rara) - ver el bloque de Parametros, riesgo documentado a
    proposito, no resuelto."""
    hoy = datetime.now(timezone.utc)
    timeframe = f"{ANIO_MINIMO}-01-01 {hoy.strftime('%Y-%m-%d')}"

    ultimo_error = None
    for intento in range(1, INTENTOS + 1):
        try:
            # sin retries/backoff_factor: rompe con la version de urllib3 instalada
            # (ver el bloque de Parametros)
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

    raise RuntimeError(
        f"no se pudo obtener datos de Google Trends tras {INTENTOS} intentos"
    ) from ultimo_error



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre del archivo del dia

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"google_trends_paraguay_{fecha_hoy}.xlsx"

    # 2. idempotente por dia: si ya se corrio hoy, no se vuelve a pedir

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    # 3. pide los datos; si Google bloquea tras los reintentos, queda omitido y el
    # ultimo archivo subido sigue vigente

    try:
        df = _pedir_interes_con_reintentos()
    except Exception as exc:  # noqa: BLE001
        print(f"[{FUENTE}] [!] no se pudo obtener datos de Google Trends esta corrida: {exc!r}")
        return "omitido: Google Trends no respondio (el ultimo archivo subido sigue vigente)"

    # 4. deja la fecha como texto AAAA-MM-DD, una fila por mes y una columna por termino

    df = df.reset_index().rename(columns={"date": "fecha"})
    df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")

    # 5. arma el Excel y lo sube

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    # 6. validacion: cuantos meses y de que rango

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(df)} meses, {df['fecha'].min()} a {df['fecha'].max()}, geo={GEO}."
    )


if __name__ == "__main__":
    run()
