"""Lectura de claves desde variables de entorno, y ocultamiento de claves en lo que se imprime o se registra.

Lectura: un secret pegado en GitHub puede traer un salto de linea al final (pasa
al copiar desde un editor o desde un gestor de claves). Si va a una URL o a una
cabecera, ese `\\n` viaja como `%0A` y la API responde 401 (visto con
CONGRESS_API_KEY el 2026-10-26: `api_key=...%0A`). Todo lo que se lea del
entorno para mandarlo a un servicio pasa por `leer_clave()`.

Ocultamiento: `requests` pone la URL completa en el mensaje de un HTTPError, y
las claves de Congreso (`api_key`) y BEA (`UserID`) viajan en esa URL. El
2026-10-26 la clave de Congreso quedo en texto claro en la pestana pipeline_log
del Sheet de auditoria. `ocultar_claves()` la tapa antes de que el texto llegue
al Sheet (src/sheets.py) o a la consola (`instalar_filtro_en_consola()`).
"""
import os
import re
import sys
from urllib.parse import quote

MARCA = "***"

# Secrets del proyecto cuyo valor exacto se tapa donde aparezca (ademas de los
# parametros de URL de abajo). Se ignoran los muy cortos para no tapar texto comun.
NOMBRES_SECRETOS = ("CONGRESS_API_KEY", "BEA_API_KEY", "SHEET_ID")
LARGO_MINIMO_SECRETO = 8

PARAMETROS_SECRETOS = ("api_key", "apikey", "userid", "key", "token", "access_token", "client_secret")
_PARAMETRO = re.compile(
    r"(?i)\b(" + "|".join(PARAMETROS_SECRETOS) + r")=([^&\s'\")\]\\]+)"
)
_BEARER = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+")
_CLAVE_PRIVADA = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)


def leer_clave(nombre):
    """Valor de la variable de entorno `nombre`, sin espacios ni saltos de linea
    en los extremos. Si no existe (o queda vacia) lanza KeyError, igual que
    `os.environ[nombre]`, para que el modulo falle con el mismo mensaje de siempre."""
    valor = os.environ[nombre].strip()
    if not valor:
        raise KeyError(nombre)
    return valor


def _valores_secretos():
    valores = []
    for nombre in NOMBRES_SECRETOS:
        valor = os.environ.get(nombre, "").strip()
        if len(valor) >= LARGO_MINIMO_SECRETO:
            valores += [valor, quote(valor, safe="")]
    return sorted(set(valores), key=len, reverse=True)  # los largos primero


def ocultar_claves(texto):
    """`texto` con las claves reemplazadas por `***`: valores de parametros de URL
    (`api_key=`, `UserID=`, `token=`...), encabezados `Bearer`, claves privadas
    PEM y el valor exacto de cada secret de NOMBRES_SECRETOS."""
    texto = str(texto)
    texto = _PARAMETRO.sub(lambda m: f"{m.group(1)}={MARCA}", texto)
    texto = _BEARER.sub(lambda m: f"{m.group(1)}{MARCA}", texto)
    texto = _CLAVE_PRIVADA.sub(MARCA, texto)
    for valor in _valores_secretos():
        texto = texto.replace(valor, MARCA)
    return texto


class _FiltroDeClaves:
    """Envuelve stdout/stderr: todo lo que se escribe pasa por ocultar_claves()."""

    def __init__(self, destino):
        self._destino = destino

    def write(self, texto):
        self._destino.write(ocultar_claves(texto))
        return len(texto)

    def __getattr__(self, nombre):  # flush, reconfigure, encoding, isatty...
        return getattr(self._destino, nombre)


def instalar_filtro_en_consola():
    """Hace que nada de lo que imprima el pipeline (ni los tracebacks) lleve una
    clave en claro. Seguro de llamar mas de una vez."""
    for nombre in ("stdout", "stderr"):
        flujo = getattr(sys, nombre)
        if not isinstance(flujo, _FiltroDeClaves):
            setattr(sys, nombre, _FiltroDeClaves(flujo))
