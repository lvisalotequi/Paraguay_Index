#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# RESPONSABLE DEL CODIGO:                                                      #
#   PIERO VALLES-MARAVI (ESPECIALISTA) - pvalles@equilibriumbdc.com            #
#                                                                              #
# FECHA DE CREACION: 08/09/2026                                                #
# NOMBRE: 02_clean_cfo                                                         #
# DETALLE: Limpia las 7 variables de la dimension 1 (Compromiso financiero     #
#          oficial) y las deja trimestrales, en USD sin escalar. Aca NO se     #
#          construye el indice ni se pondera nada: eso es 03_final.            #
#                                                                              #
# CORRE DESPUES DE: run_pipeline.py (los crudos ya tienen que estar en Drive)  #
# SALIDA: 02_limpias/1_Compromiso_financiero_oficial_limpias/{variable}/       #
#-----------------------------------------------------------------------------.#


# 0. SETUP -----

## 0.1. Entorno ---------------------------------------------------------------------

import io
import json
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


## 0.2. Rutas y credenciales --------------------------------------------------------

RAIZ_REPO = Path.cwd()

while not (RAIZ_REPO / "src").is_dir() and RAIZ_REPO != RAIZ_REPO.parent:
    RAIZ_REPO = RAIZ_REPO.parent

sys.path.insert(0, str(RAIZ_REPO))

load_dotenv(RAIZ_REPO / ".env")

if not Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).is_absolute():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
        RAIZ_REPO / os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    )


if not Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).is_file():

    raise SystemExit(
        "Falta el archivo de la cuenta de servicio que apunta "
        "GOOGLE_APPLICATION_CREDENTIALS. Revisar el .env."
    )

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos  # noqa: E402
from src.processing._common import subir_variable  # noqa: E402


## 0.3. Parametros configurables ----------------------------------------------------

# carpeta de Drive de donde se lee                                     # Input
DIMENSION_CRUDA = "1_Compromiso_financiero_oficial"

# carpeta de Drive donde se escribe                                    # Output
DIMENSION_LIMPIA = "1_Compromiso_financiero_oficial_limpias"

# piso de la serie: Solo datos desde el 2015 para todas las series.
ANIO_MINIMO = 2015

# en False el script corre entero sin tocar Drive, que es lo que se quiere
# mientras se revisa. Recien se pone en True cuando la revision cerro
SUBIR_A_DRIVE = False

# muestra las tablas completas al imprimirlas en la consola
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


#=============================================================================.#
# 1. IMPORTAR DATA CRUDA -----
#=============================================================================.#

# Las seis fuentes de esta dimension llegan en cuatro formatos distintos (JSON,
# ZIP de CSV, Excel y CSV) y con tres granos distintos (transaccion, proyecto y
# total anual). Esta seccion las deja a todas como un DataFrame a nivel de fila
# y no hace ninguna otra cosa: no filtra, no convierte fechas y no suma nada.

# Dos fuentes suben un archivo nuevo por dia con la fecha en el nombre (BID y
# Banco Mundial) y otras dos suben un archivo unico por anio o por serie
# completa. Cuando hay varios, se usa el ultimo por nombre.


## fa_gov ----------------------------------------------------------------------

# fa_gov: Ayuda exterior que EE.UU. comprometió formalmente con Paraguay

# un JSON por anio y por medida, con el nombre "PRY_{medida}_{anio}.json". Cada
# fila es una actividad financiada
fa_gov_archivos = listar_archivos(FOLDER_IDS[(DIMENSION_CRUDA, "fa_gov_asistencia_oficial")])


# 1. Arma una tabla unica con las actividades de todos los archivos
#    La medida (Obligations / Disbursements) solo esta en el nombre del
#    archivo, asi que se agrega como columna al leer cada uno

fa_gov_raw = pd.concat(
    [
        pd.DataFrame(json.loads(descargar_archivo(archivo["id"]))).assign(

            # "PRY_Obligations_2015.json" -> "Obligations"
            medida=archivo["name"].removesuffix(".json").split("_")[1],

            # se guarda para poder auditar de que archivo salio cada fila
            archivo_origen=archivo["name"],
        )
        for archivo in sorted(fa_gov_archivos, key=lambda a: a["name"])
    ],
    ignore_index=True,
)


## usaspending -----------------------------------------------------------------

# un ZIP por anio, con cuatro CSV adentro: dos de transacciones
# ("PrimeTransactions") y dos de subcontratos ("Subawards"). Los subcontratos
# son plata que ya esta contada en la transaccion que los origino, asi que
# sumarlos duplicaria: solo se leen los dos de transacciones
usaspending_archivos = listar_archivos(FOLDER_IDS[(DIMENSION_CRUDA, "usaspending_obligaciones")])


# 1. Baja cada ZIP y lo deja abierto en memoria

usaspending_zips = [
    (
        archivo["name"],
        zipfile.ZipFile(io.BytesIO(descargar_archivo(archivo["id"]))),
    )
    for archivo in sorted(usaspending_archivos, key=lambda a: a["name"])
]


# 2. Apila las transacciones de todos los anios en una sola tabla

usaspending_raw = pd.concat(
    [
        pd.read_csv(
            zip_anio.open(nombre_csv),
            usecols=["action_date", "federal_action_obligation"],
        ).assign(

            # "All_Contracts_PrimeTransactions_...csv" -> Contracts / Assistance
            tipo="Contracts" if "Contracts" in nombre_csv else "Assistance",

            archivo_origen=nombre_zip,
        )
        for nombre_zip, zip_anio in usaspending_zips
        for nombre_csv in zip_anio.namelist()
        if "PrimeTransactions" in nombre_csv
    ],
    ignore_index=True,
)


## dfc -------------------------------------------------------------------------

# Excel unico con todos los paises. La hoja "Project Data" trae una fila de
# titulo antes de los encabezados reales, de ahi el header=1
dfc_archivo = sorted(
    listar_archivos(FOLDER_IDS[(DIMENSION_CRUDA, "dfc_proyectos_activos")]),
    key=lambda a: a["name"],
)[-1]


# 1. Lee la hoja de proyectos

dfc_raw = pd.read_excel(
    io.BytesIO(descargar_archivo(dfc_archivo["id"])),
    sheet_name="Project Data",
    header=1,
)


## exim ------------------------------------------------------------------------

# CSV unico, ya filtrado a Paraguay por el script de ingestion
exim_archivo = sorted(
    listar_archivos(FOLDER_IDS[(DIMENSION_CRUDA, "exim_autorizaciones")]),
    key=lambda a: a["name"],
)[-1]


# 1. Lee las autorizaciones

exim_raw = pd.read_csv(io.BytesIO(descargar_archivo(exim_archivo["id"])))


## bid -------------------------------------------------------------------------

# JSON diario, ya filtrado a Paraguay server-side. Los proyectos vienen en la
# clave "records"
bid_archivo = sorted(
    listar_archivos(FOLDER_IDS[(DIMENSION_CRUDA, "bid_proyectos")]),
    key=lambda a: a["name"],
)[-1]


# 1. Lee los proyectos

bid_raw = pd.DataFrame(json.loads(descargar_archivo(bid_archivo["id"]))["records"])


## banco mundial ---------------------------------------------------------------

# JSON diario, ya filtrado a Paraguay server-side. Los proyectos vienen como un
# diccionario indexado por id, no como lista: hay que quedarse con los valores
bm_archivo = sorted(
    listar_archivos(FOLDER_IDS[(DIMENSION_CRUDA, "bancomundial_proyectos")]),
    key=lambda a: a["name"],
)[-1]


# 1. Lee los proyectos

bm_raw = pd.DataFrame(
    json.loads(descargar_archivo(bm_archivo["id"]))["projects"].values()
)


# Validacion de la carga ------------------------------------------------------

# 1. Que trajo cada fuente y de que archivo salio

print("CRUDOS CARGADOS")
print(f"  fa_gov        {len(fa_gov_raw):>6} filas   {len(fa_gov_archivos)} archivos")
print(f"  usaspending   {len(usaspending_raw):>6} filas   {len(usaspending_zips)} zips")
print(f"  dfc           {len(dfc_raw):>6} filas   {dfc_archivo['name']}")
print(f"  exim          {len(exim_raw):>6} filas   {exim_archivo['name']}")
print(f"  bid           {len(bid_raw):>6} filas   {bid_archivo['name']}")
print(f"  bancomundial  {len(bm_raw):>6} filas   {bm_archivo['name']}")


#=============================================================================.#
# 2. LIMPIEZA -----
#=============================================================================.#

# Las 7 variables salen del mismo molde y quedan con el mismo contrato/estructura:
#
#   trimestre       "2019-Q2"
#   anio            2019
#   trimestre_num   2
#   valor           el monto del trimestre, en USD sin escalar
#   unidad          "USD"
#
# Las seis fuentes vienen con dos granos distintos y eso cambia como se llega
# al trimestre:
#
#   grano fecha  usaspending, exim, bid, banco mundial
#                cada fila tiene su propia fecha, el trimestre es real y los
#                trimestres se pueden sumar entre si
#
#   grano anio   fa_gov, dfc
#                la fuente no publica nada mas fino que el anio fiscal. El
#                mismo total anual se REPITE en los cuatro trimestres
#
# La diferencia importa mas de lo que parece y hay que tenerla presente en
# 03_final: en las variables de grano anio, sumar los cuatro trimestres NO da
# el total del anio, da cuatro veces el total del anio. Se marca fila por fila
# en la columna grano_temporal para que el error no se pueda cometer sin
# querer.
#
# Nada de esto reescala: las seis fuentes ya publican en USD, a diferencia de
# la dimension 3 donde el BCP publica en miles y BEA en millones.


## 2.1 fa_gov_obligaciones -----------------------------------------------------

# Obligaciones = plata que EE.UU. comprometio formalmente en el anio fiscal.
# Es la contracara de los desembolsos (2.2): se comprometen en un anio y se
# pagan a lo largo de varios.
#
# Los montos negativos se dejan y no se filtran: son desobligaciones, plata
# comprometida que despues se libero. Sacarlas inflaria el compromiso neto del
# trimestre, que es justamente lo que la variable quiere medir.


# 1. Se queda con la medida de obligaciones
#    La columna original no se toca en ningun paso: todo lo derivado va a
#    columnas nuevas

fa_gov_obligaciones_limpiando = fa_gov_raw[fa_gov_raw["medida"] == "Obligations"].copy()


# 2. Normaliza el anio y el monto

fa_gov_obligaciones_limpiando = fa_gov_obligaciones_limpiando.assign(

    # el anio fiscal viene en el propio JSON, no hay que sacarlo del nombre
    anio_norm=lambda d: pd.to_numeric(
        d["fiscal_year"],
        errors="coerce",
    ),

    # 1375008 -> 1375008.0; lo que no sea numero queda nulo
    monto_norm=lambda d: pd.to_numeric(
        d["current_amount"],
        errors="coerce",
    ),
)


# 3. Marca por que una fila entra o no al total

fa_gov_obligaciones_limpiando = fa_gov_obligaciones_limpiando.assign(

    motivo_descarte=lambda d: pd.Series(pd.NA, index=d.index)
    .mask(
        d["anio_norm"].isna(),
        "anio ilegible",
    )
    .mask(
        d["monto_norm"].isna(),
        "monto ilegible",
    )
    .mask(
        d["anio_norm"].notna() & (d["anio_norm"] < ANIO_MINIMO),
        f"anterior a {ANIO_MINIMO}",
    ),
)




# 4. Suma las actividades de cada anio

fa_gov_obligaciones_anual = (
    fa_gov_obligaciones_limpiando
    .loc[fa_gov_obligaciones_limpiando["motivo_descarte"].isna()]
    .groupby("anio_norm", as_index=False)["monto_norm"]
    .sum()
    .rename(columns={"anio_norm": "anio", "monto_norm": "valor"})
)


# 5. Repite el total anual en los cuatro trimestres
#    El merge contra los cuatro numeros de trimestre es el equivalente de un
#    cross join: cada anio sale multiplicado por cuatro filas

fa_gov_obligaciones_clean = (
    fa_gov_obligaciones_anual
    .merge(
        pd.DataFrame({"trimestre_num": [1, 2, 3, 4]}),
        how="cross",
    )
    .assign(

        # 2019, 2 -> "2019-Q2"
        trimestre=lambda d: d["anio"].astype(int).astype(str) + "-Q" + d["trimestre_num"].astype(str),

        anio=lambda d: d["anio"].astype(int),

        unidad="USD",

        # el valor esta repetido: sumar los 4 trimestres NO da el total anual
        grano_temporal="anio repetido",
    )
    .sort_values(["anio", "trimestre_num"])
    .reset_index(drop=True)
)


# 6. Validacion de fa_gov_obligaciones

#    6a. Vista de inspeccion

# fa_gov_obligaciones_limpiando[[
#     "archivo_origen",        # de que JSON salio la fila
#     "activity_name",         # la actividad financiada
#     "fiscal_year",           # original, sin tocar
#     "anio_norm",             # anio ya numerico
#     "current_amount",        # original, sin tocar
#     "monto_norm",            # monto ya numerico
#     "motivo_descarte",       # por que no entro al total, si no entro
# ]]

#    6b. Que se descarto y por que

print("\n2.1 fa_gov_obligaciones")
print(f"  filas crudas    {len(fa_gov_obligaciones_limpiando)}")
print(f"  descartadas     {int(fa_gov_obligaciones_limpiando['motivo_descarte'].notna().sum())}")
print(fa_gov_obligaciones_limpiando["motivo_descarte"].value_counts().to_string())

#    6c. Cuanto pesan las desobligaciones que se dejan adentro

print(
    "  filas con monto negativo (desobligaciones, se conservan): "
    f"{int((fa_gov_obligaciones_limpiando['monto_norm'] < 0).sum())}"
)


## 2.2 fa_gov_desembolsos ------------------------------------------------------

# Desembolsos = plata efectivamente pagada en el anio fiscal. Mismo archivo y
# mismo tratamiento que 2.1, solo cambia el valor de la columna medida.


# 1. Se queda con la medida de desembolsos

fa_gov_desembolsos_limpiando = fa_gov_raw[fa_gov_raw["medida"] == "Disbursements"].copy()


# 2. Normaliza el anio y el monto

fa_gov_desembolsos_limpiando = fa_gov_desembolsos_limpiando.assign(

    anio_norm=lambda d: pd.to_numeric(
        d["fiscal_year"],
        errors="coerce",
    ),

    monto_norm=lambda d: pd.to_numeric(
        d["current_amount"],
        errors="coerce",
    ),
)


# 3. Marca por que una fila entra o no al total

fa_gov_desembolsos_limpiando = fa_gov_desembolsos_limpiando.assign(

    motivo_descarte=lambda d: pd.Series(pd.NA, index=d.index)
    .mask(
        d["anio_norm"].isna(),
        "anio ilegible",
    )
    .mask(
        d["monto_norm"].isna(),
        "monto ilegible",
    )
    .mask(
        d["anio_norm"].notna() & (d["anio_norm"] < ANIO_MINIMO),
        f"anterior a {ANIO_MINIMO}",
    ),
)


# 4. Suma las actividades de cada anio

fa_gov_desembolsos_anual = (
    fa_gov_desembolsos_limpiando
    .loc[fa_gov_desembolsos_limpiando["motivo_descarte"].isna()]
    .groupby("anio_norm", as_index=False)["monto_norm"]
    .sum()
    .rename(columns={"anio_norm": "anio", "monto_norm": "valor"})
)


# 5. Repite el total anual en los cuatro trimestres

fa_gov_desembolsos_clean = (
    fa_gov_desembolsos_anual
    .merge(
        pd.DataFrame({"trimestre_num": [1, 2, 3, 4]}),
        how="cross",
    )
    .assign(
        trimestre=lambda d: d["anio"].astype(int).astype(str) + "-Q" + d["trimestre_num"].astype(str),
        anio=lambda d: d["anio"].astype(int),
        unidad="USD",
        grano_temporal="anio repetido",
    )
    .sort_values(["anio", "trimestre_num"])
    .reset_index(drop=True)
)


# 6. Validacion de fa_gov_desembolsos

print("\n2.2 fa_gov_desembolsos")
print(f"  filas crudas    {len(fa_gov_desembolsos_limpiando)}")
print(f"  descartadas     {int(fa_gov_desembolsos_limpiando['motivo_descarte'].notna().sum())}")
print(fa_gov_desembolsos_limpiando["motivo_descarte"].value_counts().to_string())


## 2.3 usaspending_obligaciones ------------------------------------------------

# Obligaciones federales de EE.UU. con lugar de ejecucion en Paraguay. A
# diferencia de fa_gov, cada transaccion trae su propia fecha, asi que el
# trimestre es real y los trimestres se pueden sumar entre si.
#
# Se apilan contratos y asistencia. Los montos negativos son correcciones de
# transacciones anteriores y se conservan por el mismo motivo que en 2.1: el
# neto del trimestre es lo que se quiere medir.


# 1. Copia el crudo al objeto de trabajo

usaspending_limpiando = usaspending_raw.copy()


# 2. Normaliza la fecha y el monto

usaspending_limpiando = usaspending_limpiando.assign(

    # "2019-05-14" -> 2019-05-14
    fecha_norm=lambda d: pd.to_datetime(
        d["action_date"],
        format="%Y-%m-%d",
        errors="coerce",
    ),

    monto_norm=lambda d: pd.to_numeric(
        d["federal_action_obligation"],
        errors="coerce",
    ),
)


# 3. Deriva el anio y el trimestre de la fecha

usaspending_limpiando = usaspending_limpiando.assign(

    anio_norm=lambda d: d["fecha_norm"].dt.year,

    # 2019-05-14 -> 2, mayo cae en el segundo trimestre
    trimestre_num=lambda d: d["fecha_norm"].dt.quarter,
)


# 4. Marca por que una fila entra o no al total

usaspending_limpiando = usaspending_limpiando.assign(

    motivo_descarte=lambda d: pd.Series(pd.NA, index=d.index)
    .mask(
        d["fecha_norm"].isna(),
        "fecha ilegible",
    )
    .mask(
        d["monto_norm"].isna(),
        "monto ilegible",
    )
    .mask(
        d["fecha_norm"].notna() & (d["anio_norm"] < ANIO_MINIMO),
        f"anterior a {ANIO_MINIMO}",
    ),
)


# 5. Suma las transacciones de cada trimestre

usaspending_obligaciones_clean = (
    usaspending_limpiando
    .loc[usaspending_limpiando["motivo_descarte"].isna()]
    .groupby(["anio_norm", "trimestre_num"], as_index=False)["monto_norm"]
    .sum()
    .rename(columns={"anio_norm": "anio", "monto_norm": "valor"})

    # .dt.year sobre una columna con fechas nulas devuelve float: sin esto el
    # trimestre saldria "2015.0-Q1.0"
    .astype({"anio": "int64", "trimestre_num": "int64"})
    .assign(
        trimestre=lambda d: d["anio"].astype(str) + "-Q" + d["trimestre_num"].astype(str),
        unidad="USD",

        # cada transaccion tiene fecha propia: los trimestres se pueden sumar
        grano_temporal="trimestre real",
    )
    .sort_values(["anio", "trimestre_num"])
    .reset_index(drop=True)
)


# 6. Validacion de usaspending_obligaciones

#    6a. Vista de inspeccion

# usaspending_limpiando[[
#     "archivo_origen",              # de que ZIP salio la fila
#     "tipo",                        # Contracts o Assistance
#     "action_date",                 # original, sin tocar
#     "fecha_norm",                  # fecha ya parseada
#     "federal_action_obligation",   # original, sin tocar
#     "monto_norm",                  # monto ya numerico
#     "anio_norm",
#     "trimestre_num",
#     "motivo_descarte",
# ]]

print("\n2.3 usaspending_obligaciones")
print(f"  filas crudas    {len(usaspending_limpiando)}")
print(f"  descartadas     {int(usaspending_limpiando['motivo_descarte'].notna().sum())}")
print(usaspending_limpiando["motivo_descarte"].value_counts().to_string())
print(usaspending_limpiando["tipo"].value_counts().to_string())

#    6b. Cuanto pesan las correcciones negativas

print(
    "  filas con monto negativo (correcciones, se conservan): "
    f"{int((usaspending_limpiando['monto_norm'] < 0).sum())}"
)


## 2.4 dfc_comprometido --------------------------------------------------------

# Financiamiento comprometido por la DFC en proyectos de Paraguay. El Excel
# trae todos los paises, asi que aca si hay que filtrar.
#
# La fuente no publica fecha de proyecto, solo anio fiscal, asi que es de grano
# anio igual que fa_gov: el total se repite en los cuatro trimestres.


# 1. Filtra a Paraguay

dfc_limpiando = dfc_raw[dfc_raw["Country"] == "Paraguay"].copy()


# 2. Normaliza el anio fiscal y el monto comprometido

dfc_limpiando = dfc_limpiando.assign(

    anio_norm=lambda d: pd.to_numeric(
        d["Fiscal Year"],
        errors="coerce",
    ),

    monto_norm=lambda d: pd.to_numeric(
        d["Committed"],
        errors="coerce",
    ),
)


# 3. Marca por que un proyecto entra o no al total

dfc_limpiando = dfc_limpiando.assign(

    motivo_descarte=lambda d: pd.Series(pd.NA, index=d.index)
    .mask(
        d["anio_norm"].isna(),
        "anio ilegible",
    )
    .mask(
        d["monto_norm"].isna(),
        "monto ilegible",
    )
    .mask(
        d["anio_norm"].notna() & (d["anio_norm"] < ANIO_MINIMO),
        f"anterior a {ANIO_MINIMO}",
    ),
)


# 4. Suma los proyectos de cada anio

dfc_anual = (
    dfc_limpiando
    .loc[dfc_limpiando["motivo_descarte"].isna()]
    .groupby("anio_norm", as_index=False)["monto_norm"]
    .sum()
    .rename(columns={"anio_norm": "anio", "monto_norm": "valor"})
)


# 5. Repite el total anual en los cuatro trimestres
# Aquí no tenemos información para todos los años del periodo 2015-2026.

dfc_comprometido_clean = (
    dfc_anual
    .merge(
        pd.DataFrame({"trimestre_num": [1, 2, 3, 4]}),
        how="cross",
    )
    .assign(
        trimestre=lambda d: d["anio"].astype(int).astype(str) + "-Q" + d["trimestre_num"].astype(str),
        anio=lambda d: d["anio"].astype(int),
        unidad="USD",
        grano_temporal="anio repetido",
    )
    .sort_values(["anio", "trimestre_num"])
    .reset_index(drop=True)
)


# 6. Validacion de dfc_comprometido

#    Son pocos proyectos, asi que aca conviene mirarlos uno por uno en vez de
#    solo los conteos

print("\n2.4 dfc_comprometido")
print(f"  proyectos de Paraguay   {len(dfc_limpiando)}")
print(
    dfc_limpiando[[
        "Fiscal Year",       # original, sin tocar
        "Project Name",      # de que proyecto se trata
        "Committed",         # original, sin tocar
        "monto_norm",        # monto ya numerico
        "motivo_descarte",   # por que no entro, si no entro
    ]].to_string(index=False)
)


## 2.5 exim_autorizado ---------------------------------------------------------

# Autorizaciones del EXIM Bank vinculadas a Paraguay. El CSV ya viene filtrado
# a Paraguay por el script de ingestion.
#
# Se cuenta por Decision Date y no por Fiscal Year, que es la otra columna
# disponible. Las dos NO coinciden: el anio fiscal de EE.UU. arranca el 1 de
# octubre, asi que una autorizacion de noviembre de 2018 es fiscal 2019. Se usa
# la fecha de decision porque es la que ubica el hecho en el tiempo real, que
# es lo que el indice mide.
#
# El filtro por Decision == "Approved" se deja aunque hoy el archivo traiga
# solo aprobadas: si en una corrida futura EXIM publica tambien las
# rechazadas, sumarlas contaria como compromiso algo que nunca ocurrio.


# 1. Se queda con las autorizaciones aprobadas

exim_limpiando = exim_raw[exim_raw["Decision"] == "Approved"].copy()


# 2. Normaliza la fecha y el monto
#    El formato se declara explicito. Con inferencia automatica, "1/18/2013" y
#    "9/9/2014" pueden leerse como mes/dia o dia/mes segun cual venga primero
#    en el archivo, y el trimestre saldria distinto sin ningun aviso

exim_limpiando = exim_limpiando.assign(

    # "12/26/2007" -> 2007-12-26
    fecha_norm=lambda d: pd.to_datetime(
        d["Decision Date"],
        format="%m/%d/%Y",
        errors="coerce",
    ),

    monto_norm=lambda d: pd.to_numeric(
        d["Approved/Declined Amount"],
        errors="coerce",
    ),
)


# 3. Deriva el anio y el trimestre de la fecha

exim_limpiando = exim_limpiando.assign(

    anio_norm=lambda d: d["fecha_norm"].dt.year,

    trimestre_num=lambda d: d["fecha_norm"].dt.quarter,
)


# 4. Marca por que una fila entra o no al total

exim_limpiando = exim_limpiando.assign(

    motivo_descarte=lambda d: pd.Series(pd.NA, index=d.index)
    .mask(
        d["fecha_norm"].isna(),
        "fecha ilegible",
    )
    .mask(
        d["monto_norm"].isna(),
        "monto ilegible",
    )
    .mask(
        d["fecha_norm"].notna() & (d["anio_norm"] < ANIO_MINIMO),
        f"anterior a {ANIO_MINIMO}",
    ),
)


# 5. Suma las autorizaciones de cada trimestre

exim_autorizado_clean = (
    exim_limpiando
    .loc[exim_limpiando["motivo_descarte"].isna()]
    .groupby(["anio_norm", "trimestre_num"], as_index=False)["monto_norm"]
    .sum()
    .rename(columns={"anio_norm": "anio", "monto_norm": "valor"})

    # .dt.year sobre una columna con fechas nulas devuelve float: sin esto el
    # trimestre saldria "2015.0-Q1.0"
    .astype({"anio": "int64", "trimestre_num": "int64"})
    .assign(
        trimestre=lambda d: d["anio"].astype(str) + "-Q" + d["trimestre_num"].astype(str),
        unidad="USD",
        grano_temporal="trimestre real",
    )
    .sort_values(["anio", "trimestre_num"])
    .reset_index(drop=True)
)


# 6. Validacion de exim_autorizado

#    6a. Que se descarto y por que

print("\n2.5 exim_autorizado")
print(f"  filas crudas    {len(exim_limpiando)}")
print(f"  descartadas     {int(exim_limpiando['motivo_descarte'].notna().sum())}")
print(exim_limpiando["motivo_descarte"].value_counts().to_string())

#    6b. Cuanto se corre el anio fiscal contra el anio de decision
#        Si esto da distinto de cero, la eleccion de columna cambia la serie

print(
    "  filas donde Fiscal Year != anio de Decision Date: "
    f"{int((pd.to_numeric(exim_limpiando['Fiscal Year'], errors='coerce') != exim_limpiando['anio_norm']).sum())}"
)


## 2.6 bid_proyectos_aprobados -------------------------------------------------

# Proyectos del BID aprobados para Paraguay. OJO: es el monto TOTAL aprobado
# del proyecto, no la porcion atribuible a EE.UU. segun su cuota de capital en
# el banco. Como cifra de "compromiso de EE.UU." todavia NO sirve; hoy es un
# proxy de actividad multilateral. La ponderacion queda pendiente para 03_final.
#
# El JSON trae fecha y monto como texto, no como numero, asi que los dos hay
# que convertirlos.


# 1. Copia el crudo al objeto de trabajo

bid_limpiando = bid_raw.copy()


# 2. Normaliza la fecha y el monto

bid_limpiando = bid_limpiando.assign(

    # "2011-10-03 00:00:00.000000000" -> 2011-10-03
    fecha_norm=lambda d: pd.to_datetime(
        d["apprvl_dt"],
        errors="coerce",
    ),

    # "60000000.0" -> 60000000.0
    monto_norm=lambda d: pd.to_numeric(
        d["orig_apprvd_useq_amnt"],
        errors="coerce",
    ),
)


# 3. Deriva el anio y el trimestre de la fecha

bid_limpiando = bid_limpiando.assign(

    anio_norm=lambda d: d["fecha_norm"].dt.year,

    trimestre_num=lambda d: d["fecha_norm"].dt.quarter,
)


# 4. Marca por que un proyecto entra o no al total
#    Los proyectos con monto cero se dejan pasar: sumar cero no cambia el
#    trimestre, y marcarlos como descarte escondería que la fuente los publica

bid_limpiando = bid_limpiando.assign(

    motivo_descarte=lambda d: pd.Series(pd.NA, index=d.index)
    .mask(
        d["fecha_norm"].isna(),
        "fecha ilegible",
    )
    .mask(
        d["monto_norm"].isna(),
        "monto ilegible",
    )
    .mask(
        d["fecha_norm"].notna() & (d["anio_norm"] < ANIO_MINIMO),
        f"anterior a {ANIO_MINIMO}",
    ),
)


# 5. Suma los proyectos aprobados en cada trimestre

bid_proyectos_aprobados_clean = (
    bid_limpiando
    .loc[bid_limpiando["motivo_descarte"].isna()]
    .groupby(["anio_norm", "trimestre_num"], as_index=False)["monto_norm"]
    .sum()
    .rename(columns={"anio_norm": "anio", "monto_norm": "valor"})

    # .dt.year sobre una columna con fechas nulas devuelve float: sin esto el
    # trimestre saldria "2015.0-Q1.0"
    .astype({"anio": "int64", "trimestre_num": "int64"})
    .assign(
        trimestre=lambda d: d["anio"].astype(str) + "-Q" + d["trimestre_num"].astype(str),
        unidad="USD",
        grano_temporal="trimestre real",
    )
    .sort_values(["anio", "trimestre_num"])
    .reset_index(drop=True)
)


# 6. Validacion de bid_proyectos_aprobados

#    6a. Vista de inspeccion

# bid_limpiando[[
#     "oper_num",                # numero de operacion
#     "oper_nm",                 # nombre del proyecto
#     "apprvl_dt",               # original, sin tocar
#     "fecha_norm",              # fecha ya parseada
#     "orig_apprvd_useq_amnt",   # original, sin tocar
#     "monto_norm",              # monto ya numerico
#     "anio_norm",
#     "trimestre_num",
#     "motivo_descarte",
# ]]

print("\n2.6 bid_proyectos_aprobados")
print(f"  proyectos crudos   {len(bid_limpiando)}")
print(f"  descartados        {int(bid_limpiando['motivo_descarte'].notna().sum())}")
print(bid_limpiando["motivo_descarte"].value_counts().to_string())

#    6b. Proyectos que entran con monto cero

print(
    "  proyectos dentro del rango con monto 0: "
    f"{int((bid_limpiando['motivo_descarte'].isna() & (bid_limpiando['monto_norm'] == 0)).sum())}"
)


## 2.7 bancomundial_proyectos_aprobados ----------------------------------------

# Proyectos del Banco Mundial aprobados para Paraguay. Vale la misma advertencia
# que el BID (2.6): es el monto total del proyecto, sin ponderar por la cuota de
# capital de EE.UU.
#
# Dos particularidades de esta fuente que no tienen las otras:
#
#   - totalamt es el compromiso IBRD + IDA. Los proyectos que son SOLO donacion
#     lo traen vacio y el monto real esta en grantamt. Se los deja caer como
#     "monto ilegible" para no cambiar el criterio de la variable por decision
#     propia, pero quedan contados y a la vista en la validacion 6b: si se
#     decide incluirlos, el cambio va en el paso 2.
#
#   - la fuente publica aprobaciones FUTURAS ya anunciadas por el directorio,
#     asi que la serie se extiende mas alla del trimestre en curso. No es un
#     error de fecha; hay que decidir en 03_final hasta donde se corta.


# 1. Copia el crudo al objeto de trabajo

bm_limpiando = bm_raw.copy()


# 2. Normaliza la fecha y el monto

bm_limpiando = bm_limpiando.assign(

    # "2027-02-18T00:00:00Z" -> 2027-02-18, sin zona horaria para poder
    # comparar contra las demas fuentes
    fecha_norm=lambda d: pd.to_datetime(
        d["boardapprovaldate"],
        format="ISO8601",
        utc=True,
        errors="coerce",
    ).dt.tz_localize(None),

    monto_norm=lambda d: pd.to_numeric(
        d["totalamt"],
        errors="coerce",
    ),

    # el monto de las donaciones, que no entra a totalamt. Solo para poder
    # dimensionar en la validacion lo que se esta dejando afuera
    monto_donacion=lambda d: pd.to_numeric(
        d["grantamt"],
        errors="coerce",
    ),
)


# 3. Deriva el anio y el trimestre de la fecha

bm_limpiando = bm_limpiando.assign(

    anio_norm=lambda d: d["fecha_norm"].dt.year,

    trimestre_num=lambda d: d["fecha_norm"].dt.quarter,
)


# 4. Marca por que un proyecto entra o no al total

bm_limpiando = bm_limpiando.assign(

    motivo_descarte=lambda d: pd.Series(pd.NA, index=d.index)
    .mask(
        d["fecha_norm"].isna(),
        "fecha ilegible",
    )
    .mask(
        d["monto_norm"].isna(),
        "monto ilegible",
    )
    .mask(
        d["fecha_norm"].notna() & (d["anio_norm"] < ANIO_MINIMO),
        f"anterior a {ANIO_MINIMO}",
    ),
)


# 5. Suma los proyectos aprobados en cada trimestre

bancomundial_proyectos_aprobados_clean = (
    bm_limpiando
    .loc[bm_limpiando["motivo_descarte"].isna()]
    .groupby(["anio_norm", "trimestre_num"], as_index=False)["monto_norm"]
    .sum()
    .rename(columns={"anio_norm": "anio", "monto_norm": "valor"})

    # .dt.year sobre una columna con fechas nulas devuelve float: sin esto el
    # trimestre saldria "2015.0-Q1.0"
    .astype({"anio": "int64", "trimestre_num": "int64"})
    .assign(
        trimestre=lambda d: d["anio"].astype(str) + "-Q" + d["trimestre_num"].astype(str),
        unidad="USD",
        grano_temporal="trimestre real",
    )
    .sort_values(["anio", "trimestre_num"])
    .reset_index(drop=True)
)


# 6. Validacion de bancomundial_proyectos_aprobados

#    6a. Que se descarto y por que

print("\n2.7 bancomundial_proyectos_aprobados")
print(f"  proyectos crudos   {len(bm_limpiando)}")
print(f"  descartados        {int(bm_limpiando['motivo_descarte'].notna().sum())}")
print(bm_limpiando["motivo_descarte"].value_counts().to_string())

#    6b. Los proyectos del rango que se caen por no tener totalamt
#        Son las donaciones puras: la decision de incluirlas o no esta abierta

print("  proyectos del rango sin totalamt (donaciones):")
print(
    bm_limpiando.loc[
        (bm_limpiando["anio_norm"] >= ANIO_MINIMO)
        & bm_limpiando["monto_norm"].isna(),
        ["boardapprovaldate", "project_name", "totalamt", "monto_donacion"],
    ].to_string(index=False)
)

#    6c. Aprobaciones posteriores al trimestre en curso

print("  proyectos con aprobacion futura:")
print(
    bm_limpiando.loc[
        bm_limpiando["fecha_norm"] > pd.Timestamp.today(),
        ["boardapprovaldate", "project_name", "totalamt"],
    ].to_string(index=False)
)


#=============================================================================.#
# 3. EXPORTAR CLEAN -----
#=============================================================================.#

# Las 7 variables se suben a 02_limpias, una carpeta por variable, con la fecha
# de la corrida en el nombre del archivo. subir_variable() es idempotente por
# dia: si ya se corrio hoy, no vuelve a subir.
#
# La columna grano_temporal NO viaja al CSV: el contrato de 02_limpias son
# cinco columnas fijas y es igual en las cuatro dimensiones. Vive solo en los
# objetos de este script, que es donde se revisa.


# 1. Junta las 7 variables con su nombre de destino

variables_clean = [
    ("fa_gov_obligaciones",               fa_gov_obligaciones_clean),
    ("fa_gov_desembolsos",                fa_gov_desembolsos_clean),
    ("usaspending_obligaciones",          usaspending_obligaciones_clean),
    ("dfc_comprometido",                  dfc_comprometido_clean),
    ("exim_autorizado",                   exim_autorizado_clean),
    ("bid_proyectos_aprobados",           bid_proyectos_aprobados_clean),
    ("bancomundial_proyectos_aprobados",  bancomundial_proyectos_aprobados_clean),
]


# 2. Validacion final: el resumen de las 7 series antes de subir nada
#    Es la tabla que se mira para decidir si la corrida se sube o no

resumen_clean = pd.DataFrame(
    [
        {
            "variable": nombre_variable,
            "trimestres": len(tabla_clean),
            "desde": tabla_clean["trimestre"].min(),
            "hasta": tabla_clean["trimestre"].max(),
            "grano": tabla_clean["grano_temporal"].iloc[0],
            "suma_de_la_serie": tabla_clean["valor"].sum(),
        }
        for nombre_variable, tabla_clean in variables_clean
    ]
)

print("\nRESUMEN DE LAS 7 VARIABLES")
print(resumen_clean.to_string(index=False))

print(
    "\nEn las variables de grano 'anio repetido', suma_de_la_serie es CUATRO "
    "veces el total real:\nel valor anual esta repetido en los cuatro "
    "trimestres. No sumar trimestres ahi."
)


# 3. Validacion de contrato: el esquema tiene que ser el mismo en las 7
#    Si una variable sale con otras columnas, 03_final no las va a poder apilar

for nombre_variable, tabla_clean in variables_clean:

    columnas_faltantes = {"trimestre", "anio", "trimestre_num", "valor", "unidad"} - set(tabla_clean.columns)

    if columnas_faltantes:

        raise SystemExit(
            f"La variable '{nombre_variable}' no cumple el contrato de "
            f"02_limpias: le faltan las columnas {sorted(columnas_faltantes)}."
        )


# 4. Sube cada variable a su carpeta de Drive
#    Solo si SUBIR_A_DRIVE quedo en True, para poder correr el script entero
#    mientras se revisa sin escribir nada

if not SUBIR_A_DRIVE:

    print("\nSUBIR_A_DRIVE = False: no se subio nada. Los objetos *_clean quedan en memoria.")

else:

    print(f"\n[{DIMENSION_LIMPIA}]")

    for nombre_variable, tabla_clean in variables_clean:

        # subir_variable espera {(anio, trimestre): valor}, no un DataFrame
        valores = dict(
            zip(
                zip(tabla_clean["anio"], tabla_clean["trimestre_num"]),
                tabla_clean["valor"],
            )
        )

        subir_variable(DIMENSION_LIMPIA, nombre_variable, valores, "USD")
