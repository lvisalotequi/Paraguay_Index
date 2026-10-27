#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 26/08/2026                                                #
# NOMBRE: fa_gov_asistencia_oficial                                            #
# DETALLE: pide a la API del dashboard de ForeignAssistance.gov las            #
#   actividades de asistencia oficial de EE.UU. a Paraguay (obligaciones y     #
#   desembolsos, por anio fiscal) y sube el JSON crudo a Drive. NO transforma  #
#   nada: aislar la cifra y pasarla a trimestres es trabajo de                 #
#   src/processing/.                                                           #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_financiero_oficial.py                            #
# SALIDA: un JSON por anio y medida (PRY_{medida}_{anio}.json) en              #
#   01_crudas/<dimension>_crudas/fa_gov_asistencia_oficial/                    #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import json
from datetime import datetime, timezone

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_si_cambio
from src.ingestion._bloqueo import comprobar



# Parametros -------------------------------------------------------------------

# La API es la que alimenta el dashboard "By Country" de ForeignAssistance.gov y
# ya viene filtrada a Paraguay por la URL (PAIS): no hace falta bajar el dataset
# global de 3.75 GB, que trae todos los paises.
#
# El sitio paso su API a /api/ el 2026-10-26. La ruta vieja (sin /api) respondio
# 404 en una prueba local y 403 desde los runners de Actions; la nueva devuelve el
# mismo JSON (data + totalCount), verificado con 2024, 2025 y 2026 en las dos
# medidas.
URL_BASE          = "https://foreignassistance.gov/api/country_dashboard/activities"
PAIS              = "PRY"
MEDIDAS           = ["Obligations", "Disbursements"]  # las dos medidas que expone la API
ANIO_MINIMO       = 2015

# Los anios cerrados se piden una sola vez (idempotencia por nombre de archivo).
# Los ultimos ANIOS_A_REFRESCAR (el fiscal en curso y el anterior) se piden SIEMPRE
# y se reemplazan en Drive si cambiaron: ForeignAssistance.gov sigue actualizando
# esos datos durante el anio, y la cuenta de servicio NO puede borrar el archivo
# viejo para destrabarlo (rol Writer), asi que el refresco no puede depender de
# una persona. Subir este numero pide mas anios en cada corrida.
ANIOS_A_REFRESCAR = 2
PAGE_SIZE         = 100  # filas por pagina del endpoint

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "1_Compromiso_financiero_oficial"
FUENTE      = "fa_gov_asistencia_oficial"
DESCRIPCION = "Asistencia oficial de EE.UU. a Paraguay (obligaciones y desembolsos), por año"
URL_FUENTE  = "https://foreignassistance.gov"



# Funciones auxiliares ---------------------------------------------------------


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

        # un 403 trae la URL y cf-mitigated en el mensaje (ver _bloqueo.py)
        comprobar(r)
        data = r.json()
        pagina_filas = data.get("data", [])
        filas.extend(pagina_filas)

        # corta cuando una pagina viene vacia o ya se juntaron todas las filas
        if not pagina_filas or len(filas) >= data.get("totalCount", 0):
            break
        pagina += 1

    return filas



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive de esta fuente y el anio en curso

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    anio_actual = datetime.now(timezone.utc).year

    # 2. recorre cada anio y cada medida, y anota que paso con cada archivo

    nuevos, actualizados, existentes, errores = [], [], [], []
    for anio in range(ANIO_MINIMO, anio_actual + 1):
        refrescar = anio > anio_actual - ANIOS_A_REFRESCAR
        for medida in MEDIDAS:
            nombre = f"{PAIS}_{medida}_{anio}.json"

            # un anio cerrado que ya esta en Drive no se vuelve a pedir
            if not refrescar and existe_archivo(nombre, carpeta_id):
                existentes.append(nombre)
                continue

            # pide las filas y sube el JSON crudo, que se reemplaza solo si cambio
            try:
                filas = _pedir_medida(anio, medida)
                contenido = json.dumps(filas, ensure_ascii=False, indent=2).encode("utf-8")
                resultado = subir_si_cambio(contenido, nombre, carpeta_id, mime_type="application/json")
            except Exception as exc:  # noqa: BLE001
                errores.append((nombre, repr(exc)))
                continue

            if resultado == "nuevo":
                nuevos.append(nombre)
            elif resultado == "actualizado":
                actualizados.append(nombre)
            else:
                existentes.append(nombre)

    # 3. validacion: resumen de la corrida; un archivo fallido corta con error

    print(
        f"[{FUENTE}] {len(nuevos)} nuevos, {len(actualizados)} actualizados, {len(existentes)} sin cambios, "
        f"{len(errores)} errores (Drive: {DIMENSION}/{FUENTE})"
    )
    for nombre, err in errores:
        print(f"    [!] {nombre}: {err}")

    if errores:
        raise RuntimeError(f"{len(errores)} archivos fallaron: {errores}")


if __name__ == "__main__":
    run()
