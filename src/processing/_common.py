#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 03/09/2026                                                #
# NOMBRE: _common                                                              #
# DETALLE: ayudante compartido de processing: reescalar() lleva unidades       #
#   nativas a USD sin escalar y subir_variable() sube un CSV por variable con  #
#   el esquema fijo (trimestre, anio, trimestre_num, valor, unidad). NO es un  #
#   modulo de processing: run_processing.py lo ignora por el guion bajo.       #
#                                                                              #
# CORRE DESPUES DE: nada; lo importan los modulos de src/processing/           #
# SALIDA: funciones reescalar y subir_variable; esta ultima escribe            #
#   02_limpias/<dimension>_limpias/<variable>/                                 #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
from datetime import datetime, timezone

import pandas as pd

from src.drive import resolve_variable_folder, subir_si_cambio



# Funciones auxiliares ---------------------------------------------------------

# Politica de salida (2026-09-03, a pedido del usuario): cada VARIABLE de cada
# dimension sube su propio CSV a una carpeta propia, no un CSV con todas las variables
# de la dimension juntas. Asi cada variable se puede leer o actualizar sola en una
# etapa posterior. Todas comparten el mismo esquema de columnas, sin importar si son
# monetarias, de cantidad o de indice: trimestre, anio, trimestre_num, valor, unidad.


def reescalar(valores, factor):
    """{(anio,trim): valor} -> mismo dict con cada valor multiplicado por
    `factor` (para llevar unidades nativas en miles/millones a USD sin
    escalar, ver la politica de unidades en compromiso_economico_privado.py)."""
    return {clave: valor * factor for clave, valor in valores.items()}


def subir_variable(dimension_limpia, variable, valores, unidad):
    """Sube un CSV (trimestre, anio, trimestre_num, valor, unidad) a
    02_limpias/{dimension_limpia}/{variable}/. `valores` es
    {(anio,trim): valor}. Un archivo por variable y por dia: si ya hay uno de
    hoy con el mismo contenido no hace nada, y si el contenido cambio (una
    segunda corrida el mismo dia, con crudos refrescados) lo REEMPLAZA en vez
    de saltearlo - antes el archivo del dia quedaba obsoleto y habia que
    mandarlo a la papelera a mano. Devuelve True si subio o actualizo algo,
    False si no habia datos o ya estaba al dia."""

    # 1. sin datos no se sube nada
    if not valores:
        print(f"    [!] {variable}: sin datos, no se sube nada")
        return False

    # 2. resuelve la carpeta de la variable y arma el nombre del dia
    carpeta_id = resolve_variable_folder(dimension_limpia, variable)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"{variable}_trimestral_{fecha}.csv"

    # 3. arma el CSV con una fila por trimestre, en orden cronologico
    filas = [
        {
            "trimestre": f"{anio}-Q{trim}",
            "anio": anio,
            "trimestre_num": trim,
            "valor": valor,
            "unidad": unidad,
        }
        for (anio, trim), valor in sorted(valores.items())
    ]
    df = pd.DataFrame(filas)
    contenido = df.to_csv(index=False).encode("utf-8")

    # 4. sube el archivo; se reemplaza solo si el contenido cambio
    resultado = subir_si_cambio(contenido, nombre, carpeta_id, mime_type="text/csv")

    # 5. validacion: dice que paso con el archivo
    if resultado == "sin_cambios":
        print(f"    [{variable}] '{nombre}' ya estaba al dia (mismo contenido), no se subio de nuevo.")
        return False

    print(
        f"    [{variable}] '{nombre}' {resultado} ({len(df)} trimestres, "
        f"{df['trimestre'].min()} a {df['trimestre'].max()})"
    )
    return True
