#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 22/09/2026                                                #
# NOMBRE: ine_poblacion_paraguay                                               #
# DETALLE: descarga el Excel de Estimaciones y Proyecciones de la Poblacion    #
#   1950-2050 (INE, revision 2024) y lo sube tal cual a Drive. Es un insumo    #
#   transversal para expresar variables por habitante. NO filtra ni            #
#   transforma: la fila Total Pais es trabajo de src/processing/. La fuente es #
#   anual.                                                                     #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/insumos_indice.py                                           #
# SALIDA: el Excel del INE con su nombre saneado en                            #
#   insumos_indice_crudas/ine_poblacion_paraguay/                              #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import re
import unicodedata

import requests

from src.drive import resolve_ingestion_folder, subir_si_cambio



# Parametros -------------------------------------------------------------------

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente.
DIMENSION   = "insumos_indice"
FUENTE      = "ine_poblacion_paraguay"
DESCRIPCION = (
    "Población total de Paraguay por año (INE, Estimaciones y Proyecciones 1950-2050) — "
    "insumo para expresar variables por habitante"
)
URL_FUENTE  = "https://www.ine.gov.py/resumen/266/estimaciones-y-proyecciones-de-la-poblacion-nacional-por-sexo-y-edad-1950--2050-revision-2024"

# La fuente es "Estimaciones y Proyecciones de la Poblacion Nacional por Sexo y Edad,
# 1950-2050. Revision 2024" (post-Censo 2022):
# https://www.ine.gov.py/resumen/266/estimaciones-y-proyecciones-de-la-poblacion-nacional-por-sexo-y-edad-1950--2050-revision-2024
# Es un unico Excel con la serie completa (igual que bcp_inversion_directa.py y
# bcp_remesas_familiares.py): no hace falta iterar anios ni parametros.
#
# POR QUE ANUAL Y NO TRIMESTRAL: se investigo (2026-09-22, a pedido del usuario, que
# pidio trimestral "si fuera posible"). El INE, como la mayoria de los institutos de
# estadistica de la region, publica la poblacion como una ESTIMACION o PROYECCION
# demografica "a mitad de anio" (30 de junio), un solo punto por anio: no es un dato
# medido trimestralmente (la poblacion no se censa cada trimestre). No existe una
# version trimestral en la fuente; se usa la anual, repetida en los 4 trimestres
# cuando se consuma (mismo criterio que fa_gov_asistencia_oficial.py y
# bea_inversion_directa.py para otras fuentes de grano anual).
#
# NO ES UNA VARIABLE de ninguna de las 4 dimensiones: es un insumo transversal
# (denominador para expresar variables monetarias "por habitante") que usa la etapa de
# construccion del indice. Por eso vive en la pseudo-dimension insumos_indice (ver
# tambien bls_ipc_eeuu.py, el otro insumo transversal, para el deflactor de precios).
# Ya existia un denominador de poblacion en 04_construccion_indice.qmd via la API del
# Banco Mundial (SP.POP.TOTL); esta fuente es la version oficial paraguaya (INE), pedida
# por el usuario como alternativa o complemento mas autoritativo que la del Banco
# Mundial.
#
# Se sube el Excel completo tal cual: trae ademas estructura por sexo y grupos de edad,
# y otras hojas con componentes demograficos que no se usan hoy pero quedan
# disponibles. La fila "Total Pais" de la hoja "Poblac a mitad de anio 1950-2050" es la
# que se necesita (los nombres reales llevan tilde y enie).
URL_ARCHIVO = (
    "https://www.ine.gov.py/Publicaciones/Biblioteca/documento/266/"
    "Estimaciones y Proyecciones Nacional por año 1950-2050. Revisión 2024.xlsx"
)



# Funciones auxiliares ---------------------------------------------------------


def _sanear_nombre(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^\w\-.]+", "_", texto).strip("_")



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre del archivo (saneado: sin tildes)

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nombre = _sanear_nombre(URL_ARCHIVO.rsplit("/", 1)[-1])

    # 2. descarga el Excel completo, sin filtrar ni transformar

    resp = requests.get(URL_ARCHIVO, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    # 3. sube el archivo; se reemplaza solo si el contenido cambio

    resultado = subir_si_cambio(
        resp.content, nombre, carpeta_id,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # 4. validacion: dice que paso con el archivo

    print(f"[{FUENTE}] '{nombre}': {resultado} (Drive: {DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
