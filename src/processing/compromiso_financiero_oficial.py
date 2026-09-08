"""
Limpieza/consolidacion de la dimension 1 (Compromiso financiero oficial) en
un CSV trimestral por variable, en USD sin escalar (mismo patron y misma
politica de unidades/salida que src/processing/compromiso_economico_privado.py
y src/processing/_common.py - ver esos modulos para el detalle de la
convencion general: una carpeta por variable, esquema fijo trimestre/anio/
trimestre_num/valor/unidad).

Fuentes y como se tratan (confirmado con datos reales el 2026-09-03):
    - fa_gov_asistencia_oficial (un JSON por año+medida, ya filtrado a
      Paraguay): se suma `current_amount` de todas las actividades de cada
      año, por separado para Obligations y Disbursements. La fuente no
      tiene fecha mas fina que el año fiscal (`fiscal_year`) - el mismo
      total anual se repite en los 4 trimestres de ese año, igual que
      bea_inversion_directa en la dimension 3.
    - usaspending_obligaciones (un ZIP por año, con 4 CSV adentro): se usan
      los dos CSV "PrimeTransactions" (Contracts y Assistance - las
      transacciones en si, no los subawards), sumando
      `federal_action_obligation` por trimestre segun `action_date`. A
      diferencia de fa_gov, esta SI tiene fecha de transaccion real -
      trimestral autentico.
    - dfc_proyectos_activos (Excel unico, todos los paises, hoja
      "Project Data"): se filtra a `Country == "Paraguay"` y se suma
      `Committed` por `Fiscal Year`. Muy pocos proyectos en total (~4
      historicos) - sin fecha mas fina que el año, se repite en los 4
      trimestres como fa_gov.
    - exim_autorizaciones (CSV unico, ya filtrado a Paraguay): se filtra a
      `Decision == "Approved"` (se excluyen autorizaciones declinadas) y se
      suma `Approved/Declined Amount` por trimestre segun `Decision Date`.
      Trimestral autentico.
    - bid_proyectos / bancomundial_proyectos (JSON diario, ya filtrado a
      Paraguay - se usa el archivo mas reciente subido por ingestion): se
      suma el monto aprobado de cada proyecto por trimestre segun su fecha
      de aprobacion (`apprvl_dt` en BID, `boardapprovaldate` en Banco
      Mundial). **Es el monto total aprobado del proyecto, NO ponderado
      por la cuota de capital de EE.UU. en cada banco** - ese calculo
      queda pendiente (ver CLAUDE.md seccion 7), esta columna es un
      proxy de "actividad multilateral" en general, no una cifra
      atribuible a EE.UU. todavia.

Rango: ANIO_MINIMO en adelante. Cada variable se sube por separado, con la
fecha de la corrida en el nombre (idempotente por dia) - no escribe nada a
disco local.
"""
import io
import json
import zipfile

import pandas as pd

from src.drive import FOLDER_IDS, descargar_archivo, listar_archivos
from src.processing._common import subir_variable

DIMENSION_CRUDA = "1_Compromiso_financiero_oficial"
DIMENSION_LIMPIA = "1_Compromiso_financiero_oficial_limpias"

ANIO_MINIMO = 2015


def _archivos(fuente):
    return listar_archivos(FOLDER_IDS[(DIMENSION_CRUDA, fuente)])


def _sumar_por_trimestre(fechas, montos):
    """A partir de dos Series alineadas (fecha, monto), devuelve
    {(anio,trim): suma} - fechas invalidas/faltantes o < ANIO_MINIMO se
    ignoran, montos no numericos tambien."""
    fechas = pd.to_datetime(fechas, errors="coerce")
    montos = pd.to_numeric(montos, errors="coerce")
    df = pd.DataFrame({"fecha": fechas, "monto": montos}).dropna()
    df = df[df["fecha"].dt.year >= ANIO_MINIMO]

    acumulado = {}
    for fecha, monto in zip(df["fecha"], df["monto"]):
        clave = (fecha.year, (fecha.month - 1) // 3 + 1)
        acumulado[clave] = acumulado.get(clave, 0.0) + float(monto)
    return acumulado


def _repetir_en_trimestres(valores_por_anio):
    """{anio: valor} -> {(anio,trim): valor} repitiendo el mismo valor en
    los 4 trimestres (para fuentes sin fecha mas fina que el año)."""
    return {(anio, trim): valor for anio, valor in valores_por_anio.items() for trim in (1, 2, 3, 4)}


def _extraer_fa_gov():
    """Devuelve (obligaciones, desembolsos), cada una {(anio,trim): usd}
    repitiendo el total anual en los 4 trimestres (ver docstring)."""
    archivos = _archivos("fa_gov_asistencia_oficial")
    totales = {"Obligations": {}, "Disbursements": {}}

    for archivo in archivos:
        # nombre: "PRY_{medida}_{anio}.json"
        partes = archivo["name"].removesuffix(".json").split("_")
        medida, anio = partes[1], int(partes[2])
        if anio < ANIO_MINIMO or medida not in totales:
            continue
        filas = json.loads(descargar_archivo(archivo["id"]))
        totales[medida][anio] = sum(f.get("current_amount") or 0 for f in filas)

    return _repetir_en_trimestres(totales["Obligations"]), _repetir_en_trimestres(totales["Disbursements"])


def _extraer_usaspending():
    """Devuelve {(anio,trim): usd} sumando `federal_action_obligation` de
    las transacciones (Contracts + Assistance) por trimestre de `action_date`."""
    acumulado = {}
    for archivo in _archivos("usaspending_obligaciones"):
        contenido = descargar_archivo(archivo["id"])
        z = zipfile.ZipFile(io.BytesIO(contenido))
        for nombre in z.namelist():
            if "PrimeTransactions" not in nombre:
                continue
            df = pd.read_csv(z.open(nombre), usecols=["action_date", "federal_action_obligation"])
            parcial = _sumar_por_trimestre(df["action_date"], df["federal_action_obligation"])
            for clave, valor in parcial.items():
                acumulado[clave] = acumulado.get(clave, 0.0) + valor
    return acumulado


def _extraer_dfc():
    """Devuelve {(anio,trim): usd} sumando `Committed` de proyectos de
    Paraguay por `Fiscal Year`, repitiendo el total en los 4 trimestres
    (ver docstring - muy pocos proyectos, sin fecha mas fina que el año)."""
    _, contenido = _archivo_mas_reciente_por_nombre("dfc_proyectos_activos")
    df = pd.read_excel(io.BytesIO(contenido), sheet_name="Project Data", header=1)
    py = df[df["Country"] == "Paraguay"]
    por_anio = py.groupby("Fiscal Year")["Committed"].sum()
    por_anio = por_anio[por_anio.index >= ANIO_MINIMO]
    return _repetir_en_trimestres(por_anio.to_dict())


def _extraer_exim():
    """Devuelve {(anio,trim): usd} sumando `Approved/Declined Amount` de
    autorizaciones con `Decision == "Approved"`, por trimestre de
    `Decision Date`."""
    _, contenido = _archivo_mas_reciente_por_nombre("exim_autorizaciones")
    df = pd.read_csv(io.BytesIO(contenido))
    aprobadas = df[df["Decision"] == "Approved"]
    return _sumar_por_trimestre(aprobadas["Decision Date"], aprobadas["Approved/Declined Amount"])


def _extraer_bid():
    """Devuelve {(anio,trim): usd} sumando el monto originalmente aprobado
    de cada proyecto (`orig_apprvd_useq_amnt`) por trimestre de `apprvl_dt`.
    NO esta ponderado por la cuota de capital de EE.UU. (ver docstring)."""
    _, contenido = _archivo_mas_reciente_por_nombre("bid_proyectos")
    registros = json.loads(contenido)["records"]
    df = pd.DataFrame(registros)
    return _sumar_por_trimestre(df["apprvl_dt"], df["orig_apprvd_useq_amnt"])


def _extraer_bancomundial():
    """Devuelve {(anio,trim): usd} sumando el monto total del proyecto
    (`totalamt`) por trimestre de `boardapprovaldate`. NO esta ponderado
    por la cuota de capital de EE.UU. (ver docstring)."""
    _, contenido = _archivo_mas_reciente_por_nombre("bancomundial_proyectos")
    proyectos = json.loads(contenido)["projects"].values()
    df = pd.DataFrame(proyectos)
    return _sumar_por_trimestre(df["boardapprovaldate"], df["totalamt"])


def _archivo_mas_reciente_por_nombre(fuente):
    archivos = _archivos(fuente)
    archivo = sorted(archivos, key=lambda a: a["name"])[-1]
    return archivo["name"], descargar_archivo(archivo["id"])


def run():
    print(f"[{DIMENSION_LIMPIA}]")
    fuentes = []

    try:
        obligaciones_fa, desembolsos_fa = _extraer_fa_gov()
        fuentes.append(("fa_gov_obligaciones", obligaciones_fa))
        fuentes.append(("fa_gov_desembolsos", desembolsos_fa))
    except Exception as exc:  # noqa: BLE001
        print(f"    [!] fa_gov_asistencia_oficial: {exc!r}")

    for nombre_variable, extraer in (
        ("usaspending_obligaciones", _extraer_usaspending),
        ("dfc_comprometido", _extraer_dfc),
        ("exim_autorizado", _extraer_exim),
        ("bid_proyectos_aprobados", _extraer_bid),
        ("bancomundial_proyectos_aprobados", _extraer_bancomundial),
    ):
        try:
            fuentes.append((nombre_variable, extraer()))
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] {nombre_variable}: {exc!r}")

    # todas estas fuentes ya vienen nativamente en USD (no miles/millones),
    # a diferencia de la dimension 3 - no hace falta reescalar
    for nombre_variable, valores in fuentes:
        subir_variable(DIMENSION_LIMPIA, nombre_variable, valores, "USD")


if __name__ == "__main__":
    run()
