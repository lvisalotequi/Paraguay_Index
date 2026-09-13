"""Escritura de resultados del pipeline en Google Sheets via cuenta de servicio."""
import os

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _client():
    creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


def _spreadsheet(spreadsheet_id=None):
    """Por defecto abre el Sheet de auditoria (SHEET_ID, el de pipeline_log /
    catalogo_fuentes). spreadsheet_id permite apuntar a otro archivo - lo usa
    la etapa 04, que publica su resultado en un Sheet propio dentro de
    04_final (ver src/drive.py, resolver_hoja_de_calculo)."""
    sheet_id = spreadsheet_id or os.environ["SHEET_ID"]
    return _client().open_by_key(sheet_id)


def write_dataframe(tab_name, df, spreadsheet_id=None):
    """Sobreescribe (o crea) una pestana con el contenido de un DataFrame.

    Toca SOLO el contenido de esa pestana: no borra ni recrea el archivo, no
    toca las demas pestanas, y no achica la grilla. Es lo que permite que un
    dashboard enganchado a este Sheet no se rompa en cada corrida del
    pipeline."""
    sh = _spreadsheet(spreadsheet_id)
    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=1, cols=max(len(df.columns), 1))
    ws.clear()
    rows = df.astype(object).where(df.notna(), "").values.tolist()

    # la grilla por defecto de una pestana nueva son 1000 filas x 26 columnas:
    # si el DataFrame es mas grande, update() falla por "exceeds grid limits".
    # Solo se agranda, nunca se achica (achicar borraria lo que alguien haya
    # dejado a la derecha o abajo de los datos)
    filas_necesarias = len(rows) + 1
    columnas_necesarias = max(len(df.columns), 1)

    if ws.row_count < filas_necesarias or ws.col_count < columnas_necesarias:
        ws.resize(
            rows=max(ws.row_count, filas_necesarias),
            cols=max(ws.col_count, columnas_necesarias),
        )

    ws.update([df.columns.tolist()] + rows)


def append_log_row(started, finished, modules_run, errors, tab_name="pipeline_log"):
    """Agrega una fila a la pestana de log (por defecto 'pipeline_log',
    creandola si no existe). run_processing.py usa tab_name='processing_log'
    para no mezclar sus corridas con las de ingestion en la misma pestana."""
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=1, cols=5)
        ws.append_row(["started_utc", "finished_utc", "modules_run", "errors", "status"])

    status = "OK" if not errors else "ERROR"
    ws.append_row([
        started.isoformat(),
        finished.isoformat(),
        ", ".join(modules_run) or "(ninguno)",
        str(errors) if errors else "",
        status,
    ])
