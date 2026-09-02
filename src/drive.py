"""Subida de archivos crudos a Google Drive via la cuenta de servicio.

Los modulos de src/ingestion/ NO escriben a disco local: descargan cada
archivo en memoria y lo suben directo a la carpeta de Drive que le
corresponde (dentro de la Unidad compartida del proyecto). Es idempotente:
antes de subir, se revisa si ya existe un archivo con ese nombre en la
carpeta de destino.

DRIVE_ROOT_ID es la carpeta "2.Datos_recolectados" de la Unidad compartida.
La cuenta de servicio tiene rol Writer ahi (puede crear/editar, no puede
borrar - no hace falta para ingestion).

Nota de fiabilidad (2026-09-02): la busqueda por nombre de Drive
(`files.list(q="name = '...'")`) sobre la Unidad compartida no siempre
encuentra carpetas que ya existen - confirmado en la practica: llamadas a
resolve_ingestion_folder() para las mismas 14 fuentes de siempre, sin
ningun cambio de codigo, crearon carpetas duplicadas vacias porque la
busqueda no encontro las carpetas reales (con datos) en varios intentos
seguidos, para las 4 dimensiones. Para no depender de esa busqueda en cada
corrida, FOLDER_IDS de mas abajo cachea los IDs ya confirmados de las
carpetas reales - resolve_ingestion_folder los usa directo, sin buscar.
Para una fuente nueva (todavia sin entrada en FOLDER_IDS), resolve_folder
sigue buscando por nombre como antes, pero ahora con reintentos (ver
_buscar_hijo_con_reintentos) para reducir el riesgo de duplicar; conviene
agregar su ID a FOLDER_IDS a mano despues de la primera corrida exitosa,
para que las corridas siguientes ya no dependan de la busqueda.
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

# IDs de carpeta (dimension, fuente) -> folder_id, confirmados a mano el
# 2026-09-02 (ver nota de fiabilidad arriba). Evitan una busqueda por nombre
# en cada corrida - la fuente de verdad es Drive, esto es solo una cache.
FOLDER_IDS = {
    ("1.Compromiso_financiero_oficial", "fa_gov_asistencia_oficial"): "1xwZrYYSCrW5mnhfeTB3QXDFCn1JUzKB7",
    ("1.Compromiso_financiero_oficial", "usaspending_obligaciones"): "1UkTtUHZppeZ0KojVWzH4gFn-mZYdqbN1",
    ("1.Compromiso_financiero_oficial", "exim_autorizaciones"): "1ufc_mOeVDduU0ZboK0Y2_mI5nYIq9Wh6",
    ("1.Compromiso_financiero_oficial", "dfc_proyectos_activos"): "1jz2hOG81GGOETPX9JPF0G0L0oTTyt7TA",
    ("1.Compromiso_financiero_oficial", "bid_proyectos"): "1Hc0uqRJA3_4BD7EbnaVDA9TbEy7v-Lc_",
    ("1.Compromiso_financiero_oficial", "bancomundial_proyectos"): "1u1eYPMSIHxnySRvK-PEoETIp1rrdJ-bA",
    ("2.Actividad_gubernamental_y_diplomática", "congreso_menciones_paraguay"): "1V0F9qzym6h83FUYQuy_L7vdJYQ_VeYXS",
    ("2.Actividad_gubernamental_y_diplomática", "ustr_consejo_comercio_inversion"): "1URturmvdk_Ki5j_oFRKORHWrNYbqZ0co",
    ("2.Actividad_gubernamental_y_diplomática", "state_gov_tias_paraguay"): "1koUH_-Wsij9fM8VVcMQ0Oh1d1cMRAgxD",
    ("3.Compromiso_economico_privado", "bcp_comercio_exterior"): "1HFeiS2Q2Ezi7tZPWZcQvbdo0dbeWCO4u",
    ("3.Compromiso_economico_privado", "bcp_inversion_directa"): "145-zhp9c3hjQtz4vg5EManKsmpE_8r6D",
    ("3.Compromiso_economico_privado", "bcp_remesas_familiares"): "1Bk0fHMJz5WceE4vMugRThte4xAiW_RBc",
    ("3.Compromiso_economico_privado", "bea_inversion_directa"): "1ZMTwLGpNcROTrUmEVDXkX1g7yYumkwon",
    ("4.Visibilidad_mediática_y_relevancia_publica", "gdelt_proxy_b"): "108u-nqX6hKckFlfv807gZ4p-oHWA-_Ob",
}

# Igual que FOLDER_IDS pero para las carpetas de salida de processing
# (CARPETA_LIMPIAS/{dimension_limpia}) - se completa a mano la primera vez
# que cada dimension corre processing de verdad.
LIMPIAS_FOLDER_IDS = {
    "3.Compromiso_economico_privado_limpias": "17zdZbDYcC0vA7oeDLPBPEuyV_Ul2h_yR",
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
    """Atajo para CARPETA_CRUDAS/{dimension}/{fuente} - lo que usan todos los
    modulos de src/ingestion/ para saber donde subir sus archivos. Usa
    FOLDER_IDS si ya se conoce el id (evita la busqueda por nombre); si es
    una fuente nueva, cae de vuelta a resolve_folder (busqueda + reintentos)."""
    conocido = FOLDER_IDS.get((dimension, fuente))
    if conocido:
        return conocido
    return resolve_folder(CARPETA_CRUDAS, dimension, fuente)


def resolve_processing_folder(dimension_limpia):
    """Atajo para CARPETA_LIMPIAS/{dimension_limpia} - donde los modulos de
    src/processing/ suben sus CSV consolidados. Usa LIMPIAS_FOLDER_IDS si ya
    se conoce el id (evita la busqueda por nombre, ver nota de fiabilidad
    arriba); si es una dimension nueva, cae de vuelta a resolve_folder."""
    conocido = LIMPIAS_FOLDER_IDS.get(dimension_limpia)
    if conocido:
        return conocido
    return resolve_folder(CARPETA_LIMPIAS, dimension_limpia)


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
