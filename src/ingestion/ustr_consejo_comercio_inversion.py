"""
Extraccion de hitos del Consejo de Comercio e Inversion (TIFA/TIC) entre Paraguay y EE.UU.
Office of the U.S. Trade Representative (USTR)

Fuente: comunicados de prensa de ustr.gov. El buscador propio del sitio
(ustr.gov/search) no funciona - devuelve cero resultados para cualquier
termino, incluso "Paraguay" solo (confirmado 2026-09-02, sin llamada a
ninguna API detras). No hay forma de filtrar por texto en el sitio.

Que hace: combina dos partes.

1. Un historico FIJO (EVENTOS_HISTORICOS) con los 5 hitos relevantes
   encontrados entre 2015 y 2024, verificados a mano revisando TODO el
   archivo de comunicados de USTR mes por mes (2026-09-02). Ese archivo usa
   una estructura de URL distinta segun el rango de anios (varios
   rediseños del sitio) - escanearlo completo de nuevo cada 3 meses seria
   muy costoso para un periodo que ya esta cerrado y no va a cambiar.
2. Una revision liviana del sitio VIVO (no archivado) desde ANIO_DESDE_VIVO
   en adelante, que si se re-corre en cada ejecucion: recorre los listados
   mensuales de ustr.gov/.../press-releases/{anio}/{mes} (estructura estable
   del sitio actual), busca titulos que mencionen "Paraguay" junto con
   "Trade and Investment" (cubre TIFA y "Trade and Investment Council"), y
   para cada match entra a la pagina del comunicado para confirmar la fecha
   exacta. Asi que futuras reuniones del Consejo se agregan solas.

Sube un Excel (una fila por evento) a Drive. Es idempotente por dia.

Nota sobre el "tipo" de evento: de los 5 hitos del historico, solo 3 son
literalmente "reuniones del Consejo" (2022, 2023, 2024 - primera, segunda y
tercera reunion). Los otros 2 son hitos previos: el MOU de 2015 y la firma
del TIFA en 2017 que crea el marco. La columna "tipo" permite filtrar segun
que definicion de "reunion formal" se quiera usar.
"""
import io
import re
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_BASE = "https://ustr.gov"

DIMENSION = "2.Actividad_gubernamental_y_diplomática"
FUENTE = "ustr_consejo_comercio_inversion"
DESCRIPCION = "Reuniones e hitos del Consejo de Comercio e Inversión (TIFA/TIC) entre Paraguay y EE.UU."
URL_FUENTE = "https://ustr.gov/countries-regions/western-hemisphere/paraguay"

# Verificado a mano revisando el archivo completo de USTR (2015-2024), mes a
# mes, el 2026-09-02. No volver a escanear este rango cerrado.
EVENTOS_HISTORICOS = [
    {
        "fecha": "2015-06-18",
        "tipo": "Memorando de entendimiento",
        "titulo": "The United States Signs Memorandum of Understanding on Intellectual "
        "Property Rights with the Government of Paraguay",
        "url": f"{URL_BASE}/about-us/policy-offices/press-office/press-releases/2015/june/united-states-signs-memorandum",
    },
    {
        "fecha": "2017-01-13",
        "tipo": "Firma del TIFA",
        "titulo": "United States and Paraguay Sign Trade and Investment Framework Agreement",
        "url": f"{URL_BASE}/about-us/policy-offices/press-office/press-releases/archives/2017/january/united-states-and-paraguay",
    },
    {
        "fecha": "2022-09-16",
        "tipo": "Reunion del Consejo TIC",
        "titulo": "United States and Paraguay Convene First Trade and Investment Council",
        "url": f"{URL_BASE}/about-us/policy-offices/press-office/press-releases/2022/september/united-states-and-paraguay-convene-first-trade-and-investment-council",
    },
    {
        "fecha": "2023-09-29",
        "tipo": "Reunion del Consejo TIC",
        "titulo": "Paraguay and the United States hold the Second Meeting of the Trade "
        "and Investment Council",
        "url": f"{URL_BASE}/about-us/policy-offices/press-office/press-releases/2023/september/paraguay-and-united-states-hold-second-meeting-trade-and-investment-council",
    },
    {
        "fecha": "2024-09-16",
        "tipo": "Reunion del Consejo TIC",
        "titulo": "The United States and Paraguay hold the Third Meeting of the Trade "
        "and Investment Council",
        "url": f"{URL_BASE}/about-us/policy-offices/press-office/press-releases/2024/september/united-states-and-paraguay-hold-third-meeting-trade-and-investment-council",
    },
]

ANIO_DESDE_VIVO = 2025  # desde aca se revisa el sitio en vivo, no el historico fijo
MESES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
PATRON_FECHA = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December) \d{1,2},? \d{4}"
)


def _titulo_relevante(titulo):
    t = titulo.lower()
    return "paraguay" in t and ("trade and investment" in t or "tifa" in t)


def _buscar_en_mes(anio, mes):
    """Devuelve [(titulo, url)] de comunicados de ese mes con titulo relevante."""
    url = f"{URL_BASE}/about-us/policy-offices/press-office/press-releases/{anio}/{mes}"
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code == 404:
        return []
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    prefijo = f"/press-releases/{anio}/{mes}/"
    vistos = set()
    encontrados = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if prefijo not in href:
            continue
        titulo = a.get("title") or a.get_text(strip=True)
        if not _titulo_relevante(titulo):
            continue
        url_completa = href if href.startswith("http") else f"{URL_BASE}{href}"
        if url_completa in vistos:
            continue
        vistos.add(url_completa)
        encontrados.append((titulo, url_completa))

    return encontrados


def _fecha_del_comunicado(url):
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    texto = BeautifulSoup(resp.text, "html.parser").get_text(" ", strip=True)
    match = PATRON_FECHA.search(texto)
    if not match:
        return None
    fecha = datetime.strptime(match.group(0).replace(",", ""), "%B %d %Y")
    return fecha.strftime("%Y-%m-%d")


def _revisar_sitio_vivo():
    """Revisa mes a mes, desde ANIO_DESDE_VIVO hasta el anio actual, el sitio no archivado."""
    anio_actual = datetime.now(timezone.utc).year
    eventos = []
    for anio in range(ANIO_DESDE_VIVO, anio_actual + 1):
        for mes in MESES:
            try:
                hallazgos = _buscar_en_mes(anio, mes)
            except Exception as exc:  # noqa: BLE001
                print(f"    [!] {anio}/{mes}: {exc!r}")
                continue

            for titulo, url in hallazgos:
                fecha = _fecha_del_comunicado(url)
                eventos.append(
                    {
                        "fecha": fecha or f"{anio}-01-01",
                        "tipo": "Reunion del Consejo TIC (revision automatica)",
                        "titulo": titulo,
                        "url": url,
                    }
                )
    return eventos


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"ustr_consejo_comercio_inversion_{fecha_hoy}.xlsx"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    eventos = list(EVENTOS_HISTORICOS) + _revisar_sitio_vivo()
    df = pd.DataFrame(eventos).drop_duplicates(subset=["url"]).sort_values("fecha")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - {len(df)} eventos.")


if __name__ == "__main__":
    run()
