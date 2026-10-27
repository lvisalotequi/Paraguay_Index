#-----------------------------------------------------------------------------.#
# PROYECTO: US-PY ENGAGEMENT INDEX                                             #
#                                                                              #
# FECHA DE CREACION: 21/09/2026                                                #
# NOMBRE: cuota_capital_bid                                                    #
# DETALLE: sube a Drive el porcentaje de capital y poder de voto de EE.UU. en  #
#   el BID (30,006 %), un valor fijo verificado a mano. NO lo lee en vivo: la  #
#   pagina del BID dibuja la tabla con Power BI. Pondera                       #
#   bid_proyectos_aprobados en src/processing/.                                #
#                                                                              #
# CORRE DESPUES DE: nada (es la etapa 01); lo lee                              #
#   src/processing/compromiso_financiero_oficial.py                            #
# SALIDA: un CSV de una fila (cuota_capital_bid_verificado_{fecha}.csv) en     #
#   01_crudas/<dimension>_crudas/cuota_capital_bid/                            #
#-----------------------------------------------------------------------------.#

# Setup ------------------------------------------------------------------------
import io

import pandas as pd

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo



# Parametros -------------------------------------------------------------------

# Trazabilidad: run_pipeline.py arma la pestana catalogo_fuentes con estas cuatro
# constantes. No se cambian sin cambiar la fuente. La fuente es la pagina oficial
# "Capital Stock And Voting Power" del BID.
DIMENSION   = "1_Compromiso_financiero_oficial"
FUENTE      = "cuota_capital_bid"
DESCRIPCION = "Cuota de capital/poder de voto de EE.UU. en el BID, para ponderar bid_proyectos_aprobados"
URL_FUENTE  = "https://www.iadb.org/en/who-we-are/how-we-are-organized/board-governors/capital-stock-and-voting-power"

# Para que sirve: es el insumo para ponderar bid_proyectos_aprobados por la porcion
# atribuible a EE.UU. (ver CLAUDE.md, seccion 7, punto 4: "Desembolsos de BID/Banco
# Mundial ponderados por cuota de capital de EE.UU."). La logica, a pedido del
# usuario (2026-09-21): el dinero que el BID le presta a Paraguay sale del capital
# general del banco, no de un fondo exclusivo de EE.UU., asi que la porcion
# "atribuible" a EE.UU. se aproxima como monto_a_paraguay x cuota_de_capital_eeuu.
# Es el mismo principio que usa la OCDE/DAC para su estadistica de "imputed
# multilateral ODA".
#
# POR QUE ESTO NO SE SCRAPEA EN VIVO, a diferencia del resto de src/ingestion/
# (excepcion documentada, 2026-09-21): la pagina oficial "Capital Stock And Voting
# Power" del BID no tiene la tabla en HTML. La renderiza un widget de Power BI
# embebido (confirmado con un navegador real: carga idb_powerbi-embed.js y un
# iframe de app.powerbi.com con token de sesion). No hay HTML ni JSON estatico que
# requests o curl_cffi puedan leer, y automatizarlo en serio exigiria un navegador
# headless (Playwright o Selenium), una dependencia que el proyecto no usa en
# ningun otro lado, para un dato que casi no cambia. Se decidio no agregarla.
#
# POR QUE UN VALOR FIJO ES RAZONABLE y no solo un atajo: se confirmo (2026-09-21)
# que el BID no tiene un aumento de capital desde "IDB-9" (2010). Hay debate publico
# reciente (2024) sobre si conviene uno nuevo, lo que confirma que todavia no paso.
# La cuota de EE.UU. es la misma hoy que en 2015: 30,006 % del capital y del poder
# de voto (pagina oficial del BID; el mismo numero aparece en fuentes secundarias
# verificadas: Council on Foreign Relations y Wikipedia). Por eso se usa como
# CONSTANTE para todo el rango del proyecto (2015 en adelante), a diferencia del
# Banco Mundial (cuota_capital_bancomundial.py), que SI cambio en 2018 y necesita
# una serie por anio.
#
# COMO SE VERIFICA (a pedido del usuario: "una forma de verificar que ese
# porcentaje sigue siendo el mismo"): como no se puede en vivo, la verificacion es
# MANUAL. Hay que volver a mirar la pagina oficial (o el proximo Informe Anual del
# BID) de vez en cuando y actualizar PORCENTAJE_EEUU y FECHA_VERIFICACION si algo
# cambio, por ejemplo un nuevo aumento de capital. Cada corrida sube un archivo
# nuevo solo si FECHA_VERIFICACION cambio desde la ultima subida (misma idempotencia
# por nombre de archivo que el resto del proyecto): el historial de Drive documenta
# CUANDO se reviso este dato por ultima vez, no un timestamp automatico sin sentido.
INSTITUCION        = "BID"
PAIS               = "Estados Unidos"
PORCENTAJE_EEUU    = 30.006  # % del capital/poder de voto total del BID
FECHA_VERIFICACION = "2026-09-21"
METODO             = "valor fijo verificado a mano (pagina del BID usa un widget de Power BI, no scrapeable)"
NOTA = (
    "Sin aumento de capital del BID desde 2010 (IDB-9); el mismo 30.006% "
    "esta documentado como vigente en 2015 y en 2026 - se usa como "
    "constante para todo el rango del proyecto."
)



# Ejecucion --------------------------------------------------------------------


def run():

    # 1. resuelve la carpeta de Drive y arma el nombre: lleva la fecha de verificacion

    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    nombre = f"cuota_capital_bid_verificado_{FECHA_VERIFICACION}.csv"

    # 2. idempotente: si esa verificacion ya esta en Drive, no se vuelve a subir

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia, no se subio de nuevo.")
        return

    # 3. arma la fila unica con el porcentaje y de donde sale

    df = pd.DataFrame([{
        "institucion": INSTITUCION,
        "pais": PAIS,
        "porcentaje_capital_voto": PORCENTAJE_EEUU,
        "fecha_verificacion": FECHA_VERIFICACION,
        "metodo": METODO,
        "url_fuente": URL_FUENTE,
        "nota": NOTA,
    }])

    # 4. sube el CSV a Drive

    contenido = df.to_csv(index=False).encode("utf-8-sig")
    subir_archivo(contenido, nombre, carpeta_id, mime_type="text/csv")

    # 5. validacion: dice que porcentaje se subio y cuando se verifico

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{PORCENTAJE_EEUU}% verificado {FECHA_VERIFICACION}."
    )


if __name__ == "__main__":
    run()
