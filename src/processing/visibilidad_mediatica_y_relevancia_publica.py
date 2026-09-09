"""
Limpieza/consolidacion de la dimension 4 (Visibilidad mediatica y
relevancia publica) en un CSV trimestral por variable (ver
src/processing/_common.py para la convencion de salida: una carpeta por
variable, esquema fijo trimestre/anio/trimestre_num/valor/unidad).

Unica fuente: gdelt_proxy_b (ver src/ingestion/gdelt_proxy_b.py y
gdelt_extraction/ para el detalle completo de como se construye). Sube a
Drive varios CSV mensuales con la cobertura mediatica bilateral PY-US
segun la regla "proxy B" - una fila por (mes, source_country), donde
source_country puede ser "PY", "US" o "BOTH" (coocurrencia geografica de
ambos paises en el mismo articulo, que es la señal bilateral que interesa
a este proyecto).

Solo se usan los archivos con prefijo "monthly_" - tilan sin huecos ni
superposicion todo el rango feb-2015 a ene-2026 (confirmado a mano el
2026-09-03, comparando los rangos de fecha en cada nombre de archivo).
"historical_processed_*.csv" queda afuera a proposito: es un archivo
redundante con esos mismos meses (el conglomerado de todos los monthly_,
ver gdelt_extraction/README.md) - usarlo ademas de los "monthly_"
duplicaria esos meses.

**Tres variantes por metrica, una por cada valor de `source_country`
(politica 2026-09-09, a pedido del usuario - antes solo se usaba "BOTH",
perdiendo la distincion de si la cobertura viene de medios paraguayos o
estadounidenses):**
    - `source_country == "BOTH"`: el TOTAL de articulos proxy-B de ese mes,
      sumando los de fuente PY y los de fuente US - no es una tercera
      categoria de articulos, es la union de las otras dos (verificado
      2026-09-09 contra un CSV real: mes 2026-01, BOTH=241 = PY(238) +
      US(3) exacto - ver gdelt_queries.py, `expanded` hace
      `CROSS JOIN UNNEST([s.source_country, 'BOTH'])`, cada articulo
      seleccionado se cuenta una vez bajo su propio pais y otra vez bajo
      "BOTH"). El tono de BOTH tampoco es el promedio de tono(PY) y
      tono(US): es el promedio de tono pooled sobre TODOS los articulos de
      ambos paises juntos (por eso, si un mes tiene 238 articulos PY y solo
      3 US, el tono de BOTH queda mucho mas cerca del tono de PY que de un
      promedio simple 50/50 entre los dos).
    - `source_country == "PY"`: solo articulos cuyo dominio de origen esta
      verificado como paraguayo en el catalogo de fuentes (ver
      gdelt_extraction/README.md, "PY/US es pais de fuente, no direccion
      de la interaccion").
    - `source_country == "US"`: idem, dominio verificado como
      estadounidense.

Para cada uno de los 3, dos variables (mismo calculo, ver `_extraer_gdelt()`):
    - `gdelt_proxy_articles[_py|_us]`: suma de `proxy_articles` (cantidad
      de articulos que matchean la regla proxy B) de los meses del
      trimestre. Tipo "cantidad". La variable sin sufijo (BOTH) no cambio
      de nombre, para no romper la carpeta de Drive ya existente.
    - `gdelt_tone_promedio[_py|_us]`: promedio de `tone_mean` de esos
      mismos meses, ponderado por `proxy_articles` de cada mes (para no
      pesar igual un mes con 0 articulos que uno con 200) - None si el
      trimestre no tuvo ningun articulo de ese pais. Tipo "indice" (tono
      GDELT, no una unidad monetaria ni un conteo).

Rango: ANIO_MINIMO en adelante. Cada variable se sube por separado, con la
fecha de la corrida en el nombre (idempotente por dia) - no escribe nada a
disco local.
"""
import io

import pandas as pd

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos
from src.processing._common import subir_variable

DIMENSION_CRUDA = "4_Visibilidad_mediatica_y_relevancia_publica"
DIMENSION_LIMPIA = "4_Visibilidad_mediatica_y_relevancia_publica_limpias"
FUENTE = "gdelt_proxy_b"

ANIO_MINIMO = 2015


SUFIJO_VARIABLE = {"BOTH": "", "PY": "_py", "US": "_us"}


def _extraer_gdelt():
    """Devuelve {"BOTH"/"PY"/"US": (articulos, tone_ponderado)}, cada una
    {(anio,trim): valor} - tone_ponderado solo tiene clave para los
    trimestres con al menos 1 articulo de ese pais (ver docstring del
    modulo para que significa cada uno de los 3)."""
    carpeta_id = FOLDER_IDS[(DIMENSION_CRUDA, FUENTE)]
    archivos = [a for a in listar_archivos(carpeta_id) if a["name"].startswith("monthly_")]

    filas = []
    for archivo in archivos:
        contenido = descargar_archivo(archivo["id"])
        filas.append(pd.read_csv(io.BytesIO(contenido)))

    todo = pd.concat(filas, ignore_index=True)
    todo["month"] = pd.to_datetime(todo["month"])
    todo = todo[todo["month"].dt.year >= ANIO_MINIMO]
    todo["trimestre_clave"] = list(zip(todo["month"].dt.year, (todo["month"].dt.month - 1) // 3 + 1))

    resultado = {}
    for pais in SUFIJO_VARIABLE:
        subset = todo[todo["source_country"] == pais]
        articulos, tone_ponderado = {}, {}
        for clave, grupo in subset.groupby("trimestre_clave"):
            total_articulos = int(grupo["proxy_articles"].sum())
            articulos[clave] = total_articulos
            if total_articulos > 0:
                tone_ponderado[clave] = (grupo["tone_mean"].fillna(0) * grupo["proxy_articles"]).sum() / total_articulos
        resultado[pais] = (articulos, tone_ponderado)

    return resultado


def run():
    print(f"[{DIMENSION_LIMPIA}]")
    try:
        resultado = _extraer_gdelt()
    except Exception as exc:  # noqa: BLE001
        print(f"    [!] gdelt_proxy_b: {exc!r}")
        return

    for pais, sufijo in SUFIJO_VARIABLE.items():
        articulos, tone_ponderado = resultado[pais]
        subir_variable(DIMENSION_LIMPIA, f"gdelt_proxy_articles{sufijo}", articulos, "cantidad")
        subir_variable(DIMENSION_LIMPIA, f"gdelt_tone_promedio{sufijo}", tone_ponderado, "indice")


if __name__ == "__main__":
    run()
