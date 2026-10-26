"""Lectura de claves desde variables de entorno.

Un secret pegado en GitHub puede traer un salto de linea al final (pasa al
copiar desde un editor o desde un gestor de claves). Si va a una URL o a una
cabecera, ese `\\n` viaja como `%0A` y la API responde 401 (visto con
CONGRESS_API_KEY el 2026-10-26: `api_key=...%0A`). Todo lo que se lea del
entorno para mandarlo a un servicio pasa por `leer_clave()`.
"""
import os


def leer_clave(nombre):
    """Valor de la variable de entorno `nombre`, sin espacios ni saltos de linea
    en los extremos. Si no existe (o queda vacia) lanza KeyError, igual que
    `os.environ[nombre]`, para que el modulo falle con el mismo mensaje de siempre."""
    valor = os.environ[nombre].strip()
    if not valor:
        raise KeyError(nombre)
    return valor
