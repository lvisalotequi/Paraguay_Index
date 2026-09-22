"""
Poblacion total de Paraguay por año (insumo para variables per capita)
Instituto Nacional de Estadistica de Paraguay (INE)

Fuente: "Estimaciones y Proyecciones de la Población Nacional por Sexo y
Edad, 1950-2050. Revisión 2024" (post-Censo 2022) -
https://www.ine.gov.py/resumen/266/estimaciones-y-proyecciones-de-la-poblacion-nacional-por-sexo-y-edad-1950--2050-revision-2024
Un unico Excel con la serie completa (igual que bcp_inversion_directa.py/
bcp_remesas_familiares.py) - no hace falta iterar años ni parametros.

**Por que anual y no trimestral**: se investigo (2026-09-22, a pedido del
usuario, que pidio trimestral "si fuera posible") - el INE, como la mayoria
de los institutos de estadistica de la region, publica la poblacion como
una ESTIMACION/PROYECCION demografica "a mitad de año" (30 de junio), un
solo punto por año - no es un dato medido trimestralmente (la poblacion no
se censa cada trimestre). No existe una version trimestral en la fuente;
se usa la anual, repetida en los 4 trimestres cuando se consuma (mismo
criterio que fa_gov_asistencia_oficial.py y bea_inversion_directa.py para
otras fuentes de grano anual).

**No es una variable de ninguna de las 4 dimensiones**: es un insumo
transversal (denominador para expresar variables monetarias "por
habitante") que usa la etapa de construccion del indice - por eso vive en
la pseudo-dimension `insumos_indice`, no en ninguna de las 4 reales (ver
tambien bls_ipc_eeuu.py, el otro insumo transversal, para el deflactor de
precios). Ya existia un denominador de poblacion en
`04_construccion_indice.qmd` via la API del Banco Mundial (`SP.POP.TOTL`) -
esta fuente es la version oficial paraguaya (INE), pedida por el usuario
como alternativa/complemento mas autoritativa que la del Banco Mundial.

Se sube el Excel completo tal cual (trae ademas estructura por sexo y
grupos de edad, y otras hojas con componentes demograficos que no se usan
hoy pero quedan disponibles) - la fila "Total País" de la hoja "Poblac a
mitad de año 1950-2050" es la que se necesita.
"""
import re
import unicodedata

import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

DIMENSION = "insumos_indice"
FUENTE = "ine_poblacion_paraguay"
DESCRIPCION = "Población total de Paraguay por año (INE, Estimaciones y Proyecciones 1950-2050) — insumo para expresar variables por habitante"
URL_FUENTE = "https://www.ine.gov.py/resumen/266/estimaciones-y-proyecciones-de-la-poblacion-nacional-por-sexo-y-edad-1950--2050-revision-2024"

URL_ARCHIVO = (
    "https://www.ine.gov.py/Publicaciones/Biblioteca/documento/266/"
    "Estimaciones y Proyecciones Nacional por año 1950-2050. Revisión 2024.xlsx"
)


def _sanear_nombre(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^\w\-.]+", "_", texto).strip("_")


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nombre = _sanear_nombre(URL_ARCHIVO.rsplit("/", 1)[-1])

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    resp = requests.get(URL_ARCHIVO, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    subir_archivo(
        resp.content, nombre, carpeta_id,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}).")


if __name__ == "__main__":
    run()
