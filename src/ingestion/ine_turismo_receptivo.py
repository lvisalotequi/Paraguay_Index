"""
Turismo receptivo a Paraguay por mes, segun nacionalidad - fila de Estados
Unidos. Instituto Nacional de Estadistica (INE) de Paraguay.

Fuente: Cuadro 2.4.2 "Turismo receptivo por mes, segun nacionalidad" del
Anuario Estadistico del INE (un cuadro por edicion anual - no es la misma
publicacion que el "Compendio Estadistico", que solo tiene desglose por
CONTINENTE, nunca por pais). Credito de la fuente original, tal como
aparece en el propio cuadro: "Direccion General de Migraciones y
Secretaria Nacional de Turismo" (SENATUR).

**Por que un historico fijo en vez de descubrir los links en cada
corrida**: el buscador del sitio del INE (ine.gov.py) es JavaScript puro -
no devuelve resultados a un `requests`/`curl_cffi` normal (confirmado
2026-09-28, mismo tipo de limite que ya tiene `state_gov_tias_paraguay.py`
con el buscador de DuckDuckGo). Los 9 links de abajo se encontraron
navegando el sitio a mano una sola vez; cada corrida los vuelve a pedir
para confirmar que el archivo siga ahi y que la fila "Estados Unidos"
siga presente (mismo patron que `ustr_consejo_comercio_inversion.py`/
`state_gov_tias_paraguay.py`).

**Falta 2016** (investigado a fondo 2026-09-28, no es un link que falte
encontrar): se revisaron el Anuario Estadistico 2016 completo (311
paginas - solo tiene el cuadro por continente, no por nacionalidad), el
Compendio Estadistico 2017 completo (82 paginas - esa serie nunca tuvo
desglose por pais en ninguna edicion), el sitio de Migraciones (sin datos
historicos, solo un dashboard en vivo desde 2026), y el archivo historico
del Observatorio de Turismo de SENATUR en Wayback Machine (que sí tiene
una tabla equivalente para 2010-2015, pero se dejo de actualizar despues
de 2015). El propio SENATUR firmo un convenio con la entonces DGEEC (hoy
INE) recien el 2017-02-08 "para fortalecer su sistema de estadisticas
turisticas" - encaja con que 2016 haya sido justo el año de transicion
entre el sistema viejo de SENATUR (que si llego a cubrir 2015) y el nuevo,
conjunto con el INE (que arranca en 2017). El hueco se resuelve en
`src/processing/compromiso_economico_privado.py` con un promedio
aritmetico simple mes a mes de 2015 y 2017 - ver ese modulo para el
detalle y el piloto que valido el metodo.

**Para agregar un año nuevo** (2025 en adelante, cuando el INE lo
publique): buscar "turismo" en el buscador del propio sitio
(ine.gov.py, la caja de busqueda arriba a la derecha - no funciona por
`requests`, hay que hacerlo a mano con un navegador) y ubicar el link
"Cuadro 2.4.2. Turismo receptivo por mes, segun nacionalidad. Año {año}" -
agregar la URL a AÑOS_HISTORICOS.

Sube un unico Excel (una fila por año) a Drive. Es idempotente por dia.
"""
import io
from datetime import datetime, timezone

import pandas as pd
from curl_cffi import requests

from src.drive import existe_archivo, resolve_ingestion_folder, subir_archivo

DIMENSION = "3_Compromiso_economico_privado"
FUENTE = "ine_turismo_receptivo"
DESCRIPCION = "Turistas de EE.UU. que ingresaron a Paraguay por mes, según nacionalidad (INE)"
URL_FUENTE = "https://www.ine.gov.py/publicacion/16/anuario"

IMPERSONATE = "chrome"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]

# Historico fijo verificado a mano 2026-09-28 (ver docstring del modulo
# para por que no se puede descubrir por busqueda automatica, y por que
# falta 2016). Cada corrida vuelve a pedir estos mismos 9 archivos para
# confirmar que sigan existiendo y que la fila "Estados Unidos" siga ahi.
AÑOS_HISTORICOS = {
    2015: "https://www.ine.gov.py/Publicaciones/Biblioteca/anuario2015/Anuario%20Estadistico%202015.pdf",
    2017: "https://www.ine.gov.py/assets/documento/0720bCuadro-2.4.2_2017.xlsx",
    2018: "https://www.ine.gov.py/assets/documento/1bda9Cuadro_2.4.2.xlsx",
    2019: "https://www.ine.gov.py/assets/documento/4edbc2.4.2_AEP_2019.xlsx",
    2020: "https://www.ine.gov.py/assets/documento/8870f2.4.2_AEP2020.xlsx",
    2021: "https://www.ine.gov.py/assets/documento/0/2.4.2_AEP2021.xlsx",
    2022: "https://www.ine.gov.py/assets/documento/61/2.4.2_AE2022.xlsx",
    2023: "https://www.ine.gov.py/assets/documento/61/2.4.2_AE2023..xlsx",
    2024: "https://www.ine.gov.py/assets/documento/0/2.4.2_AE2024.xlsx",
}


def _fila_eeuu_desde_xlsx(contenido):
    """Extrae la fila de Estados Unidos (total + 12 meses) de un Cuadro
    2.4.2 en formato xlsx suelto (2017 en adelante)."""
    df = pd.read_excel(io.BytesIO(contenido), header=None)
    col_nacionalidad = df.iloc[:, 1].astype(str)
    fila = df[col_nacionalidad.str.contains("Estados Unidos", na=False)]
    if fila.empty:
        raise RuntimeError("no se encontro la fila 'Estados Unidos' en el archivo")
    total = fila.iloc[0, 2]
    meses = pd.to_numeric(fila.iloc[0, 3:15], errors="coerce").fillna(0).astype(int).tolist()
    return total, meses


def _fila_eeuu_desde_pdf_2015(contenido):
    """2015 no tiene un xlsx suelto - el Cuadro 2.4.2 solo esta adentro
    del PDF completo del Anuario Estadistico 2015 (ver docstring del
    modulo). Se busca la pagina con 'CUADRO 2.4.2' y se parsea la linea
    de Estados Unidos con el mismo formato de columnas."""
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(contenido))
    for pagina in lector.pages:
        texto = pagina.extract_text() or ""
        if "CUADRO 2.4.2" in texto.upper() and "NACIONALIDAD" in texto.upper():
            for linea in texto.split("\n"):
                if linea.strip().startswith("Estados Unidos"):
                    partes = linea.replace(".", "").split()
                    numeros = [int(p) for p in partes if p.replace(",", "").isdigit()]
                    if len(numeros) < 13:
                        raise RuntimeError(f"fila de Estados Unidos con formato inesperado: {linea!r}")
                    return numeros[0], numeros[1:13]
    raise RuntimeError("no se encontro el Cuadro 2.4.2 con la fila de Estados Unidos en el PDF de 2015")


def run():
    carpeta_id = resolve_ingestion_folder(DIMENSION, FUENTE)
    fecha_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nombre = f"ine_turismo_receptivo_{fecha_hoy}.xlsx"

    if existe_archivo(nombre, carpeta_id):
        print(f"[{FUENTE}] '{nombre}' ya existia (ya se corrio hoy), no se subio de nuevo.")
        return

    filas = []
    for anio, url in sorted(AÑOS_HISTORICOS.items()):
        try:
            resp = requests.get(url, impersonate=IMPERSONATE, timeout=60)
            resp.raise_for_status()
            if anio == 2015:
                total, meses = _fila_eeuu_desde_pdf_2015(resp.content)
            else:
                total, meses = _fila_eeuu_desde_xlsx(resp.content)
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] {anio}: {exc!r}")
            continue

        fila = {"anio": anio, "total": total}
        fila.update(dict(zip(MESES, meses)))
        filas.append(fila)

    if not filas:
        print(f"[{FUENTE}] no se pudo verificar ningun año del historico esta corrida.")
        return

    df = pd.DataFrame(filas).sort_values("anio")

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")

    mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    subir_archivo(buffer.getvalue(), nombre, carpeta_id, mime_type=mime_xlsx)

    print(
        f"[{FUENTE}] '{nombre}' subido a Drive ({DIMENSION}/{FUENTE}) - "
        f"{len(df)}/{len(AÑOS_HISTORICOS)} años verificados, años: {sorted(df['anio'].tolist())}."
    )


if __name__ == "__main__":
    run()
