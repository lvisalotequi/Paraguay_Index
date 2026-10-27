#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 02/09/2026                                                #
# NOMBRE: state_gov_tias_paraguay                                              #
# DETALLE: arma un Excel con las publicaciones TIAS entre Paraguay y EE.UU.    #
#   desde 2015: un historico fijo de 3 TIAS, verificado en cada corrida, mas   #
#   una busqueda en vivo en DuckDuckGo. Hoy ninguna variable lo usa (la        #
#   reemplaza state_gov_tif_vigentes), pero se conserva a proposito.           #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); hoy no lo lee ningun modulo de      #
#   processing                                                                 #
# SALIDA: un Excel por dia (state_gov_tias_paraguay_{fecha}.xlsx) en           #
#   01_crudas/<dimension>_crudas/state_gov_tias_paraguay/                      #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import re
import time
from datetime import datetime, timezone

import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo



# Parametros -------------------------------------------------------------------

# La fuente son las paginas individuales de cada tratado en state.gov (por ejemplo
# state.gov/paraguay-21-1022). State.gov no tiene un indice navegable de TIAS por
# pais, y su propio buscador tampoco sirve para esto (confirmado 2026-09-02): la
# unica forma de encontrar estas paginas es buscando por texto. Se usa DuckDuckGo
# (paquete ddgs) solo para DESCUBRIR las URLs candidatas; los datos en si (titulo,
# categoria, fechas) se sacan pidiendo cada pagina individual y no de los
# fragmentos de la busqueda, que pueden venir truncados.
#
# Adaptado de un script de referencia que proporciono el usuario (que ademas
# generaba un CSV "limpio", un CSV de "auditoria", un JSON de metadatos y llamaba a
# un script de Node.js para armar el Excel). Se simplifico a un unico Excel, en
# memoria, sin escribir nada a disco local ni depender de Node, siguiendo la
# convencion del resto de src/ingestion/.
URL_BASE    = "https://www.state.gov"
PAIS        = "Paraguay"
IMPERSONATE = "chrome"  # state.gov bloquea requests normal (403), confirmado 2026-09-02

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "2_Actividad_gubernamental_y_diplomatica"
FUENTE      = "state_gov_tias_paraguay"
DESCRIPCION = "Publicaciones TIAS (tratados y acuerdos internacionales) entre Paraguay y EE.UU."
URL_FUENTE  = "https://www.state.gov/treaties-and-other-international-acts-series-tias/"

# Sin tope superior fijo: el pipeline corre de forma indefinida (ver CLAUDE.md), asi
# que un ANIO_MAXIMO fijo en 2025 iria quedando obsoleto cada vez que apareciera un
# TIAS nuevo. Paso de verdad el 2026-09-02: el TIAS 26-317, vigente desde
# 2026-03-17, quedaba afuera con un tope fijo pese a estar ya verificado como real.
# El limite superior es siempre "el anio en curso".
ANIO_MINIMO = 2015

PATRON_TITULO = re.compile(
    r"Paraguay\s*\((?P<tias>[\d.\-]+)\)\s*[-–—]\s*(?P<nombre>.+?)\s*[-–—]\s*"
    r"United States Department of State",
    re.IGNORECASE,
)
PATRON_DETALLE = re.compile(
    r"TIAS Office of Treaty Affairs\s+\w+ \d{1,2},? \d{4}\s+(?P<categoria>.+?)\s+"
    r"Signed at\s+(?P<lugar>.+?)\s+(?P<fecha_firma>\w+ \d{1,2},? \d{4})\s*;\s*"
    r"entered into force\s+(?P<fecha_vigor>\w+ \d{1,2},? \d{4})",
    re.IGNORECASE,
)

# RIESGO REAL, distinto al resto de las fuentes: la busqueda de DuckDuckGo puede
# fallar o devolver menos resultados corriendo desde GitHub Actions (IPs compartidas
# entre muchos usuarios, mas propensas a bloqueos de buscadores que una IP
# residencial), algo que no le pasa a las APIs oficiales que usan las demas fuentes.
# Por eso el diseno es hibrido, igual que ustr_consejo_comercio_inversion.py:
#
#   1. Un historico FIJO (EVENTOS_HISTORICOS) con los 3 TIAS de Paraguay encontrados
#      y confirmados el 2026-09-02 (anios de TIAS 2021, 2025 y 2026: los unicos >=
#      ANIO_MINIMO). Tambien existen TIAS de Paraguay mas viejos, con numeracion
#      pre-2000 sin guion (por ejemplo "12995", de 1998, y "94-817", de 1994): quedan
#      fuera de este rango a proposito. En cada corrida se vuelve a pedir la pagina
#      de cada uno directamente (sin pasar por la busqueda) para confirmar que los
#      datos guardados sigan siendo reales: columnas verificado y nota_verificacion.
#      Completitud del rango 2015-2024 chequeada a mano el 2026-09-02 con una
#      busqueda por prefijo de anio ("Paraguay (15-" ... "Paraguay (24-"
#      site:state.gov): hubo hits sueltos y ruidosos en varios anios, pero ninguno
#      matcheo el patron real de URL de un TIAS (state.gov/paraguay-XX-...), asi
#      que no hay ningun TIAS de Paraguay perdido en ese rango.
#   2. Una busqueda EN VIVO via DuckDuckGo para detectar TIAS nuevos que todavia no
#      esten en el historico. Si falla por completo (bloqueo, sin resultados en
#      ninguna consulta), no rompe el modulo: se sube igual el historico fijo ya
#      verificado y se avisa por consola.
EVENTOS_HISTORICOS = [
    {
        "tias": "21-1022",
        "url": f"{URL_BASE}/paraguay-21-1022",
    },
    {
        "tias": "25-814",
        "url": f"{URL_BASE}/paraguay-25-814",
    },
    {
        "tias": "26-317",
        "url": f"{URL_BASE}/paraguay-26-317",
    },
]

CONSULTAS_BUSQUEDA = [
    f'site:state.gov "{PAIS} (" "TIAS"',
    f'site:state.gov/{PAIS.lower()}- "entered into force"',
    f'site:state.gov "{PAIS} (" agreement',
]



# Funciones auxiliares ---------------------------------------------------------


def _normalizar_fecha(texto):
    return datetime.strptime(texto.replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")


def _anio_desde_tias(tias):
    """Los TIAS modernos usan el formato AA-NNNN (ej. 21-1022 = 2021). Los
    TIAS viejos (pre-2000) no tienen guion (ej. "12995") - no hay forma
    confiable de sacarles el anio del numero solo, y quedan fuera de
    ANIO_MINIMO/ANIO_MAXIMO de todos modos, asi que se devuelve None."""
    match = re.match(r"^(\d{2})-\d+", tias)
    if not match:
        return None
    return 2000 + int(match.group(1))


def _parsear_pagina_tias(url):
    """Pide una pagina individual de TIAS y extrae sus datos. None si no matchea el patron esperado."""
    resp = requests.get(url, impersonate=IMPERSONATE, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # el titulo de la pagina trae el numero de TIAS y el nombre del acuerdo
    titulo_pagina = soup.title.get_text(strip=True) if soup.title else ""
    match_titulo = PATRON_TITULO.search(titulo_pagina)
    if not match_titulo:
        return None

    tias = match_titulo.group("tias")
    nombre = match_titulo.group("nombre").strip(" .–—-")

    # el cuerpo trae la categoria, el lugar y las fechas de firma y entrada en vigor
    texto = soup.get_text(" ", strip=True)
    match_detalle = PATRON_DETALLE.search(texto)
    categoria = lugar_firma = fecha_firma = fecha_vigor = ""
    if match_detalle:
        categoria = match_detalle.group("categoria").strip()
        lugar_firma = match_detalle.group("lugar").strip()
        fecha_firma = _normalizar_fecha(match_detalle.group("fecha_firma"))
        fecha_vigor = _normalizar_fecha(match_detalle.group("fecha_vigor"))

    return {
        "tias": tias,
        "nombre": nombre,
        "categoria": categoria,
        "lugar_firma": lugar_firma,
        "fecha_firma": fecha_firma,
        "fecha_entrada_vigor": fecha_vigor,
        "url": url,
    }


def _historico_verificado():
    """Vuelve a pedir la pagina de cada evento del historico fijo y confirma que siga siendo real."""
    resultado = []
    for evento in EVENTOS_HISTORICOS:
        try:
            datos = _parsear_pagina_tias(evento["url"])
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] historico sin verificar - TIAS {evento['tias']}: {exc!r}")
            resultado.append(
                {**evento, "verificado": False, "nota_verificacion": f"no se pudo acceder: {exc!r}"}
            )
            continue

        if datos is None:
            print(
                f"    [!] historico sin verificar - TIAS {evento['tias']}: "
                "la pagina ya no tiene el formato esperado"
            )
            resultado.append(
                {
                    **evento,
                    "verificado": False,
                    "nota_verificacion": "la pagina ya no tiene el formato esperado",
                }
            )
            continue

        if datos["tias"] != evento["tias"]:
            print(
                f"    [!] historico sin verificar - TIAS {evento['tias']}: "
                f"la pagina ahora dice TIAS {datos['tias']}"
            )
            datos["verificado"] = False
            datos["nota_verificacion"] = f"la pagina ahora dice TIAS {datos['tias']}, no {evento['tias']}"
            resultado.append(datos)
            continue

        datos["verificado"] = True
        datos["nota_verificacion"] = "OK - pagina accesible, datos confirmados"
        resultado.append(datos)

    return resultado


def _buscar_candidatos_vivo(urls_conocidas):
    """Busca en DuckDuckGo paginas de TIAS de Paraguay que todavia no esten en el historico."""
    try:
        from ddgs import DDGS
    except Exception as exc:  # noqa: BLE001
        print(f"    [!] no se pudo importar ddgs, se saltea la busqueda en vivo: {exc!r}")
        return []

    patron_url = re.compile(rf"^https://www\.state\.gov/{PAIS.lower()}-", re.IGNORECASE)
    candidatas = set()
    alguna_consulta_ok = False

    # 1. corre las consultas y junta las URLs que parecen paginas de TIAS de Paraguay
    for consulta in CONSULTAS_BUSQUEDA:
        try:
            resultados = list(DDGS().text(consulta, max_results=50))
            alguna_consulta_ok = True
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] busqueda fallo ('{consulta}'): {exc!r}")
            continue

        for item in resultados:
            href = (item.get("href") or "").split("#")[0]
            if patron_url.match(href) and href not in urls_conocidas:
                candidatas.add(href)

        time.sleep(1)  # pausa breve para no saturar el buscador

    if not alguna_consulta_ok:
        print(
            f"    [!] las {len(CONSULTAS_BUSQUEDA)} consultas de busqueda fallaron - "
            "sin revision en vivo esta corrida"
        )
        return []

    # 2. pide cada candidata y se queda con las que tienen el formato esperado
    nuevos = []
    for url in sorted(candidatas):
        try:
            datos = _parsear_pagina_tias(url)
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] no se pudo procesar candidato {url}: {exc!r}")
            continue
        if datos is None:
            continue
        datos["verificado"] = True
        datos["nota_verificacion"] = "extraido y confirmado en esta misma corrida (busqueda en vivo)"
        nuevos.append(datos)

    return nuevos



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre del archivo del dia

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"state_gov_tias_paraguay_{fecha_hoy}.xlsx"

    # 2. idempotente por dia: si ya se corrio hoy, no se vuelve a pedir

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    # 3. historico verificado + busqueda en vivo de TIAS nuevos

    eventos = _historico_verificado()
    urls_conocidas = {e["url"] for e in eventos}
    eventos += _buscar_candidatos_vivo(urls_conocidas)

    # 4. se queda con los TIAS entre ANIO_MINIMO y el anio en curso

    anio_maximo = datetime.now(timezone.utc).year
    filas = []
    for evento in eventos:
        anio = _anio_desde_tias(evento["tias"])
        if anio is None or not (ANIO_MINIMO <= anio <= anio_maximo):
            continue
        filas.append({**evento, "anio_tias": anio})

    if not filas:
        print(f"[{FUENTE}] no quedo ningun TIAS dentro de {ANIO_MINIMO}-{anio_maximo} tras filtrar.")
        return

    # 5. arma el Excel (una fila por TIAS) y lo sube

    df = pd.DataFrame(filas).drop_duplicates(subset=["tias"]).sort_values("anio_tias")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    # 6. validacion: cuantos TIAS y cuantos quedaron sin verificar

    sin_verificar = (~df["verificado"]).sum()
    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(df)} TIAS, {sin_verificar} sin verificar."
    )


if __name__ == "__main__":
    run()
