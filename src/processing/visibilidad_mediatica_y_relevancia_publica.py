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
superposicion todo el rango feb-2015 a dic-2025 (confirmado a mano el
2026-09-03, comparando los rangos de fecha en cada nombre de archivo).
"historical_processed_2015-02_2020-03.csv" queda afuera a proposito: es un
archivo redundante con esos mismos meses (una corrida vieja/intermedia del
extractor, ver gdelt_extraction/README.md) - usarlo ademas de los
"monthly_" duplicaria esos meses.

Dos variables por trimestre, ambas de la fila source_country == "BOTH":
    - `gdelt_proxy_articles_cantidad`: suma de `proxy_articles` (cantidad
      de articulos que matchean la regla proxy B) de los meses del
      trimestre. Tipo "cantidad".
    - `gdelt_tone_promedio_indice`: promedio de `tone_mean` de esos mismos
      meses, ponderado por `proxy_articles` (para no pesar igual un mes
      con 0 articulos que uno con 200) - None si el trimestre no tuvo
      ningun articulo. Tipo "indice" (tono GDELT, no una unidad monetaria
      ni un conteo).

Rango: ANIO_MINIMO en adelante. Cada variable se sube por separado, con la
fecha de la corrida en el nombre (idempotente por dia) - no escribe nada a
disco local.
"""
import io

import pandas as pd

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos
from src.processing._common import subir_variable

DIMENSION_CRUDA = "4.Visibilidad_mediática_y_relevancia_publica"
DIMENSION_LIMPIA = "4.Visibilidad_mediática_y_relevancia_publica_limpias"
FUENTE = "gdelt_proxy_b"

ANIO_MINIMO = 2015


def _extraer_gdelt():
    """Devuelve (articulos, tone_ponderado), cada una {(anio,trim): valor} -
    la segunda solo tiene clave para los trimestres con al menos 1 articulo."""
    carpeta_id = FOLDER_IDS[(DIMENSION_CRUDA, FUENTE)]
    archivos = [a for a in listar_archivos(carpeta_id) if a["name"].startswith("monthly_")]

    filas = []
    for archivo in archivos:
        contenido = descargar_archivo(archivo["id"])
        df = pd.read_csv(io.BytesIO(contenido))
        filas.append(df[df["source_country"] == "BOTH"])

    todo = pd.concat(filas, ignore_index=True)
    todo["month"] = pd.to_datetime(todo["month"])
    todo = todo[todo["month"].dt.year >= ANIO_MINIMO]
    todo["trimestre_clave"] = list(zip(todo["month"].dt.year, (todo["month"].dt.month - 1) // 3 + 1))

    articulos, tone_ponderado = {}, {}
    for clave, grupo in todo.groupby("trimestre_clave"):
        total_articulos = int(grupo["proxy_articles"].sum())
        articulos[clave] = total_articulos
        if total_articulos > 0:
            tone_ponderado[clave] = (grupo["tone_mean"].fillna(0) * grupo["proxy_articles"]).sum() / total_articulos

    return articulos, tone_ponderado


def run():
    print(f"[{DIMENSION_LIMPIA}]")
    try:
        articulos, tone_ponderado = _extraer_gdelt()
    except Exception as exc:  # noqa: BLE001
        print(f"    [!] gdelt_proxy_b: {exc!r}")
        return

    subir_variable(DIMENSION_LIMPIA, "gdelt_proxy_articles", articulos, "cantidad")
    subir_variable(DIMENSION_LIMPIA, "gdelt_tone_promedio", tone_ponderado, "indice")


if __name__ == "__main__":
    run()
