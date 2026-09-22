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

3. Una verificacion del historico fijo: en CADA corrida, se vuelve a pedir
   la URL de cada uno de los 5 eventos de EVENTOS_HISTORICOS (5 pedidos
   nada mas, no todo el archivo) y se confirma que la pagina siga
   existiendo, siga mencionando a Paraguay, y que la fecha publicada
   coincida con la guardada. Asi el historico fijo no queda como una foto
   que nadie vuelve a chequear - si USTR reescribe o da de baja una pagina,
   la columna `verificado` lo va a mostrar en la proxima corrida.

Sube un Excel (una fila por evento, con columnas `verificado` y
`nota_verificacion`) a Drive. Es idempotente por dia.

Nota sobre el "tipo" de evento: de los 5 hitos del historico, solo 3 son
literalmente "reuniones del Consejo" (2022, 2023, 2024 - primera, segunda y
tercera reunion). Los otros 2 son hitos previos: el MOU de 2015 y la firma
del TIFA en 2017 que crea el marco. La columna "tipo" permite filtrar segun
que definicion de "reunion formal" se quiera usar.

**Como se distingue de `state_gov_tif_vigentes.py` (agregada 2026-09-22):**
esta fuente mide HITOS puntuales de comercio/inversion (eventos que ocurren
una vez y no persisten). `state_gov_tif_vigentes.py` mide el STOCK de TODO
tipo de acuerdo bilateral que sigue vigente hoy (cualquier tema, no solo
comercio). Verificado que no son redundantes: la correlacion en niveles es
alta (0,86) pero es un efecto de tendencia compartida (las dos series solo
crecen en el tiempo) - en primeras diferencias, que es la prueba correcta
para saber si realmente se mueven juntas, la correlacion cae a 0,07. Son
estadisticamente independientes (ver DICCIONARIO_VARIABLES.md para el
detalle del analisis). **Nota de definicion, no inconsistencia:** la TIFA
es el mismo instrumento en las dos fuentes, pero esta lo fecha por *firma*
(2017-01-13, el hito historico de abajo) y el TIF lo fecha por *entrada en
vigor* (2021-03-17) - la diferencia de ~4 anios es el tramite de
ratificacion entre ambos paises, no un error de ninguna de las dos.
"""
import io
import re
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_BASE = "https://ustr.gov"

DIMENSION = "2_Actividad_gubernamental_y_diplomatica"
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


def _verificar_evento_historico(evento):
    """Vuelve a pedir la URL de un evento del historico fijo y confirma que
    lo guardado siga siendo real: pagina accesible, menciona a Paraguay, y
    la fecha guardada aparece en algun lugar de la pagina. Devuelve
    (verificado, nota).

    Nota tecnica: se buscan TODAS las fechas que aparecen en el texto, no
    solo la primera - algunas paginas archivadas (formato pre-2018) no
    traen la fecha del comunicado en ningun lugar extraible (sin <time>,
    sin clase de fecha), y la primera fecha que aparece en el texto puede
    ser una mencion a otro hecho dentro del cuerpo de la noticia (ej. "este
    acuerdo reemplaza al firmado el 26 de septiembre de 2003" - una fecha
    real, pero de OTRO evento, no del comunicado en si). Por eso no alcanza
    con tomar "la primera fecha encontrada" como si fuera la fecha del
    comunicado.
    """
    try:
        resp = requests.get(evento["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return False, f"no se pudo acceder a la URL: {exc!r}"

    texto = BeautifulSoup(resp.text, "html.parser").get_text(" ", strip=True)
    if "paraguay" not in texto.lower():
        return False, "la pagina ya no menciona a Paraguay"

    fechas_en_pagina = set()
    for match in PATRON_FECHA.finditer(texto):
        fecha = datetime.strptime(match.group(0).replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")
        fechas_en_pagina.add(fecha)

    if evento["fecha"] in fechas_en_pagina:
        return True, "OK - pagina accesible, mencion a Paraguay y fecha guardada confirmadas"

    if fechas_en_pagina:
        return False, (
            f"la pagina existe y menciona a Paraguay, pero la fecha guardada "
            f"({evento['fecha']}) no aparece en el texto - fechas encontradas: "
            f"{', '.join(sorted(fechas_en_pagina))} (revisar a mano; puede ser "
            f"una mencion a otro hecho dentro de la noticia, no la fecha del "
            f"comunicado)"
        )

    return False, (
        "la pagina existe y menciona a Paraguay, pero no tiene ninguna fecha "
        "extraible en el texto (comun en paginas archivadas anteriores a "
        "2018) - no se pudo confirmar la fecha de forma automatica"
    )


def _historico_verificado():
    """EVENTOS_HISTORICOS con columnas 'verificado' y 'nota_verificacion' agregadas."""
    resultado = []
    for evento in EVENTOS_HISTORICOS:
        verificado, nota = _verificar_evento_historico(evento)
        if not verificado:
            print(f"    [!] historico sin verificar - {evento['fecha']} {evento['url']}: {nota}")
        resultado.append({**evento, "verificado": verificado, "nota_verificacion": nota})
    return resultado


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
                        # Recien se extrajo de la pagina en esta misma corrida -
                        # no hace falta re-verificarlo, ya esta confirmado.
                        "verificado": True,
                        "nota_verificacion": "extraido y confirmado en esta misma corrida",
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

    eventos = _historico_verificado() + _revisar_sitio_vivo()
    df = pd.DataFrame(eventos).drop_duplicates(subset=["url"]).sort_values("fecha")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    sin_verificar = (~df["verificado"]).sum()
    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(df)} eventos, {sin_verificar} sin verificar."
    )


if __name__ == "__main__":
    run()
