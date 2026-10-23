#!/usr/bin/env python3
"""Actualizacion INCREMENTAL de las noticias del MRE, sin disco ni corrida larga.

Contexto: la recoleccion completa 2015-2025 (`scraper_mre.py`) tarda ~5 horas
porque baja ~9.300 URL, la mayoria historicas (Wayback). Pero esas ya estan
hechas y clasificadas en `noticias_clasificadas_*.csv` (en Drive). Lo unico que
cambia con el tiempo son las noticias NUEVAS del archivo actual de mre.gov.py,
que lista las mas recientes primero. Este script parte del archivo clasificado
anterior, recorre el archivo actual desde la primera pagina y se detiene cuando
encuentra una racha de noticias que ya conoce; descarga y clasifica solo lo
nuevo (mas las que quedaron en `error_descarga`) y devuelve el conjunto
completo. Lo que tarda es proporcional a las noticias nuevas: minutos, no horas.

Reusa sin cambios las funciones de `scraper_mre.py` (descubrimiento, extraccion,
conteo de menciones) y de `clasificar_bilateral.py` (clasificacion por reglas
explicitas, sin IA), asi una noticia nueva se trata exactamente igual que una
vieja. No escribe a disco salvo la cache de HTML en `cache_dir` (temporal).

Lo usa `src/ingestion/mre_menciones_eeuu.py`, que se ocupa de bajar el archivo
anterior de Drive y subir el resultado. Tambien se puede usar a mano:

    python actualizar_incremental.py --previo noticias_clasificadas.csv --salida nuevo.csv
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from clasificar_bilateral import FIELDS as CAMPOS_CLASIFICACION
from clasificar_bilateral import classify, compile_rules
from scraper_mre import (
    CURRENT_ARCHIVE,
    FIELDS,
    Candidate,
    Fetcher,
    candidate_to_record,
    canonical_url,
    discover_current,
    load_patterns,
)

AQUI = Path(__file__).resolve().parent
ANIO_MINIMO = 2015
RACHA_CONOCIDAS = 40  # noticias seguidas ya conocidas que indican "de aqui para atras no hay nada nuevo"
MAX_NUEVAS = 600  # tope de seguridad por corrida
MAX_REINTENTOS_ERROR = 100


class SitioNoAccesible(RuntimeError):
    """El archivo actual del MRE no respondio (bloqueo o caida)."""


def reevaluar_periodo(filas, hasta_anio, anio_minimo=ANIO_MINIMO):
    """Corrige el estado de las filas marcadas `fuera_periodo` por una corrida
    cuyo rango terminaba antes (la recoleccion completa se hizo con --hasta
    2025, asi que las ~275 noticias de 2026 que ya se habian descargado y
    clasificado quedaron como `fuera_periodo`). No vuelve a descargar nada:
    el texto y la clasificacion ya estan en la fila, solo cambia el estado.
    Devuelve cuantas filas cambio."""
    cambiadas = 0
    for fila in filas:
        if fila.get("estado") != "fuera_periodo":
            continue
        anio = (fila.get("fecha") or "")[:4]
        if not anio.isdigit() or not (anio_minimo <= int(anio) <= hasta_anio):
            continue
        fila["estado"] = "ok" if len(fila.get("texto") or "") >= 80 else "texto_insuficiente"
        cambiadas += 1
    return cambiadas


def _candidato_desde_fila(fila):
    """Reconstruye el Candidate de una noticia que fallo en una corrida anterior."""
    url_consulta = fila.get("url_consulta") or fila["url_original"]
    # el sitio actual exige la barra final (ver scraper_mre.discover_current)
    if fila.get("fuente") == "actual" and "?" not in url_consulta and not url_consulta.endswith("/"):
        url_consulta += "/"
    return Candidate(
        source=fila.get("fuente", "actual"),
        fetch_url=url_consulta,
        original_url=fila["url_original"],
        capture_timestamp=fila.get("captura_wayback", ""),
        listing_date=fila.get("fecha", "") if fila.get("fuente") == "actual" else "",
        listing_title=fila.get("titulo", "") if fila.get("fuente") == "actual" else "",
        listing_description=fila.get("descripcion", "") if fila.get("fuente") == "actual" else "",
    )


def descubrir_nuevas(fetcher, conocidas, racha=RACHA_CONOCIDAS, max_nuevas=MAX_NUEVAS):
    """Candidatos del archivo actual que NO estan en `conocidas` (clave = url
    canonica). Corta la lectura de paginas tras `racha` conocidas seguidas."""
    try:
        fetcher.get(CURRENT_ARCHIVE, use_cache=False)
    except RuntimeError as exc:
        raise SitioNoAccesible(f"no se pudo leer el archivo actual del MRE: {exc}") from exc

    nuevas, seguidas = [], 0
    for candidato in discover_current(fetcher, None):
        if canonical_url(candidato.original_url) in conocidas:
            seguidas += 1
            if seguidas >= racha:
                break
            continue
        seguidas = 0
        nuevas.append(candidato)
        if len(nuevas) >= max_nuevas:
            break
    return nuevas


def actualizar(previas, cache_dir, demora=1.0, trabajadores=4, hasta_anio=None,
               terminos=AQUI / "terminos_eeuu.json", reglas=AQUI / "reglas_bilaterales.json"):
    """previas: lista de dicts (filas del noticias_clasificadas anterior).
    Devuelve (filas, resumen): todas las filas (previas + nuevas, sin
    duplicar URL; lo recien descargado reemplaza a lo viejo) y un resumen."""
    hasta_anio = hasta_anio or datetime.now(timezone.utc).year
    previas = [dict(f) for f in previas]  # no se modifica la lista del llamador
    reevaluadas = reevaluar_periodo(previas, hasta_anio)
    conocidas = {canonical_url(f["url_original"]): f for f in previas}
    con_error = [f for f in previas if f.get("estado") == "error_descarga"]

    fetcher = Fetcher(Path(cache_dir), demora, 45.0, 3)
    patrones = load_patterns(terminos)
    config, reglas_compiladas = compile_rules(Path(reglas))

    # lo conocido (excepto lo fallido) corta la busqueda; lo fallido se vuelve a pedir
    sin_error = {k: f for k, f in conocidas.items() if f.get("estado") != "error_descarga"}
    candidatos = descubrir_nuevas(fetcher, sin_error)
    ya_en_cola = {canonical_url(c.original_url) for c in candidatos}
    reintentos = [
        _candidato_desde_fila(f) for f in con_error[:MAX_REINTENTOS_ERROR]
        if canonical_url(f["url_original"]) not in ya_en_cola
    ]
    pendientes = candidatos + reintentos

    with ThreadPoolExecutor(max_workers=max(1, trabajadores)) as pool:
        registros = list(pool.map(
            lambda c: candidate_to_record(c, fetcher, patrones, ANIO_MINIMO, hasta_anio), pendientes
        ))

    nuevas_filas = {}
    for registro in registros:
        fila = asdict(registro)
        fila.update(classify(fila, patrones, config, reglas_compiladas))
        nuevas_filas[canonical_url(fila["url_original"])] = fila

    resultado = dict(conocidas)
    resueltas = 0
    for clave, fila in nuevas_filas.items():
        anterior = resultado.get(clave)
        # un reintento que sigue fallando no pisa lo que ya habia
        if anterior is not None and fila["estado"] == "error_descarga":
            continue
        if anterior is not None and anterior.get("estado") == "error_descarga":
            resueltas += 1
        resultado[clave] = fila

    filas = sorted(resultado.values(), key=lambda f: (f.get("fecha") or "9999", f["url_original"]))
    resumen = {
        "previas": len(previas),
        "candidatas_nuevas": len(candidatos),
        "reintentos_de_errores": len(reintentos),
        "errores_resueltos": resueltas,
        "reevaluadas_por_periodo": reevaluadas,
        "agregadas": len([k for k in nuevas_filas if k not in conocidas]),
        "total": len(filas),
    }
    return filas, resumen


def columnas(previas):
    if previas:
        return list(previas[0].keys())
    return FIELDS + CAMPOS_CLASIFICACION


def leer_csv(ruta):
    csv.field_size_limit(2**31 - 1)
    with Path(ruta).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def escribir_csv(ruta, filas, campos):
    with Path(ruta).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--previo", type=Path, required=True, help="noticias_clasificadas.csv anterior")
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--cache", type=Path, default=Path("cache_incremental"))
    p.add_argument("--demora", type=float, default=1.0)
    p.add_argument("--trabajadores", type=int, default=4)
    a = p.parse_args()
    previas = leer_csv(a.previo)
    filas, resumen = actualizar(previas, a.cache, a.demora, a.trabajadores)
    escribir_csv(a.salida, filas, columnas(previas))
    print(resumen)


if __name__ == "__main__":
    main()
