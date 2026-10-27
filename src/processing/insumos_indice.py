#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 05/10/2026                                                #
# NOMBRE: insumos_indice                                                       #
# DETALLE: lleva el IPC de EE.UU. y la poblacion de Paraguay al esquema        #
#   trimestral de las 4 dimensiones. Son insumos transversales de la etapa 04  #
#   (deflactar y expresar por habitante), no variables del vinculo bilateral.  #
#   NO consulta ninguna API: lee solo los crudos de Drive.                     #
#                                                                              #
# CORRE DESPUES DE: ingestion de bls_ipc_eeuu e ine_poblacion_paraguay         #
#   (src/ingestion/)                                                           #
# SALIDA: un CSV por variable (ipc_eeuu, poblacion_paraguay) en                #
#   02_limpias/insumos_indice_limpias/<variable>/                              #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import json
from datetime import datetime, timezone

import pandas as pd

from src.drive import descargar_archivo, listar_archivos, resolve_ingestion_folder
from src.processing._common import subir_variable



# Parametros -------------------------------------------------------------------

# Carpetas de Drive: la cruda la escribe ingestion y la limpia la escribe este modulo.
DIMENSION_CRUDA  = "insumos_indice"
DIMENSION_LIMPIA = "insumos_indice_limpias"

ANIO_MINIMO = 2015

# La proyeccion del INE llega a 2050; se corta en el anio en curso (antes era una
# constante a mano que habia que subir en cada edicion).
ANIO_MAXIMO_POBLACION = datetime.now(timezone.utc).year

# Meses que el BLS declara inexistentes; se excluyen del promedio y no cuentan como
# faltantes del trimestre.
MESES_SIN_PUBLICAR = {(2025, 10)}

HOJA_POBLACION   = "Poblac a mitad de año 1950-2050"
ROTULO_POBLACION = "Total País"



# Funciones auxiliares ---------------------------------------------------------


def _carpeta(fuente):
    return resolve_ingestion_folder(DIMENSION_CRUDA, fuente)



# IPC de EE.UU. ----------------------------------------------------------------

# Entrada: JSON crudo de la API del BLS (bls_ipc_eeuu), serie CUUR0000SA0: IPC de todos
# los consumidores urbanos, sin desestacionalizar, base 1982-84=100, en tramos de 10
# anios. Si dos archivos repiten un mes, gana el que queda ultimo en orden alfabetico
# (el tramo mas reciente).
#
# Salida: promedio simple de los meses publicados del trimestre, unidad "indice".
#
# POR QUE 2025-Q4 SE PROMEDIA CON DOS MESES: octubre de 2025 no existe en la fuente (el
# BLS no lo publico por la interrupcion de fondos del gobierno federal de 2025), asi
# que el trimestre es el promedio de noviembre y diciembre. Se descarto dejar 2025-Q4
# sin dato porque perderia el ultimo trimestre del panel por un hueco que no es de la
# serie sino de la publicacion.
#
# POR QUE UN TRIMESTRE EN CURSO NO SE PUBLICA: sin sus 3 meses, su promedio no seria
# comparable con el de los demas trimestres.


def _extraer_ipc():
    """{(anio, trim): promedio de los meses publicados del trimestre}."""

    # 1. lista los JSON de la carpeta cruda
    archivos = [
        archivo
        for archivo in listar_archivos(_carpeta("bls_ipc_eeuu"))
        if archivo["name"].endswith(".json")
    ]
    if not archivos:
        raise ValueError("no hay ningun .json en la carpeta cruda")

    # 2. junta los meses de todos los tramos; el ultimo tramo pisa a los anteriores
    meses = {}
    for archivo in sorted(archivos, key=lambda a: a["name"]):
        contenido = json.loads(descargar_archivo(archivo["id"]))
        if contenido.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError(f"{archivo['name']}: la API no devolvio REQUEST_SUCCEEDED")

        for punto in contenido["Results"]["series"][0]["data"]:
            # M13 es el promedio anual que el BLS agrega a veces; no es un mes
            if not punto["period"].startswith("M") or punto["period"] == "M13":
                continue

            # "-" es el valor que usa el BLS para un mes sin dato
            if punto["value"] in ("-", ""):
                continue

            meses[(int(punto["year"]), int(punto["period"][1:]))] = float(punto["value"])

    # 3. agrupa los meses por trimestre, desde ANIO_MINIMO
    trimestres = {}
    for (anio, mes), valor in meses.items():
        if anio >= ANIO_MINIMO:
            trimestres.setdefault((anio, (mes - 1) // 3 + 1), {})[mes] = valor

    # 4. promedia solo los trimestres completos
    resultado = {}
    for (anio, trim), valores_mes in trimestres.items():
        esperados = {
            mes
            for mes in range(3 * trim - 2, 3 * trim + 1)
            if (anio, mes) not in MESES_SIN_PUBLICAR
        }

        # trimestre en curso o con un mes faltante no declarado: no se publica
        if set(valores_mes) != esperados:
            print(f"    [ipc_eeuu] {anio}-Q{trim} incompleto ({len(valores_mes)} meses), no se publica")
            continue

        resultado[(anio, trim)] = sum(valores_mes.values()) / len(valores_mes)

    return resultado



# Poblacion de Paraguay --------------------------------------------------------

# Entrada: Excel del INE (ine_poblacion_paraguay), hoja HOJA_POBLACION (poblacion a
# mitad de anio, 1950-2050), fila ROTULO_POBLACION (el total del pais).
#
# Salida: poblacion a mitad de anio repetida en los 4 trimestres del anio, unidad
# "cantidad". Es el mismo criterio que fa_gov y bea para fuentes de grano anual: la
# fuente no publica un dato trimestral, y repetir el valor anual evita inventar uno.
# Se corta en ANIO_MAXIMO_POBLACION porque la fuente es una proyeccion hasta 2050.


def _extraer_poblacion():
    """{(anio, trim): poblacion a mitad de anio}, el mismo valor en los 4 trimestres."""

    # 1. toma el Excel mas reciente de la carpeta cruda
    archivos = [
        archivo
        for archivo in listar_archivos(_carpeta("ine_poblacion_paraguay"))
        if archivo["name"].endswith(".xlsx")
    ]
    if not archivos:
        raise ValueError("no hay ningun .xlsx en la carpeta cruda")

    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    hoja = pd.read_excel(
        io.BytesIO(descargar_archivo(archivo["id"])),
        sheet_name=HOJA_POBLACION,
        header=None,
    )

    # 2. ubica la fila de anios y la fila de poblacion total
    # la fila de anios es la que tiene 1950; la de poblacion, la del rotulo
    es_fila_anios = hoja.apply(lambda f: (pd.to_numeric(f, errors="coerce") == 1950).any(), axis=1)
    es_fila_total = hoja.apply(lambda f: f.astype(str).str.strip().eq(ROTULO_POBLACION).any(), axis=1)
    if not es_fila_anios.any() or not es_fila_total.any():
        raise ValueError(f"no se encontro la fila de anios o la fila '{ROTULO_POBLACION}'")

    fila_anios = hoja.index[es_fila_anios][0]
    fila_total = hoja.index[es_fila_total][0]

    # 3. recorre las columnas y repite el valor anual en los 4 trimestres
    resultado = {}
    for columna in hoja.columns:
        anio = pd.to_numeric(hoja.at[fila_anios, columna], errors="coerce")
        valor = pd.to_numeric(hoja.at[fila_total, columna], errors="coerce")
        if pd.isna(anio) or pd.isna(valor):
            continue

        if ANIO_MINIMO <= int(anio) <= ANIO_MAXIMO_POBLACION:
            for trim in range(1, 5):
                resultado[(int(anio), trim)] = float(valor)

    return resultado



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. avisa que dimension procesa
    print(f"[{DIMENSION_LIMPIA}]")
    errores = []

    # 2. IPC de EE.UU.: una variable que falla no frena a la otra
    try:
        subir_variable(DIMENSION_LIMPIA, "ipc_eeuu", _extraer_ipc(), "indice")
    except Exception as exc:  # noqa: BLE001
        errores.append(("ipc_eeuu", repr(exc)))
        print(f"    [!] ipc_eeuu: {exc!r}")

    # 3. poblacion de Paraguay
    try:
        subir_variable(DIMENSION_LIMPIA, "poblacion_paraguay", _extraer_poblacion(), "cantidad")
    except Exception as exc:  # noqa: BLE001
        errores.append(("poblacion_paraguay", repr(exc)))
        print(f"    [!] poblacion_paraguay: {exc!r}")

    # 4. validacion: si fallo alguna variable, termina con error despues de subir las otras
    if errores:
        raise RuntimeError(f"Fallaron {len(errores)} fuentes de {DIMENSION_LIMPIA}: {errores}")


if __name__ == "__main__":
    run()
