"""
Cuota de poder de voto de EE.UU. en el IBRD (Banco Mundial), por año fiscal
International Bank for Reconstruction and Development (IBRD)

Fuente: "Information Statement" anual del IBRD (informe oficial para
inversores en sus bonos, publicado poco despues del cierre de cada año
fiscal - 30 de junio). Cada edicion trae una tabla "Subscriptions and
Voting Power of Member Countries" con el % de EE.UU. Se busca en
thedocs.worldbank.org - a diferencia del BID, esta fuente SI se puede
descargar con un `requests.get()` normal, sin Cloudflare ni Power BI de
por medio.

**Por que un historico fijo en vez de un scraper (2026-09-22, a pedido
del usuario - "no complicar tanto el scrapeo... una opcion para que la
persona sepa donde mapear la modificacion"):** cada edicion vive en una
URL con un hash que no sigue un patron predecible (ej.
".../f3508084cc8eae0e08c432b2427b6946-0340022022/original/IBRD-Information-Statement-FY22.pdf")
- no hay una pagina indice con el listado de todas las ediciones, hay que
buscar cada año a mano. A diferencia del BID (cuota constante desde 2010),
acá el % SI cambia año a año de verdad (confirmado 2026-09-22: entre
15,49% y 16,63% segun el año, sin patron simple) asi que hace falta la
serie completa - pero automatizar la busqueda de una URL nueva cada año
no es practico con los mismos metodos que el resto de src/ingestion/
(requeriria un buscador o una IA, no un scraper de una pagina fija). Se
opta por un historico fijo, editado a mano cuando salga la edicion de un
año nuevo (julio/agosto, despues del cierre de año fiscal del 30 de
junio) - ver "COMO AGREGAR UN AÑO NUEVO" mas abajo.

Años sin dato todavia (2026-09-22): FY2015, FY2017, FY2020, FY2021,
FY2026. `src/processing/compromiso_financiero_oficial.py` arrastra el
ultimo valor confirmado hacia adelante para esos huecos (mismo criterio
que ya usa el proyecto para otras fuentes anuales) - no son ceros ni
faltantes reales, son años donde el dato exacto todavia no se busco.

======================== COMO AGREGAR UN AÑO NUEVO =========================
1. Buscar en Google: "IBRD Information Statement FY{año}" (ej. "IBRD
   Information Statement FY26"). El resultado suele ser un PDF en
   thedocs.worldbank.org, nombrado algo como
   "IBRD-Information-Statement-FY{año}.pdf". Tambien puede aparecer en
   https://treasury.worldbank.org/en/about/unit/treasury/ibrd/ibrd-financials-and-ratings
   (esa pagina solo linkea la edicion MAS RECIENTE, no el historico).
2. Abrir el PDF y buscar (Ctrl+F) el texto "largest shareholder" - va a
   aparecer una oracion tipo "The United States is IBRD's largest
   shareholder, with XX.XX% of total voting power." Ese numero (el de la
   ORACION, no el de la tabla resumida que a veces redondea a un entero)
   es el que va en `HISTORICO`.
3. Agregar una fila nueva a la lista `HISTORICO` de abajo, con el año
   fiscal (entero), el porcentaje, la fecha de cierre de ese año fiscal
   (siempre 30 de junio), y la URL exacta del PDF usado.
4. Correr este modulo (`python -m src.ingestion.cuota_capital_bancomundial`)
   para subir la fila nueva a Drive.
==============================================================================
"""
import pandas as pd

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

DIMENSION = "1_Compromiso_financiero_oficial"
FUENTE = "cuota_capital_bancomundial"
DESCRIPCION = "Cuota de poder de voto de EE.UU. en el IBRD (Banco Mundial) por año fiscal, para ponderar bancomundial_proyectos_aprobados"
URL_FUENTE = "https://treasury.worldbank.org/en/about/unit/treasury/ibrd/ibrd-financials-and-ratings"

INSTITUCION = "Banco Mundial (IBRD)"
PAIS = "Estados Unidos"

# Verificado a mano, uno por uno, contra el "Information Statement" oficial
# de cada año fiscal (ver "COMO AGREGAR UN AÑO NUEVO" arriba). NO son
# valores estimados ni interpolados - cada fila viene de abrir el PDF y
# leer la oracion "The United States is IBRD's largest shareholder, with
# XX.XX% of total voting power."
HISTORICO = [
    {
        "anio_fiscal": 2016, "porcentaje_voto": 16.63, "cierre_anio_fiscal": "2016-06-30",
        "url_fuente": "http://documents.worldbank.org/curated/en/106321475287278758/pdf/FY16-IBRD-Information-Statement-09222016.pdf",
    },
    {
        "anio_fiscal": 2018, "porcentaje_voto": 15.98, "cierre_anio_fiscal": "2018-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/571971537558659917-0340022018/render/IBRDInformationStatementFY18Final.pdf",
    },
    {
        "anio_fiscal": 2019, "porcentaje_voto": 15.68, "cierre_anio_fiscal": "2019-06-30",
        "url_fuente": "http://pubdocs.worldbank.org/en/767901569597693292/IBRD-Information-Statement-2019.pdf",
    },
    {
        "anio_fiscal": 2022, "porcentaje_voto": 15.79, "cierre_anio_fiscal": "2022-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/f3508084cc8eae0e08c432b2427b6946-0340022022/original/IBRD-Information-Statement-FY22.pdf",
    },
    {
        "anio_fiscal": 2023, "porcentaje_voto": 15.75, "cierre_anio_fiscal": "2023-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/e384d12cfea59bdcb3adf25487894197-0340022023/original/IBRD-Information-Statement-FY23.pdf",
    },
    {
        "anio_fiscal": 2024, "porcentaje_voto": 15.49, "cierre_anio_fiscal": "2024-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/515cd9fcae37dad3185833617c3cf2b8-0340022024/original/IBRD-Information-Statement-FY24.pdf",
    },
    {
        "anio_fiscal": 2025, "porcentaje_voto": 15.79, "cierre_anio_fiscal": "2025-06-30",
        "url_fuente": "https://thedocs.worldbank.org/en/doc/02acefd82f121687f3aa3b429ee50801-0340022025/original/IBRD-Information-Statement-FY25.pdf",
    },
]
FECHA_VERIFICACION = "2026-09-22"  # fecha en que se armo/reviso esta lista completa


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nombre = f"cuota_capital_bancomundial_verificado_{FECHA_VERIFICACION}.csv"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    df = pd.DataFrame(HISTORICO)
    df.insert(0, "institucion", INSTITUCION)
    df.insert(1, "pais", PAIS)
    df["fecha_verificacion"] = FECHA_VERIFICACION

    contenido = df.to_csv(index=False).encode("utf-8-sig")
    subir_archivo(contenido, nombre, carpeta_id, mime_type="text/csv")
    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - {len(HISTORICO)} años fiscales.")


if __name__ == "__main__":
    run()
