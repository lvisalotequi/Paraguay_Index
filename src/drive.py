"""Subida de archivos crudos a Google Drive via la cuenta de servicio.

Los modulos de src/ingestion/ NO escriben a disco local: descargan cada
archivo en memoria y lo suben directo a la carpeta de Drive que le
corresponde (dentro de la Unidad compartida del proyecto). Es idempotente:
antes de subir, se revisa si ya existe un archivo con ese nombre en la
carpeta de destino.

DRIVE_ROOT_ID es la carpeta "2.Datos_recolectados" de la Unidad compartida.
La cuenta de servicio tiene rol Writer ahi (puede crear/editar, no puede
borrar - no hace falta para ingestion).
"""
import io
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

DRIVE_ROOT_ID = "1iFJsRRCMSa7u4-GpYNbl7BE2HnvDGxrL"  # carpeta "2.Datos_recolectados"
CARPETA_CRUDAS = "01_crudas"  # subcarpeta donde va todo lo que sube ingestion


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


def resolve_folder(*segmentos):
    """Devuelve el id de DRIVE_ROOT_ID/segmentos[0]/segmentos[1]/..., creando lo que falte."""
    drive = _client()
    carpeta_id = DRIVE_ROOT_ID
    for segmento in segmentos:
        existente = _buscar_hijo(drive, segmento, carpeta_id)
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
    modulos de src/ingestion/ para saber donde subir sus archivos."""
    return resolve_folder(CARPETA_CRUDAS, dimension, fuente)


def existe_archivo(nombre, carpeta_id):
    """True si ya hay un archivo con ese nombre en esa carpeta de Drive."""
    return _buscar_hijo(_client(), nombre, carpeta_id) is not None


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
