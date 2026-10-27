#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 22/09/2026                                                #
# NOMBRE: cuota_capital_bancomundial                                           #
# DETALLE: sube a Drive el poder de voto de EE.UU. en el IBRD por anio fiscal: #
#   un historico fijo verificado a mano contra cada Information Statement, mas #
#   el anio en curso leido en vivo de la tabla vigente de worldbank.org. NO    #
#   completa los anios sin dato: processing arrastra el ultimo valor.          #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_financiero_oficial.py                            #
# SALIDA: un CSV por corte                                                     #
#   (cuota_capital_bancomundial_verificado_{fecha}_corte_{cierre}.csv) en      #
#   01_crudas/<dimension>_crudas/cuota_capital_bancomundial/                   #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import re
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests
from pypdf import PdfReader

from src.drive import (
    descargar_archivo,
    existe_archivo,
    listar_archivos,
    resolve_ingestion_folder,
    subir_archivo,
)



# Parametros -------------------------------------------------------------------

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "1_Compromiso_financiero_oficial"
FUENTE      = "cuota_capital_bancomundial"
DESCRIPCION = (
    "Cuota de poder de voto de EE.UU. en el IBRD (Banco Mundial) por año fiscal, "
    "para ponderar bancomundial_proyectos_aprobados"
)
URL_FUENTE  = "https://treasury.worldbank.org/en/about/unit/treasury/ibrd/ibrd-financials-and-ratings"

# La fuente es el "Information Statement" anual del IBRD (informe para inversores en
# sus bonos), publicado poco despues del cierre de cada anio fiscal (30 de junio).
# Cada edicion trae una tabla "Subscriptions and Voting Power of Member Countries"
# con el % de EE.UU. Se busca en thedocs.worldbank.org y, a diferencia del BID, se
# puede descargar con un requests.get() normal, sin Cloudflare ni Power BI de por
# medio.
INSTITUCION = "Banco Mundial (IBRD)"
PAIS        = "Estados Unidos"

# POR QUE UN HISTORICO FIJO EN VEZ DE UN SCRAPER (2026-09-22, a pedido del usuario:
# "no complicar tanto el scrapeo... una opcion para que la persona sepa donde mapear
# la modificacion"): cada edicion vive en una URL con un hash que no sigue un patron
# predecible, por ejemplo
# .../f3508084cc8eae0e08c432b2427b6946-0340022022/original/
# IBRD-Information-Statement-FY22.pdf
# No hay una pagina indice con todas las ediciones: hay que buscar cada anio a mano.
# A diferencia del BID (cuota constante desde 2010), aca el % SI cambia de verdad
# (confirmado 2026-09-22: entre 15,49 % y 16,63 % segun el anio, sin patron simple),
# asi que hace falta la serie completa. Pero automatizar la busqueda de una URL nueva
# cada anio no es practico con los metodos del resto de src/ingestion/ (requeriria
# un buscador o una IA, no un scraper de una pagina fija).
#
# Anios sin dato todavia (2026-09-22): FY2015, FY2017, FY2020, FY2021, FY2026.
# src/processing/compromiso_financiero_oficial.py arrastra el ultimo valor
# confirmado hacia adelante para esos huecos (mismo criterio que otras fuentes
# anuales): no son ceros ni faltantes reales, son anios donde el dato exacto
# todavia no se busco.
#
# COMO AGREGAR UN ANIO NUEVO (la edicion sale en julio o agosto, despues del cierre
# del anio fiscal):
#   1. Buscar en Google "IBRD Information Statement FY{anio}" (por ejemplo "FY26").
#      El resultado suele ser un PDF en thedocs.worldbank.org. Tambien puede estar en
#      https://treasury.worldbank.org/en/about/unit/treasury/ibrd/ibrd-financials-and-ratings
#      (esa pagina solo linkea la edicion MAS RECIENTE, no el historico).
#   2. Abrir el PDF y buscar (Ctrl+F) "largest shareholder": aparece una oracion
#      "The United States is IBRD's largest shareholder, with XX.XX% of total voting
#      power." Ese numero (el de la ORACION, no el de la tabla resumida, que a veces
#      redondea a un entero) es el que va en HISTORICO.
#   3. Agregar una fila a HISTORICO con el anio fiscal (entero), el porcentaje, la
#      fecha de cierre (siempre 30 de junio) y la URL exacta del PDF usado.
#   4. Correr este modulo (python -m src.ingestion.cuota_capital_bancomundial) para
#      subir la fila nueva a Drive.
#
# Verificado a mano, uno por uno, contra el "Information Statement" oficial de cada
# anio fiscal. NO son valores estimados ni interpolados: cada fila viene de abrir el
# PDF y leer esa oracion.
HISTORICO = [
    {
        "anio_fiscal": 2016, "porcentaje_voto": 16.63, "cierre_anio_fiscal": "2016-06-30",
        "url_fuente": "http://documents.worldbank.org/curated/en/106321475287278758/pdf/FY16-IBRD-Information-Statement-09222016.pdf",
    },
    {
        "anio_fiscal": 2018, "porcentaje_voto": 15.98, "cierre_anio_fiscal": "2018-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/571971537558659917-0340022018/render/IBRDInformationStatementFY18Final.pdf",
    },
    {
        "anio_fiscal": 2019, "porcentaje_voto": 15.68, "cierre_anio_fiscal": "2019-06-30",
        "url_fuente": "http://pubdocs.worldbank.org/en/767901569597693292/IBRD-Information-Statement-2019.pdf",
    },
    {
        "anio_fiscal": 2022, "porcentaje_voto": 15.79, "cierre_anio_fiscal": "2022-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/f3508084cc8eae0e08c432b2427b6946-0340022022/original/IBRD-Information-Statement-FY22.pdf",
    },
    {
        "anio_fiscal": 2023, "porcentaje_voto": 15.75, "cierre_anio_fiscal": "2023-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/e384d12cfea59bdcb3adf25487894197-0340022023/original/IBRD-Information-Statement-FY23.pdf",
    },
    {
        "anio_fiscal": 2024, "porcentaje_voto": 15.49, "cierre_anio_fiscal": "2024-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/515cd9fcae37dad3185833617c3cf2b8-0340022024/original/IBRD-Information-Statement-FY24.pdf",
    },
    {
        "anio_fiscal": 2025, "porcentaje_voto": 15.79, "cierre_anio_fiscal": "2025-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/02acefd82f121687f3aa3b429ee50801-0340022025/original/IBRD-Information-Statement-FY25.pdf",
    },
]
FECHA_VERIFICACION = "2026-09-22"  # fecha en que se armo/reviso esta lista completa

# LECTURA EN VIVO DE LA TABLA VIGENTE (2026-10, rama de ajuste). Para el anio fiscal
# EN CURSO el modulo ya no depende de los pasos manuales de arriba: cada corrida abre
# la pagina oficial de poder de voto, ubica el PDF "IBRD Subscriptions and Voting
# Power of Member Countries" vigente (el link cambia, la pagina no), lee la fecha de
# corte ("as of: June 30, 2026") y la fila UNITED STATES, y suma esa fila al historico
# si ese anio fiscal todavia no esta. Reglas:
#   - HISTORICO (verificado a mano) manda sobre cualquier otra cosa.
#   - Lo leido en vivo se guarda en Drive y se conserva en las corridas siguientes
#     (se lee el ultimo archivo subido): no se pierde cuando la pagina pase a mostrar
#     una fecha de corte mas nueva.
#   - Si la pagina o el PDF cambian de formato y no se pueden leer, el modulo avisa
#     y sube el historico tal cual (el comportamiento anterior).
# Los anios sin dato (FY2015, 2017, 2020, 2021 y los intermedios que nadie alcance a
# leer) siguen arrastrandose en processing.
URL_PAGINA_VOTOS    = "https://www.worldbank.org/en/about/leadership/votingpowers"
PREFIJO_ARCHIVO     = "cuota_capital_bancomundial_verificado_"
PATRON_FECHA_CORTE  = re.compile(r"as of:\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})", re.IGNORECASE)
PATRON_FILA_EEUU    = re.compile(r"UNITED STATES\s+[\d,.]+\s+[\d.]+\s+[\d,]+\s+([\d.]+)")
PORCENTAJE_MIN, PORCENTAJE_MAX = 10.0, 25.0  # cota de cordura para descartar una lectura mal parseada



# Funciones auxiliares ---------------------------------------------------------


def _anio_fiscal(fecha_corte):
    """El año fiscal del Banco Mundial cierra el 30 de junio y se nombra por el
    año en que cierra (julio 2025 - junio 2026 = FY2026)."""
    return fecha_corte.year if fecha_corte.month <= 6 else fecha_corte.year + 1


def _leer_tabla_vigente():
    """Fila {anio_fiscal, porcentaje_voto, cierre_anio_fiscal, url_fuente,
    origen} de la tabla de poder de voto vigente del IBRD, o None (con aviso)
    si la pagina o el PDF no se pueden leer."""
    try:
        # 1. abre la pagina oficial y busca el link al PDF de la tabla vigente
        resp = requests.get(URL_PAGINA_VOTOS, impersonate="chrome", timeout=60)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content.decode("utf-8", "replace"), "html.parser")
        enlaces = [a["href"] for a in soup.select("a[href]") if "ibrdcountryvotingtable" in a["href"].lower()]
        if not enlaces:
            raise RuntimeError("no hay link a IBRDCountryVotingTable en la pagina")
        url_pdf = enlaces[0]

        # 2. descarga el PDF y extrae su texto
        pdf = requests.get(url_pdf, impersonate="chrome", timeout=90)
        pdf.raise_for_status()
        texto = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.content)).pages)

        # 3. ubica la fecha de corte y la fila de EE.UU.
        corte = PATRON_FECHA_CORTE.search(texto)
        fila = PATRON_FILA_EEUU.search(texto)
        if not corte or not fila:
            raise RuntimeError("no se encontro la fecha de corte o la fila UNITED STATES en el PDF")

        # June 30, 2026 -> 2026-06-30
        texto_fecha = re.sub(r"\s*,\s*", ", ", re.sub(r"\s+", " ", corte.group(1)))
        fecha_corte = datetime.strptime(texto_fecha, "%B %d, %Y")
        porcentaje = float(fila.group(1))

        # 4. cota de cordura: un porcentaje fuera de rango es una lectura mal parseada
        if not (PORCENTAJE_MIN <= porcentaje <= PORCENTAJE_MAX):
            raise RuntimeError(f"porcentaje fuera de rango: {porcentaje}")

        return {
            "anio_fiscal": _anio_fiscal(fecha_corte),
            "porcentaje_voto": porcentaje,
            "cierre_anio_fiscal": fecha_corte.strftime("%Y-%m-%d"),
            "url_fuente": url_pdf,
            "origen": "tabla_vigente_en_vivo",
        }
    except Exception as exc:  # noqa: BLE001
        print(
            f"[{FUENTE}] [!] no se pudo leer la tabla vigente del IBRD ({exc!r}); "
            "se usa solo el historico."
        )
        return None


def _filas_previas_en_drive(carpeta_id):
    """Filas del ultimo archivo que este modulo subio a Drive (incluye lo que
    se leyo en vivo en corridas anteriores), para no perderlo."""
    candidatos = [a for a in listar_archivos(carpeta_id) if a["name"].startswith(PREFIJO_ARCHIVO)]
    if not candidatos:
        return []
    ultimo = sorted(candidatos, key=lambda a: a["name"])[-1]
    df = pd.read_csv(io.BytesIO(descargar_archivo(ultimo["id"])))
    columnas = ["anio_fiscal", "porcentaje_voto", "cierre_anio_fiscal", "url_fuente"]
    if not set(columnas) <= set(df.columns):
        return []
    filas = df[columnas].to_dict("records")
    for fila in filas:
        fila["origen"] = "tabla_vigente_en_vivo"
    return filas



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive de esta fuente

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)

    # 2. junta las tres fuentes de filas, por anio fiscal. Precedencia: HISTORICO
    # (verificado a mano) > tabla vigente leida en vivo hoy > lo leido en vivo en
    # corridas anteriores

    por_anio = {
        fila["anio_fiscal"]: dict(fila, origen="previo_en_drive")
        for fila in _filas_previas_en_drive(carpeta_id)
    }
    vigente = _leer_tabla_vigente()
    if vigente:
        por_anio[vigente["anio_fiscal"]] = vigente
    for fila in HISTORICO:
        por_anio[fila["anio_fiscal"]] = dict(fila, origen="historico_verificado")

    filas = [por_anio[anio] for anio in sorted(por_anio)]
    ultimo_cierre = max(fila["cierre_anio_fiscal"] for fila in filas)

    # 3. arma el nombre. Lleva la fecha de corte mas reciente: cuando la tabla vigente
    # trae un anio fiscal nuevo el nombre cambia, se sube un archivo nuevo y processing
    # (que toma el ultimo por nombre) lo recoge. Sin anio nuevo el nombre se repite y
    # no se sube nada (idempotente).

    nombre = f"{PREFIJO_ARCHIVO}{FECHA_VERIFICACION}_corte_{ultimo_cierre}.csv"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    # 4. arma la tabla con las columnas fijas de institucion, pais y verificacion

    df = pd.DataFrame(filas)
    df.insert(0, "institucion", INSTITUCION)
    df.insert(1, "pais", PAIS)
    df["fecha_verificacion"] = FECHA_VERIFICACION

    # 5. sube el CSV a Drive

    contenido = df.to_csv(index=False).encode("utf-8-sig")
    subir_archivo(contenido, nombre, carpeta_id, mime_type="text/csv")

    # 6. validacion: cuantos anios fiscales se subieron y cuantos no son del historico fijo

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - {len(filas)} años fiscales "
        f"({sum(1 for f in filas if f['origen'] != 'historico_verificado')} no vienen del historico fijo)."
    )


if __name__ == "__main__":
    run()
