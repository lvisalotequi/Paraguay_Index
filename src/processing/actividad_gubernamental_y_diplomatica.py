"""
Limpieza/consolidacion de la dimension 2 (Actividad gubernamental y
diplomatica) en un CSV trimestral por variable (ver src/processing/_common.py
para la convencion de salida: una carpeta por variable, esquema fijo
trimestre/anio/trimestre_num/valor/unidad).

A diferencia de la dimension 3 (todas variables monetarias, ver
compromiso_economico_privado.py), las 3 fuentes de esta dimension son de
tipo "cantidad": conteo de eventos/proyectos por trimestre, no montos - no
hace falta reescalar nada, la unidad de las 3 es literalmente "cantidad".

Fuentes y como se tratan (confirmado con datos reales el 2026-09-03):
    - congreso_menciones_paraguay (un Excel, una fila por proyecto de ley/
      resolucion del Congreso de EE.UU. que menciona a Paraguay): cantidad
      de proyectos por trimestre segun `fecha_introduccion`.
    - ustr_consejo_comercio_inversion (un Excel, una fila por hito del
      Consejo de Comercio e Inversion o antecedente): cantidad de hitos por
      trimestre segun `fecha`. Fuente muy dispersa (pocos eventos en total
      desde 2015) - la mayoria de los trimestres van a quedar en 0/ausentes.
    - state_gov_tias_paraguay (un Excel, una fila por TIAS de Paraguay):
      cantidad de TIAS por trimestre segun `fecha_entrada_vigor` (cuando el
      tratado entro en vigor, no cuando se firmo). Igual de dispersa que
      USTR.

Se usa el archivo mas reciente subido por ingestion de cada fuente (todas
suben un Excel nuevo por dia con fecha en el nombre).

Rango: ANIO_MINIMO en adelante. Cada variable se sube por separado, con la
fecha de la corrida en el nombre (idempotente por dia) - no escribe nada a
disco local.
"""
import io

import pandas as pd

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos
from src.processing._common import subir_variable

DIMENSION_CRUDA = "2.Actividad_gubernamental_y_diplomática"
DIMENSION_LIMPIA = "2.Actividad_gubernamental_y_diplomática_limpias"

ANIO_MINIMO = 2015


def _excel_mas_reciente(fuente):
    carpeta_id = FOLDER_IDS[(DIMENSION_CRUDA, fuente)]
    archivos = listar_archivos(carpeta_id)
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    contenido = descargar_archivo(archivo["id"])
    return pd.read_excel(io.BytesIO(contenido))


def _contar_por_trimestre(fechas):
    """Devuelve {(anio,trim): cantidad de filas} a partir de una Serie de fechas."""
    fechas = pd.to_datetime(fechas, errors="coerce").dropna()
    fechas = fechas[fechas.dt.year >= ANIO_MINIMO]

    conteo = {}
    for fecha in fechas:
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        conteo[clave] = conteo.get(clave, 0) + 1
    return conteo


def _extraer_congreso():
    df = _excel_mas_reciente("congreso_menciones_paraguay")
    return _contar_por_trimestre(df["fecha_introduccion"])


def _extraer_ustr():
    df = _excel_mas_reciente("ustr_consejo_comercio_inversion")
    return _contar_por_trimestre(df["fecha"])


def _extraer_tias():
    df = _excel_mas_reciente("state_gov_tias_paraguay")
    return _contar_por_trimestre(df["fecha_entrada_vigor"])


def run():
    print(f"[{DIMENSION_LIMPIA}]")

    for nombre_variable, extraer in (
        ("congreso_proyectos_mencion_paraguay", _extraer_congreso),
        ("ustr_hitos_consejo_comercio_inversion", _extraer_ustr),
        ("state_gov_tias_vigentes", _extraer_tias),
    ):
        try:
            subir_variable(DIMENSION_LIMPIA, nombre_variable, extraer(), "cantidad")
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] {nombre_variable}: {exc!r}")


if __name__ == "__main__":
    run()
