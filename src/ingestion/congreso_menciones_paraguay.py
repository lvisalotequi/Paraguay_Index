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

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_GOVINFO_SEARCH = "https://api.govinfo.gov/search"
URL_CONGRESS_BILL = "https://api.congress.gov/v3/bill/{congreso}/{tipo}/{numero}"

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

DIMENSION = "2.Actividad_gubernamental_y_diplomática"
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
    """Deduplica los hits de GovInfo a nivel de proyecto (congreso+tipo+numero)."""
    proyectos = {}
    for hit in hits:
        match = PATRON_PACKAGE_ID.match(hit.get("packageId", ""))
        if not match:
            continue
        congreso, tipo, numero, version = match.groups()
        clave = (int(congreso), tipo.upper(), numero)
        proyectos.setdefault(clave, []).append(version)
    return proyectos


def _enriquecer_proyecto(congreso, tipo, numero):
    """Pide a Congress.gov los datos estructurados de un proyecto puntual."""
    url = URL_CONGRESS_BILL.format(congreso=congreso, tipo=tipo.lower(), numero=numero)
    resp = requests.get(url, params={"api_key": _api_key(), "format": "json"}, timeout=30)
    resp.raise_for_status()
    return resp.json()["bill"]


def _fila_desde_proyecto(congreso, tipo, numero, versiones, bill):
    sponsors = bill.get("sponsors") or [{}]
    patrocinador = sponsors[0]
    latest = bill.get("latestAction") or {}

    return {
        "congreso": congreso,
        "tipo": tipo,
        "numero": numero,
        "identificador": f"{IDENTIFICADOR_POR_TIPO.get(tipo, tipo)} {numero}",
        "titulo": bill.get("title"),
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
    for (congreso, tipo, numero), versiones in sorted(candidatos.items()):
        try:
            bill = _enriquecer_proyecto(congreso, tipo, numero)
        except Exception as exc:  # noqa: BLE001
            errores.append((f"{congreso}-{tipo}-{numero}", repr(exc)))
            continue

        fila = _fila_desde_proyecto(congreso, tipo, numero, versiones, bill)
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
