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
      **stock acumulado** de TIAS vigentes por trimestre (politica
      2026-09-10, a pedido del usuario - antes era cantidad de TIAS NUEVOS
      ese trimestre, igual de disperso que USTR, lo cual no calzaba con el
      propio nombre de la variable, "vigentes"). Ver `_acumular_por_trimestre()`.

**Por que un stock y no un conteo de eventos, solo para TIAS (2026-09-10):**
un tratado, a diferencia de una reunion o un proyecto de ley, tiene efecto
legal que persiste despues de entrar en vigor - "cuantos TIAS estan
vigentes hoy" es exactamente como el propio Departamento de Estado mide
esto en su publicacion anual "Treaties in Force" (lista lo que sigue
vigente, no solo lo firmado ese año), y es el enfoque estandar en la
literatura de relaciones internacionales para tratados bilaterales (ej. el
World Treaty Index usa el stock de acuerdos vigentes para operacionalizar
relaciones bilaterales). Congreso y USTR NO se cambiaron a este enfoque:
una reunion o un proyecto de ley no tiene "vigencia" en el mismo sentido -
ocurren y terminan, no hay un estado legal que persista despues.

**Limite explicito, no verificado:** `_acumular_por_trimestre()` asume que
ningun TIAS se da de baja (terminado/reemplazado/vencido) despues de
entrar en vigor - no hay ningun mecanismo que lo detecte. La fuente que
trackearia esto formalmente es el reporte anual "Treaties in Force" del
Departamento de Estado, pero no es lo que scrapea
`state_gov_tias_paraguay.py` (investigado 2026-09-10: `www.state.gov`
devuelve 403 al pedirlo sin el bypass de Cloudflare que ya usa el resto de
state.gov, y una edicion vieja probada es un PDF escaneado como imagen, no
texto extraible - agregarlo seria un modulo de ingestion nuevo y separado,
no algo que este calculo resuelva). No es un problema practico hoy (ninguno
de los 3 TIAS conocidos esta documentado como terminado), pero queda como
supuesto explicito, no como algo confirmado.

Se usa el archivo mas reciente subido por ingestion de cada fuente (todas
suben un Excel nuevo por dia con fecha en el nombre).

Rango: ANIO_MINIMO en adelante. Cada variable se sube por separado, con la
fecha de la corrida en el nombre (idempotente por dia) - no escribe nada a
disco local.
"""
import io
from datetime import datetime, timezone

import pandas as pd

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos
from src.processing._common import subir_variable

DIMENSION_CRUDA = "2_Actividad_gubernamental_y_diplomatica"
DIMENSION_LIMPIA = "2_Actividad_gubernamental_y_diplomatica_limpias"

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


def _acumular_por_trimestre(fechas):
    """Devuelve {(anio,trim): cantidad ACUMULADA} - a diferencia de
    _contar_por_trimestre, no es cuantos eventos son NUEVOS ese trimestre,
    es un stock: cuantos ya estaban vigentes a esa fecha, repitiendo el
    ultimo acumulado en los trimestres sin eventos nuevos (para que no
    queden huecos entre un evento y el siguiente). Cubre desde el trimestre
    del primer evento hasta el trimestre actual (no hasta donde llega la
    fuente - el stock sigue siendo valido despues del ultimo evento
    conocido). Ver docstring del modulo para el supuesto de que ningun
    evento se da de baja."""
    eventos = _contar_por_trimestre(fechas)
    if not eventos:
        return {}

    anio, trim = min(eventos)
    hoy = datetime.now(timezone.utc)
    ultimo_trim = (hoy.year, (hoy.month - 1) // 3 + 1)

    acumulado = {}
    total = 0
    while (anio, trim) <= ultimo_trim:
        total += eventos.get((anio, trim), 0)
        acumulado[(anio, trim)] = total
        trim += 1
        if trim > 4:
            trim = 1
            anio += 1
    return acumulado


def _extraer_tias():
    """Devuelve el STOCK acumulado de TIAS vigentes por trimestre (no la
    cantidad de TIAS nuevos ese trimestre) - ver docstring del modulo,
    politica 2026-09-10."""
    df = _excel_mas_reciente("state_gov_tias_paraguay")
    return _acumular_por_trimestre(df["fecha_entrada_vigor"])


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
