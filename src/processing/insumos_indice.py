"""
Processing de la pseudo-dimension `insumos_indice`: IPC de EE.UU. y poblacion
de Paraguay, llevados al mismo esquema trimestral que las 4 dimensiones.

No son variables del vinculo bilateral sino insumos transversales que usa la
etapa 04: el IPC para deflactar las variables monetarias y la poblacion para
expresarlas por habitante. Pasan por 02_limpias igual que las demas variables
para que la etapa 04 lea todo del panel de 03_integracion y no tenga que ir a
ninguna API ni a los crudos.

Entradas (subidas por ingestion a 01_crudas/insumos_indice_crudas/):
  - bls_ipc_eeuu: JSON crudo de la API del BLS, serie CUUR0000SA0 (IPC de
    todos los consumidores urbanos, sin desestacionalizar, base 1982-84=100),
    en tramos de 10 anios. Si dos archivos repiten un mes, gana el que queda
    ultimo en orden alfabetico (el tramo mas reciente).
  - ine_poblacion_paraguay: Excel del INE, hoja "Poblac a mitad de año
    1950-2050", fila "Total País".

Salidas (02_limpias/insumos_indice_limpias/{variable}/):
  - ipc_eeuu: promedio simple de los meses publicados del trimestre, unidad
    "indice". Octubre de 2025 no existe en la fuente (el BLS no lo publico por
    la interrupcion de fondos del gobierno federal de 2025), asi que 2025-Q4
    es el promedio de noviembre y diciembre. Un trimestre en curso (sin sus 3
    meses) no se publica: su promedio no seria comparable con los demas.
  - poblacion_paraguay: poblacion a mitad de anio, repetida en los 4
    trimestres del anio (mismo criterio que fa_gov y bea para fuentes de grano
    anual), unidad "cantidad". Se corta en ANIO_MAXIMO_POBLACION porque la
    fuente es una proyeccion hasta 2050.
"""
import io
import json

import pandas as pd

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos
from src.processing._common import subir_variable

DIMENSION_CRUDA = "insumos_indice"
DIMENSION_LIMPIA = "insumos_indice_limpias"

ANIO_MINIMO = 2015

# la proyeccion del INE llega a 2050; se corta en el ultimo anio del panel
ANIO_MAXIMO_POBLACION = 2026

# meses que el BLS declara inexistentes; se excluyen del promedio y no
# cuentan como faltantes del trimestre
MESES_SIN_PUBLICAR = {(2025, 10)}

HOJA_POBLACION = "Poblac a mitad de año 1950-2050"
ROTULO_POBLACION = "Total País"


def _carpeta(fuente):
    return FOLDER_IDS[(DIMENSION_CRUDA, fuente)]


def _extraer_ipc():
    """{(anio, trim): promedio de los meses publicados del trimestre}."""
    archivos = [
        archivo
        for archivo in listar_archivos(_carpeta("bls_ipc_eeuu"))
        if archivo["name"].endswith(".json")
    ]
    if not archivos:
        raise ValueError("no hay ningun .json en la carpeta cruda")

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

    trimestres = {}
    for (anio, mes), valor in meses.items():
        if anio >= ANIO_MINIMO:
            trimestres.setdefault((anio, (mes - 1) // 3 + 1), {})[mes] = valor

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


def _extraer_poblacion():
    """{(anio, trim): poblacion a mitad de anio}, el mismo valor en los 4 trimestres."""
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

    # la fila de anios es la que tiene 1950; la de poblacion, la del rotulo
    es_fila_anios = hoja.apply(lambda f: (pd.to_numeric(f, errors="coerce") == 1950).any(), axis=1)
    es_fila_total = hoja.apply(lambda f: f.astype(str).str.strip().eq(ROTULO_POBLACION).any(), axis=1)
    if not es_fila_anios.any() or not es_fila_total.any():
        raise ValueError(f"no se encontro la fila de anios o la fila '{ROTULO_POBLACION}'")

    fila_anios = hoja.index[es_fila_anios][0]
    fila_total = hoja.index[es_fila_total][0]

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


def run():
    print(f"[{DIMENSION_LIMPIA}]")
    errores = []

    try:
        subir_variable(DIMENSION_LIMPIA, "ipc_eeuu", _extraer_ipc(), "indice")
    except Exception as exc:  # noqa: BLE001
        errores.append(("ipc_eeuu", repr(exc)))
        print(f"    [!] ipc_eeuu: {exc!r}")

    try:
        subir_variable(DIMENSION_LIMPIA, "poblacion_paraguay", _extraer_poblacion(), "cantidad")
    except Exception as exc:  # noqa: BLE001
        errores.append(("poblacion_paraguay", repr(exc)))
        print(f"    [!] poblacion_paraguay: {exc!r}")

    if errores and len(errores) == 2:
        raise RuntimeError(f"Fallaron todas las fuentes de {DIMENSION_LIMPIA}: {errores}")


if __name__ == "__main__":
    run()
