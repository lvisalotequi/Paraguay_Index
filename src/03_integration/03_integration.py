#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# RESPONSABLE DEL CODIGO:                                                      #
#   PIERO VALLES-MARAVI (ESPECIALISTA) - pvalles@equilibriumbdc.com            #
#                                                                              #
# FECHA DE CREACION: 09/09/2026                                                #
# NOMBRE: 03_integration                                                       #
# DETALLE: Trae de Drive los CSV ya limpios de 02_limpias (de las cuatro       #
#          dimensiones que ya tienen variables revisadas) y los deja en un     #
#          panel trimestral CUADRADO: todos los trimestres de 2015 a 2026      #
#          por todas las variables, con NA donde la fuente no tiene dato.      #
#          Aca NO se limpia nada (eso es 02_clean) ni se normaliza ni se       #
#          pondera nada (eso es 04_analysis_index).                            #
#                                                                              #
# CORRE DESPUES DE: 02_clean_compromiso_financiero_oficial.py y el resto de    #
#                   processing (las variables limpias ya tienen que estar en   #
#                   Drive)                                                     #
# SALIDA: Drive 03_integracion/ - el panel en formato largo y en formato       #
#         ancho, un CSV cada uno. El largo es lo que lee 04_analysis_index     #
#-----------------------------------------------------------------------------.#


# 0. SETUP -----

## 0.1. Entorno ---------------------------------------------------------------------

import io
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


## 0.2. Rutas y credenciales --------------------------------------------------------

RAIZ_REPO = Path.cwd()

while not (RAIZ_REPO / "src").is_dir() and RAIZ_REPO != RAIZ_REPO.parent:
    RAIZ_REPO = RAIZ_REPO.parent

sys.path.insert(0, str(RAIZ_REPO))

load_dotenv(RAIZ_REPO / ".env")

# se lee con .get y no con os.environ[...] a proposito: si la variable no
# esta definida, lo que se quiere es el mensaje de abajo y no un KeyError
CREDENCIALES = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")


if not CREDENCIALES:

    raise SystemExit(
        "Falta la variable GOOGLE_APPLICATION_CREDENTIALS. Revisar el .env "
        "de la raiz del repo."
    )


if not Path(CREDENCIALES).is_absolute():

    CREDENCIALES = str(RAIZ_REPO / CREDENCIALES)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENCIALES


if not Path(CREDENCIALES).is_file():

    raise SystemExit(
        f"No existe el archivo de la cuenta de servicio: {CREDENCIALES}. "
        "Revisar el .env."
    )

from src.drive import (  # noqa: E402
    CARPETA_INTEGRACION,
    VARIABLE_FOLDER_IDS,
    descargar_archivo,
    listar_archivos,
    resolve_etapa_folder,
    subir_o_reemplazar,
)


## 0.3. Parametros configurables ----------------------------------------------------

# carpetas de Drive de donde se lee, una por dimension                 # Input
DIMENSION_1 = "1_Compromiso_financiero_oficial_limpias"
DIMENSION_2 = "2_Actividad_gubernamental_y_diplomatica_limpias"
DIMENSION_3 = "3_Compromiso_economico_privado_limpias"
DIMENSION_4 = "4_Visibilidad_mediatica_y_relevancia_publica_limpias"

# Las variables que se traen, agrupadas por dimension, cada una con dos
# atributos que NO vienen en el CSV y hay que declarar aca.
#
# 02_limpias tiene un contrato de cinco columnas fijas (trimestre, anio,
# trimestre_num, valor, unidad) y nada mas - todo lo que diga como se puede
# usar una serie a lo largo del tiempo vive fuera del CSV. Son dos cosas
# distintas y las dos importan:
#
#   grano_temporal
#     "trimestre real"   cada fila salio de hechos con fecha propia dentro de
#                        ese trimestre.
#     "anio repetido"    la fuente no publica nada mas fino que el anio
#                        fiscal, asi que el mismo total anual esta repetido en
#                        los cuatro trimestres.
#
#   agregacion (que pasa si se juntan varios trimestres)
#     "suma"                 flujo sumable: los cuatro trimestres suman el
#                            total del anio.
#     "no sumar"             el valor NO es un flujo, es un nivel: o el total
#                            del anio repetido cuatro veces (fa_gov), o un
#                            STOCK acumulado que ya trae adentro todo lo
#                            anterior (state_gov_tias_vigentes - cuantos TIAS
#                            siguen vigentes a esa fecha, no cuantos entraron
#                            en vigor ESE trimestre). En los dos casos, sumar
#                            los cuatro trimestres cuenta lo mismo mas de una
#                            vez.
#     "promedio ponderado"   es un promedio, no un flujo. Sumar no significa
#                            nada; para llevarlo a anio hay que promediar
#                            ponderando por la cantidad de articulos del
#                            mismo pais (la variable gdelt_proxy_articles_*
#                            que va al lado).
#
# El caso que obliga a tener las dos columnas es el tono de GDELT (y ahora
# tambien state_gov_tias_vigentes): son "trimestre real" y aun asi no se
# pueden sumar. Con una sola marca, el error se puede cometer sin querer en
# 04_analysis_index.

VARIABLES_D1 = [
    # variable                      grano temporal     agregacion
    ("fa_gov_obligaciones",         "anio repetido",   "no sumar"),
    ("fa_gov_desembolsos",          "anio repetido",   "no sumar"),
    ("usaspending_obligaciones",    "trimestre real",  "suma"),
]

# Las dos variables de processing/actividad_gubernamental_y_diplomatica.py
# que ya estan limpias y en Drive (rediseño 2026-09-10 - ver CLAUDE.md
# seccion 6). Las otras dos de esa dimension (ustr_hitos_consejo_comercio_
# inversion, congreso_menciones_totales_paraguay) siguen sin entrar al panel:
# el usuario todavia no pidio incorporarlas.
VARIABLES_D2 = [
    # variable                                  grano temporal     agregacion
    ("congreso_proyectos_relevantes_paraguay",   "trimestre real",  "suma"),
    ("state_gov_tias_vigentes",                  "trimestre real",  "no sumar"),
]

VARIABLES_D3 = [
    # variable                      grano temporal     agregacion
    ("exportaciones",               "trimestre real",  "suma"),
    ("importaciones",               "trimestre real",  "suma"),
    ("remesas",                     "trimestre real",  "suma"),
]

VARIABLES_D4 = [
    # variable                      grano temporal     agregacion
    ("gdelt_proxy_articles_py",     "trimestre real",  "suma"),
    ("gdelt_tone_promedio_py",      "trimestre real",  "promedio ponderado"),
    ("gdelt_proxy_articles_us",     "trimestre real",  "suma"),
    ("gdelt_tone_promedio_us",      "trimestre real",  "promedio ponderado"),
]

# el registro completo, en el orden en que se apilan al final del paso 1
DIMENSIONES = [
    (DIMENSION_1, VARIABLES_D1),
    (DIMENSION_2, VARIABLES_D2),
    (DIMENSION_3, VARIABLES_D3),
    (DIMENSION_4, VARIABLES_D4),
]

# el contrato de 02_limpias: estas cinco columnas, igual en las 4 dimensiones
COLUMNAS_CONTRATO = ["trimestre", "anio", "trimestre_num", "valor", "unidad"]

# Rango del panel: fijo y declarado, NO deducido de los datos. El panel
# siempre tiene los 48 trimestres de 2015-Q1 a 2026-Q4 por variable, aunque
# una fuente no llegue hasta ahi (esos trimestres quedan en NA) y aunque otra
# publique mas alla (esas filas quedan afuera, y la validacion lo avisa - hoy
# no pasa con estas doce, pero el Banco Mundial en la dimension 1 ya publica
# aprobaciones futuras).
ANIO_MINIMO = 2015
ANIO_MAXIMO = 2026

# carpeta de Drive donde se publica el panel                          # Output
CARPETA_SALIDA = CARPETA_INTEGRACION

# Nombres FIJOS, sin fecha: cada corrida reemplaza el contenido del mismo
# archivo en vez de dejar uno nuevo al lado (ver subir_o_reemplazar en
# src/drive.py). El largo es el que lee 04_analysis_index
ARCHIVO_PANEL_LARGO = "panel_trimestral_largo.csv"
ARCHIVO_PANEL_ANCHO = "panel_trimestral_ancho.csv"

# en False el script corre entero sin tocar Drive, que es lo que se quiere
# mientras se revisa. En True publica el panel
SUBIR_A_DRIVE = True

# muestra las tablas completas al imprimirlas en la consola
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


#=============================================================================.#
# 1. IMPORTAR DATA LIMPIA -----
#=============================================================================.#

# Cada variable de 02_limpias vive en su propia carpeta de Drive y guarda un
# CSV por corrida, con la fecha en el nombre
# ("{variable}_trimestral_AAAA-MM-DD.csv"). De cada carpeta se toma el mas
# reciente y del contenido no se toca nada: no se convierte ninguna unidad y
# no se recalcula ningun valor. Lo unico que se agrega son las columnas de
# trazabilidad (dimension, variable, grano_temporal, agregacion, en_fuente,
# archivo_origen) para saber, ya dentro del panel, de donde salio cada fila y
# como se la puede usar.
#
# Las cuatro dimensiones se leen por separado (1.1 a 1.4), se apilan (1.5) y
# recien ahi se cuadra el panel contra la grilla completa de trimestres (1.6).
# Las unidades NO son homogeneas entre dimensiones: la 1 y la 3 son monetarias
# (USD sin escalar), la 2 y la 4 son cantidad (mezclada con indice de tono en
# la 4). Ese es justamente el problema que resuelve 04_analysis_index; aca
# solo se transporta la unidad tal como vino.


def csv_mas_reciente(dimension_limpia, variable):
    """Devuelve (nombre_archivo, DataFrame) del ultimo CSV subido a la carpeta
    de esa variable.

    El id se busca en VARIABLE_FOLDER_IDS y no con resolve_variable_folder()
    a proposito: resolve_variable_folder CREA la carpeta si no la encuentra, y
    este script solo lee - ante un nombre de variable mal escrito se prefiere
    un KeyError ruidoso a una carpeta vacia nueva en Drive.

    El orden alfabetico del nombre alcanza para saber cual es el mas reciente:
    la fecha va al final y en formato ISO (AAAA-MM-DD)."""

    carpeta_id = VARIABLE_FOLDER_IDS[(dimension_limpia, variable)]

    archivos = sorted(
        (a for a in listar_archivos(carpeta_id) if a["name"].endswith(".csv")),
        key=lambda a: a["name"],
    )

    if not archivos:

        raise SystemExit(
            f"La carpeta de '{variable}' en {dimension_limpia} no tiene ningun "
            "CSV. Correr processing/02_clean de esa dimension antes de este paso."
        )

    archivo = archivos[-1]

    return archivo["name"], pd.read_csv(io.BytesIO(descargar_archivo(archivo["id"])))


def importar_dimension(dimension_limpia, variables):
    """Baja todas las variables de una dimension. Devuelve dos dicts indexados
    por nombre de variable: {variable: DataFrame} y {variable: nombre_archivo}.
    No apila ni transforma - cada tabla queda tal como vino de Drive."""

    tablas = {}
    archivos = {}

    for nombre_variable, _, _ in variables:

        nombre_archivo, tabla = csv_mas_reciente(dimension_limpia, nombre_variable)

        tablas[nombre_variable] = tabla
        archivos[nombre_variable] = nombre_archivo

        print(
            f"  {nombre_variable:<26} {len(tabla):>3} trimestres   "
            f"{tabla['trimestre'].min()} a {tabla['trimestre'].max()}   "
            f"{nombre_archivo}"
        )

    return tablas, archivos


# los dos dicts que van acumulando lo de las cuatro dimensiones
limpias = {}
archivos_usados = {}


## 1.1. Dimension 1 - Compromiso financiero oficial ---------------------------------

# fa_gov_* son de anio repetido (ForeignAssistance.gov no publica nada mas
# fino que el anio fiscal); usaspending es trimestral real, por action_date de
# cada transaccion. Las tres en USD sin escalar.

print(f"[{DIMENSION_1}]")

limpias_d1, archivos_d1 = importar_dimension(DIMENSION_1, VARIABLES_D1)

limpias.update(limpias_d1)
archivos_usados.update(archivos_d1)


# Objetos con nombre propio, para abrirlos de a uno en el panel de Variables
# de Positron (el panel de verdad es limpias_largo, en 1.5)

fa_gov_obligaciones_limpia = limpias_d1["fa_gov_obligaciones"]
fa_gov_desembolsos_limpia = limpias_d1["fa_gov_desembolsos"]
usaspending_obligaciones_limpia = limpias_d1["usaspending_obligaciones"]


## 1.2. Dimension 2 - Actividad gubernamental y diplomatica -------------------------

# Primera vez que esta dimension entra al panel (2026-09-10) - hasta ahora
# quedaba afuera porque sus variables eran conteos de eventos demasiado raros
# (ver CLAUDE.md seccion 7, pendiente #6). Las dos que entran ahora son
# "trimestre real" pero con comportamiento opuesto:
#   congreso_proyectos_relevantes_paraguay   FLUJO - cuantos proyectos nuevos
#                                             se introdujeron ese trimestre,
#                                             se puede sumar.
#   state_gov_tias_vigentes                  STOCK - cuantos TIAS siguen
#                                             vigentes a esa fecha, NO se
#                                             puede sumar (ver 0.3).
# Las dos en "cantidad", sin reescalar.

print(f"\n[{DIMENSION_2}]")

limpias_d2, archivos_d2 = importar_dimension(DIMENSION_2, VARIABLES_D2)

limpias.update(limpias_d2)
archivos_usados.update(archivos_d2)


congreso_proyectos_relevantes_paraguay_limpia = limpias_d2["congreso_proyectos_relevantes_paraguay"]
state_gov_tias_vigentes_limpia = limpias_d2["state_gov_tias_vigentes"]


## 1.3. Dimension 3 - Compromiso economico privado ----------------------------------

# Las tres salen del BCP y son trimestrales reales: exportaciones e
# importaciones vienen ya trimestrales en el Boletin de Comercio Exterior, y
# remesas viene mensual y 02_limpias ya sumo los tres meses de cada
# trimestre. Las tres en USD sin escalar (el BCP publica en miles, el
# reescalado ya paso en processing).

print(f"\n[{DIMENSION_3}]")

limpias_d3, archivos_d3 = importar_dimension(DIMENSION_3, VARIABLES_D3)

limpias.update(limpias_d3)
archivos_usados.update(archivos_d3)


exportaciones_limpia = limpias_d3["exportaciones"]
importaciones_limpia = limpias_d3["importaciones"]
remesas_limpia = limpias_d3["remesas"]


## 1.4. Dimension 4 - Visibilidad mediatica y relevancia publica --------------------

# Las cuatro salen de GDELT (regla proxy B) y van en pares: por cada pais de
# la fuente (PY = medios paraguayos, US = medios estadounidenses) hay una
# cantidad de articulos y un tono promedio.
#
# Dos cosas a tener presentes en 04_analysis_index:
#
#   - el tono es un indice (no un monto ni un conteo) y ya viene ponderado por
#     cantidad de articulos dentro del trimestre. Para agregarlo a un periodo
#     mas largo hay que volver a ponderar por su gdelt_proxy_articles_*, no
#     promediar los trimestres a lo seco.
#
#   - PY y US son el pais de la FUENTE del articulo, no la direccion de la
#     interaccion. No se traen las variantes sin sufijo (BOTH) a proposito:
#     BOTH no es una tercera categoria, es la suma de PY + US, asi que
#     sumarla al panel contaria los mismos articulos dos veces.

print(f"\n[{DIMENSION_4}]")

limpias_d4, archivos_d4 = importar_dimension(DIMENSION_4, VARIABLES_D4)

limpias.update(limpias_d4)
archivos_usados.update(archivos_d4)


gdelt_proxy_articles_py_limpia = limpias_d4["gdelt_proxy_articles_py"]
gdelt_tone_promedio_py_limpia = limpias_d4["gdelt_tone_promedio_py"]
gdelt_proxy_articles_us_limpia = limpias_d4["gdelt_proxy_articles_us"]
gdelt_tone_promedio_us_limpia = limpias_d4["gdelt_tone_promedio_us"]


## 1.5. Apilado de las cuatro dimensiones --------------------------------------------

# 1. Apila las doce variables en una sola tabla, tal como vinieron
#    Todavia desparejo: cada variable trae solo los trimestres que su fuente
#    publica. Cuadrarlo es el paso 1.6

limpias_apiladas = pd.concat(
    [
        limpias[nombre_variable].assign(variable=nombre_variable)
        for _, variables in DIMENSIONES
        for nombre_variable, _, _ in variables
    ],
    ignore_index=True,
)


# 2. Chequeos estructurales antes de cuadrar
#    Van aca y no en la validacion del final porque el paso 1.5 depende de
#    ellos: si el esquema o la unidad no son los esperados, el panel se arma
#    mal en silencio

for nombre_variable, tabla in limpias.items():

    columnas_faltantes = set(COLUMNAS_CONTRATO) - set(tabla.columns)

    if columnas_faltantes:

        raise SystemExit(
            f"La variable '{nombre_variable}' no cumple el contrato de "
            f"02_limpias: le faltan las columnas {sorted(columnas_faltantes)}."
        )


unidades_por_variable = limpias_apiladas.groupby("variable")["unidad"].nunique()

if (unidades_por_variable > 1).any():

    raise SystemExit(
        "Estas variables traen mas de una unidad en el mismo CSV: "
        f"{sorted(unidades_por_variable[unidades_por_variable > 1].index)}."
    )


## 1.6. Panel cuadrado (2015-2026, NA donde no hay dato) ----------------------------

# El panel tiene forma fija: 48 trimestres (ANIO_MINIMO-Q1 a ANIO_MAXIMO-Q4)
# por cada variable declarada en 0.3, esten o no en los CSV. Se arma la grilla
# completa primero y los valores se pegan encima con un left join, asi el
# tamano del panel no depende de hasta donde llego cada fuente.
#
# Lo que queda en NA es "la fuente no publica ese trimestre", que NO es cero:
# 2026-Q3 no tiene exportaciones porque el BCP todavia no publico el
# trimestre, no porque Paraguay no le haya exportado nada a EE.UU. La columna
# en_fuente lo deja explicito fila por fila, para no tener que deducirlo de un
# NaN (y para que siga siendo distinguible si algun dia un CSV trae un valor
# nulo de verdad).


# 1. Los atributos de cada variable, que no dependen del trimestre

catalogo_variables = pd.DataFrame(
    [
        {
            "dimension": dimension_limpia,
            "variable": nombre_variable,
            "grano_temporal": grano,
            "agregacion": agregacion,
            "unidad": limpias[nombre_variable]["unidad"].iloc[0],
            "archivo_origen": archivos_usados[nombre_variable],
        }
        for dimension_limpia, variables in DIMENSIONES
        for nombre_variable, grano, agregacion in variables
    ]
)


# 2. Los 48 trimestres del panel

trimestres_panel = pd.DataFrame(
    [
        {"anio": anio, "trimestre_num": trim, "trimestre": f"{anio}-Q{trim}"}
        for anio in range(ANIO_MINIMO, ANIO_MAXIMO + 1)
        for trim in (1, 2, 3, 4)
    ]
)


# 3. La grilla: cada variable por cada trimestre (el cross join es lo que hace
#    que el panel salga cuadrado, sin depender de los datos)

grilla_panel = catalogo_variables.merge(trimestres_panel, how="cross")


# 4. Pega los valores sobre la grilla
#    en_fuente se marca en el lado derecho ANTES del join: asi distingue "no
#    habia fila para ese trimestre" de "habia fila con valor nulo"

valores = (
    limpias_apiladas[["variable", "anio", "trimestre_num", "valor"]]
    .assign(en_fuente=True)
)

limpias_largo = (
    grilla_panel
    .merge(valores, on=["variable", "anio", "trimestre_num"], how="left")

    # despues del left join, en_fuente es True donde habia fila y NaN donde no,
    # asi que notna() ya es el booleano que se busca (un fillna(False) sobre una
    # columna object dispara un FutureWarning de pandas por el downcasting)
    .assign(en_fuente=lambda d: d["en_fuente"].notna())
    [[
        "dimension", "variable", "grano_temporal", "agregacion", "trimestre",
        "anio", "trimestre_num", "valor", "unidad", "en_fuente", "archivo_origen",
    ]]
    .sort_values(["dimension", "variable", "anio", "trimestre_num"])
    .reset_index(drop=True)
)


# 5. La misma cosa en formato ancho, para mirarla de un vistazo
#    Una fila por trimestre y una columna por variable, en el orden de las
#    dimensiones. Es la vista comoda para el Data Explorer de Positron, pero
#    ojo: las columnas NO comparten unidad, no se pueden sumar entre si

limpias_ancho = (
    limpias_largo
    .pivot(index="trimestre", columns="variable", values="valor")
    .reindex(index=trimestres_panel["trimestre"], columns=catalogo_variables["variable"])
)


# Validacion de la carga ------------------------------------------------------

# 1. Que el panel tenga exactamente la forma declarada

filas_esperadas = len(catalogo_variables) * len(trimestres_panel)

if len(limpias_largo) != filas_esperadas:

    raise SystemExit(
        f"El panel salio con {len(limpias_largo)} filas y se esperaban "
        f"{filas_esperadas} ({len(catalogo_variables)} variables x "
        f"{len(trimestres_panel)} trimestres). Revisar duplicados en los CSV."
    )

print(
    f"\nPANEL CUADRADO: {len(limpias_largo)} filas = "
    f"{len(catalogo_variables)} variables x {len(trimestres_panel)} trimestres "
    f"({trimestres_panel['trimestre'].iloc[0]} a {trimestres_panel['trimestre'].iloc[-1]})"
)


# 2. Que trajo cada variable, de que archivo salio y cuanto le falta

resumen_limpias = (
    catalogo_variables
    .assign(dimension=lambda d: d["dimension"].str.split("_").str[0])
    .merge(
        limpias_largo[limpias_largo["en_fuente"]]
        .groupby("variable", as_index=False)
        .agg(
            con_dato=("valor", "size"),
            desde=("trimestre", "min"),
            hasta=("trimestre", "max"),
        ),
        on="variable",
        how="left",
    )
    .assign(en_na=lambda d: len(trimestres_panel) - d["con_dato"])
    [[
        "dimension", "variable", "con_dato", "en_na", "desde", "hasta",
        "grano_temporal", "agregacion", "unidad", "archivo_origen",
    ]]
)

print("\nLIMPIAS IMPORTADAS")
print(resumen_limpias.to_string(index=False))


# 3. Los NA del panel, por variable
#    Son todos de cola (trimestres que la fuente todavia no publico). Si
#    alguna variable tuviera un hueco en el medio de la serie, aparece aca

na_intercalados = (
    limpias_largo[~limpias_largo["en_fuente"]]
    .groupby("variable")
    .agg(desde=("trimestre", "min"), hasta=("trimestre", "max"), cuantos=("trimestre", "size"))
)

print(f"\ntrimestres en NA: {int((~limpias_largo['en_fuente']).sum())} de {len(limpias_largo)}")

if len(na_intercalados):

    print(na_intercalados.to_string())


# 4. Que no haya trimestres repetidos dentro de una misma variable
#    (el chequeo de forma del punto 1 ya lo detectaria, esto dice cual es)

duplicados = limpias_apiladas[limpias_apiladas.duplicated(["variable", "trimestre"], keep=False)]

print(f"\nfilas con (variable, trimestre) duplicado: {len(duplicados)}")

if len(duplicados):

    print(duplicados.to_string(index=False))


# 5. Filas de los CSV que quedaron FUERA del panel por caer fuera del rango
#    Si esto da distinto de cero, hay datos reales que el panel esta tirando y
#    conviene revisar ANIO_MAXIMO

fuera_de_rango = limpias_apiladas[
    (limpias_apiladas["anio"] < ANIO_MINIMO) | (limpias_apiladas["anio"] > ANIO_MAXIMO)
]

print(f"filas de los CSV fuera del rango {ANIO_MINIMO}-{ANIO_MAXIMO}: {len(fuera_de_rango)}")

if len(fuera_de_rango):

    print(fuera_de_rango.groupby("variable")["trimestre"].agg(["size", "min", "max"]).to_string())


# 6. Unidades presentes en el panel

print("\nunidades en el panel (no son comparables entre si, normalizar en 04):")

for unidad, variables_de_esa_unidad in catalogo_variables.groupby("unidad")["variable"]:

    print(f"  {unidad:<10} {', '.join(variables_de_esa_unidad)}")


# 7. Hasta donde llega el panel con todas las variables a la vez
#    Es el candidato natural a cierre de serie en 04_analysis_index

cobertura = limpias_largo.pivot_table(
    index="trimestre",
    columns="variable",
    values="en_fuente",
    aggfunc="sum",
    fill_value=0,
)

completos = cobertura[(cobertura > 0).all(axis=1)]

if len(completos):

    print(
        f"\nultimo trimestre con las {len(cobertura.columns)} variables: "
        f"{completos.index.max()}  ({len(completos)} trimestres completos)"
    )

else:

    print("\nno hay ningun trimestre con las doce variables a la vez")


#=============================================================================.#
# 2. EXPORTAR PANEL -----
#=============================================================================.#

# El panel se publica en Drive en los dos formatos que ya existen en memoria:
# largo (una fila por variable y trimestre, con las columnas de trazabilidad) y
# ancho (una fila por trimestre, una columna por variable). El largo es el
# insumo de 04_analysis_index - trae todo lo que el ancho no puede llevar
# (dimension, grano_temporal, agregacion, unidad, en_fuente, archivo_origen);
# el ancho es la vista comoda para mirar el panel de un vistazo.
#
# Los dos van con nombre FIJO y cada corrida reemplaza el contenido del mismo
# archivo, a diferencia de 01_crudas y 02_limpias, que acumulan una foto por
# dia. El motivo es que esto no es un dato nuevo cada dia sino el estado
# vigente de la etapa, y con nombre fijo el id (y el link) del archivo no
# cambia nunca. El historial de cada version lo guarda igual Drive.


# 1. Ordena el panel largo segun el orden declarado de las variables
#    limpias_largo esta ordenado alfabeticamente por variable dentro de cada
#    dimension, y el orden que importa es el declarado en 0.3: es el que
#    reconstruye 04_analysis_index al leer el archivo (fa_gov_obligaciones
#    antes que fa_gov_desembolsos, y no al reves)

orden_variables = {nombre: i for i, nombre in enumerate(catalogo_variables["variable"])}

panel_largo_export = (
    limpias_largo

    # columna auxiliar solo para ordenar, se saca antes de exportar
    .assign(orden_variable=lambda d: d["variable"].map(orden_variables))
    .sort_values(["orden_variable", "anio", "trimestre_num"])
    .drop(columns="orden_variable")
    .reset_index(drop=True)
)


# 2. Baja el trimestre del indice a columna en el formato ancho
#    limpias_ancho tiene el trimestre como indice y el CSV no lo guardaria

panel_ancho_export = limpias_ancho.reset_index()


# 3. Publica los dos formatos en la carpeta de la etapa

if not SUBIR_A_DRIVE:

    print(
        "\nSUBIR_A_DRIVE = False: no se subio nada. panel_largo_export y "
        "panel_ancho_export quedan en memoria."
    )

else:

    carpeta_salida_id = resolve_etapa_folder(CARPETA_SALIDA)

    print(f"\n[{CARPETA_SALIDA}]")

    for nombre_archivo, tabla_export in (
        (ARCHIVO_PANEL_LARGO, panel_largo_export),
        (ARCHIVO_PANEL_ANCHO, panel_ancho_export),
    ):

        contenido = tabla_export.to_csv(index=False).encode("utf-8")

        subir_o_reemplazar(contenido, nombre_archivo, carpeta_salida_id, mime_type="text/csv")

        print(
            f"  {nombre_archivo:<28} {len(tabla_export):>4} filas x "
            f"{tabla_export.shape[1]:>2} columnas"
        )

