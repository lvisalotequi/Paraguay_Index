"""Ruta base donde src/ingestion/ guarda los datos crudos descargados.

Los datos NO viven dentro del repo: viven en la carpeta de datos del
proyecto en la Unidad compartida (fuera de git, no se versiona). Cada
modulo de ingestion arma su propia subcarpeta debajo de DATA_ROOT, dentro
de la carpeta de la dimension a la que pertenece.

Se puede sobreescribir con la variable de entorno DATA_ROOT (por ejemplo si
otra maquina monta la Unidad compartida en una letra de unidad distinta).
"""
import os

DATA_ROOT = os.environ.get(
    "DATA_ROOT",
    r"G:\Unidades compartidas\PROYECTOS 🌍📂\🥁 PROYECTOS\🏆 Proyectos S. Empresarial"
    r"\02-9-0406 - Global Americans - US-PY Engagement Index\2. Implementación"
    r"\2.Datos_recolectados",
)


def ruta_larga(ruta):
    """Antepone el prefijo \\\\?\\ en Windows para evitar el limite de 260
    caracteres de MAX_PATH. Los nombres de carpeta de la Unidad compartida
    son largos (y con emojis), asi que cualquier archivo con nombre largo
    dentro de DATA_ROOT lo pisa facil. Usar en cada os.makedirs/open/exists
    que toque una ruta dentro de DATA_ROOT. No hace nada fuera de Windows.
    """
    if os.name == "nt":
        ruta_abs = os.path.abspath(ruta)
        if not ruta_abs.startswith("\\\\?\\"):
            return "\\\\?\\" + ruta_abs
    return ruta
