"""Subida de archivos crudos a Google Drive via la cuenta de servicio.

Los modulos de src/ingestion/ NO escriben a disco local: descargan cada
archivo en memoria y lo suben directo a la carpeta de Drive que le
corresponde (dentro de la Unidad compartida del proyecto). Es idempotente:
antes de subir, se revisa si ya existe un archivo con ese nombre en la
carpeta de destino.

DRIVE_ROOT_ID es la carpeta "2.Datos_recolectados" de la Unidad compartida.
La cuenta de servicio tiene rol Writer ahi (puede crear/editar, no puede
borrar - no hace falta para ingestion).

Nota sobre los nombres de carpeta de dimension (2026-09-02): el usuario
renombro a mano las 4 carpetas de dimension dentro de CARPETA_CRUDAS en
Drive, agregandoles el sufijo "_crudas" (ej. "3_Compromiso_economico_privado"
paso a llamarse "3_Compromiso_economico_privado_crudas"). Los modulos de
src/ingestion/ NO se tocaron - sus constantes DIMENSION siguen siendo el
nombre de dimension SIN el sufijo (asi queda mas prolijo el resto del
codigo, ver CLAUDE.md seccion 1). Por eso resolve_ingestion_folder agrega
el sufijo "_crudas" el buscar/crear la carpeta de dimension - si a alguien
se le ocurre buscar "{dimension}" sin el sufijo, va a encontrar (o peor,
crear) una carpeta vacia que no es la real. Esto ya paso una vez (el mismo
2026-09-02, antes de que el usuario avisara del rename): quedaron 8
carpetas duplicadas vacias en Drive de esa confusion - el servicio no
puede borrarlas (rol Writer), hay que borrarlas a mano desde Drive cuando
se pueda.

FOLDER_IDS de mas abajo cachea los IDs ya confirmados de las carpetas
reales (con datos) de cada fuente, para no depender de la busqueda por
nombre en cada corrida - resolve_ingestion_folder los usa directo. Para
una fuente nueva (todavia sin entrada en FOLDER_IDS), cae de vuelta a
resolve_folder con el sufijo "_crudas" ya aplicado, con reintentos (ver
_buscar_hijo_con_reintentos) como defensa extra ante demoras de indexado
de Drive; conviene agregar su ID a FOLDER_IDS a mano despues de la primera
corrida exitosa.

Las etapas 03 y 04 escriben distinto (2026-09-10): publican en
03_integracion y 04_final (ver ETAPA_FOLDER_IDS) con nombre de archivo FIJO
y reemplazando el contenido del mismo archivo en cada corrida
(subir_o_reemplazar), en vez de acumular una foto por dia como ingestion y
processing. El motivo esta explicado en el docstring de esa funcion.
"""
import io
import os
import time

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

DRIVE_ROOT_ID = "1iFJsRRCMSa7u4-GpYNbl7BE2HnvDGxrL"  # carpeta "2.Datos_recolectados"
CARPETA_CRUDAS = "01_crudas"  # subcarpeta donde va todo lo que sube ingestion
CARPETA_LIMPIAS = "02_limpias"  # subcarpeta donde processing sube sus CSV consolidados
CARPETA_INTEGRACION = "03_integracion"  # subcarpeta donde 03_integration publica el panel
CARPETA_FINAL = "04_final"  # subcarpeta donde 04_analysis_index publica el resultado

MIME_HOJA_DE_CALCULO = "application/vnd.google-apps.spreadsheet"

# IDs de carpeta (dimension, fuente) -> folder_id, confirmados a mano el
# 2026-09-02 (ver nota de fiabilidad arriba). Evitan una busqueda por nombre
# en cada corrida - la fuente de verdad es Drive, esto es solo una cache.
FOLDER_IDS = {
    ("1_Compromiso_financiero_oficial", "fa_gov_asistencia_oficial"): "1xwZrYYSCrW5mnhfeTB3QXDFCn1JUzKB7",
    ("1_Compromiso_financiero_oficial", "usaspending_obligaciones"): "1UkTtUHZppeZ0KojVWzH4gFn-mZYdqbN1",
    ("1_Compromiso_financiero_oficial", "exim_autorizaciones"): "1ufc_mOeVDduU0ZboK0Y2_mI5nYIq9Wh6",
    ("1_Compromiso_financiero_oficial", "dfc_proyectos_activos"): "1jz2hOG81GGOETPX9JPF0G0L0oTTyt7TA",
    ("1_Compromiso_financiero_oficial", "bid_proyectos"): "1Hc0uqRJA3_4BD7EbnaVDA9TbEy7v-Lc_",
    ("1_Compromiso_financiero_oficial", "bancomundial_proyectos"): "1u1eYPMSIHxnySRvK-PEoETIp1rrdJ-bA",
    ("2_Actividad_gubernamental_y_diplomatica", "congreso_menciones_paraguay"): "1V0F9qzym6h83FUYQuy_L7vdJYQ_VeYXS",
    ("2_Actividad_gubernamental_y_diplomatica", "ustr_consejo_comercio_inversion"): "1URturmvdk_Ki5j_oFRKORHWrNYbqZ0co",
    ("2_Actividad_gubernamental_y_diplomatica", "state_gov_tias_paraguay"): "1koUH_-Wsij9fM8VVcMQ0Oh1d1cMRAgxD",
    ("3_Compromiso_economico_privado", "bcp_comercio_exterior"): "1HFeiS2Q2Ezi7tZPWZcQvbdo0dbeWCO4u",
    ("3_Compromiso_economico_privado", "bcp_inversion_directa"): "145-zhp9c3hjQtz4vg5EManKsmpE_8r6D",
    ("3_Compromiso_economico_privado", "bcp_remesas_familiares"): "1Bk0fHMJz5WceE4vMugRThte4xAiW_RBc",
    ("3_Compromiso_economico_privado", "bea_inversion_directa"): "1ZMTwLGpNcROTrUmEVDXkX1g7yYumkwon",
    ("4_Visibilidad_mediatica_y_relevancia_publica", "gdelt_proxy_b"): "108u-nqX6hKckFlfv807gZ4p-oHWA-_Ob",
}

# Igual que FOLDER_IDS pero para las carpetas de salida de processing
# (CARPETA_LIMPIAS/{dimension_limpia}/{variable} - una carpeta POR VARIABLE
# dentro de cada dimension limpia, politica 2026-09-03 a pedido del
# usuario) - se completa a mano la primera vez que cada variable sube algo
# de verdad.
VARIABLE_FOLDER_IDS = {
    ("1_Compromiso_financiero_oficial_limpias", "fa_gov_obligaciones"): "1j4_Go3o8LfjttUV-VtLCiuYhL6nijzb9",
    ("1_Compromiso_financiero_oficial_limpias", "fa_gov_desembolsos"): "1XZh4cR8mNXNuCb70J-NWqUA038_ivlTn",
    ("1_Compromiso_financiero_oficial_limpias", "usaspending_obligaciones"): "11cN6Qhmdmv6OLkSzFFHa3LZwCFi504rL",
    ("1_Compromiso_financiero_oficial_limpias", "dfc_comprometido"): "1gi1QRZcTF71hD54Q2j-L35WLlwnDnrgO",
    ("1_Compromiso_financiero_oficial_limpias", "exim_autorizado"): "1AI277d3J1R-Qxj52S67MZW3qqypwSdfe",
    ("1_Compromiso_financiero_oficial_limpias", "exim_desembolsado"): "17zBu-hQgFEz7lKRdwi4o0gsGjNcqpPQi",
    ("1_Compromiso_financiero_oficial_limpias", "bid_proyectos_aprobados"): "1yrQJ5qp0Ha5_emlQ9XKIzMpH5rqF4MLD",
    ("1_Compromiso_financiero_oficial_limpias", "bancomundial_proyectos_aprobados"): "1vpfBqS9csMIuJn17G_GcaPOQxrKpvkxQ",
    ("2_Actividad_gubernamental_y_diplomatica_limpias", "congreso_proyectos_mencion_paraguay"): "1TDkovCTe7_HfErPbFzkQzl2z2hq66EbY",  # retirada 2026-09-10, ver src/processing/actividad_gubernamental_y_diplomatica.py
    ("2_Actividad_gubernamental_y_diplomatica_limpias", "congreso_proyectos_relevantes_paraguay"): "1hMlEqdFxJFrjWh9dKwgcP1BuNKe3JA3B",
    ("2_Actividad_gubernamental_y_diplomatica_limpias", "congreso_menciones_totales_paraguay"): "1Z_nmQz66XJGVRYrBVzJGZucUb3IHxaGr",
    ("2_Actividad_gubernamental_y_diplomatica_limpias", "ustr_hitos_consejo_comercio_inversion"): "1JGXXrWqPA7gYHzOuhaVcDPnJyFKCj-dx",
    ("2_Actividad_gubernamental_y_diplomatica_limpias", "state_gov_tias_vigentes"): "1JvNvfSbalrOv0TfpxKQbCCn9-jGXR0mW",
    ("3_Compromiso_economico_privado_limpias", "exportaciones"): "1R7RGu_NJ4pzo_0Y56lADLNUn3O6J1KOx",
    ("3_Compromiso_economico_privado_limpias", "importaciones"): "1yyry1LlAUZVSfwXkJ-LjZ8sY4t6hURl0",
    ("3_Compromiso_economico_privado_limpias", "inversion_directa_bcp"): "1HKc9ZONIfM7EMkUjusxVzUtrtg1tLBVk",
    ("3_Compromiso_economico_privado_limpias", "remesas"): "1YXlotyhgt_rbyr5GOp4O1rty8UlJKwYQ",
    ("3_Compromiso_economico_privado_limpias", "bea_inversion_directa"): "1M6IvbQK4ShQwrLQtHyhMAkKCORw95oOC",
    ("4_Visibilidad_mediatica_y_relevancia_publica_limpias", "gdelt_proxy_articles"): "1es-fZCxupBXBkhtL4rg0LIhcdWriforY",
    ("4_Visibilidad_mediatica_y_relevancia_publica_limpias", "gdelt_tone_promedio"): "1YfWSeWAVULcUh9bS1WiYy5rDFH-yu3DI",
    ("4_Visibilidad_mediatica_y_relevancia_publica_limpias", "gdelt_proxy_articles_py"): "1e-0fTbbr3skSOTt2D6x2dMhlSgpXU9KO",
    ("4_Visibilidad_mediatica_y_relevancia_publica_limpias", "gdelt_tone_promedio_py"): "1ksnf--1J-0bGXQOb7SxH9r_-QKkWBA7v",
    ("4_Visibilidad_mediatica_y_relevancia_publica_limpias", "gdelt_proxy_articles_us"): "1PQj2dAUno-c-UbIXf-vMqL5d5Ix1KXZJ",
    ("4_Visibilidad_mediatica_y_relevancia_publica_limpias", "gdelt_tone_promedio_us"): "1WWoWzRRl0gISTUbZPlhhHTMLmtGsYFbY",
}

# Igual que los dos diccionarios de arriba, pero para las carpetas de salida de
# las etapas 03 y 04 (hermanas de 01_crudas/02_limpias dentro de DRIVE_ROOT_ID,
# ids confirmados a mano el 2026-09-10). A diferencia de ingestion y processing,
# estas dos etapas tienen UNA carpeta cada una, no una por fuente/variable.
ETAPA_FOLDER_IDS = {
    CARPETA_INTEGRACION: "1ePuS3VBB3EG36zA00_MS8PnAj5ICD4Ib",
    CARPETA_FINAL: "1BPhoxDLryWrJ4-6Z02H3EtcyaENFaJUe",
}


def _client():
    creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _buscar_hijo(drive, nombre, carpeta_id):
    """Busca un archivo/carpeta por nombre exacto dentro de carpeta_id. None si no existe."""
    nombre_seguro = nombre.replace("'", "\\'")
    resp = (
        drive.files()
        .list(
            q=f"'{carpeta_id}' in parents and name = '{nombre_seguro}' and trashed = false",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    archivos = resp.get("files", [])
    return archivos[0] if archivos else None


def _buscar_hijo_con_reintentos(drive, nombre, carpeta_id, intentos=3, espera_seg=2):
    """Como _buscar_hijo, pero reintenta antes de asumir que no existe (ver
    nota de fiabilidad arriba - la busqueda puede fallar en encontrar algo
    que si existe). Usado donde una busqueda fallida crea una carpeta/sube
    un archivo duplicado, que es lo que se quiere evitar."""
    for intento in range(intentos):
        encontrado = _buscar_hijo(drive, nombre, carpeta_id)
        if encontrado:
            return encontrado
        if intento < intentos - 1:
            time.sleep(espera_seg)
    return None


def resolve_folder(*segmentos):
    """Devuelve el id de DRIVE_ROOT_ID/segmentos[0]/segmentos[1]/..., creando lo que falte.
    Usa reintentos antes de crear un segmento nuevo (ver nota de fiabilidad arriba)."""
    drive = _client()
    carpeta_id = DRIVE_ROOT_ID
    for segmento in segmentos:
        existente = _buscar_hijo_con_reintentos(drive, segmento, carpeta_id)
        if existente:
            carpeta_id = existente["id"]
        else:
            nueva = (
                drive.files()
                .create(
                    body={
                        "name": segmento,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [carpeta_id],
                    },
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )
            carpeta_id = nueva["id"]
    return carpeta_id


def resolve_ingestion_folder(dimension, fuente):
    """Atajo para CARPETA_CRUDAS/{dimension}_crudas/{fuente} - lo que usan
    todos los modulos de src/ingestion/ para saber donde subir sus
    archivos (el sufijo "_crudas" es el nombre REAL de la carpeta en Drive,
    ver la nota del modulo arriba - DIMENSION en cada modulo no lo lleva).
    Usa FOLDER_IDS si ya se conoce el id (evita la busqueda por nombre); si
    es una fuente nueva, cae de vuelta a resolve_folder (busqueda + reintentos)."""
    conocido = FOLDER_IDS.get((dimension, fuente))
    if conocido:
        return conocido
    return resolve_folder(CARPETA_CRUDAS, f"{dimension}_crudas", fuente)


def resolve_variable_folder(dimension_limpia, variable):
    """Atajo para CARPETA_LIMPIAS/{dimension_limpia}/{variable} - una
    carpeta por variable, donde cada modulo de src/processing/ sube el CSV
    de esa variable. Usa VARIABLE_FOLDER_IDS si ya se conoce el id (evita
    la busqueda por nombre); si es una variable nueva, cae de vuelta a
    resolve_folder (busqueda + reintentos)."""
    conocido = VARIABLE_FOLDER_IDS.get((dimension_limpia, variable))
    if conocido:
        return conocido
    return resolve_folder(CARPETA_LIMPIAS, dimension_limpia, variable)


def resolve_etapa_folder(carpeta):
    """Atajo para la carpeta de salida de una etapa posterior a processing
    (CARPETA_INTEGRACION o CARPETA_FINAL, colgando directo de DRIVE_ROOT_ID).
    Usa ETAPA_FOLDER_IDS si ya se conoce el id; si no, cae de vuelta a
    resolve_folder (busqueda + reintentos)."""
    conocido = ETAPA_FOLDER_IDS.get(carpeta)
    if conocido:
        return conocido
    return resolve_folder(carpeta)


def existe_archivo(nombre, carpeta_id):
    """True si ya hay un archivo con ese nombre en esa carpeta de Drive.
    Con reintentos (ver nota de fiabilidad arriba) - una busqueda fallida
    aca sube un archivo duplicado, no solo una carpeta vacia de mas."""
    return _buscar_hijo_con_reintentos(_client(), nombre, carpeta_id) is not None


def listar_archivos(carpeta_id):
    """Lista {id, name} de todos los archivos/carpetas dentro de carpeta_id
    (sin filtrar por tipo). Usado por processing para leer los archivos
    crudos que ingestion ya subio."""
    drive = _client()
    archivos = []
    token = None
    while True:
        resp = (
            drive.files()
            .list(
                q=f"'{carpeta_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name)",
                pageSize=1000,
                pageToken=token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        archivos.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            break
    return archivos


def descargar_archivo(file_id):
    """Descarga el contenido (bytes) de un archivo de Drive por su id."""
    return _client().files().get_media(fileId=file_id, supportsAllDrives=True).execute()


def subir_archivo(contenido, nombre, carpeta_id, mime_type="application/octet-stream"):
    """Sube `contenido` (bytes) como `nombre` dentro de carpeta_id. Devuelve el id creado."""
    drive = _client()
    media = MediaIoBaseUpload(io.BytesIO(contenido), mimetype=mime_type, resumable=False)
    archivo = (
        drive.files()
        .create(
            body={"name": nombre, "parents": [carpeta_id]},
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    return archivo["id"]


def subir_o_reemplazar(contenido, nombre, carpeta_id, mime_type="application/octet-stream"):
    """Como subir_archivo, pero si ya hay un archivo con ese nombre en la
    carpeta REEMPLAZA su contenido (files.update) en vez de crear otro.
    Devuelve el id, que es siempre el mismo entre corridas.

    Es lo contrario del criterio de ingestion/processing (nombre con fecha,
    idempotente por dia, nunca se pisa nada): ahi cada corrida agrega una foto
    mas al historial de una fuente, y aca lo que se publica es el estado
    vigente de una etapa, que otra cosa puede tener enganchado por link. Con un
    nombre fijo, ese link no se rompe nunca; el historial de cada version lo
    guarda igual Drive."""
    drive = _client()
    existente = _buscar_hijo_con_reintentos(drive, nombre, carpeta_id)

    if not existente:
        return subir_archivo(contenido, nombre, carpeta_id, mime_type=mime_type)

    media = MediaIoBaseUpload(io.BytesIO(contenido), mimetype=mime_type, resumable=False)
    archivo = (
        drive.files()
        .update(
            fileId=existente["id"],
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    return archivo["id"]


def resolver_hoja_de_calculo(nombre, carpeta_id):
    """Devuelve el id del Google Sheet `nombre` dentro de carpeta_id, creandolo
    vacio si todavia no existe. Devuelve siempre el mismo id: el archivo no se
    borra ni se recrea nunca, para que lo que este enganchado a ese Sheet (un
    dashboard, por ejemplo) siga apuntando al mismo lado.

    Solo resuelve el archivo - escribir las pestanas es trabajo de
    src/sheets.py (write_dataframe)."""
    drive = _client()
    existente = _buscar_hijo_con_reintentos(drive, nombre, carpeta_id)

    if existente:
        return existente["id"]

    nueva = (
        drive.files()
        .create(
            body={
                "name": nombre,
                "mimeType": MIME_HOJA_DE_CALCULO,
                "parents": [carpeta_id],
            },
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    return nueva["id"]
