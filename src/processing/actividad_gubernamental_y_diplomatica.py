"""
Limpieza/consolidacion de la dimension 2 (Actividad gubernamental y
diplomatica) en un CSV trimestral por variable (ver src/processing/_common.py
para la convencion de salida: una carpeta por variable, esquema fijo
trimestre/anio/trimestre_num/valor/unidad).

A diferencia de la dimension 3 (todas variables monetarias, ver
compromiso_economico_privado.py), las 3 fuentes de esta dimension son de
tipo "cantidad": conteo de eventos/proyectos por trimestre, no montos - no
hace falta reescalar nada, la unidad de las 3 es literalmente "cantidad".

Fuentes y como se tratan (confirmado con datos reales el 2026-09-03,
congreso_menciones_paraguay rediseñado 2026-09-10):
    - congreso_menciones_paraguay (un Excel, una fila por proyecto de ley/
      resolucion del Congreso de EE.UU. que menciona a Paraguay, con la
      columna `cantidad_menciones_paraguay` que agrega
      `congreso_menciones_paraguay.py` desde 2026-09-10 - cuantas veces
      aparece "Paraguay" en el texto completo, no solo si aparece):
      **dos variables**, no una (mismo patron que fa_gov en
      compromiso_financiero_oficial.py - una fuente, dos series):
        - `congreso_proyectos_relevantes_paraguay`: cantidad de proyectos
          por trimestre (segun `fecha_introduccion`) con
          `cantidad_menciones_paraguay > UMBRAL_MENCIONES_RELEVANTE` (3).
          El umbral es un proxy de que Paraguay es un tema central del
          proyecto, no una mencion de paso (ver docstring de
          `congreso_menciones_paraguay.py` para el piloto real que lo
          valido - saliency theory del Comparative Manifestos Project:
          los proyectos con "Paraguay" en el titulo promediaron 12
          menciones contra 1.14 de los que lo mencionan de paso).
        - `congreso_menciones_totales_paraguay`: suma de
          `cantidad_menciones_paraguay` de TODOS los proyectos de ese
          trimestre (relevantes o no) - una medida continua de volumen de
          mencion, sin el umbral, complementaria a la anterior.
      **Reemplaza** a la variable `congreso_proyectos_mencion_paraguay`
      (conteo simple de proyectos, sin distinguir mencion de paso de
      mencion central) que existia hasta el 2026-09-09 - su carpeta de
      Drive queda huerfana, el servicio no puede borrarla (rol Writer).
    - ustr_consejo_comercio_inversion (un Excel, una fila por hito del
      Consejo de Comercio e Inversion o antecedente): cantidad de hitos por
      trimestre segun `fecha`. Fuente muy dispersa (pocos eventos en total
      desde 2015) - la mayoria de los trimestres van a quedar en 0/ausentes.
    - state_gov_tias_paraguay: **rediseñada 2026-09-29, ya no es la fuente
      de datos de `state_gov_tias_vigentes`** (a pedido del usuario - "no
      eliminemos la variable, pero reconstruyamosla con la info del TIF").
      `_extraer_tias()` ahora filtra el archivo de `state_gov_tif_vigentes`
      (ver mas abajo) a las filas cuya `cita` contiene "TIAS", en vez de
      leer el Excel que sube este modulo - ver el detalle completo mas
      abajo, junto a `state_gov_tif_vigentes`. El modulo de ingestion
      (`src/ingestion/state_gov_tias_paraguay.py`) queda en el repo sin
      tocar, simplemente processing ya no lo usa.
    - mre_menciones_eeuu (2026-09-22, un CSV `noticias_clasificadas_*.csv`,
      una fila por noticia del archivo del MRE de Paraguay): **dos
      variables**, mismo patron que Congreso - `mre_noticias_bilaterales`
      (cantidad por trimestre con `es_bilateral == 1`, clasificacion ya
      calculada en `mre_scraping/clasificar_bilateral.py` con reglas
      explicitas y sin IA - a diferencia de Congreso, el umbral de
      relevancia ya viene aplicado en el dato crudo, no hace falta
      reaplicarlo acá) y `mre_menciones_totales_eeuu` (suma de
      `numero_menciones_eeuu` de todas las noticias validas del trimestre,
      sin umbral). Es la contraparte del lado paraguayo de USTR/Congreso
      (que miden actividad diplomatica/legislativa del lado de EE.UU.) -
      ver `mre_scraping/README.md` para el detalle completo de como se
      recolecta (scraping local, no vive en `src/ingestion/` por el mismo
      motivo que `gdelt_extraction/`).

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

**`state_gov_tif_vigentes` (agregada 2026-09-22):** stock acumulado de
TODOS los tratados y acuerdos bilaterales EE.UU.-Paraguay que siguen
vigentes segun "Treaties in Force" (TIF), la publicacion oficial anual del
Departamento de Estado - ver `state_gov_tif_vigentes.py` para el detalle
completo de como se extrae. A diferencia del enfoque original de
`state_gov_tias_vigentes`, no se limita a instrumentos con numero TIAS ni a
firmas posteriores a 2015 - incluye acuerdos vigentes firmados desde 1860.
Por eso su acumulado usa `_acumular_con_base_historica()` en vez de
`_acumular_por_trimestre()`: la base de 2015-Q1 ya arranca en 33 (los
acuerdos firmados antes de 2015 que seguian vigentes), no en 0.
**Verificacion de que no es redundante con
`ustr_hitos_consejo_comercio_inversion` (2026-09-22):** correlacion en
niveles 0,86 (esperable, ambas series solo crecen en el tiempo - efecto de
tendencia compartida, no de comovimiento real), pero en primeras
diferencias (¿coincide el trimestre en que aparece un acuerdo nuevo del TIF
con el trimestre de un hito de USTR?) la correlacion cae a 0,07 - son
estadisticamente independientes, confirmando que miden cosas distintas
(stock legal de cualquier tema vs. hitos diplomaticos puntuales solo de
comercio/inversion). Ver `DICCIONARIO_VARIABLES.md` para el detalle
completo del analisis. **Nota de definicion, no inconsistencia:** la TIFA
es el mismo instrumento en ambas fuentes, pero USTR la fecha por *firma*
(2017-01-13) y el TIF por *entrada en vigor* (2021-03-17) - los ~4 anios de
diferencia son el tramite de ratificacion, no un error de ninguna de las
dos fuentes.

**`state_gov_tias_vigentes`, rediseñada 2026-09-29 para usar el TIF como
fuente (a pedido del usuario - no se elimina la variable, se reconstruye):**
antes leia el Excel que sube `state_gov_tias_paraguay.py` (busqueda en vivo
por DuckDuckGo, encontraba solo 3 TIAS, los 3 posteriores a 2015 - por eso
el stock arrancaba en 0 en 2015-Q1 y el docstring de `_extraer_tias()`
dejaba explicito el supuesto no verificado de que ningun TIAS se daba de
baja). Ahora `_extraer_tias()` filtra el mismo archivo de
`state_gov_tif_vigentes` a las filas cuya columna `cita` contiene "TIAS"
(29 de los 39 acuerdos - el resto son citas "TS"/"NP"/sin numero, no TIAS)
y les aplica `_acumular_con_base_historica()`, el mismo metodo que usa
`_extraer_tif()`. Dos mejoras de una sola vez, verificadas con datos reales
2026-09-29:
    1. **Base historica real**: de los 29 TIAS filtrados, 26 son anteriores
       a 2015 (el mas viejo, 1947) y 3 son 2015 en adelante - la base de
       2015-Q1 pasa de 0 a **26**, en vez de ignorar todo lo firmado antes.
    2. **Se hereda la garantia de "vigente" del TIF**: como el DOS ya
       excluye del TIF lo terminado/reemplazado antes de publicarlo, el
       supuesto de "ningun TIAS se da de baja" que tenia la version vieja
       queda resuelto, no solo documentado - la misma razon por la que TIF
       no lo necesita.
    Los 3 TIAS posteriores a 2015 que arroja el filtro son exactamente los
    mismos 3 que ya conocia el scraper original (TIFA 2021-03-17, cooperacion
    aduanera/policial 2021-10-22, migracion 2025-08-14) - confirma que no se
    pierde ningun TIAS conocido al cambiar de fuente, solo se gana la base
    pre-2015. El modulo `state_gov_tias_paraguay.py` (ingestion) queda en el
    repo sin usar por processing - el usuario decidio no eliminarlo por
    ahora ("vamos a dejarlo").

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
UMBRAL_MENCIONES_RELEVANTE = 3  # ver docstring del modulo (piloto 2026-09-10)


def _excel_mas_reciente(fuente):
    carpeta_id = FOLDER_IDS[(DIMENSION_CRUDA, fuente)]
    archivos = listar_archivos(carpeta_id)
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    contenido = descargar_archivo(archivo["id"])
    return pd.read_excel(io.BytesIO(contenido))


def _csv_mas_reciente(fuente, prefijo_nombre):
    """Igual que _excel_mas_reciente pero para CSV, filtrando primero por
    prefijo - mre_menciones_eeuu.py sube mas de un archivo por corrida
    (noticias_clasificadas_*.csv y manifiesto_*.json), hace falta elegir
    cual de los dos."""
    carpeta_id = FOLDER_IDS[(DIMENSION_CRUDA, fuente)]
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


def _extraer_congreso():
    """Devuelve (proyectos_relevantes, menciones_totales), cada una
    {(anio,trim): cantidad} segun trimestre de `fecha_introduccion` - ver
    docstring del modulo para la definicion de cada una y por que son dos
    variables separadas en vez de una."""
    df = _excel_mas_reciente("congreso_menciones_paraguay")
    fechas = pd.to_datetime(df["fecha_introduccion"], errors="coerce")
    menciones = pd.to_numeric(df["cantidad_menciones_paraguay"], errors="coerce")

    valido = fechas.notna() & menciones.notna() & (fechas.dt.year >= ANIO_MINIMO)
    fechas = fechas[valido]
    menciones = menciones[valido]

    proyectos_relevantes, menciones_totales = {}, {}
    for fecha, cantidad in zip(fechas, menciones):
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        menciones_totales[clave] = menciones_totales.get(clave, 0) + cantidad
        if cantidad > UMBRAL_MENCIONES_RELEVANTE:
            proyectos_relevantes[clave] = proyectos_relevantes.get(clave, 0) + 1

    return proyectos_relevantes, menciones_totales


def _extraer_ustr():
    df = _excel_mas_reciente("ustr_consejo_comercio_inversion")
    return _contar_por_trimestre(df["fecha"])


def _extraer_tias():
    """Devuelve el STOCK acumulado de TIAS (Treaties and Other International
    Acts Series) de Paraguay vigentes por trimestre, con base historica
    pre-2015 - rediseñada 2026-09-29 para leer de `state_gov_tif_vigentes`
    en vez de `state_gov_tias_paraguay` (ver docstring del modulo para el
    detalle completo de por que y que cambia).

    Filtra el archivo ya subido por state_gov_tif_vigentes.py (39 acuerdos,
    cualquier tipo de cita) a solo las filas cuya `cita` contiene "TIAS" (29
    de 39 - verificado 2026-09-29: 26 anteriores a 2015, que pasan a formar
    la base de 2015-Q1 via _acumular_con_base_historica(), y 3 desde 2015 en
    adelante, los mismos 3 que ya encontraba el scraper original)."""
    df = _excel_mas_reciente("state_gov_tif_vigentes")
    es_tias = df["cita"].astype(str).str.contains("TIAS", na=False)
    return _acumular_con_base_historica(df.loc[es_tias, "fecha_entrada_vigor"])


def _acumular_con_base_historica(fechas):
    """Devuelve el STOCK acumulado por trimestre, igual que un conteo con
    stock normal, pero sin descartar los eventos anteriores a ANIO_MINIMO:
    los suma todos a una BASE que ya arranca activa en el primer trimestre
    (2015-Q1), en vez de ignorarlos. Usada por _extraer_tif() (39 acuerdos,
    el mas viejo de 1860) y por _extraer_tias() (el subconjunto de esos 39
    con cita TIAS) - las dos fuentes de esta dimension que tienen eventos
    anteriores a 2015 que siguen vigentes hoy."""
    fechas = pd.to_datetime(fechas, errors="coerce").dropna()
    base = int((fechas.dt.year < ANIO_MINIMO).sum())
    fechas_en_rango = fechas[fechas.dt.year >= ANIO_MINIMO]

    nuevos_por_trimestre = {}
    for fecha in fechas_en_rango:
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        nuevos_por_trimestre[clave] = nuevos_por_trimestre.get(clave, 0) + 1

    hoy = datetime.now(timezone.utc)
    ultimo_trim = (hoy.year, (hoy.month - 1) // 3 + 1)

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
    state_gov_tif_vigentes.py). La base de 2015-Q1 incluye los 33 (de 39
    conocidos al 2026-09-22) acuerdos firmados ANTES de 2015 que seguian
    vigentes - por eso usa _acumular_con_base_historica(). _extraer_tias()
    es el mismo calculo sobre el subconjunto de estos 39 con cita TIAS."""
    df = _excel_mas_reciente("state_gov_tif_vigentes")
    return _acumular_con_base_historica(df["fecha_entrada_vigor"])


def _extraer_mre():
    """Devuelve (noticias_bilaterales, menciones_totales), cada una
    {(anio,trim): cantidad} - mismo patron que Congreso (una fuente, dos
    variables: conteo con umbral de relevancia + volumen total sin umbral).

    Fuente: mre_scraping/ (scraper de noticias del MRE de Paraguay +
    clasificacion bilateral, ver mre_scraping/README.md), subido por
    src/ingestion/mre_menciones_eeuu.py como `noticias_clasificadas_*.csv` -
    una fila por noticia, con columnas `estado` (solo "ok" entra al calculo,
    mismo criterio que descarta "error_descarga"/"fuera_periodo"/etc en el
    propio scraper), `es_bilateral` (0/1, ya calculado por
    mre_scraping/clasificar_bilateral.py con reglas explicitas, sin IA) y
    `numero_menciones_eeuu` (cuantas veces aparece una variante de "Estados
    Unidos" en titulo+texto).

    `noticias_bilaterales`: cantidad de noticias por trimestre (segun
    `fecha`) con `es_bilateral == 1` - la clasificacion ya incorpora el
    umbral de relevancia (puntaje >= `umbral_bilateral` en
    reglas_bilaterales.json), asi que a diferencia de Congreso acá no hace
    falta aplicar un segundo umbral en processing, ya viene aplicado.
    `menciones_totales`: suma de `numero_menciones_eeuu` de TODAS las
    noticias validas del trimestre (bilaterales o no) - medida continua de
    volumen, sin umbral, igual que `congreso_menciones_totales_paraguay`."""
    df = _csv_mas_reciente("mre_menciones_eeuu", "noticias_clasificadas")
    df = df[df["estado"] == "ok"].copy()
    fechas = pd.to_datetime(df["fecha"], errors="coerce")
    es_bilateral = pd.to_numeric(df["es_bilateral"], errors="coerce")
    menciones = pd.to_numeric(df["numero_menciones_eeuu"], errors="coerce")

    valido = fechas.notna() & (fechas.dt.year >= ANIO_MINIMO)
    fechas = fechas[valido]
    es_bilateral = es_bilateral[valido]
    menciones = menciones[valido]

    noticias_bilaterales, menciones_totales = {}, {}
    for fecha, bilateral, cantidad in zip(fechas, es_bilateral, menciones):
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        menciones_totales[clave] = menciones_totales.get(clave, 0) + (cantidad if pd.notna(cantidad) else 0)
        if bilateral == 1:
            noticias_bilaterales[clave] = noticias_bilaterales.get(clave, 0) + 1

    return noticias_bilaterales, menciones_totales


def run():
    print(f"[{DIMENSION_LIMPIA}]")

    try:
        proyectos_relevantes, menciones_totales = _extraer_congreso()
        subir_variable(DIMENSION_LIMPIA, "congreso_proyectos_relevantes_paraguay", proyectos_relevantes, "cantidad")
        subir_variable(DIMENSION_LIMPIA, "congreso_menciones_totales_paraguay", menciones_totales, "cantidad")
    except Exception as exc:  # noqa: BLE001
        print(f"    [!] congreso_menciones_paraguay: {exc!r}")

    for nombre_variable, extraer in (
        ("ustr_hitos_consejo_comercio_inversion", _extraer_ustr),
        ("state_gov_tias_vigentes", _extraer_tias),
        ("state_gov_tif_vigentes", _extraer_tif),
    ):
        try:
            subir_variable(DIMENSION_LIMPIA, nombre_variable, extraer(), "cantidad")
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] {nombre_variable}: {exc!r}")

    try:
        noticias_bilaterales, menciones_totales_mre = _extraer_mre()
        subir_variable(DIMENSION_LIMPIA, "mre_noticias_bilaterales", noticias_bilaterales, "cantidad")
        subir_variable(DIMENSION_LIMPIA, "mre_menciones_totales_eeuu", menciones_totales_mre, "cantidad")
    except Exception as exc:  # noqa: BLE001
        print(f"    [!] mre_menciones_eeuu: {exc!r}")


if __name__ == "__main__":
    run()
