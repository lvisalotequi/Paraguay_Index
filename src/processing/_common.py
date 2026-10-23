"""Helper compartido por los modulos de src/processing/.

Prefijo `_`: este archivo no es un modulo de processing en si
(run_processing.py lo ignora, igual que src/ingestion/_bcp_common.py), es
un helper que importan los que si lo son.

Politica de salida (2026-09-03, a pedido del usuario): cada VARIABLE de
cada dimension sube su propio CSV a una carpeta propia
(02_limpias/{dimension_limpia}/{variable}/), no un solo CSV con todas las
variables de la dimension juntas - asi cada variable se puede leer o
actualizar de forma independiente en una etapa posterior. Todas las
variables, sin importar el tipo (monetario/cantidad/indice), comparten el
mismo esquema de columnas: trimestre, anio, trimestre_num, valor, unidad.
"""
from datetime import datetime, timezone

import pandas as pd

from src.drive import resolve_variable_folder, subir_si_cambio


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
    if not valores:
        print(f"    [!] {variable}: sin datos, no se sube nada")
        return False

    carpeta_id = resolve_variable_folder(dimension_limpia, variable)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"{variable}_trimestral_{fecha}.csv"

    filas = [
        {"trimestre": f"{anio}-Q{trim}", "anio": anio, "trimestre_num": trim, "valor": valor, "unidad": unidad}
        for (anio, trim), valor in sorted(valores.items())
    ]
    df = pd.DataFrame(filas)
    contenido = df.to_csv(index=False).encode("utf-8")
    resultado = subir_si_cambio(contenido, nombre, carpeta_id, mime_type="text/csv")

    if resultado == "sin_cambios":
        print(f"    [{variable}] '{nombre}' ya estaba al dia (mismo contenido), no se subio de nuevo.")
        return False

    print(
        f"    [{variable}] '{nombre}' {resultado} ({len(df)} trimestres, "
        f"{df['trimestre'].min()} a {df['trimestre'].max()})"
    )
    return True
