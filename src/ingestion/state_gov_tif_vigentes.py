#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 22/09/2026                                                #
# NOMBRE: state_gov_tif_vigentes                                               #
# DETALLE: descarga el PDF anual Treaties in Force del Departamento de Estado, #
#   aisla la seccion de Paraguay y sube un Excel con todos los acuerdos        #
#   bilaterales vigentes (39 en la edicion 2026). NO decide vigencia: ya la    #
#   resuelve la fuente. Acumular por trimestre es trabajo de src/processing/.  #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/actividad_gubernamental_y_diplomatica.py                    #
# SALIDA: un Excel por dia (state_gov_tif_vigentes_{fecha}.xlsx) en            #
#   01_crudas/<dimension>_crudas/state_gov_tif_vigentes/                       #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io
import re
from datetime import datetime, timezone

import pandas as pd
from curl_cffi import requests
from pypdf import PdfReader

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo



# Parametros -------------------------------------------------------------------

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "2_Actividad_gubernamental_y_diplomatica"
FUENTE      = "state_gov_tif_vigentes"
DESCRIPCION = (
    "Todos los tratados y acuerdos bilaterales EE.UU.-Paraguay vigentes, segun "
    "'Treaties in Force' (listado oficial anual del Departamento de Estado)"
)
URL_FUENTE  = "https://www.state.gov/treaties-in-force/"

# "Treaties in Force" (TIF) es la publicacion oficial ANUAL del Departamento de
# Estado que lista TODOS los tratados y acuerdos bilaterales de EE.UU. que siguen
# vigentes a una fecha dada. El propio Departamento ya excluye los terminados,
# reemplazados o superados: no hay que decidir "vigencia" con criterio propio, la
# fuente ya lo resuelve.
#
# La pagina linkea un PDF nuevo cada anio (por ejemplo "Treaties-in-Force-2026.pdf").
# Se busca ese link en la pagina y NO se hardcodea el anio, para que el modulo siga
# funcionando cuando salga la edicion siguiente.
#
# 2026-09-22: NO es un PDF escaneado como imagen (una nota anterior del repo
# asumia eso, de una edicion vieja probada de otra forma). La edicion 2026 tiene
# texto real, extraible con pypdf (551 paginas, unos 5 MB, un tamano consistente con
# texto y no con escaneo). Verificado bajandola y parseandola con datos reales.
#
# POR QUE EXISTE ADEMAS DE state_gov_tias_paraguay.py (no lo reemplaza; 2026-09-22, a
# pedido del usuario): ese modulo busca publicaciones de la serie TIAS posteriores a
# 2015 con una busqueda en DuckDuckGo (state.gov no tiene un indice navegable de TIAS
# por pais). Este TIF es mucho mas completo: agrupa TODO tipo de acuerdo bilateral
# vigente (TIAS, TS, EAS, UST, o "NP" = no publicado), de cualquier fecha de firma
# (hoy 1860-2025 para Paraguay), y no depende de que un acuerdo tenga un numero TIAS
# asignado ni de encontrarlo por busqueda. El analisis de correlacion (2026-09-22,
# ver DICCIONARIO_VARIABLES.md) confirmo que esta variable y
# ustr_consejo_comercio_inversion NO miden lo mismo (correlacion en diferencias de
# unos 0.07): una es stock legal acumulado de cualquier tema, la otra son hitos
# diplomaticos puntuales solo de comercio. state_gov_tias_paraguay.py queda en
# revision (no Validado) y es candidato a eliminarse mas adelante, porque este TIF
# lo contiene como subconjunto, pero esa decision se toma despues, no ahora.
#
# LIMITE EXPLICITO, no resuelto: esto es una FOTO del estado vigente a la fecha de la
# edicion mas reciente. Si un acuerdo estuvo vigente parte de 2015-2025 pero ya fue
# terminado por completo antes de la edicion usada, no aparece en ningun lado del PDF
# (el Departamento de Estado ya lo saco de la lista) y quedaria subcontado en los
# trimestres en que si estuvo vigente. Para Paraguay no hay indicio de esto en la
# edicion 2026 (todo lo que aparece, incluidos acuerdos con enmiendas parciales,
# sigue listado), pero no esta descartado sin cruzar contra una edicion vieja.
#
# COMO SE AISLA LA SECCION DE PARAGUAY (sin asumir numeros de pagina fijos, que
# cambian de edicion a edicion):
#   1. El documento trae una tabla de contenidos (paginas 5 a 7 aproximadamente)
#      con cada pais y su numero de pagina IMPRESO (el del pie de cada pagina, no el
#      indice del PDF). Se busca "PARAGUAY" ahi y se toma el numero de pagina de la
#      entrada siguiente como limite superior (exclusivo).
#   2. Se mapea cada numero de pagina IMPRESO a su indice real dentro del PDF
#      (leyendo el pie de cada una) y se concatena el texto de las paginas del rango.
#   3. Ese texto puede traer la cola del pais anterior (el encabezado de pagina
#      anticipa el pais cuya seccion arranca en esa pagina, aunque el contenido de
#      arriba todavia sea del anterior): se recorta hasta la ULTIMA vez que aparece
#      la palabra "PARAGUAY" seguida de una categoria (no de un numero de pagina).
#
# COMO SE SEPARAN LOS ACUERDOS dentro de la seccion ya aislada (sin IA, por
# estructura de texto):
#   - Los encabezados de categoria (ARMS CONTROL, DEFENSE, TRADE & INVESTMENT, etc.)
#     son lineas enteramente en mayusculas. Los tokens de cita que tambien son
#     mayusculas sueltas (TIAS, NP, UST, TS, EAS, UNTS, Stat., Bevans) quedan
#     excluidos por una lista negra explicita; si no, el parser los confunde con una
#     categoria nueva.
#   - Cada acuerdo cierra con su linea "Entered into force ...", que puede venir
#     partida en dos lineas fisicas (por ejemplo "provisionally <fecha>;" +
#     "definitively <fecha>.") o con una clausula extra ("; operative <fecha>."): se
#     juntan lineas hasta topar con un punto final antes de extraer la fecha.
#   - La cita (numero TIAS, UST, TS, etc.) es la linea inmediatamente siguiente a la
#     de entrada en vigor.
#   - Los bloques "Amendment(s):" y "Related Agreement:" (enmiendas o acuerdos
#     relacionados de un acuerdo YA cerrado) no cuentan como acuerdos nuevos: se
#     descartan mientras las lineas siguientes tengan algun digito (fechas o numeros
#     de cita), que es como se ven todas sus lineas en la practica.
#
# Verificado 2026-09-22 contra la edicion 2026: 39 acuerdos para Paraguay, fechas de
# entrada en vigor de 1860-03-07 a 2025-08-14, los 39 confirmados a mano uno por uno
# contra el texto del PDF antes de escribir este parser.
IMPERSONATE = "chrome"  # state.gov puede bloquear requests normal (403), mismo criterio que el resto
PAIS        = "PARAGUAY"

PATRON_LINK_PDF = re.compile(
    r"https://www\.state\.gov/wp-content/uploads/\d{4}/\d{2}/Treaties-in-Force-(\d{4})\.pdf"
)
PATRON_PIE_PAGINA = re.compile(
    r"Bilateral Treaties in Force as of [^\n]*\n[^\n]*\n\s*\n\s*\n\s*(\d+)\s*\n"
)
PATRON_ENTRADA_TOC = re.compile(r"([A-Z][A-Z \-'&.]+?)\.{5,}\s*(\d+)")

TOKENS_CITA = {"TIAS", "NP", "UST", "TS", "EAS", "UNTS", "STAT", "BEVANS", "F.R.", "ILM", "LNTS"}
CATEGORIA_RE = re.compile(r"^[A-Z][A-Z &,\-]{2,60}$")
SUBENTRADA_RE = re.compile(r"^(Amendments?|Related Agreement)s?:?$", re.IGNORECASE)
EIF_START_RE = re.compile(r"^Entered into force", re.IGNORECASE)
EIF_EXTRACT_RE = re.compile(
    r"Entered into force(?: provisionally)?\s+(?P<f1>[A-Za-z]+ \d{1,2},? ?\d{4})"
    r"(?:[;,]?\s*definitively\s+(?P<f2>[A-Za-z]+ \d{1,2},? ?\d{4}))?",
    re.IGNORECASE,
)
TIENE_DIGITO = re.compile(r"\d")



# Funciones auxiliares ---------------------------------------------------------


def _es_categoria(linea):
    return bool(CATEGORIA_RE.match(linea)) and linea.strip() not in TOKENS_CITA


def _normalizar_fecha(texto):
    texto = re.sub(r"\s+", " ", texto.replace(",", "")).strip()
    return datetime.strptime(texto, "%B %d %Y").strftime("%Y-%m-%d")


def _url_pdf_vigente():
    """Busca en la pagina de aterrizaje el link al PDF de la edicion mas reciente."""
    resp = requests.get(URL_FUENTE, impersonate=IMPERSONATE, timeout=30)
    resp.raise_for_status()
    match = PATRON_LINK_PDF.search(resp.text)
    if not match:
        raise RuntimeError(f"no se encontro el link al PDF de Treaties in Force en {URL_FUENTE}")
    return match.group(0), int(match.group(1))


def _descargar_pdf(url):
    resp = requests.get(url, impersonate=IMPERSONATE, timeout=120)
    resp.raise_for_status()
    return resp.content


def _paginas_de_texto(contenido_pdf):
    lector = PdfReader(io.BytesIO(contenido_pdf))
    return [pagina.extract_text() or "" for pagina in lector.pages]


def _aislar_seccion_pais(paginas, pais=PAIS):
    """Devuelve el texto de la seccion bilateral de `pais`, usando la tabla
    de contenidos del documento para ubicar el rango de paginas (no asume
    numeros de pagina fijos - ver docstring del modulo)."""

    # 1. mapea cada numero de pagina IMPRESO a su indice real dentro del PDF
    pagina_impresa_a_indice = {}
    for idx, texto in enumerate(paginas):
        m = PATRON_PIE_PAGINA.search(texto)
        if m:
            pagina_impresa_a_indice[int(m.group(1))] = idx

    # 2. busca el pais en la tabla de contenidos: su pagina y la de la entrada siguiente
    texto_toc = "\n".join(paginas[3:10])  # la tabla de contenidos vive en las primeras paginas
    entradas_toc = [(n.strip(), int(p)) for n, p in PATRON_ENTRADA_TOC.findall(texto_toc)]
    nombres_toc = [n for n, _ in entradas_toc]
    if pais not in nombres_toc:
        raise RuntimeError(f"'{pais}' no aparece en la tabla de contenidos del PDF de Treaties in Force")
    idx_pais = nombres_toc.index(pais)
    pagina_inicio = entradas_toc[idx_pais][1]
    pagina_fin_exclusiva = entradas_toc[idx_pais + 1][1]

    indices_pdf = sorted(
        {
            pagina_impresa_a_indice[p]
            for p in range(pagina_inicio, pagina_fin_exclusiva)
            if p in pagina_impresa_a_indice
        }
    )
    if not indices_pdf:
        raise RuntimeError(
            f"no se pudieron ubicar las paginas {pagina_inicio}-{pagina_fin_exclusiva} "
            f"de '{pais}' en el PDF"
        )

    texto_bruto = "\n".join(paginas[i] for i in indices_pdf)

    # 3. recorta antes del inicio real del contenido (puede traer la cola del pais anterior)
    candidatos_inicio = []
    for m in re.finditer(rf"\n\s*{pais}\s*\n", texto_bruto):
        resto = texto_bruto[m.end():m.end() + 80]
        primera_linea = next((l.strip() for l in resto.split("\n") if l.strip()), "")
        if not re.match(r"^\d+$", primera_linea) and re.match(r"^[A-Z][A-Z &,\-]{2,60}$", primera_linea):
            candidatos_inicio.append(m.end())
    inicio = candidatos_inicio[-1] if candidatos_inicio else 0
    seccion = texto_bruto[inicio:]

    # 4. quita los encabezados de pagina embebidos (repiten "Bilateral Treaties in
    # Force as of ..." + el numero de pagina en medio del contenido real)
    seccion = re.sub(
        r"Bilateral Treaties in Force as of [^\n]*\n(?:[^\n]*\n){0,4}?\s*\d+\s*\n",
        "\n",
        seccion,
    )
    return seccion


def _parsear_acuerdos(seccion_texto):
    """Recorre la seccion linea por linea y arma una fila por acuerdo vigente."""
    lineas = [l.strip() for l in seccion_texto.split("\n")]
    lineas = [l for l in lineas if l]

    categoria_actual = None
    bloque = []
    filas = []
    i, n = 0, len(lineas)

    while i < n:
        linea = lineas[i]

        # encabezado de categoria (puede ocupar varias lineas seguidas)
        if _es_categoria(linea):
            categorias = [linea]
            j = i + 1
            while j < n and _es_categoria(lineas[j]):
                categorias.append(lineas[j])
                j += 1
            categoria_actual = " ".join(categorias).strip()
            bloque = []
            i = j
            continue

        # enmiendas y acuerdos relacionados: no cuentan como acuerdos nuevos
        if SUBENTRADA_RE.match(linea):
            i += 1
            while i < n and TIENE_DIGITO.search(lineas[i]) and not _es_categoria(lineas[i]):
                i += 1
            continue

        # cierre de un acuerdo: su linea "Entered into force ..." y la cita que sigue
        if EIF_START_RE.match(linea):
            trozo = linea
            k = i
            while not trozo.rstrip().endswith(".") and k + 1 < n and not _es_categoria(lineas[k + 1]):
                k += 1
                trozo += " " + lineas[k]
            match = EIF_EXTRACT_RE.search(trozo)
            fecha_texto = match.group("f2") or match.group("f1")
            i = k + 1

            cita = ""
            if (
                i < n
                and not _es_categoria(lineas[i])
                and not SUBENTRADA_RE.match(lineas[i])
                and not EIF_START_RE.match(lineas[i])
            ):
                cita = lineas[i]
                i += 1

            filas.append(
                {
                    "categoria": categoria_actual,
                    "descripcion": " ".join(bloque).strip(),
                    "fecha_entrada_vigor": _normalizar_fecha(fecha_texto),
                    "cita": cita,
                }
            )
            bloque = []
            continue

        # cualquier otra linea es parte de la descripcion del acuerdo en curso
        bloque.append(linea)
        i += 1

    return filas



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre del archivo del dia

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"state_gov_tif_vigentes_{fecha_hoy}.xlsx"

    # 2. idempotente por dia: si ya se subio hoy, no se vuelve a pedir el PDF

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    # 3. descarga el PDF vigente, aisla la seccion de Paraguay y separa los acuerdos

    url_pdf, anio_edicion = _url_pdf_vigente()
    contenido_pdf = _descargar_pdf(url_pdf)
    paginas = _paginas_de_texto(contenido_pdf)
    seccion = _aislar_seccion_pais(paginas)
    filas = _parsear_acuerdos(seccion)

    # 4. validacion: sin acuerdos no se sube nada (el parser no entiende la edicion)

    if not filas:
        print(
            f"[{FUENTE}] no se pudo extraer ningun acuerdo de la seccion de {PAIS} - "
            f"revisar el parser contra la edicion {anio_edicion}."
        )
        return

    # 5. arma el Excel (una fila por acuerdo vigente) y lo sube

    df = pd.DataFrame(filas)
    df["edicion_tif"] = anio_edicion
    df["url_pdf"] = url_pdf
    df = df.drop_duplicates(subset=["fecha_entrada_vigor", "cita"]).sort_values("fecha_entrada_vigor")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    # 6. validacion: cuantos acuerdos y de que rango de fechas

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(df)} acuerdos vigentes (edicion TIF {anio_edicion}), "
        f"{df['fecha_entrada_vigor'].min()} a {df['fecha_entrada_vigor'].max()}."
    )


if __name__ == "__main__":
    run()
