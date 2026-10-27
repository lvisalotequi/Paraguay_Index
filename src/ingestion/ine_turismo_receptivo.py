#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 29/09/2026                                                #
# NOMBRE: ine_turismo_receptivo                                                #
# DETALLE: descarga los Cuadros 2.4.2 del Anuario del INE (turismo receptivo   #
#   por mes y nacionalidad) y sube un Excel con la fila de Estados Unidos de   #
#   cada anio: historico fijo de 9 anios, re-verificado en cada corrida, mas   #
#   los anios nuevos que halle. NO sube un archivo parcial ni estima 2016: eso #
#   es de src/processing/.                                                     #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_economico_privado.py                             #
# SALIDA: un Excel por dia (ine_turismo_receptivo_{fecha}.xlsx) en             #
#   01_crudas/<dimension>_crudas/ine_turismo_receptivo/                        #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import time
from datetime import datetime, timezone

import pandas as pd
from curl_cffi import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo



# Parametros -------------------------------------------------------------------

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "3_Compromiso_economico_privado"
FUENTE      = "ine_turismo_receptivo"
DESCRIPCION = "Turistas de EE.UU. que ingresaron a Paraguay por mes, según nacionalidad (INE)"
URL_FUENTE  = "https://www.ine.gov.py/publicacion/16/anuario"

# La fuente es el Cuadro 2.4.2 "Turismo receptivo por mes, segun nacionalidad" del
# Anuario Estadistico del INE (un cuadro por edicion anual). No es la misma
# publicacion que el "Compendio Estadistico", que solo tiene desglose por CONTINENTE,
# nunca por pais. Credito de la fuente original, tal como aparece en el cuadro:
# "Direccion General de Migraciones y Secretaria Nacional de Turismo" (SENATUR).
# Se sube la fila de Estados Unidos, filtrada antes de subir (mismo criterio que
# exim_autorizaciones.py: filtrar en el origen no es "tratamiento").
IMPERSONATE      = "chrome"
TIMEOUT_DESCARGA = 300  # segundos por intento: el PDF de 2015 pesa unos 11 MB y a veces baja lento
INTENTOS         = 3
ESPERA_REINTENTO = 10   # segundos, se multiplica por el numero de intento
MESES            = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]

# POR QUE UN HISTORICO FIJO en vez de descubrir los links en cada corrida: el
# buscador del sitio del INE (ine.gov.py) es JavaScript puro y no devuelve resultados
# a un requests o curl_cffi normal (confirmado 2026-09-28; el mismo tipo de limite
# que state_gov_tias_paraguay.py con el buscador de DuckDuckGo). Los 9 links de abajo
# se encontraron navegando el sitio a mano una sola vez. Cada corrida los vuelve a
# pedir para confirmar que el archivo siga ahi y que la fila "Estados Unidos" siga
# presente (mismo patron que ustr_consejo_comercio_inversion.py y
# state_gov_tias_paraguay.py). Verificado a mano el 2026-09-28.
#
# FALTA 2016 (investigado a fondo el 2026-09-28; no es un link que falte encontrar):
# se revisaron el Anuario Estadistico 2016 completo (311 paginas, solo tiene el
# cuadro por continente, no por nacionalidad), el Compendio Estadistico 2017 completo
# (82 paginas; esa serie nunca tuvo desglose por pais en ninguna edicion), el sitio de
# Migraciones (sin datos historicos, solo un dashboard en vivo desde 2026) y el archivo
# historico del Observatorio de Turismo de SENATUR en Wayback Machine (que si tiene
# una tabla equivalente para 2010-2015 pero se dejo de actualizar despues de 2015).
# SENATUR firmo un convenio con la entonces DGEEC (hoy INE) recien el 2017-02-08 "para
# fortalecer su sistema de estadisticas turisticas": encaja con que 2016 haya sido
# justo el anio de transicion entre el sistema viejo de SENATUR (que llego a cubrir
# 2015) y el nuevo, conjunto con el INE (que arranca en 2017). El hueco se resuelve en
# src/processing/compromiso_economico_privado.py con un promedio aritmetico simple
# mes a mes de 2015 y 2017 (ver ese modulo para el detalle y el piloto que valido el
# metodo).
#
# PARA AGREGAR UN ANIO NUEVO (2025 en adelante, cuando el INE lo publique): buscar
# "turismo" en el buscador del propio sitio (ine.gov.py, la caja de busqueda arriba a
# la derecha; no funciona por requests, hay que hacerlo a mano con un navegador),
# ubicar el link del "Cuadro 2.4.2. Turismo receptivo por mes, segun nacionalidad"
# del anio buscado y agregar la URL a AÑOS_HISTORICOS.
AÑOS_HISTORICOS = {
    2015: "https://www.ine.gov.py/Publicaciones/Biblioteca/anuario2015/Anuario%20Estadistico%202015.pdf",
    2017: "https://www.ine.gov.py/assets/documento/0720bCuadro-2.4.2_2017.xlsx",
    2018: "https://www.ine.gov.py/assets/documento/1bda9Cuadro_2.4.2.xlsx",
    2019: "https://www.ine.gov.py/assets/documento/4edbc2.4.2_AEP_2019.xlsx",
    2020: "https://www.ine.gov.py/assets/documento/8870f2.4.2_AEP2020.xlsx",
    2021: "https://www.ine.gov.py/assets/documento/0/2.4.2_AEP2021.xlsx",
    2022: "https://www.ine.gov.py/assets/documento/61/2.4.2_AE2022.xlsx",
    2023: "https://www.ine.gov.py/assets/documento/61/2.4.2_AE2023..xlsx",
    2024: "https://www.ine.gov.py/assets/documento/0/2.4.2_AE2024.xlsx",
}



# Funciones auxiliares ---------------------------------------------------------


def _descargar(url, intentos=INTENTOS, timeout=TIMEOUT_DESCARGA):
    """Bytes de `url`, completos o con error: nunca devuelve un archivo cortado.

    El Anuario 2015 (PDF de ~11 MB) llega lento desde los runners de Actions y
    con 60 s se cortaba a los 3-6 MB (tres corridas seguidas, 2026-10-26). Se
    reintenta ante error de red, 429 o 5xx; un 4xx es definitivo y no se
    reintenta. Si el servidor informa Content-Length y llega menos, tambien
    cuenta como fallo (un cuerpo cortado no debe llegar al parser)."""
    ultimo = None
    for intento in range(1, intentos + 1):
        try:
            resp = requests.get(url, impersonate=IMPERSONATE, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise RuntimeError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            esperado = resp.headers.get("content-length")
            if esperado and esperado.isdigit() and len(resp.content) < int(esperado):
                raise RuntimeError(f"descarga incompleta: {len(resp.content)} de {esperado} bytes")
            return resp.content
        except Exception as exc:  # noqa: BLE001
            ultimo = exc

            # un 4xx (salvo 429) es definitivo: no se reintenta
            if (
                getattr(exc, "response", None) is not None
                and 400 <= exc.response.status_code < 500
                and exc.response.status_code != 429
            ):
                raise
            if intento < intentos:
                print(
                    f"    [!] intento {intento}/{intentos} de {url.rsplit('/', 1)[-1]}: {exc!r}; "
                    f"reintento en {ESPERA_REINTENTO * intento} s"
                )
                time.sleep(ESPERA_REINTENTO * intento)
    raise ultimo


def _fila_eeuu_desde_xlsx(contenido):
    """Extrae la fila de Estados Unidos (total + 12 meses) de un Cuadro
    2.4.2 en formato xlsx suelto (2017 en adelante)."""
    df = pd.read_excel(io.BytesIO(contenido), header=None)
    col_nacionalidad = df.iloc[:, 1].astype(str)
    fila = df[col_nacionalidad.str.contains("Estados Unidos", na=False)]
    if fila.empty:
        raise RuntimeError("no se encontro la fila 'Estados Unidos' en el archivo")
    total = fila.iloc[0, 2]
    meses = pd.to_numeric(fila.iloc[0, 3:15], errors="coerce").fillna(0).astype(int).tolist()
    return total, meses


def _fila_eeuu_desde_pdf_2015(contenido):
    """2015 no tiene un xlsx suelto - el Cuadro 2.4.2 solo esta adentro
    del PDF completo del Anuario Estadistico 2015 (ver docstring del
    modulo). Se busca la pagina con 'CUADRO 2.4.2' y se parsea la linea
    de Estados Unidos con el mismo formato de columnas."""
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(contenido))
    for pagina in lector.pages:
        texto = pagina.extract_text() or ""
        if "CUADRO 2.4.2" in texto.upper() and "NACIONALIDAD" in texto.upper():
            for linea in texto.split("\n"):
                if linea.strip().startswith("Estados Unidos"):
                    partes = linea.replace(".", "").split()
                    numeros = [int(p) for p in partes if p.replace(",", "").isdigit()]
                    if len(numeros) < 13:
                        raise RuntimeError(f"fila de Estados Unidos con formato inesperado: {linea!r}")
                    return numeros[0], numeros[1:13]
    raise RuntimeError("no se encontro el Cuadro 2.4.2 con la fila de Estados Unidos en el PDF de 2015")


# DESCUBRIMIENTO AUTOMATICO DE ANIOS NUEVOS (2026-10, rama de ajuste): el buscador del
# INE sigue siendo inutil para requests, pero los archivos del Anuario 2017 en adelante
# siguen un patron de nombre estable (assets/documento/{0|61}/2.4.2_AE{anio}.xlsx,
# verificado con 2022-2024; 2023 lleva un punto de mas). En cada corrida, para cada
# anio posterior al ultimo de AÑOS_HISTORICOS y anterior al anio en curso, se prueban
# estas URL candidatas; la que responda con un Excel valido (con la fila "Estados
# Unidos") se suma a esa corrida. Si el INE cambia el patron, no se encuentra nada y
# el anio queda sin dato (el aviso lo dice). Cuando se confirme una URL nueva conviene
# agregarla a AÑOS_HISTORICOS.
PLANTILLAS_URL_NUEVOS = (
    "https://www.ine.gov.py/assets/documento/0/2.4.2_AE{anio}.xlsx",
    "https://www.ine.gov.py/assets/documento/61/2.4.2_AE{anio}.xlsx",
    "https://www.ine.gov.py/assets/documento/0/2.4.2_AE{anio}..xlsx",
    "https://www.ine.gov.py/assets/documento/61/2.4.2_AE{anio}..xlsx",
)


def _descubrir_anios_nuevos(anio_actual):
    """{anio: (url, total, meses)} de los años posteriores al historico fijo
    cuyo Cuadro 2.4.2 ya este publicado bajo el patron de nombre del INE."""
    encontrados = {}
    for anio in range(max(AÑOS_HISTORICOS) + 1, anio_actual):
        for plantilla in PLANTILLAS_URL_NUEVOS:
            url = plantilla.format(anio=anio)
            try:
                resp = requests.get(url, impersonate=IMPERSONATE, timeout=120)
                if resp.status_code != 200 or "html" in (resp.headers.get("content-type") or "").lower():
                    continue
                total, meses = _fila_eeuu_desde_xlsx(resp.content)
            except Exception:  # noqa: BLE001
                continue
            encontrados[anio] = (url, total, meses)
            break
    return encontrados



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre del archivo del dia

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"ine_turismo_receptivo_{fecha_hoy}.xlsx"

    # 2. idempotente por dia: si ya se corrio hoy, no se vuelve a pedir

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    # 3. vuelve a pedir cada anio del historico y extrae su fila de EE.UU.

    filas = []
    errores = []
    for anio, url in sorted(AÑOS_HISTORICOS.items()):
        try:
            contenido = _descargar(url)
            if anio == 2015:
                total, meses = _fila_eeuu_desde_pdf_2015(contenido)
            else:
                total, meses = _fila_eeuu_desde_xlsx(contenido)
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] {anio}: {exc!r}")
            errores.append(anio)
            continue

        fila = {"anio": anio, "total": total}
        fila.update(dict(zip(MESES, meses)))
        filas.append(fila)

    # 4. validacion de contrato: si un anio no se pudo verificar, NO se sube un archivo
    # parcial (processing toma el ultimo y se perderia ese anio)

    if errores:
        raise RuntimeError(f"no se pudo verificar {errores} del historico: no se sube un archivo parcial")

    # 5. suma los anios nuevos que el INE ya haya publicado bajo el patron conocido

    nuevos = _descubrir_anios_nuevos(datetime.now(timezone.utc).year)
    for anio, (url, total, meses) in sorted(nuevos.items()):
        print(f"[{FUENTE}] año nuevo descubierto: {anio} ({url}). Conviene agregarlo a AÑOS_HISTORICOS.")
        fila = {"anio": anio, "total": total}
        fila.update(dict(zip(MESES, meses)))
        filas.append(fila)

    # 6. arma el Excel (una fila por anio) y lo sube

    df = pd.DataFrame(filas).sort_values("anio")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    # 7. validacion: cuantos anios del historico se verificaron y cuantos se descubrieron

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(AÑOS_HISTORICOS)} años del historico verificados + {len(nuevos)} descubiertos, "
        f"años: {sorted(df['anio'].tolist())}."
    )


if __name__ == "__main__":
    run()
