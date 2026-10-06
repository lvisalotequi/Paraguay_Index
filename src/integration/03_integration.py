#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# RESPONSABLE DEL CODIGO:                                                      #
#   PIERO VALLES-MARAVI (ESPECIALISTA) - pvalles@equilibriumbdc.com            #
#                                                                              #
# FECHA DE CREACION: 09/09/2026                                                #
# ULTIMA REVISION: 05/10/2026 - trae TODAS las variables de 02_limpias,        #
#                  descubriendolas en Drive en vez de leer una lista fija      #
# NOMBRE: 03_integration                                                       #
# DETALLE: Recorre las cuatro carpetas de dimension de 02_limpias y la de      #
#          insumos del indice (IPC y poblacion), toma el                       #
#          ultimo CSV de cada variable y los deja en un panel trimestral       #
#          CUADRADO: todos los trimestres de 2015 a 2026 por todas las         #
#          variables, con NA donde la fuente no tiene dato.                    #
#          Aca NO se limpia nada (eso es processing) ni se selecciona, se      #
#          normaliza o se pondera nada (eso es analysis_index).                #
#                                                                              #
# CORRE DESPUES DE: run_processing.py (las variables limpias ya tienen que     #
#                   estar en Drive)                                            #
# SALIDA: Drive 03_integracion/ - el panel en formato largo y en formato       #
#         ancho, un CSV cada uno. El largo es lo que lee analysis_index        #
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
    CARPETA_LIMPIAS,
    DRIVE_ROOT_ID,
    descargar_archivo,
    listar_archivos,
    resolve_etapa_folder,
    subir_o_reemplazar,
)


## 0.3. Parametros configurables ----------------------------------------------------

# carpetas de dimension dentro de 02_limpias, en el orden del panel     # Input
DIMENSION_1 = "1_Compromiso_financiero_oficial_limpias"
DIMENSION_2 = "2_Actividad_gubernamental_y_diplomatica_limpias"
DIMENSION_3 = "3_Compromiso_economico_privado_limpias"
DIMENSION_4 = "4_Visibilidad_mediatica_y_relevancia_publica_limpias"

# insumos del indice: no miden el vinculo, la etapa 04 los usa para deflactar
# y expresar por habitante
DIMENSION_INSUMOS = "insumos_indice_limpias"

DIMENSIONES = [DIMENSION_1, DIMENSION_2, DIMENSION_3, DIMENSION_4, DIMENSION_INSUMOS]

# Las variables NO se listan a mano para saber cuales traer: el script las
# descubre recorriendo las carpetas de Drive (paso 1.1), asi que una variable
# nueva que suba processing entra sola al panel.
#
# Lo que si se declara a mano es lo que el CSV no trae. 02_limpias tiene un
# contrato de cinco columnas fijas (trimestre, anio, trimestre_num, valor,
# unidad) y nada mas; todo lo que diga como se puede usar una serie a lo largo
# del tiempo vive fuera del CSV y hay que declararlo aca:
#
#   grano_temporal
#     "trimestre real"   cada fila salio de hechos con fecha propia dentro de
#                        ese trimestre.
#     "anio repetido"    la fuente no publica nada mas fino que el anio, asi
#                        que el mismo total anual esta repetido en los cuatro
#                        trimestres.
#
#   agregacion (que pasa si se juntan varios trimestres)
#     "suma"                 flujo sumable: los cuatro trimestres suman el
#                            total del anio.
#     "no sumar"             nivel o stock: el total anual repetido cuatro
#                            veces, o una cantidad vigente a esa fecha. Sumar
#                            los cuatro trimestres cuenta lo mismo mas de una
#                            vez.
#     "promedio ponderado"   promedio que solo se puede llevar a anio
#                            ponderando por la cantidad de articulos de la
#                            variable gdelt_proxy_articles* que va al lado.
#     "promedio simple"      indice relativo que processing arma como promedio
#                            de los meses del trimestre; tampoco se suma.
#
# Si el paso 1.2 descubre en Drive una variable que no esta declarada aca, el
# script se detiene: una variable nueva obliga a decidir su grano y su
# agregacion, no entra con un valor por defecto.
#
# El panel trae TODAS las variables de 02_limpias. Que una variable este en el
# panel no significa que entre al indice: la seleccion se hace en
# analysis_index, con el diccionario de variables (docs/).

ATRIBUTOS_VARIABLE = {

    # variable                                  dimension     grano temporal    agregacion

    # dimension 1 - compromiso financiero oficial
    "fa_gov_obligaciones":                      (DIMENSION_1, "anio repetido",  "no sumar"),
    "fa_gov_desembolsos":                       (DIMENSION_1, "anio repetido",  "no sumar"),
    "usaspending_obligaciones":                 (DIMENSION_1, "trimestre real", "suma"),
    "usaspending_operativo":                    (DIMENSION_1, "trimestre real", "suma"),
    "dfc_comprometido":                         (DIMENSION_1, "anio repetido",  "no sumar"),
    "dfc_proyectos_vigentes":                   (DIMENSION_1, "trimestre real", "no sumar"),
    "exim_autorizado":                          (DIMENSION_1, "trimestre real", "suma"),
    "exim_desembolsado":                        (DIMENSION_1, "trimestre real", "suma"),
    "bid_proyectos_aprobados":                  (DIMENSION_1, "trimestre real", "suma"),
    "bid_proyectos_atribuible_eeuu":            (DIMENSION_1, "trimestre real", "suma"),
    "bancomundial_proyectos_aprobados":         (DIMENSION_1, "trimestre real", "suma"),
    "bancomundial_proyectos_atribuible_eeuu":   (DIMENSION_1, "trimestre real", "suma"),

    # dimension 2 - actividad gubernamental y diplomatica
    "congreso_proyectos_relevantes_paraguay":   (DIMENSION_2, "trimestre real", "suma"),
    "congreso_menciones_totales_paraguay":      (DIMENSION_2, "trimestre real", "suma"),
    "congreso_proyectos_mencion_paraguay":      (DIMENSION_2, "trimestre real", "suma"),
    "ustr_hitos_consejo_comercio_inversion":    (DIMENSION_2, "trimestre real", "suma"),
    "state_gov_tias_vigentes":                  (DIMENSION_2, "trimestre real", "no sumar"),
    "state_gov_tif_vigentes":                   (DIMENSION_2, "trimestre real", "no sumar"),
    "mre_noticias_bilaterales":                 (DIMENSION_2, "trimestre real", "suma"),
    "mre_menciones_totales_eeuu":               (DIMENSION_2, "trimestre real", "suma"),

    # dimension 3 - compromiso economico privado
    "exportaciones":                            (DIMENSION_3, "trimestre real", "suma"),
    "importaciones":                            (DIMENSION_3, "trimestre real", "suma"),
    "remesas":                                  (DIMENSION_3, "trimestre real", "suma"),
    "inversion_directa_bcp":                    (DIMENSION_3, "trimestre real", "suma"),
    "bea_inversion_directa":                    (DIMENSION_3, "anio repetido",  "no sumar"),
    "turismo_receptivo_eeuu":                   (DIMENSION_3, "trimestre real", "suma"),

    # dimension 4 - visibilidad mediatica y relevancia publica
    "gdelt_proxy_articles":                     (DIMENSION_4, "trimestre real", "suma"),
    "gdelt_proxy_articles_py":                  (DIMENSION_4, "trimestre real", "suma"),
    "gdelt_proxy_articles_us":                  (DIMENSION_4, "trimestre real", "suma"),
    "gdelt_tone_promedio":                      (DIMENSION_4, "trimestre real", "promedio ponderado"),
    "gdelt_tone_promedio_py":                   (DIMENSION_4, "trimestre real", "promedio ponderado"),
    "gdelt_tone_promedio_us":                   (DIMENSION_4, "trimestre real", "promedio ponderado"),
    "google_trends_paraguay_trade":             (DIMENSION_4, "trimestre real", "promedio simple"),
    "google_trends_paraguay_tariffs":           (DIMENSION_4, "trimestre real", "promedio simple"),
    "google_trends_paraguay_embassy":           (DIMENSION_4, "trimestre real", "promedio simple"),

    # insumos del indice - IPC de EE.UU. (promedio de los meses del trimestre)
    # y poblacion de Paraguay (a mitad de anio, repetida en los 4 trimestres)
    "ipc_eeuu":                                 (DIMENSION_INSUMOS, "trimestre real", "promedio simple"),
    "poblacion_paraguay":                       (DIMENSION_INSUMOS, "anio repetido",  "no sumar"),
}

# el contrato de 02_limpias: estas cinco columnas, igual en las 4 dimensiones
COLUMNAS_CONTRATO = ["trimestre", "anio", "trimestre_num", "valor", "unidad"]

# Rango del panel: fijo y declarado, NO deducido de los datos. El panel tiene
# siempre los 48 trimestres de 2015-Q1 a 2026-Q4 por variable, aunque una
# fuente no llegue hasta ahi (esos trimestres quedan en NA) y aunque otra
# publique mas alla. Las filas de mas alla quedan afuera y la validacion 5 lo
# avisa: hoy pasa con las dos variables del Banco Mundial, que registran una
# aprobacion anunciada para 2027-Q1. Se deja afuera a proposito, porque
# ampliar ANIO_MAXIMO agregaria cuatro trimestres vacios a todas las
# variables por una sola observacion.
ANIO_MINIMO = 2015
ANIO_MAXIMO = 2026

# carpeta de Drive donde se publica el panel                          # Output
CARPETA_SALIDA = CARPETA_INTEGRACION

# Nombres FIJOS, sin fecha: cada corrida reemplaza el contenido del mismo
# archivo en vez de dejar uno nuevo al lado (ver subir_o_reemplazar en
# src/drive.py). El largo es el que lee analysis_index
ARCHIVO_PANEL_LARGO = "panel_trimestral_largo.csv"
ARCHIVO_PANEL_ANCHO = "panel_trimestral_ancho.csv"

# en False el script corre entero sin tocar Drive, que es lo que se quiere
# mientras se revisa. En True publica el panel
SUBIR_A_DRIVE = True

# muestra las tablas completas al imprimirlas en la consola
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 220)


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


def carpeta_hija(carpeta_padre_id, nombre):
    """Devuelve el id de la subcarpeta `nombre` dentro de carpeta_padre_id.

    Solo lee: a diferencia de resolve_folder() de src/drive.py, nunca crea una
    carpeta si no la encuentra. Este script no escribe en 02_limpias, y ante
    un nombre mal escrito se prefiere un error ruidoso a una carpeta vacia
    nueva en Drive."""

    # todos los hijos de la carpeta padre que tienen exactamente ese nombre
    coincidencias = [
        hijo
        for hijo in listar_archivos(carpeta_padre_id)
        if hijo["name"] == nombre
    ]

    if len(coincidencias) != 1:

        raise SystemExit(
            f"Se esperaba una carpeta '{nombre}' y se encontraron "
            f"{len(coincidencias)}. Revisar la estructura de Drive."
        )

    return coincidencias[0]["id"]


def csv_mas_reciente(carpeta_variable_id):
    """Devuelve (nombre_archivo, DataFrame) del ultimo CSV de la carpeta de una
    variable, o (None, None) si la carpeta no tiene ningun CSV.

    El orden alfabetico del nombre alcanza para saber cual es el mas reciente:
    la fecha va al final y en formato ISO (AAAA-MM-DD)."""

    # los CSV de la carpeta, ordenados por nombre
    archivos = sorted(
        (
            archivo
            for archivo in listar_archivos(carpeta_variable_id)
            if archivo["name"].endswith(".csv")
        ),
        key=lambda archivo: archivo["name"],
    )

    if not archivos:

        return None, None

    archivo = archivos[-1]

    return archivo["name"], pd.read_csv(io.BytesIO(descargar_archivo(archivo["id"])))


def importar_dimension(dimension_limpia, carpeta_limpias_id):
    """Descubre todas las variables de una carpeta de dimension y baja el ultimo
    CSV de cada una. Devuelve dos dicts indexados por nombre de variable:
    {variable: DataFrame} y {variable: nombre_archivo}.

    Dentro de la carpeta de dimension, una variable es una SUBCARPETA. Los
    archivos sueltos que quedaron de las primeras corridas (CSV combinados por
    dimension, de antes de la politica de una carpeta por variable) se
    ignoran: llevan extension, las carpetas de variable no."""

    carpeta_dimension_id = carpeta_hija(carpeta_limpias_id, dimension_limpia)

    # las subcarpetas de la dimension, en orden alfabetico
    carpetas_variable = sorted(
        (
            hijo
            for hijo in listar_archivos(carpeta_dimension_id)
            if "." not in hijo["name"]
        ),
        key=lambda hijo: hijo["name"],
    )

    tablas = {}
    archivos = {}

    for carpeta_variable in carpetas_variable:

        nombre_variable = carpeta_variable["name"]

        nombre_archivo, tabla = csv_mas_reciente(carpeta_variable["id"])

        if tabla is None:

            print(f"  {nombre_variable:<42} SIN CSV, no entra al panel")

            continue

        tablas[nombre_variable] = tabla
        archivos[nombre_variable] = nombre_archivo

        print(
            f"  {nombre_variable:<42} {len(tabla):>3} filas   "
            f"{tabla['trimestre'].min()} a {tabla['trimestre'].max()}   "
            f"{nombre_archivo}"
        )

    return tablas, archivos


## 1.1. Descubrimiento de las variables en Drive -----------------------------------

# 1. La carpeta 02_limpias, colgando de la raiz del proyecto en Drive
carpeta_limpias_id = carpeta_hija(DRIVE_ROOT_ID, CARPETA_LIMPIAS)


# 2. Recorre las cuatro dimensiones y la de insumos, y acumula lo que encuentra
#    limpias guarda cada variable tal como vino de Drive, archivos_usados el
#    nombre del CSV que se leyo y dimension_encontrada en que carpeta aparecio
limpias = {}
archivos_usados = {}
dimension_encontrada = {}

for dimension_limpia in DIMENSIONES:

    print(f"\n[{dimension_limpia}]")

    tablas_dimension, archivos_dimension = importar_dimension(
        dimension_limpia,
        carpeta_limpias_id,
    )

    limpias.update(tablas_dimension)
    archivos_usados.update(archivos_dimension)

    dimension_encontrada.update({
        nombre_variable: dimension_limpia
        for nombre_variable in tablas_dimension
    })


## 1.2. Contraste con lo declarado en 0.3 -------------------------------------------

# Va aca y no en la validacion del final porque todo lo que sigue depende de
# que cada variable tenga su grano y su agregacion declarados

# 1. Variables que aparecieron en Drive pero no estan declaradas en 0.3
sin_declarar = sorted(set(limpias) - set(ATRIBUTOS_VARIABLE))

if sin_declarar:

    raise SystemExit(
        "Estas variables estan en 02_limpias pero no en ATRIBUTOS_VARIABLE: "
        f"{sin_declarar}. Declarar su dimension, grano y agregacion en 0.3 "
        "antes de integrarlas."
    )


# 2. Variables declaradas en 0.3 que no aparecieron en Drive
sin_carpeta = sorted(set(ATRIBUTOS_VARIABLE) - set(limpias))

if sin_carpeta:

    raise SystemExit(
        "Estas variables estan declaradas en ATRIBUTOS_VARIABLE pero no se "
        f"encontraron en 02_limpias: {sin_carpeta}. Revisar si el nombre esta "
        "mal escrito o si processing todavia no las publico."
    )


# 3. Variables que aparecieron en una dimension distinta de la declarada
en_otra_dimension = sorted(
    nombre_variable
    for nombre_variable, carpeta in dimension_encontrada.items()
    if carpeta != ATRIBUTOS_VARIABLE[nombre_variable][0]
)

if en_otra_dimension:

    raise SystemExit(
        "Estas variables estan en una carpeta de dimension distinta de la "
        f"declarada en ATRIBUTOS_VARIABLE: {en_otra_dimension}."
    )


# 4. Cada CSV cumple el contrato de cinco columnas de 02_limpias
for nombre_variable, tabla in limpias.items():

    columnas_faltantes = set(COLUMNAS_CONTRATO) - set(tabla.columns)

    if columnas_faltantes:

        raise SystemExit(
            f"La variable '{nombre_variable}' no cumple el contrato de "
            f"02_limpias: le faltan las columnas {sorted(columnas_faltantes)}."
        )


# 5. El orden del panel es el declarado en 0.3, no el alfabetico de Drive
ORDEN_VARIABLES = list(ATRIBUTOS_VARIABLE)

print(f"\nvariables encontradas y declaradas: {len(ORDEN_VARIABLES)}")


## 1.3. Apilado de todas las variables ----------------------------------------------

# 1. Apila todas las variables en una sola tabla, tal como vinieron
#    Todavia desparejo: cada variable trae solo los trimestres que su fuente
#    publica. Cuadrarlo es el paso 1.4
limpias_apiladas = pd.concat(
    [
        limpias[nombre_variable].assign(variable=nombre_variable)
        for nombre_variable in ORDEN_VARIABLES
    ],
    ignore_index=True,
)


# 2. Cada variable trae una sola unidad
#    Si una variable mezclara unidades, el panel se armaria mal en silencio
unidades_por_variable = limpias_apiladas.groupby("variable")["unidad"].nunique()

if (unidades_por_variable > 1).any():

    raise SystemExit(
        "Estas variables traen mas de una unidad en el mismo CSV: "
        f"{sorted(unidades_por_variable[unidades_por_variable > 1].index)}."
    )


## 1.4. Panel cuadrado (2015-2026, NA donde no hay dato) ----------------------------

# El panel tiene forma fija: 48 trimestres (ANIO_MINIMO-Q1 a ANIO_MAXIMO-Q4)
# por cada variable, esten o no en los CSV. Se arma la grilla completa primero
# y los valores se pegan encima con un left join, asi el tamano del panel no
# depende de hasta donde llego cada fuente.
#
# Lo que queda en NA es "la fuente no publica ese trimestre", que NO es cero.
# La columna en_fuente lo deja explicito fila por fila, para no tener que
# deducirlo de un NaN. Si un NA de una serie de eventos es en realidad un cero
# se decide en analysis_index, no aca.


# 1. Los atributos de cada variable, que no dependen del trimestre
catalogo_variables = pd.DataFrame(
    [
        {
            "dimension": ATRIBUTOS_VARIABLE[nombre_variable][0],
            "variable": nombre_variable,
            "grano_temporal": ATRIBUTOS_VARIABLE[nombre_variable][1],
            "agregacion": ATRIBUTOS_VARIABLE[nombre_variable][2],
            "unidad": limpias[nombre_variable]["unidad"].iloc[0],
            "archivo_origen": archivos_usados[nombre_variable],
        }
        for nombre_variable in ORDEN_VARIABLES
    ]
)


# 2. Los 48 trimestres del panel
trimestres_panel = pd.DataFrame(
    [
        {
            "anio": anio,
            "trimestre_num": trimestre_num,
            "trimestre": f"{anio}-Q{trimestre_num}",
        }
        for anio in range(ANIO_MINIMO, ANIO_MAXIMO + 1)
        for trimestre_num in (1, 2, 3, 4)
    ]
)


# 3. La grilla: cada variable por cada trimestre
#    el cross join es lo que hace que el panel salga cuadrado
grilla_panel = catalogo_variables.merge(
    trimestres_panel,
    how="cross",
)


# 4. Los valores que trajo cada CSV, marcados como presentes en la fuente
#    en_fuente se marca del lado derecho ANTES del join: asi distingue "no
#    habia fila para ese trimestre" de "habia fila con valor nulo"
valores = (
    limpias_apiladas[["variable", "anio", "trimestre_num", "valor"]]
    .assign(en_fuente=True)
)


# 5. Pega los valores sobre la grilla
limpias_largo = grilla_panel.merge(
    valores,
    on=["variable", "anio", "trimestre_num"],
    how="left",
)


# 6. Completa en_fuente
#    despues del left join vale True donde habia fila y NaN donde no, asi que
#    notna() ya es el booleano buscado (un fillna(False) sobre una columna
#    object dispara un FutureWarning de pandas por el downcasting)
limpias_largo = limpias_largo.assign(
    en_fuente=lambda d: d["en_fuente"].notna(),
)


# 7. Ordena las columnas y las filas segun el orden declarado
#    orden_variable es auxiliar: solo sirve para ordenar y se descarta
orden_variable = {nombre: posicion for posicion, nombre in enumerate(ORDEN_VARIABLES)}

limpias_largo = (
    limpias_largo
    .assign(orden_variable=lambda d: d["variable"].map(orden_variable))
    .sort_values(["orden_variable", "anio", "trimestre_num"])
    .drop(columns="orden_variable")
    [[
        "dimension",
        "variable",
        "grano_temporal",
        "agregacion",
        "trimestre",
        "anio",
        "trimestre_num",
        "valor",
        "unidad",
        "en_fuente",
        "archivo_origen",
    ]]
    .reset_index(drop=True)
)


# 8. La misma cosa en formato ancho, para mirarla de un vistazo
#    una fila por trimestre y una columna por variable. Ojo: las columnas NO
#    comparten unidad, no se pueden sumar entre si
limpias_ancho = (
    limpias_largo
    .pivot(index="trimestre", columns="variable", values="valor")
    .reindex(index=trimestres_panel["trimestre"], columns=ORDEN_VARIABLES)
)


# Validacion de la carga ------------------------------------------------------

# 1. El panel tiene exactamente la forma declarada
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
        "dimension",
        "variable",
        "con_dato",
        "en_na",
        "desde",
        "hasta",
        "grano_temporal",
        "agregacion",
        "unidad",
        "archivo_origen",
    ]]
)

print("\nLIMPIAS IMPORTADAS")
print(resumen_limpias.to_string(index=False))


# 3. Donde caen los NA de cada variable
#    Un NA puede estar en la cabecera (la fuente todavia no empezaba), en la
#    cola (todavia no publica) o en el MEDIO de la serie. Los del medio son los
#    que hay que mirar: en las variables que cuentan eventos pueden ser un cero
#    y no un dato faltante, y eso se decide en analysis_index
primer_dato = limpias_largo[limpias_largo["en_fuente"]].groupby("variable")["trimestre"].min()
ultimo_dato = limpias_largo[limpias_largo["en_fuente"]].groupby("variable")["trimestre"].max()

na_por_posicion = limpias_largo[~limpias_largo["en_fuente"]].copy()

na_por_posicion["posicion"] = [

    # antes del primer dato de esa variable
    "cabecera" if trimestre < primer_dato[variable]

    # despues del ultimo dato de esa variable
    else "cola" if trimestre > ultimo_dato[variable]

    # entre el primero y el ultimo
    else "medio"

    for variable, trimestre in zip(na_por_posicion["variable"], na_por_posicion["trimestre"])
]

na_por_variable = (
    na_por_posicion
    .pivot_table(
        index="variable",
        columns="posicion",
        values="trimestre",
        aggfunc="size",
        fill_value=0,
    )
    .reindex(columns=["cabecera", "medio", "cola"], fill_value=0)
    .reindex(ORDEN_VARIABLES)
    .fillna(0)
    .astype(int)
    .assign(total=lambda d: d.sum(axis=1))
)

print(f"\ntrimestres en NA: {int((~limpias_largo['en_fuente']).sum())} de {len(limpias_largo)}")
print("\nNA por posicion dentro de la serie de cada variable:")
print(na_por_variable[na_por_variable["total"] > 0].to_string())

con_huecos_en_el_medio = na_por_variable[na_por_variable["medio"] > 0].index.tolist()

print(f"\nvariables con huecos en el MEDIO de la serie: {len(con_huecos_en_el_medio)}")


# 4. Que no haya trimestres repetidos dentro de una misma variable
#    el chequeo de forma del punto 1 ya lo detectaria; esto dice cual es
duplicados = limpias_apiladas[
    limpias_apiladas.duplicated(["variable", "trimestre"], keep=False)
]

print(f"\nfilas con (variable, trimestre) duplicado: {len(duplicados)}")

if len(duplicados):

    print(duplicados.to_string(index=False))


# 5. Filas de los CSV que quedaron FUERA del panel por caer fuera del rango
#    si da distinto de cero, hay datos reales que el panel no incluye
fuera_de_rango = limpias_apiladas[
    (limpias_apiladas["anio"] < ANIO_MINIMO) | (limpias_apiladas["anio"] > ANIO_MAXIMO)
]

print(f"filas de los CSV fuera del rango {ANIO_MINIMO}-{ANIO_MAXIMO}: {len(fuera_de_rango)}")

if len(fuera_de_rango):

    print(fuera_de_rango.groupby("variable")["trimestre"].agg(["size", "min", "max"]).to_string())


# 6. Unidades presentes en el panel
print("\nunidades en el panel (no son comparables entre si, normalizar en 04):")

for unidad, variables_de_esa_unidad in catalogo_variables.groupby("unidad")["variable"]:

    print(f"  {unidad:<10} {len(variables_de_esa_unidad):>2} variables")


# 7. Hasta donde llega el panel con todas las variables a la vez
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

    print(f"\nningun trimestre tiene dato en las {len(cobertura.columns)} variables a la vez")


#=============================================================================.#
# 2. EXPORTAR PANEL -----
#=============================================================================.#

# El panel se publica en Drive en los dos formatos que ya existen en memoria:
# largo (una fila por variable y trimestre, con las columnas de trazabilidad) y
# ancho (una fila por trimestre, una columna por variable). El largo es el
# insumo de analysis_index - trae todo lo que el ancho no puede llevar
# (dimension, grano_temporal, agregacion, unidad, en_fuente, archivo_origen);
# el ancho es la vista comoda para mirar el panel de un vistazo.
#
# Los dos van con nombre FIJO y cada corrida reemplaza el contenido del mismo
# archivo, a diferencia de 01_crudas y 02_limpias, que acumulan una foto por
# dia. El motivo es que esto no es un dato nuevo cada dia sino el estado
# vigente de la etapa, y con nombre fijo el id (y el link) del archivo no
# cambia nunca. El historial de cada version lo guarda igual Drive.


# 1. El panel largo ya esta en el orden declarado (paso 1.4.7)
panel_largo_export = limpias_largo.copy()


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

        subir_o_reemplazar(
            contenido,
            nombre_archivo,
            carpeta_salida_id,
            mime_type="text/csv",
        )

        print(
            f"  {nombre_archivo:<28} {len(tabla_export):>4} filas x "
            f"{tabla_export.shape[1]:>2} columnas"
        )
