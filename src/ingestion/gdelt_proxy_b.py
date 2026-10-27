#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 01/09/2026                                                #
# NOMBRE: gdelt_proxy_b                                                        #
# DETALLE: deduce que meses faltan en Drive y los extrae de GDELT 2.1 GKG      #
#   (BigQuery, regla proxy B) con la cuenta de servicio, respetando los topes  #
#   de consumo y registrando cada consulta en gdelt_registro. NO agrega ni     #
#   limpia: sumar articulos y promediar el tono por trimestre es trabajo de    #
#   src/processing/.                                                           #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/visibilidad_mediatica_y_relevancia_publica.py               #
# SALIDA: un monthly_AAAA-MM_AAAA-MM.csv por mes en                            #
#   01_crudas/<dimension>_crudas/gdelt_proxy_b/                                #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
from pathlib import Path

from src.drive import existe_archivo, listar_archivos, resolve_ingestion_folder, subir_archivo
from src.ingestion import _gdelt_auto



# Parametros -------------------------------------------------------------------

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "4_Visibilidad_mediatica_y_relevancia_publica"
FUENTE      = "gdelt_proxy_b"
DESCRIPCION = (
    "Cobertura mediática bilateral Paraguay-EE.UU. vía GDELT (regla proxy B) — "
    "extrae con la cuenta de servicio los meses que faltan en Drive"
)
URL_FUENTE  = "https://www.gdeltproject.org"

# La fuente es GDELT 2.1 GKG en BigQuery, filtrado por coocurrencia geografica PY-US
# y senales tematicas (regla "proxy B", version aceptada el 2026-08-27; ver
# gdelt_extraction/proxy_b_config.json).
#
# COMO FUNCIONA (cambio de la rama Pruebas-de-ajuste, 2026-10-23): antes este modulo
# NO extraia nada, solo subia los CSV que la extraccion manual de gdelt_extraction/
# ya habia dejado en una carpeta local, y esa extraccion necesitaba un login personal
# de gcloud, asi que en GitHub Actions no hacia nada. Ahora, en cada corrida:
#
#   1. Si existe la carpeta local de la extraccion manual
#      (gdelt_extraction/output/.../proxy_b_metrics), sube sus CSV como siempre
#      (sirve para recargas historicas o para quien extraiga a mano).
#   2. Deduce que meses faltan mirando los monthly_*.csv que ya estan en Drive y
#      extrae los que falten con la CUENTA DE SERVICIO (ver _gdelt_auto.py): mismo
#      SQL, mismos topes de consumo, registro de cada consulta en la pestana
#      gdelt_registro del Sheet de auditoria y verificacion de que el proyecto siga
#      sin facturacion. No hay nada local: corre igual en Actions.
#
# Si no hay meses pendientes no consulta BigQuery ni exige credenciales de BigQuery.
# Si hay pendientes y no puede verificar la facturacion, lanza un error que explica
# que falta configurar en Google Cloud (ver _gdelt_auto.py).
REPO_ROOT        = Path(__file__).resolve().parents[2]
LOCAL_OUTPUT_DIR = REPO_ROOT / "gdelt_extraction" / "output" / "historical_rule_b" / "proxy_b_metrics"



# Funciones auxiliares ---------------------------------------------------------


def _archivos_a_subir(carpeta_local):
    nombres = sorted(p.name for p in carpeta_local.glob("monthly_*.csv"))
    nombres += sorted(p.name for p in carpeta_local.glob("historical_processed_*.csv"))
    return [carpeta_local / nombre for nombre in nombres]


def _subir_extraccion_local(carpeta_id):
    """Sube lo que dejo la extraccion manual, si existe en esta maquina."""
    if not LOCAL_OUTPUT_DIR.is_dir():
        return 0, 0

    nuevos, existentes = [], []
    for path in _archivos_a_subir(LOCAL_OUTPUT_DIR):

        # un archivo que ya esta en Drive no se vuelve a subir
        if existe_archivo(path.name, carpeta_id):
            existentes.append(path.name)
            continue
        subir_archivo(path.read_bytes(), path.name, carpeta_id, mime_type="text/csv")
        nuevos.append(path.name)

    print(
        f"[{FUENTE}] extraccion local: {len(nuevos)} nuevos, {len(existentes)} ya existian "
        f"(Drive: {DIMENSION}/{FUENTE})"
    )
    return len(nuevos), len(existentes)



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y sube lo que haya de una extraccion manual local

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)

    _subir_extraccion_local(carpeta_id)

    # 2. lista lo que ya esta en Drive: de ahi se deduce que meses faltan

    nombres = [a["name"] for a in listar_archivos(carpeta_id)]

    def subir(nombre, contenido):
        subir_archivo(contenido, nombre, carpeta_id, mime_type="text/csv")

    # 3. extrae con la cuenta de servicio los meses que faltan (ver _gdelt_auto.py)

    subidos, pendientes = _gdelt_auto.actualizar(subir, nombres)

    # 4. validacion: dice que se subio; si un tope dejo meses pendientes, queda omitido

    if subidos:
        print(f"[{FUENTE}] {len(subidos)} meses extraidos y subidos: {subidos}")
    if pendientes:
        return (
            f"omitido: quedan {len(pendientes)} meses pendientes por tope de consumo "
            f"({pendientes[0]} a {pendientes[-1]})"
        )


if __name__ == "__main__":
    run()
