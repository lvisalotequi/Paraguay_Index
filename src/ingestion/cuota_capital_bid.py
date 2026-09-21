"""
Cuota de capital / poder de voto de EE.UU. en el BID
Inter-American Development Bank (IDB/BID)

Fuente: https://www.iadb.org/en/who-we-are/how-we-are-organized/board-governors/capital-stock-and-voting-power
("Capital Stock And Voting Power", pagina oficial del BID).

Para que sirve: es el insumo para ponderar `bid_proyectos_aprobados` por la
porcion atribuible a EE.UU. (pendiente historico del proyecto, ver
CLAUDE.md seccion 7, punto 4 - "Desembolsos de BID/Banco Mundial
ponderados por cuota de capital de EE.UU."). La logica (a pedido del
usuario, 2026-09-21): el dinero que el BID le presta a Paraguay sale del
capital general del banco, no de un fondo exclusivo de EE.UU., asi que la
porcion "atribuible" a EE.UU. se aproxima como
`monto_a_paraguay x cuota_de_capital_eeuu` - mismo principio que usa la
OCDE/DAC para su estadistica de "imputed multilateral ODA".

**Por que esto NO se scrapea en vivo, a diferencia del resto de
src/ingestion/ (excepcion documentada, 2026-09-21):** la pagina oficial de
arriba no tiene la tabla en HTML - la renderiza un widget de Power BI
embebido (confirmado inspeccionando la pagina con un navegador real: carga
`idb_powerbi-embed.js` y un iframe de `app.powerbi.com` con token de sesion).
No hay HTML ni JSON estatico que `requests`/`curl_cffi` puedan leer, y
automatizar esto en serio exigiria un navegador headless (Playwright/
Selenium) - una dependencia que el proyecto no usa en ningun otro lado, para
un dato que casi no cambia (ver mas abajo). Se decidio no agregarla.

**Por que un valor fijo es razonable, no solo un atajo:** se confirmo por
investigacion (2026-09-21) que el BID no tiene un aumento de capital desde
"IDB-9" (2010) - hay debate publico reciente (2024) sobre si conviene uno
nuevo, lo que confirma que todavia no paso. La cuota de EE.UU. es la misma
publicada hoy que en 2015: **30,006% del capital/poder de voto** (fuente:
pagina oficial del BID arriba, mismo numero citado en fuentes secundarias
verificadas - Council on Foreign Relations, Wikipedia). Por eso se usa como
CONSTANTE para todo el rango del proyecto (2015 en adelante), a diferencia
del Banco Mundial (`cuota_capital_bancomundial.py`, pendiente), que SI tuvo
un cambio real en 2018 y necesita una serie por anio.

**Verificacion (a pedido del usuario, "quisiera tener una forma de
verificar que ese porcentaje sigue siendo el mismo"):** como no se puede
verificar en vivo por lo de arriba, la verificacion es MANUAL - hay que
volver a mirar la pagina oficial (o el proximo Informe Anual del BID) de
vez en cuando y actualizar `PORCENTAJE_EEUU`/`FECHA_VERIFICACION` si cambio
(un nuevo aumento de capital, por ejemplo). Cada corrida sube un archivo
nuevo solo si `FECHA_VERIFICACION` cambio desde la ultima subida (mismo
patron de idempotencia por nombre de archivo que el resto del proyecto) -
asi el historial de Drive documenta CUANDO se reviso este dato por ultima
vez, no un timestamp automatico sin sentido.
"""
import io

import pandas as pd

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

DIMENSION = "1_Compromiso_financiero_oficial"
FUENTE = "cuota_capital_bid"
DESCRIPCION = "Cuota de capital/poder de voto de EE.UU. en el BID, para ponderar bid_proyectos_aprobados"
URL_FUENTE = "https://www.iadb.org/en/who-we-are/how-we-are-organized/board-governors/capital-stock-and-voting-power"

INSTITUCION = "BID"
PAIS = "Estados Unidos"
PORCENTAJE_EEUU = 30.006  # % del capital/poder de voto total del BID
FECHA_VERIFICACION = "2026-09-21"
METODO = "valor fijo verificado a mano (pagina del BID usa un widget de Power BI, no scrapeable)"
NOTA = (
    "Sin aumento de capital del BID desde 2010 (IDB-9); el mismo 30.006% "
    "esta documentado como vigente en 2015 y en 2026 - se usa como "
    "constante para todo el rango del proyecto."
)


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nombre = f"cuota_capital_bid_verificado_{FECHA_VERIFICACION}.csv"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    df = pd.DataFrame([{
        "institucion": INSTITUCION,
        "pais": PAIS,
        "porcentaje_capital_voto": PORCENTAJE_EEUU,
        "fecha_verificacion": FECHA_VERIFICACION,
        "metodo": METODO,
        "url_fuente": URL_FUENTE,
        "nota": NOTA,
    }])

    contenido = df.to_csv(index=False).encode("utf-8-sig")
    subir_archivo(contenido, nombre, carpeta_id, mime_type="text/csv")
    print(f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - {PORCENTAJE_EEUU}% verificado {FECHA_VERIFICACION}.")


if __name__ == "__main__":
    run()
