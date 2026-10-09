#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# RESPONSABLE DEL CODIGO:                                                      #
#   PIERO VALLES-MARAVI (ESPECIALISTA) - pvalles@equilibriumbdc.com            #
#                                                                              #
# FECHA DE CREACION: 09/10/2026                                                #
# NOMBRE: exportar_datos                                                       #
# DETALLE: Descarga del Google Sheet del tablero (us_py_engagement_index) las  #
#          pestanas indice_ancho y diccionario como CSV, para que el dashboard #
#          las lea junto a su index.html. Lo corre el workflow                 #
#          publicar_dashboard.yml con la cuenta de servicio: el Sheet sigue    #
#          privado (la organizacion no permite publicarlo en la web).          #
# CORRE DESPUES DE: src/analysis_index/indice_script/construccion_indice.py    #
# SALIDA: {carpeta}/indice_ancho.csv y {carpeta}/diccionario.csv               #
#         (carpeta = primer argumento; por defecto _site/datos)                #
#-----------------------------------------------------------------------------.#


# 0. SETUP -----

## 0.1. Entorno ---------------------------------------------------------------------

import csv
import os
import sys
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials


## 0.2. Rutas y credenciales --------------------------------------------------------

# misma cuenta de servicio que escribe el Sheet; aca solo se lee
CREDENCIALES = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

# solo lectura: abrir el Sheet por nombre necesita ver los metadatos de Drive
ALCANCES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

CARPETA_SALIDA = Path(sys.argv[1] if len(sys.argv) > 1 else "_site/datos")


## 0.3. Parametros configurables ----------------------------------------------------

# el Sheet que publica construccion_indice.py (NOMBRE_HOJA_RESULTADO) y su carpeta 04_final
NOMBRE_HOJA = "us_py_engagement_index"

ID_CARPETA_FINAL = "1BPhoxDLryWrJ4-6Z02H3EtcyaENFaJUe"

PESTANAS = ["indice_ancho", "diccionario"]

# columnas sin las que el dashboard no puede dibujarse; si faltan, se corta antes de publicar
COLUMNAS_OBLIGATORIAS = [
    "trimestre",
    "indice_agregado_base_2015_2019",
    "banda_series_p05_base_2015_2019",
    "banda_series_p95_base_2015_2019",
]


#=============================================================================.#
# 1. LEER EL SHEET -----
#=============================================================================.#

# 1. Abre el Sheet por nombre dentro de 04_final (busqueda, no crea nada si no existe)
cliente = gspread.authorize(
    Credentials.from_service_account_file(
        CREDENCIALES,
        scopes=ALCANCES,
    )
)

hoja = cliente.open(
    NOMBRE_HOJA,
    folder_id=ID_CARPETA_FINAL,
)


# 2. Valores de cada pestana sin formato de la configuracion regional (1234.5, no "1,234.50")
tablas_raw = {
    pestana: hoja.worksheet(pestana).get_all_values(
        value_render_option="UNFORMATTED_VALUE",
    )
    for pestana in PESTANAS
}


#=============================================================================.#
# 2. VALIDAR -----
#=============================================================================.#

# 1. Columnas que el dashboard necesita en indice_ancho
encabezado_ancho = tablas_raw["indice_ancho"][0]

faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in encabezado_ancho]

if faltantes:

    # se corta aca para que el sitio ya publicado no se reemplace por uno roto
    raise SystemExit(
        f"Faltan columnas en indice_ancho: {', '.join(faltantes)}. "
        "Hay que correr construccion_indice.py para que el Sheet las publique."
    )


# 2. Cada pestana trae al menos una fila de datos
vacias = [p for p, filas in tablas_raw.items() if len(filas) < 2]

if vacias:

    raise SystemExit(f"Pestanas sin datos: {', '.join(vacias)}.")


#=============================================================================.#
# 3. EXPORTAR -----
#=============================================================================.#

CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

for pestana, filas in tablas_raw.items():

    ruta = CARPETA_SALIDA / f"{pestana}.csv"

    # utf-8 y saltos de linea \n: los lee el parser del dashboard
    with ruta.open("w", encoding="utf-8", newline="") as archivo:

        csv.writer(archivo, lineterminator="\n").writerows(filas)

    print(f"  {ruta}: {len(filas) - 1} filas x {len(filas[0])} columnas")
