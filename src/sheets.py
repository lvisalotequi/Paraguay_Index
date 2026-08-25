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


def _spreadsheet():
    sheet_id = os.environ["SHEET_ID"]
    return _client().open_by_key(sheet_id)


def write_dataframe(tab_name, df):
    """Sobreescribe (o crea) una pestana con el contenido de un DataFrame."""
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=1, cols=max(len(df.columns), 1))
    ws.clear()
    rows = df.astype(object).where(df.notna(), "").values.tolist()
    ws.update([df.columns.tolist()] + rows)


def append_log_row(started, finished, modules_run, errors):
    """Agrega una fila a la pestana 'pipeline_log', creandola si no existe."""
    sh = _spreadsheet()
    try:
        ws = sh.worksheet("pipeline_log")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="pipeline_log", rows=1, cols=5)
        ws.append_row(["started_utc", "finished_utc", "modules_run", "errors", "status"])

    status = "OK" if not errors else "ERROR"
    ws.append_row([
        started.isoformat(),
        finished.isoformat(),
        ", ".join(modules_run) or "(ninguno)",
        str(errors) if errors else "",
        status,
    ])
