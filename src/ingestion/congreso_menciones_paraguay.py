"""
Extraccion de proyectos de ley y resoluciones del Congreso de EE.UU. que mencionan a Paraguay
GovInfo.gov (busqueda de texto completo) + Congress.gov (datos estructurados)

Fuentes:
    - https://api.govinfo.gov/search - busqueda de texto completo sobre la
      coleccion BILLS (incluye HR, S, HRES, SRES, HJRES, SJRES, HCONRES,
      SCONRES). GovInfo no permite filtrar por pais mencionado en el titulo
      via API, asi que se trae todo lo que matchea "Paraguay" en el texto y
      se filtra por fecha despues.
    - https://api.congress.gov/v3/bill/{congreso}/{tipo}/{numero} - una vez
      identificado cada proyecto (via GovInfo), se pide su info estructurada
      (titulo, fecha de introduccion, ultima accion, camara, area de
      politica, patrocinador) - mas completa y confiable que los metadatos
      crudos de GovInfo.

Que hace: arma un Excel con una fila por proyecto de ley/resolucion distinto
que menciona a Paraguay, introducido entre ANIO_MINIMO y ANIO_MAXIMO, y lo
sube a Drive. A diferencia de la mayoria de los modulos de ingestion, esta
fuente no existe como archivo descargable en ningun lado - se construye acá
a partir de dos APIs. El Excel resultante esta pensado para que lo lea otro
script despues (columnas fijas, un proyecto por fila, sin texto libre en
columnas que deberian ser numericas/fecha).

GovInfo devuelve una fila por cada VERSION publicada de un mismo proyecto
(introducido, reportado, aprobado, etc.) - se deduplica a nivel de proyecto
(congreso + tipo + numero), no de version, porque lo que se quiere contar es
"cuantos proyectos mencionan a Paraguay", no cuantas veces se republico cada
uno.

Cada fila incluye ademas `extracto_mencion_paraguay`: un fragmento real del
texto del proyecto centrado en la primera mencion de "Paraguay", sacado del
mismo documento que GovInfo ya encontro que la contiene (endpoint de
contenido `/packages/{packageId}/htm`, no un snippet inventado). Es para
poder verificar de un vistazo, sin abrir el proyecto entero, que el hit es
real y en que contexto aparece Paraguay (ver el limite de busqueda de texto
completo mas abajo).

Limite importante: es busqueda de texto completo, no un filtro tematico. Un
proyecto puede aparecer solo porque menciona a Paraguay de paso (ej. un
listado de paises de la region en una resolucion sobre Venezuela) y no
porque trate especificamente sobre la relacion bilateral. No asumir que
"aparece en este archivo" equivale a "proyecto sobre Paraguay" sin revisar
el titulo/ultima_accion de cada fila.

Requiere la variable de entorno CONGRESS_API_KEY (gratuita, se genera en
https://api.congress.gov/sign-up/ - la misma key sirve para GovInfo, ambas
APIs pertenecen al mismo sistema de api.data.gov).
"""
import io
import os
import re
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_GOVINFO_SEARCH = "https://api.govinfo.gov/search"
URL_GOVINFO_TEXTO = "https://api.govinfo.gov/packages/{package_id}/htm"
URL_CONGRESS_BILL = "https://api.congress.gov/v3/bill/{congreso}/{tipo}/{numero}"

RADIO_EXTRACTO = 150  # caracteres a cada lado de "Paraguay" en el extracto

# Coleccion BILLS de GovInfo = todo tipo de proyecto/resolucion del Congreso.
QUERY_GOVINFO = "Paraguay AND collection:BILLS"

ANIO_MINIMO = 2015
ANIO_MAXIMO = 2025

# "BILLS-{congreso}{tipo}{numero}{version}", ej. "BILLS-119hres1056ih".
# El orden importa: los codigos largos van primero para que la alternancia
# no matchee "hr" adentro de "hres"/"hconres" (aunque re ya hace backtracking,
# este orden es mas claro de leer).
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

DIMENSION = "2_Actividad_gubernamental_y_diplomatica"
FUENTE = "congreso_menciones_paraguay"
DESCRIPCION = "Proyectos de ley y resoluciones del Congreso de EE.UU. que mencionan a Paraguay, 2015-2025"
URL_FUENTE = "https://www.congress.gov"


def _api_key():
    return os.environ["CONGRESS_API_KEY"]


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

        nuevo_offset = data.get("offsetMark")
        if not resultados or not nuevo_offset or nuevo_offset == offset:
            break
        offset = nuevo_offset

    return hits


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


def _extracto_mencion_paraguay(package_id):
    """Descarga el texto de una version del proyecto que GovInfo ya encontro
    que menciona a Paraguay, y devuelve un extracto real centrado en la
    primera mencion - para poder verificar el hit sin abrir el documento
    entero. "" si por algun motivo no se encuentra (ej. texto reformateado
    entre la busqueda y esta descarga)."""
    resp = requests.get(
        URL_GOVINFO_TEXTO.format(package_id=package_id),
        params={"api_key": _api_key()},
        timeout=30,
    )
    resp.raise_for_status()

    texto = BeautifulSoup(resp.text, "html.parser").get_text(" ", strip=True)
    texto = re.sub(r"\s+", " ", texto).strip()

    match = re.search(r"paraguay", texto, re.IGNORECASE)
    if not match:
        return ""

    inicio = max(match.start() - RADIO_EXTRACTO, 0)
    fin = min(match.end() + RADIO_EXTRACTO, len(texto))
    extracto = texto[inicio:fin].strip()
    return f"{'...' if inicio > 0 else ''}{extracto}{'...' if fin < len(texto) else ''}"


def _enriquecer_proyecto(congreso, tipo, numero):
    """Pide a Congress.gov los datos estructurados de un proyecto puntual."""
    url = URL_CONGRESS_BILL.format(congreso=congreso, tipo=tipo.lower(), numero=numero)
    resp = requests.get(url, params={"api_key": _api_key(), "format": "json"}, timeout=30)
    resp.raise_for_status()
    return resp.json()["bill"]


def _fila_desde_proyecto(congreso, tipo, numero, versiones, bill, extracto):
    sponsors = bill.get("sponsors") or [{}]
    patrocinador = sponsors[0]
    latest = bill.get("latestAction") or {}

    return {
        "congreso": congreso,
        "tipo": tipo,
        "numero": numero,
        "identificador": f"{IDENTIFICADOR_POR_TIPO.get(tipo, tipo)} {numero}",
        "titulo": bill.get("title"),
        "extracto_mencion_paraguay": extracto,
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


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"congreso_menciones_paraguay_{fecha}.xlsx"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    hits = _buscar_proyectos_govinfo()
    proyectos = _proyectos_unicos(hits)
    # Descarta congresos que no pueden superponerse con el rango de anios
    # pedido, para no gastar pedidos a Congress.gov en proyectos viejos.
    candidatos = {k: v for k, v in proyectos.items() if k[0] >= 114}

    filas = []
    errores = []
    for (congreso, tipo, numero), info in sorted(candidatos.items()):
        try:
            bill = _enriquecer_proyecto(congreso, tipo, numero)
        except Exception as exc:  # noqa: BLE001
            errores.append((f"{congreso}-{tipo}-{numero}", repr(exc)))
            continue

        try:
            extracto = _extracto_mencion_paraguay(info["package_id_ref"])
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] no se pudo sacar extracto de {congreso}-{tipo}-{numero}: {exc!r}")
            extracto = ""

        fila = _fila_desde_proyecto(congreso, tipo, numero, info["versiones"], bill, extracto)
        fecha_intro = fila["fecha_introduccion"] or ""
        if fecha_intro[:4].isdigit():
            anio_intro = int(fecha_intro[:4])
            if not (ANIO_MINIMO <= anio_intro <= ANIO_MAXIMO):
                continue
        filas.append(fila)
        time.sleep(0.2)  # pausa breve para no saturar la API

    if not filas and not errores:
        print(f"[{FUENTE}] no se encontro ningun proyecto en el rango {ANIO_MINIMO}-{ANIO_MAXIMO}.")
        return

    df = pd.DataFrame(filas).sort_values(["fecha_introduccion", "congreso"], na_position="last")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(filas)} proyectos, {len(errores)} errores."
    )
    for identificador, err in errores:
        print(f"    [!] {identificador}: {err}")


if __name__ == "__main__":
    run()
