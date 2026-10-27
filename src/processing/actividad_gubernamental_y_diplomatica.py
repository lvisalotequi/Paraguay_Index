#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 03/09/2026                                                #
# NOMBRE: actividad_gubernamental_y_diplomatica                                #
# DETALLE: lleva a trimestres las 4 fuentes de la dimension 2 y las deja en 7  #
#   variables de tipo cantidad: Congreso de EE.UU. (2), USTR (1), tratados     #
#   vigentes TIAS y TIF del Departamento de Estado (2, stock acumulado) y MRE  #
#   de Paraguay (2). NO consulta ninguna API: lee solo los crudos de Drive.    #
#                                                                              #
# CORRE DESPUES DE: ingestion de congreso_menciones_paraguay,                  #
#   ustr_consejo_comercio_inversion, state_gov_tif_vigentes y                  #
#   mre_menciones_eeuu (src/ingestion/)                                        #
# SALIDA: un CSV por variable (7) en                                           #
#   02_limpias/2_Actividad_gubernamental_y_diplomatica_limpias/<variable>/     #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
from datetime import datetime, timezone

import pandas as pd

from src.drive import descargar_archivo, listar_archivos, resolve_ingestion_folder
from src.processing._common import subir_variable



# Parametros -------------------------------------------------------------------

# Carpetas de Drive: las crudas las escribe ingestion y las limpias este modulo.
DIMENSION_CRUDA  = "2_Actividad_gubernamental_y_diplomatica"
DIMENSION_LIMPIA = "2_Actividad_gubernamental_y_diplomatica_limpias"

ANIO_MINIMO = 2015

# Cantidad de menciones de "Paraguay" por encima de la cual un proyecto del Congreso
# cuenta como relevante (ver el comentario de la seccion Congreso, piloto 2026-09-10).
UMBRAL_MENCIONES_RELEVANTE = 3



# Funciones auxiliares ---------------------------------------------------------

# A diferencia de la dimension 3 (todas variables monetarias, ver
# compromiso_economico_privado.py), las 7 variables de esta dimension son de tipo
# "cantidad": conteos de eventos o proyectos por trimestre, no montos. No hace falta
# reescalar nada: la unidad de todas es literalmente "cantidad".
#
# De cada fuente se usa el archivo mas reciente que subio ingestion (todas suben uno
# nuevo por dia, con la fecha en el nombre).


def _excel_mas_reciente(fuente):
    carpeta_id = resolve_ingestion_folder(DIMENSION_CRUDA, fuente)
    archivos = listar_archivos(carpeta_id)
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    contenido = descargar_archivo(archivo["id"])
    return pd.read_excel(io.BytesIO(contenido))


def _csv_mas_reciente(fuente, prefijo_nombre):
    """Igual que _excel_mas_reciente pero para CSV, filtrando primero por
    prefijo - mre_menciones_eeuu.py sube mas de un archivo por corrida
    (noticias_clasificadas_*.csv y manifiesto_*.json), hace falta elegir
    cual de los dos."""
    carpeta_id = resolve_ingestion_folder(DIMENSION_CRUDA, fuente)
    archivos = [a for a in listar_archivos(carpeta_id) if a["name"].startswith(prefijo_nombre)]
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    contenido = descargar_archivo(archivo["id"])
    return pd.read_csv(io.BytesIO(contenido))


def _contar_por_trimestre(fechas):
    """Devuelve {(anio,trim): cantidad de filas} a partir de una Serie de fechas."""
    fechas = pd.to_datetime(fechas, errors="coerce").dropna()
    fechas = fechas[fechas.dt.year >= ANIO_MINIMO]

    conteo = {}
    for fecha in fechas:
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        conteo[clave] = conteo.get(clave, 0) + 1
    return conteo



# Congreso de EE.UU. -----------------------------------------------------------

# Entrada: un Excel con una fila por proyecto de ley o resolucion del Congreso que
# menciona a Paraguay (congreso_menciones_paraguay). Desde el 2026-09-10 trae la columna
# `cantidad_menciones_paraguay`: cuantas veces aparece "Paraguay" en el texto completo,
# no solo si aparece.
#
# Salida: dos variables, no una (una fuente, dos series, el mismo patron que fa_gov en
# compromiso_financiero_oficial.py), ambas por trimestre de `fecha_introduccion`:
#   - congreso_proyectos_relevantes_paraguay: cantidad de proyectos con
#     `cantidad_menciones_paraguay > UMBRAL_MENCIONES_RELEVANTE`.
#   - congreso_menciones_totales_paraguay: suma de `cantidad_menciones_paraguay` de
#     TODOS los proyectos del trimestre, relevantes o no. Es una medida continua de
#     volumen, sin umbral, complementaria a la anterior.
#
# POR QUE UN UMBRAL DE 3 MENCIONES: es un proxy de que Paraguay es tema central del
# proyecto y no una mencion de paso (saliency theory del Comparative Manifestos
# Project). El piloto del 2026-09-10 lo valido: los proyectos con "Paraguay" en el
# titulo promediaron 12 menciones contra 1.14 de los que lo mencionan de paso (ver el
# docstring de congreso_menciones_paraguay.py).
#
# Reemplaza a `congreso_proyectos_mencion_paraguay` (conteo simple de proyectos, sin
# distinguir mencion de paso de mencion central), que existio hasta el 2026-09-09. Su
# carpeta de Drive quedo huerfana: el servicio no puede borrarla (rol Writer).


def _extraer_congreso():
    """Devuelve (proyectos_relevantes, menciones_totales), cada una
    {(anio,trim): cantidad} segun trimestre de `fecha_introduccion` - ver
    el comentario de la seccion para la definicion de cada una y por que son
    dos variables separadas en vez de una."""

    # 1. lee el Excel mas reciente y se queda con las filas validas desde ANIO_MINIMO
    df = _excel_mas_reciente("congreso_menciones_paraguay")
    fechas = pd.to_datetime(df["fecha_introduccion"], errors="coerce")
    menciones = pd.to_numeric(df["cantidad_menciones_paraguay"], errors="coerce")

    valido = fechas.notna() & menciones.notna() & (fechas.dt.year >= ANIO_MINIMO)
    fechas = fechas[valido]
    menciones = menciones[valido]

    # 2. suma las menciones de cada trimestre y cuenta los proyectos sobre el umbral
    proyectos_relevantes, menciones_totales = {}, {}
    for fecha, cantidad in zip(fechas, menciones):
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        menciones_totales[clave] = menciones_totales.get(clave, 0) + cantidad
        if cantidad > UMBRAL_MENCIONES_RELEVANTE:
            proyectos_relevantes[clave] = proyectos_relevantes.get(clave, 0) + 1

    return proyectos_relevantes, menciones_totales



# USTR: Consejo de Comercio e Inversion ----------------------------------------

# Entrada: un Excel con una fila por hito del Consejo de Comercio e Inversion (o
# antecedente), de ustr_consejo_comercio_inversion.
#
# Salida: ustr_hitos_consejo_comercio_inversion, la cantidad de hitos por trimestre segun
# `fecha`. Es una fuente muy dispersa (pocos eventos desde 2015): la mayoria de los
# trimestres quedan en 0 o ausentes.


def _extraer_ustr():
    df = _excel_mas_reciente("ustr_consejo_comercio_inversion")
    return _contar_por_trimestre(df["fecha"])



# Tratados vigentes del Departamento de Estado (TIAS y TIF) --------------------

# Entrada: el Excel de state_gov_tif_vigentes, con los 39 tratados y acuerdos bilaterales
# EE.UU.-Paraguay que siguen vigentes segun "Treaties in Force" (TIF), la publicacion
# oficial anual del Departamento de Estado (el mas viejo es de 1860). Sale de ahi tanto
# `state_gov_tif_vigentes` como `state_gov_tias_vigentes`.
#
# Salida: dos variables que son un STOCK acumulado por trimestre, no un conteo de
# eventos.
#   - state_gov_tif_vigentes: todos los acuerdos del TIF, de cualquier tipo de cita.
#   - state_gov_tias_vigentes: el subconjunto cuya `cita` contiene "TIAS" (29 de los 39;
#     el resto son citas "TS", "NP" o sin numero).
#
# POR QUE UN STOCK Y NO UN CONTEO DE EVENTOS (2026-09-10): un tratado, a diferencia de
# una reunion o un proyecto de ley, tiene efecto legal que persiste despues de entrar en
# vigor. "Cuantos acuerdos estan vigentes hoy" es como el propio Departamento de Estado
# mide esto en el TIF, y es el enfoque estandar para operacionalizar relaciones
# bilaterales (el World Treaty Index usa el stock de acuerdos vigentes). Se descarto
# aplicarlo tambien a Congreso y USTR: una reunion o un proyecto de ley ocurren y
# terminan, no dejan un estado legal que persista.
#
# POR QUE LA BASE DE 2015-Q1 NO ES 0: el stock no descarta lo firmado antes de ANIO_MINIMO
# sino que lo suma como base (_acumular_con_base_historica). Al 2026-09-22 la base del
# TIF es 33 acuerdos y la de TIAS, 26 (verificado el 2026-09-29; el mas viejo, de 1947).
# Ademas el DOS ya excluye del TIF lo terminado o reemplazado antes de publicarlo, asi
# que se hereda la garantia de "vigente" sin suponer que nada se da de baja.
#
# POR QUE TIAS SE RECONSTRUYO CON EL TIF (2026-09-29, a pedido del usuario: "no
# eliminemos la variable, pero reconstruyamosla con la info del TIF"): antes leia el
# Excel de state_gov_tias_paraguay.py (busqueda en vivo por DuckDuckGo), que solo
# encontraba 3 TIAS, todos posteriores a 2015. Por eso el stock arrancaba en 0 y dependia
# de un supuesto no verificado: que ningun TIAS se daba de baja. Los 3 TIAS desde 2015
# que arroja el filtro son los mismos 3 que ya conocia ese scraper (TIFA 2021-03-17,
# cooperacion aduanera y policial 2021-10-22, migracion 2025-08-14): no se pierde ninguno
# al cambiar de fuente. El modulo de ingestion state_gov_tias_paraguay.py queda en el repo
# sin que processing lo use (el usuario decidio no eliminarlo por ahora).
#
# POR QUE TIF NO ES REDUNDANTE CON USTR (verificado el 2026-09-22): la correlacion en
# niveles con ustr_hitos_consejo_comercio_inversion es 0,86, pero es un efecto de
# tendencia compartida (ambas solo crecen). En primeras diferencias, es decir si el
# trimestre en que aparece un acuerdo nuevo del TIF coincide con el de un hito de USTR,
# cae a 0,07: son estadisticamente independientes. Miden cosas distintas: stock legal de
# cualquier tema contra hitos diplomaticos puntuales de comercio e inversion (detalle en
# DICCIONARIO_VARIABLES.md). La TIFA aparece en ambas fuentes con fechas distintas, USTR
# la fecha por firma (2017-01-13) y el TIF por entrada en vigor (2021-03-17): los ~4
# anios son el tramite de ratificacion, no un error de ninguna.


def _extraer_tias():
    """Devuelve el STOCK acumulado de TIAS (Treaties and Other International
    Acts Series) de Paraguay vigentes por trimestre, con base historica
    pre-2015: filtra el archivo de state_gov_tif_vigentes a las filas cuya
    `cita` contiene "TIAS" (ver el comentario de la seccion)."""

    # 1. lee el TIF y se queda con las filas de cita TIAS
    df = _excel_mas_reciente("state_gov_tif_vigentes")
    es_tias = df["cita"].astype(str).str.contains("TIAS", na=False)

    # 2. acumula por trimestre, con los anteriores a 2015 como base
    return _acumular_con_base_historica(df.loc[es_tias, "fecha_entrada_vigor"])


def _acumular_con_base_historica(fechas):
    """Devuelve el STOCK acumulado por trimestre, igual que un conteo con
    stock normal, pero sin descartar los eventos anteriores a ANIO_MINIMO:
    los suma todos a una BASE que ya arranca activa en el primer trimestre
    (2015-Q1), en vez de ignorarlos. Usada por _extraer_tif() y por
    _extraer_tias() (el subconjunto del TIF con cita TIAS) - las dos fuentes
    de esta dimension que tienen eventos anteriores a 2015 que siguen
    vigentes hoy."""

    # 1. separa la base (anterior a ANIO_MINIMO) de los eventos del rango
    fechas = pd.to_datetime(fechas, errors="coerce").dropna()
    base = int((fechas.dt.year < ANIO_MINIMO).sum())
    fechas_en_rango = fechas[fechas.dt.year >= ANIO_MINIMO]

    # 2. cuenta los eventos nuevos de cada trimestre
    nuevos_por_trimestre = {}
    for fecha in fechas_en_rango:
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        nuevos_por_trimestre[clave] = nuevos_por_trimestre.get(clave, 0) + 1

    hoy = datetime.now(timezone.utc)
    ultimo_trim = (hoy.year, (hoy.month - 1) // 3 + 1)

    # 3. recorre los trimestres desde ANIO_MINIMO hasta el actual sumando a la base
    acumulado = {}
    total = base
    anio, trim = ANIO_MINIMO, 1
    while (anio, trim) <= ultimo_trim:
        total += nuevos_por_trimestre.get((anio, trim), 0)
        acumulado[(anio, trim)] = total
        trim += 1
        if trim > 4:
            trim = 1
            anio += 1
    return acumulado


def _extraer_tif():
    """Devuelve el STOCK acumulado de TODOS los tratados y acuerdos
    bilaterales vigentes EE.UU.-Paraguay por trimestre (no solo
    publicaciones TIAS, cualquier tipo de cita - ver
    state_gov_tif_vigentes.py). La base de 2015-Q1 incluye los acuerdos
    firmados ANTES de 2015 que seguian vigentes (33 de 39 al 2026-09-22) -
    por eso usa _acumular_con_base_historica()."""
    df = _excel_mas_reciente("state_gov_tif_vigentes")
    return _acumular_con_base_historica(df["fecha_entrada_vigor"])



# MRE de Paraguay --------------------------------------------------------------

# Entrada: un CSV `noticias_clasificadas_*.csv` con una fila por noticia del archivo del
# MRE de Paraguay (mre_menciones_eeuu, que sube lo que produce mre_scraping/; ver
# mre_scraping/README.md). Es la contraparte del lado paraguayo de USTR y Congreso, que
# miden actividad diplomatica y legislativa del lado de EE.UU. Solo entran las filas con
# `estado == "ok"`: el resto (error_descarga, fuera_periodo, etc.) ya las descarta el
# propio scraper.
#
# Salida: dos variables, el mismo patron que Congreso, ambas por trimestre de `fecha`:
#   - mre_noticias_bilaterales: cantidad de noticias con `es_bilateral == 1`, clasificacion
#     ya calculada por mre_scraping/clasificar_bilateral.py con reglas explicitas y sin
#     IA. A diferencia de Congreso, el umbral de relevancia (puntaje >= `umbral_bilateral`
#     en reglas_bilaterales.json) ya viene aplicado en el dato crudo, asi que processing
#     no aplica un segundo umbral.
#   - mre_menciones_totales_eeuu: suma de `numero_menciones_eeuu` (cuantas veces aparece
#     una variante de "Estados Unidos" en titulo y texto) de todas las noticias validas,
#     bilaterales o no. Es una medida continua de volumen, sin umbral.


def _extraer_mre():
    """Devuelve (noticias_bilaterales, menciones_totales), cada una
    {(anio,trim): cantidad} - mismo patron que Congreso (una fuente, dos
    variables: conteo con umbral de relevancia + volumen total sin umbral).
    Ver el comentario de la seccion para el detalle de cada una."""

    # 1. lee el CSV mas reciente y se queda con las noticias validas
    df = _csv_mas_reciente("mre_menciones_eeuu", "noticias_clasificadas")
    df = df[df["estado"] == "ok"].copy()
    fechas = pd.to_datetime(df["fecha"], errors="coerce")
    es_bilateral = pd.to_numeric(df["es_bilateral"], errors="coerce")
    menciones = pd.to_numeric(df["numero_menciones_eeuu"], errors="coerce")

    # 2. descarta las filas sin fecha y las anteriores a ANIO_MINIMO
    valido = fechas.notna() & (fechas.dt.year >= ANIO_MINIMO)
    fechas = fechas[valido]
    es_bilateral = es_bilateral[valido]
    menciones = menciones[valido]

    # 3. suma las menciones de cada trimestre y cuenta las noticias bilaterales
    noticias_bilaterales, menciones_totales = {}, {}
    for fecha, bilateral, cantidad in zip(fechas, es_bilateral, menciones):
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        menciones_totales[clave] = (
            menciones_totales.get(clave, 0) + (cantidad if pd.notna(cantidad) else 0)
        )
        if bilateral == 1:
            noticias_bilaterales[clave] = noticias_bilaterales.get(clave, 0) + 1

    return noticias_bilaterales, menciones_totales



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. avisa que dimension procesa
    print(f"[{DIMENSION_LIMPIA}]")
    errores = []

    # 2. Congreso: dos variables; una fuente que falla no frena a las otras
    try:
        proyectos_relevantes, menciones_totales = _extraer_congreso()
        subir_variable(
            DIMENSION_LIMPIA, "congreso_proyectos_relevantes_paraguay", proyectos_relevantes, "cantidad"
        )
        subir_variable(
            DIMENSION_LIMPIA, "congreso_menciones_totales_paraguay", menciones_totales, "cantidad"
        )
    except Exception as exc:  # noqa: BLE001
        errores.append(("congreso_menciones_paraguay", repr(exc)))
        print(f"    [!] congreso_menciones_paraguay: {exc!r}")

    # 3. USTR y tratados vigentes (TIAS y TIF): una variable por fuente
    for nombre_variable, extraer in (
        ("ustr_hitos_consejo_comercio_inversion", _extraer_ustr),
        ("state_gov_tias_vigentes", _extraer_tias),
        ("state_gov_tif_vigentes", _extraer_tif),
    ):
        try:
            subir_variable(DIMENSION_LIMPIA, nombre_variable, extraer(), "cantidad")
        except Exception as exc:  # noqa: BLE001
            errores.append((nombre_variable, repr(exc)))
            print(f"    [!] {nombre_variable}: {exc!r}")

    # 4. MRE de Paraguay: dos variables
    try:
        noticias_bilaterales, menciones_totales_mre = _extraer_mre()
        subir_variable(DIMENSION_LIMPIA, "mre_noticias_bilaterales", noticias_bilaterales, "cantidad")
        subir_variable(DIMENSION_LIMPIA, "mre_menciones_totales_eeuu", menciones_totales_mre, "cantidad")
    except Exception as exc:  # noqa: BLE001
        errores.append(("mre_menciones_eeuu", repr(exc)))
        print(f"    [!] mre_menciones_eeuu: {exc!r}")

    # 5. validacion: si fallo alguna fuente, termina con error despues de subir las otras
    if errores:
        raise RuntimeError(f"Fallaron {len(errores)} fuentes de {DIMENSION_LIMPIA}: {errores}")


if __name__ == "__main__":
    run()
