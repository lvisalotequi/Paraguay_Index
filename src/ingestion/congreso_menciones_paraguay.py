#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 02/09/2026                                                #
# NOMBRE: congreso_menciones_paraguay                                          #
# DETALLE: arma un Excel con una fila por proyecto de ley o resolucion del     #
#   Congreso de EE.UU. que menciona a Paraguay (introducido desde 2015),       #
#   cruzando GovInfo (busqueda de texto completo) y Congress.gov (datos        #
#   estructurados). Cuenta cuantas veces aparece Paraguay en cada texto. NO    #
#   juzga el tono ni decide cuales son centrales: umbrales y variables son de  #
#   src/processing/.                                                           #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/actividad_gubernamental_y_diplomatica.py                    #
# SALIDA: un Excel por dia (congreso_menciones_paraguay_{fecha}.xlsx) en       #
#   01_crudas/<dimension>_crudas/congreso_menciones_paraguay/                  #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import re
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo
from src.entorno import leer_clave



# Parametros -------------------------------------------------------------------

# Esta fuente no existe como archivo descargable en ningun lado: se CONSTRUYE aca
# combinando dos APIs.
#   - GovInfo (api.govinfo.gov/search): busqueda de texto completo sobre la
#     coleccion BILLS (HR, S, HRES, SRES, HJRES, SJRES, HCONRES, SCONRES). No
#     permite filtrar por pais mencionado en el titulo, asi que se trae todo lo que
#     matchea "Paraguay" en el texto y se filtra por fecha despues.
#   - Congress.gov (api.congress.gov/v3/bill/{congreso}/{tipo}/{numero}): una vez
#     identificado cada proyecto via GovInfo, se pide su info estructurada (titulo,
#     fecha de introduccion, ultima accion, camara, area de politica, patrocinador),
#     mas completa y confiable que los metadatos crudos de GovInfo.
# El Excel resultante tiene una fila por proyecto, con columnas fijas y sin texto
# libre en columnas que deberian ser numericas o de fecha, para que lo lea
# src/processing/.
URL_GOVINFO_SEARCH = "https://api.govinfo.gov/search"
URL_GOVINFO_TEXTO  = "https://api.govinfo.gov/packages/{package_id}/htm"
URL_CONGRESS_BILL  = "https://api.congress.gov/v3/bill/{congreso}/{tipo}/{numero}"

# POR QUE CONTAR MENCIONES y no solo detectar si aparece (2026-09-10, a pedido del
# usuario; antes se guardaba un extracto de la PRIMERA mencion): cada fila lleva
# cantidad_menciones_paraguay (cuantas veces aparece "Paraguay" en el texto completo)
# y extractos_menciones_paraguay (un fragmento real de +-RADIO_EXTRACTO caracteres
# alrededor de CADA mencion, unidos por SEPARADOR_EXTRACTOS), para poder verificar
# cada mencion contada sin abrir el documento entero. Salen del mismo documento
# que GovInfo ya encontro que contiene "Paraguay" (endpoint /packages/{packageId}/htm),
# no son snippets inventados.
#
# Es un proxy de que tan central es Paraguay en el proyecto, no de si la mencion es
# positiva o negativa: la misma logica de la "saliency theory" del Comparative
# Manifestos Project y del "expressed agenda model" de Grimmer (2013, "Text as
# Data"), que miden atencion a un tema por frecuencia de mencion. Piloto real
# (2026-09-10, 3 anios: 2020, 2021 y 2024): los proyectos con "Paraguay" en el
# titulo promediaron 12.0 menciones contra 1.14 de los que lo mencionan de paso,
# una separacion clara.
#
# LIMITE EXPLICITO, ya reconocido en la literatura: la frecuencia no mide
# intensidad (una oracion muy fuerte puede eclipsar a una docena de menciones
# tibias). Contar dice cuanto se habla de Paraguay, no si el tono es favorable o
# critico. Clasificar el tono de cada mencion exigiria NLP o un LLM, lo cual rompe
# el principio del proyecto de que todo corra de forma deterministica y sin depender
# de un servicio externo: se decidio explicitamente no hacerlo.
RADIO_EXTRACTO      = 150      # caracteres a cada lado de "Paraguay" en cada extracto
SEPARADOR_EXTRACTOS = " ||| "  # entre extractos de distintas menciones

# LIMITE IMPORTANTE: es busqueda de texto completo, no un filtro tematico. Un
# proyecto puede aparecer solo porque menciona a Paraguay de paso (por ejemplo, un
# listado de paises de la region en una resolucion sobre Venezuela) y no porque
# trate de la relacion bilateral. Por eso el conteo de menciones: no asumir que
# "aparece en este archivo" equivale a "proyecto sobre Paraguay" sin revisar
# cantidad_menciones_paraguay, titulo y ultima_accion de cada fila.
# La coleccion BILLS de GovInfo es todo tipo de proyecto o resolucion del Congreso.
QUERY_GOVINFO = "Paraguay AND collection:BILLS"

ANIO_MINIMO           = 2015
ANIO_MAXIMO           = datetime.now(timezone.utc).year  # el anio en curso: no se sube a mano
INTENTOS_POR_PROYECTO = 3

# "BILLS-{congreso}{tipo}{numero}{version}", por ejemplo "BILLS-119hres1056ih".
# El orden importa: los codigos largos van primero para que la alternancia no
# matchee "hr" adentro de "hres" o "hconres" (aunque re ya hace backtracking, este
# orden es mas claro de leer).
PATRON_PACKAGE_ID = re.compile(
    r"^BILLS-(\d+)(hconres|sconres|hjres|sjres|hres|sres|hr|s)(\d+)([a-z]+)$",
    re.IGNORECASE,
)

IDENTIFICADOR_POR_TIPO = {
    "HR": "H.R.",
    "S": "S.",
    "HRES": "H.RES.",
    "SRES": "S.RES.",
    "HJRES": "H.J.RES.",
    "SJRES": "S.J.RES.",
    "HCONRES": "H.CON.RES.",
    "SCONRES": "S.CON.RES.",
}

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente. Van al final porque DESCRIPCION
# usa ANIO_MINIMO y ANIO_MAXIMO.
DIMENSION   = "2_Actividad_gubernamental_y_diplomatica"
FUENTE      = "congreso_menciones_paraguay"
DESCRIPCION = (
    f"Proyectos de ley y resoluciones del Congreso de EE.UU. que mencionan a Paraguay, "
    f"{ANIO_MINIMO}-{ANIO_MAXIMO}"
)
URL_FUENTE  = "https://www.congress.gov"



# Funciones auxiliares ---------------------------------------------------------


# Requiere CONGRESS_API_KEY (gratuita, se genera en https://api.congress.gov/sign-up/).
# La misma clave sirve para GovInfo: ambas APIs pertenecen al mismo sistema de
# api.data.gov. leer_clave quita el salto de linea que a veces trae el secret.
def _api_key():
    return leer_clave("CONGRESS_API_KEY")


def _buscar_proyectos_govinfo():
    """Pagina la busqueda de texto completo en GovInfo. Devuelve la lista cruda de hits."""
    hits = []
    offset = "*"
    while True:
        body = {"query": QUERY_GOVINFO, "pageSize": 100, "offsetMark": offset}
        resp = requests.post(
            URL_GOVINFO_SEARCH, json=body, params={"api_key": _api_key()}, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        resultados = data.get("results", [])
        hits.extend(resultados)

        # corta cuando no hay mas resultados o el cursor deja de avanzar
        nuevo_offset = data.get("offsetMark")
        if not resultados or not nuevo_offset or nuevo_offset == offset:
            break
        offset = nuevo_offset

    return hits


# GovInfo devuelve una fila por cada VERSION publicada de un mismo proyecto
# (introducido, reportado, aprobado, etc.). Se deduplica a nivel de proyecto
# (congreso + tipo + numero) y no de version, porque lo que se quiere contar es
# "cuantos proyectos mencionan a Paraguay", no cuantas veces se republico cada uno.
def _proyectos_unicos(hits):
    """Deduplica los hits de GovInfo a nivel de proyecto (congreso+tipo+numero).
    Se queda tambien con el packageId del primer hit de cada proyecto -
    alcanza para el extracto: GovInfo ya confirmo que ESA version contiene
    "Paraguay", no hace falta pedir el texto de las demas versiones."""
    proyectos = {}
    for hit in hits:
        match = PATRON_PACKAGE_ID.match(hit.get("packageId", ""))
        if not match:
            continue
        congreso, tipo, numero, version = match.groups()
        clave = (int(congreso), tipo.upper(), numero)
        info = proyectos.setdefault(clave, {"versiones": [], "package_id_ref": hit["packageId"]})
        info["versiones"].append(version)
    return proyectos


def _menciones_paraguay(package_id):
    """Descarga el texto de una version del proyecto que GovInfo ya encontro
    que menciona a Paraguay, y devuelve (cantidad, extractos): cantidad es
    el total de menciones de "Paraguay" en el texto completo; extractos es
    un fragmento real centrado en CADA mencion (mismo radio que antes),
    unidos por SEPARADOR_EXTRACTOS - para poder verificar cada una sin
    abrir el documento entero. (0, "") si por algun motivo no se encuentra
    ninguna (ej. texto reformateado entre la busqueda y esta descarga)."""
    resp = requests.get(
        URL_GOVINFO_TEXTO.format(package_id=package_id),
        params={"api_key": _api_key()},
        timeout=30,
    )
    resp.raise_for_status()

    texto = BeautifulSoup(resp.text, "html.parser").get_text(" ", strip=True)
    texto = re.sub(r"\s+", " ", texto).strip()

    matches = list(re.finditer(r"paraguay", texto, re.IGNORECASE))
    if not matches:
        return 0, ""

    # un fragmento por mencion, con "..." donde el texto sigue
    extractos = []
    for match in matches:
        inicio = max(match.start() - RADIO_EXTRACTO, 0)
        fin = min(match.end() + RADIO_EXTRACTO, len(texto))
        extracto = texto[inicio:fin].strip()
        extractos.append(f"{'...' if inicio > 0 else ''}{extracto}{'...' if fin < len(texto) else ''}")

    return len(matches), SEPARADOR_EXTRACTOS.join(extractos)


def _enriquecer_proyecto(congreso, tipo, numero):
    """Pide a Congress.gov los datos estructurados de un proyecto puntual."""
    url = URL_CONGRESS_BILL.format(congreso=congreso, tipo=tipo.lower(), numero=numero)
    resp = requests.get(url, params={"api_key": _api_key(), "format": "json"}, timeout=30)
    resp.raise_for_status()
    return resp.json()["bill"]


def _fila_desde_proyecto(congreso, tipo, numero, versiones, bill, cantidad_menciones, extractos):
    sponsors = bill.get("sponsors") or [{}]
    patrocinador = sponsors[0]
    latest = bill.get("latestAction") or {}

    return {
        "congreso": congreso,
        "tipo": tipo,
        "numero": numero,
        "identificador": f"{IDENTIFICADOR_POR_TIPO.get(tipo, tipo)} {numero}",
        "titulo": bill.get("title"),
        "cantidad_menciones_paraguay": cantidad_menciones,
        "extractos_menciones_paraguay": extractos,
        "fecha_introduccion": bill.get("introducedDate"),
        "fecha_ultima_accion": latest.get("actionDate"),
        "ultima_accion": latest.get("text"),
        "camara_origen": bill.get("originChamber"),
        "area_politica": (bill.get("policyArea") or {}).get("name"),
        "patrocinador": patrocinador.get("fullName"),
        "partido_patrocinador": patrocinador.get("party"),
        "estado_patrocinador": patrocinador.get("state"),
        "url_congress_gov": bill.get("legislationUrl"),
        "versiones_publicadas": len(set(versiones)),
    }


def _con_reintentos(funcion, *args):
    """Llama funcion(*args) hasta INTENTOS_POR_PROYECTO veces antes de rendirse
    (un fallo transitorio de la API no debe dejar un proyecto fuera del
    archivo ni contarlo como 0 menciones)."""
    for intento in range(1, INTENTOS_POR_PROYECTO + 1):
        try:
            return funcion(*args)
        except Exception:  # noqa: BLE001
            if intento == INTENTOS_POR_PROYECTO:
                raise
            time.sleep(2 * intento)



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre del archivo del dia

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"congreso_menciones_paraguay_{fecha}.xlsx"

    # 2. idempotente por dia: si ya se corrio hoy, no se vuelve a pedir

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    # 3. busca en GovInfo y deduplica por proyecto

    hits = _buscar_proyectos_govinfo()
    proyectos = _proyectos_unicos(hits)

    # descarta congresos que no pueden superponerse con el rango de anios pedido,
    # para no gastar pedidos a Congress.gov en proyectos viejos (114 = 2015-2016)
    candidatos = {k: v for k, v in proyectos.items() if k[0] >= 114}

    # 4. enriquece cada proyecto con Congress.gov y cuenta sus menciones

    filas = []
    errores = []
    for (congreso, tipo, numero), info in sorted(candidatos.items()):
        try:
            bill = _con_reintentos(_enriquecer_proyecto, congreso, tipo, numero)
            cantidad_menciones, extractos = _con_reintentos(_menciones_paraguay, info["package_id_ref"])
        except Exception as exc:  # noqa: BLE001
            errores.append((f"{congreso}-{tipo}-{numero}", repr(exc)))
            continue

        # solo entran los proyectos introducidos entre ANIO_MINIMO y ANIO_MAXIMO
        fila = _fila_desde_proyecto(
            congreso,
            tipo,
            numero,
            info["versiones"],
            bill,
            cantidad_menciones,
            extractos,
        )
        fecha_intro = fila["fecha_introduccion"] or ""
        if fecha_intro[:4].isdigit():
            anio_intro = int(fecha_intro[:4])
            if not (ANIO_MINIMO <= anio_intro <= ANIO_MAXIMO):
                continue
        filas.append(fila)
        time.sleep(0.2)  # pausa breve para no saturar la API

    # 5. validacion de contrato: un archivo con proyectos faltantes (o con menciones
    # contadas como 0) pasaria a ser "el mas reciente" que lee processing. Mejor no
    # subir nada y dejar el ultimo archivo completo.

    if errores:
        for identificador, err in errores:
            print(f"    [!] {identificador}: {err}")
        raise RuntimeError(
            f"{len(errores)} proyectos fallaron tras {INTENTOS_POR_PROYECTO} intentos; "
            "no se sube un archivo parcial"
        )

    if not filas:
        print(f"[{FUENTE}] no se encontro ningun proyecto en el rango {ANIO_MINIMO}-{ANIO_MAXIMO}.")
        return

    # 6. arma el Excel (una fila por proyecto) y lo sube

    df = pd.DataFrame(filas).sort_values(["fecha_introduccion", "congreso"], na_position="last")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    # 7. validacion: cuantos proyectos se subieron

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(filas)} proyectos."
    )


if __name__ == "__main__":
    run()
