"""
Extraccion de Asistencia Oficial de EE.UU. a Paraguay
ForeignAssistance.gov (Departamento de Estado / USAID)

Fuente: https://foreignassistance.gov (API que alimenta el dashboard "By Country")

Que hace: para cada anio desde ANIO_MINIMO hasta el actual, y para las dos
medidas que expone la API (Obligations y Disbursements), pagina el endpoint
country_dashboard/activities/PRY/0/{anio}/{medida} -ya filtrado a Paraguay
por la propia API, no hace falta bajar el dataset global (3.75 GB, todos
los paises)- y sube el JSON crudo consolidado a Drive. No lo transforma.

Es idempotente por anio+medida: una vez subido un anio, no se vuelve a
pedir. Ojo: el anio fiscal en curso queda "congelado" en el valor que tenia
al momento de la primera corrida - ForeignAssistance.gov sigue actualizando
esos datos durante el anio. Si hace falta refrescarlo, borrar el archivo de
ese anio en Drive y volver a correr el pipeline.
"""
import json
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

URL_BASE = "https://foreignassistance.gov/country_dashboard/activities"
PAIS = "PRY"
MEDIDAS = ["Obligations", "Disbursements"]
ANIO_MINIMO = 2015
PAGE_SIZE = 100

DIMENSION = "1.Compromiso_financiero_oficial"
FUENTE = "fa_gov_asistencia_oficial"
DESCRIPCION = "Asistencia oficial de EE.UU. a Paraguay (obligaciones y desembolsos), por año"
URL_FUENTE = "https://foreignassistance.gov"


def _pedir_medida(anio, medida):
    """Pagina el endpoint hasta traer todas las filas de un anio+medida (ya filtradas a Paraguay)."""
    filas = []
    pagina = 1
    while True:
        r = requests.get(
            f"{URL_BASE}/{PAIS}/0/{anio}/{medida}",
            params={"page": pagina, "pageSize": PAGE_SIZE},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        pagina_filas = data.get("data", [])
        filas.extend(pagina_filas)

        if not pagina_filas or len(filas) >= data.get("totalCount", 0):
            break
        pagina += 1

    return filas


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    anio_actual = datetime.now(timezone.utc).year

    nuevos, existentes, errores = [], [], []
    for anio in range(ANIO_MINIMO, anio_actual + 1):
        for medida in MEDIDAS:
            nombre = f"{PAIS}_{medida}_{anio}.json"
            if existe_archivo(nombre, carpeta_id):
                existentes.append(nombre)
                continue

            try:
                filas = _pedir_medida(anio, medida)
            except Exception as exc:  # noqa: BLE001
                errores.append((nombre, repr(exc)))
                continue

            contenido = json.dumps(filas, ensure_ascii=False, indent=2).encode("utf-8")
            subir_archivo(contenido, nombre, carpeta_id, mime_type="application/json")
            nuevos.append(nombre)

    print(
        f"[{FUENTE}] {len(nuevos)} nuevos, {len(existentes)} ya existian, "
        f"{len(errores)} errores (Drive: {DIMENSION}/{FUENTE})"
    )
    for nombre, err in errores:
        print(f"    [!] {nombre}: {err}")

    if errores and not nuevos and not existentes:
        raise RuntimeError(f"No se pudo subir ningun archivo: {errores}")


if __name__ == "__main__":
    run()
