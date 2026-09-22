#!/usr/bin/env python3
"""Recolector reproducible de noticias del MRE de Paraguay (2015-2025).

No usa IA. Descubre noticias en el archivo actual y en el índice CDX de
Wayback Machine, extrae campos, cuenta menciones mediante expresiones regulares
y escribe CSV/JSON auditables.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import logging
import random
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Iterator
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from curl_cffi import requests


LOG = logging.getLogger("mre_scraper")
CURRENT_ARCHIVE = "https://www.mre.gov.py/archivo-de-noticias/"
CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
WAYBACK_REPLAY = "https://web.archive.org/web/{timestamp}id_/{original}"
DATE_RX = re.compile(
    r"\b([0-3]?\d)\s+de\s+"
    r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
    r"octubre|noviembre|diciembre)\s+(?:de\s+)?(20\d{2})\b",
    re.I,
)
ISO_DATE_RX = re.compile(r"\b(20\d{2})[-/]([01]\d)[-/]([0-3]\d)\b")
PUBLISHED_NUMERIC_RX = re.compile(
    r"Publicado:\s*([01]?\d)/([0-3]?\d)/(\d{2,4})\b", re.I
)
MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
    "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
BLOCK_MARKERS = ("acceso restringido", "attention required", "cf-chl-", "captcha")


@dataclass(frozen=True)
class Candidate:
    source: str
    fetch_url: str
    original_url: str
    capture_timestamp: str = ""
    listing_date: str = ""
    listing_title: str = ""
    listing_description: str = ""


@dataclass
class Record:
    fecha: str
    mes: str
    titulo: str
    descripcion: str
    texto: str
    url_original: str
    url_consulta: str
    fuente: str
    captura_wayback: str
    menciona_eeuu: int
    numero_menciones_eeuu: int
    terminos_encontrados: str
    estado: str


class Fetcher:
    def __init__(self, cache_dir: Path, delay: float, timeout: float, retries: int):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = max(delay, 0)
        self.timeout = timeout
        self.retries = retries
        self.headers = {
            "User-Agent": "MRE-Paraguay-research-scraper/1.0 (academic reproducible collection)",
            "Accept-Language": "es-419,es;q=0.9,en;q=0.5",
        }
        self.local = threading.local()
        self.rate_lock = threading.Lock()
        self.last_request = 0.0

    def _session(self) -> requests.Session:
        if not hasattr(self.local, "session"):
            # mre.gov.py devuelve 403 con requests normal (bloqueo por huella
            # TLS, no por headers) - mismo bloqueo que bcp.gov.py y state.gov
            # en este proyecto, se pasa igual con curl_cffi impersonate="chrome".
            self.local.session = requests.Session(impersonate="chrome")
            self.local.session.headers.update(self.headers)
        return self.local.session

    def _wait_turn(self) -> None:
        if not self.delay:
            return
        with self.rate_lock:
            remaining = self.delay - (time.monotonic() - self.last_request)
            if remaining > 0:
                time.sleep(remaining)
            self.last_request = time.monotonic()

    def get(self, url: str, *, use_cache: bool = True) -> str:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        body_path = self.cache_dir / f"{key}.html"
        meta_path = self.cache_dir / f"{key}.json"
        if use_cache and body_path.exists():
            return body_path.read_text(encoding="utf-8", errors="replace")
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                self._wait_turn()
                response = self._session().get(url, timeout=self.timeout)
                response.raise_for_status()
                text = response.text
                low = text[:8000].lower()
                if any(marker in low for marker in BLOCK_MARKERS):
                    raise RuntimeError("la respuesta contiene una página de bloqueo")
                body_path.write_text(text, encoding="utf-8")
                meta_path.write_text(json.dumps({
                    "url_solicitada": url,
                    "url_final": response.url,
                    "status": response.status_code,
                    "descargado_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                return text
            except (requests.exceptions.RequestException, RuntimeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"No se pudo descargar {url}: {last_error}")

    def get_json(self, url: str) -> object:
        return json.loads(self.get(url))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.netloc.lower().replace(":80", "")
    if host in {"mre.gov.py", "www2.mre.gov.py"}:
        host = "www.mre.gov.py"
    kept = [(k, v) for k, v in parse_qsl(parts.query) if k not in {
        "ccm_paging_p", "_page", "utm_source", "utm_medium", "utm_campaign"
    }]
    path = re.sub(r"/{2,}", "/", parts.path)
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(("https", host, path, urlencode(kept), ""))


def parse_date(text: str) -> str:
    match = DATE_RX.search(clean_text(text))
    if match:
        try:
            return date(int(match.group(3)), MONTHS[match.group(2).lower()], int(match.group(1))).isoformat()
        except ValueError:
            pass
    match = ISO_DATE_RX.search(text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            pass
    # El portal histórico muestra "Publicado: 08/01/18" en orden mes/día/año.
    match = PUBLISHED_NUMERIC_RX.search(text)
    if match:
        year = int(match.group(3))
        year = year + 2000 if year < 100 else year
        try:
            return date(year, int(match.group(1)), int(match.group(2))).isoformat()
        except ValueError:
            pass
    return ""


def meta_content(soup: BeautifulSoup, *selectors: tuple[str, str]) -> str:
    for attr, name in selectors:
        tag = soup.find("meta", attrs={attr: name})
        if tag and tag.get("content"):
            return clean_text(str(tag["content"]))
    return ""


def extract_article(raw_html: str, candidate: Candidate) -> tuple[str, str, str, str]:
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup.select("script, style, noscript, nav, footer, header, form, aside, .sidebar, .breadcrumb, .pagination, .tags, .taglib-categorization-filter"):
        tag.decompose()
    title = candidate.listing_title
    if not title:
        node = soup.select_one("article h1, main h1, h1, .page-title, article h2")
        title = clean_text(node.get_text(" ")) if node else ""
    if not title:
        title = meta_content(soup, ("property", "og:title"), ("name", "twitter:title"))
    if not title and soup.title:
        title = clean_text(soup.title.get_text(" ")).split(" :: ")[-1]
    description = candidate.listing_description or meta_content(
        soup, ("name", "description"), ("property", "og:description")
    )
    container = None
    for selector in (
        "article .entry-content", "article .post-content", ".contenido_principal",
        "article", "main .entry-content", "main", "#main-content", ".page-content",
        ".ccm-page",
    ):
        container = soup.select_one(selector)
        if container:
            break
    container = container or soup.body
    if container and "contenido_principal" in (container.get("class") or []):
        # El portal histórico añade dentro del mismo contenedor un carrusel de
        # "Últimas Noticias Publicadas". El primer <hr> marca el fin del cuerpo.
        body_parts: list[str] = []
        for child in container.find_all(recursive=False):
            if child.name == "hr" or (
                child.name in {"h4", "h5", "h6"}
                and "últimas noticias" in clean_text(child.get_text(" ")).lower()
            ):
                break
            if child.name not in {"style", "script"}:
                part = clean_text(child.get_text(" "))
                if part:
                    body_parts.append(part)
        text = " ".join(body_parts)
    else:
        text = clean_text(container.get_text(" ")) if container else ""
    # Elimina título repetido al inicio, pero conserva íntegro el resto del artículo.
    if title and text.lower().startswith(title.lower()):
        text = text[len(title):].lstrip(" :-–—")
    if not description:
        paragraphs = container.find_all("p") if container else []
        description = next((clean_text(p.get_text(" ")) for p in paragraphs if len(clean_text(p.get_text(" "))) >= 60), "")
    date_value = candidate.listing_date
    if not date_value:
        date_value = meta_content(
            soup, ("property", "article:published_time"), ("name", "date"),
            ("itemprop", "datePublished"),
        )
        date_value = parse_date(date_value) or parse_date(text)
    return title, description, text, date_value[:10] if date_value else ""


def load_patterns(path: Path) -> list[re.Pattern[str]]:
    config = json.loads(path.read_text(encoding="utf-8"))
    return [re.compile(item, re.I | re.UNICODE) for item in config["patrones"]]


def count_mentions(text: str, patterns: list[re.Pattern[str]]) -> tuple[int, list[str]]:
    spans: set[tuple[int, int]] = set()
    labels: set[str] = set()
    for pattern in patterns:
        for match in pattern.finditer(text):
            span = match.span()
            if span not in spans:
                spans.add(span)
                labels.add(clean_text(match.group(0)))
    return len(spans), sorted(labels, key=str.casefold)


def discover_current(fetcher: Fetcher, max_pages: int | None) -> Iterator[Candidate]:
    page = 1
    seen: set[str] = set()
    while max_pages is None or page <= max_pages:
        url = CURRENT_ARCHIVE if page == 1 else f"{CURRENT_ARCHIVE}?_page={page}"
        try:
            raw = fetcher.get(url)
        except RuntimeError as exc:
            LOG.warning("Archivo actual detenido en página %s: %s", page, exc)
            return
        soup = BeautifulSoup(raw, "html.parser")
        candidates: list[Candidate] = []
        for heading in soup.select("h2, h3, h4"):
            link = heading.find("a", href=True)
            if not link:
                continue
            original = canonical_url(urljoin(url, str(link["href"])))
            if urlsplit(original).netloc not in {"www.mre.gov.py", "mre.gov.py"}:
                continue
            parent = heading.find_parent(["article", "li", "div"]) or heading.parent
            found_date = ""
            block = ""
            probe = parent
            # Los temas de WordPress varían: fecha, extracto y título pueden estar
            # en div hermanos. Sube hasta el primer bloque que contenga una fecha.
            for _ in range(7):
                if not probe or probe.name in {"body", "html"}:
                    break
                block = clean_text(probe.get_text(" "))
                found_date = parse_date(block)
                if found_date:
                    parent = probe
                    break
                probe = probe.parent
            if not found_date:
                continue
            desc = ""
            if parent:
                p = parent.find("p")
                desc = clean_text(p.get_text(" ")) if p else ""
            if original not in seen:
                seen.add(original)
                candidates.append(Candidate(
                    source="actual", fetch_url=original, original_url=original,
                    listing_date=found_date, listing_title=clean_text(link.get_text(" ")),
                    listing_description=desc,
                ))
        if not candidates:
            return
        yield from candidates
        page += 1


def cdx_query_url(prefix: str, start_year: int, end_year: int) -> str:
    params = [
        ("url", prefix), ("matchType", "prefix"), ("from", str(start_year)),
        ("to", str(end_year)), ("output", "json"), ("filter", "statuscode:200"),
        ("filter", "mimetype:text/html"), ("collapse", "urlkey"),
        ("fl", "timestamp,original,statuscode,mimetype,digest"),
    ]
    return CDX_ENDPOINT + "?" + urlencode(params)


def looks_like_historical_article(url: str) -> bool:
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    low = path.lower()
    if re.search(r"/(20\d{2})/(0?[1-9]|1[0-2])$", low):
        return False
    if low.endswith(("/noticias", "/noticias-de-embajadas-y-consulados")):
        return False
    if any(x in low for x in ("/tag/", "/category/", "/wp-content/", "/component/")):
        return False
    match = re.search(r"/(noticias|noticias-de-embajadas-y-consulados)/([^/]+)$", low)
    return bool(match and not match.group(2).isdigit())


def discover_wayback(fetcher: Fetcher, start_year: int, end_year: int) -> Iterator[Candidate]:
    prefixes = (
        "www.mre.gov.py/index.php/noticias",
        "www.mre.gov.py/index.php/noticias-de-embajadas-y-consulados",
        "www2.mre.gov.py/index.php/noticias",
        "www2.mre.gov.py/index.php/noticias-de-embajadas-y-consulados",
    )
    by_url: dict[str, tuple[str, str]] = {}
    for prefix in prefixes:
        try:
            # Incluye el año siguiente porque una noticia de diciembre puede ser
            # archivada por primera vez semanas después de publicarse.
            payload = fetcher.get_json(cdx_query_url(prefix, start_year, end_year + 1))
        except (RuntimeError, json.JSONDecodeError) as exc:
            LOG.warning("Fallo al consultar CDX para %s: %s", prefix, exc)
            continue
        if not isinstance(payload, list):
            continue
        for row in payload[1:]:
            if not isinstance(row, list) or len(row) < 2:
                continue
            timestamp, original = str(row[0]), str(row[1])
            canonical = canonical_url(original)
            if not looks_like_historical_article(canonical):
                continue
            # Prefiere una captura de la URL limpia. Los parámetros de paginación
            # aparecen en CDX como 200 pero algunas reproducciones devuelven 404.
            old = by_url.get(canonical)
            clean_capture = not urlsplit(original).query
            old_clean = bool(old and not urlsplit(old[1]).query)
            if old is None or (clean_capture and not old_clean) or (
                clean_capture == old_clean and timestamp > old[0]
            ):
                by_url[canonical] = (timestamp, original)
    for canonical in sorted(by_url):
        timestamp, original = by_url[canonical]
        yield Candidate(
            source="wayback", original_url=canonical,
            fetch_url=WAYBACK_REPLAY.format(timestamp=timestamp, original=original),
            capture_timestamp=timestamp,
        )


def candidate_to_record(candidate: Candidate, fetcher: Fetcher, patterns: list[re.Pattern[str]], start_year: int, end_year: int) -> Record:
    try:
        raw = fetcher.get(candidate.fetch_url)
        title, description, text, date_value = extract_article(raw, candidate)
        if not date_value:
            status = "sin_fecha"
        elif not (start_year <= int(date_value[:4]) <= end_year):
            status = "fuera_periodo"
        elif len(text) < 80:
            status = "texto_insuficiente"
        else:
            status = "ok"
        # La descripción suele repetir el primer párrafo; no se suma para evitar
        # inflar el conteo. El título y el cuerpo sí son partes distintas.
        searchable = " ".join((title, text))
        count, labels = count_mentions(searchable, patterns)
        return Record(
            fecha=date_value, mes=date_value[:7] if date_value else "", titulo=title,
            descripcion=description, texto=text, url_original=candidate.original_url,
            url_consulta=candidate.fetch_url, fuente=candidate.source,
            captura_wayback=candidate.capture_timestamp, menciona_eeuu=int(count > 0),
            numero_menciones_eeuu=count, terminos_encontrados=" | ".join(labels), estado=status,
        )
    except Exception as exc:  # se registra por fila; una URL no aborta toda la corrida
        LOG.error("Error en %s: %s", candidate.fetch_url, exc)
        return Record(
            fecha=candidate.listing_date, mes=candidate.listing_date[:7],
            titulo=candidate.listing_title, descripcion=candidate.listing_description,
            texto="", url_original=candidate.original_url, url_consulta=candidate.fetch_url,
            fuente=candidate.source, captura_wayback=candidate.capture_timestamp,
            menciona_eeuu=0, numero_menciones_eeuu=0, terminos_encontrados="",
            estado="error_descarga",
        )


FIELDS = [field.name for field in Record.__dataclass_fields__.values()]


def write_csv(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def month_range(start_year: int, end_year: int) -> Iterator[str]:
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            yield f"{year:04d}-{month:02d}"


def deduplicate(records: list[Record]) -> list[Record]:
    chosen: dict[str, Record] = {}
    for record in records:
        key = canonical_url(record.url_original)
        old = chosen.get(key)
        rank = (record.estado == "ok", len(record.texto), record.fuente == "actual")
        old_rank = (old.estado == "ok", len(old.texto), old.fuente == "actual") if old else None
        if old is None or rank > old_rank:
            chosen[key] = record
    return sorted(chosen.values(), key=lambda r: (r.fecha or "9999", r.url_original))


def export_results(output_dir: Path, records: list[Record], start_year: int, end_year: int, args: argparse.Namespace) -> None:
    valid = [r for r in records if r.estado == "ok"]
    row_dicts = [asdict(r) for r in records]
    write_csv(output_dir / "noticias_todas.csv", row_dicts, FIELDS)
    write_csv(output_dir / "noticias_menciones_eeuu.csv", [asdict(r) for r in valid if r.menciona_eeuu], FIELDS)
    monthly: list[dict[str, object]] = []
    for month in month_range(start_year, end_year):
        rows = [r for r in valid if r.mes == month]
        mentions = [r for r in rows if r.menciona_eeuu]
        monthly.append({
            "mes": month,
            "noticias_recolectadas": len(rows),
            "noticias_que_mencionan_eeuu": len(mentions),
            "total_menciones_eeuu": sum(r.numero_menciones_eeuu for r in mentions),
            "noticias_fuente_actual": sum(r.fuente == "actual" for r in rows),
            "noticias_fuente_wayback": sum(r.fuente == "wayback" for r in rows),
        })
    write_csv(output_dir / "resumen_mensual.csv", monthly, list(monthly[0]))
    statuses = Counter(r.estado for r in records)
    serialized_args = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in vars(args).items()
    }
    manifest = {
        "generado_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "periodo": {"desde": start_year, "hasta": end_year},
        "parametros": serialized_args,
        "registros_unicos": len(records),
        "estados": dict(sorted(statuses.items())),
        "noticias_validas": len(valid),
        "noticias_con_mencion_eeuu": sum(r.menciona_eeuu for r in valid),
        "total_menciones_eeuu": sum(r.numero_menciones_eeuu for r in valid),
        "archivos": ["noticias_todas.csv", "noticias_menciones_eeuu.csv", "resumen_mensual.csv"],
    }
    (output_dir / "manifiesto.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def load_checkpoint(path: Path) -> dict[str, Record]:
    records: dict[str, Record] = {}
    if not path.exists():
        return records
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                item = json.loads(line)
                record = Record(**item)
                records[canonical_url(record.url_original)] = record
            except (json.JSONDecodeError, TypeError) as exc:
                LOG.warning("Línea inválida en checkpoint %s:%s: %s", path, line_number, exc)
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desde", type=int, default=2015)
    parser.add_argument("--hasta", type=int, default=2025)
    parser.add_argument("--salida", type=Path, default=Path("salida"))
    parser.add_argument("--cache", type=Path, default=Path("cache"))
    parser.add_argument("--demora", type=float, default=1.0, help="Segundos mínimos entre solicitudes")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--reintentos", type=int, default=3)
    parser.add_argument("--trabajadores", type=int, default=6, help="Descargas simultáneas (recomendado: 4 a 8)")
    parser.add_argument("--max-paginas-actual", type=int, default=None)
    parser.add_argument("--limite", type=int, default=None, help="Límite total para una prueba piloto")
    parser.add_argument("--solo", choices=("ambas", "actual", "wayback"), default="ambas")
    parser.add_argument("--terminos", type=Path, default=Path(__file__).with_name("terminos_eeuu.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.desde > args.hasta:
        raise SystemExit("--desde no puede ser mayor que --hasta")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    fetcher = Fetcher(args.cache, args.demora, args.timeout, args.reintentos)
    patterns = load_patterns(args.terminos)
    candidates: list[Candidate] = []
    if args.solo in ("ambas", "actual"):
        LOG.info("Descubriendo noticias del archivo actual")
        candidates.extend(discover_current(fetcher, args.max_paginas_actual))
    if args.solo in ("ambas", "wayback"):
        LOG.info("Descubriendo noticias históricas en Wayback")
        candidates.extend(discover_wayback(fetcher, args.desde, args.hasta))
    unique: dict[str, Candidate] = {}
    for candidate in candidates:
        key = canonical_url(candidate.original_url)
        old = unique.get(key)
        if old is None or (candidate.source == "actual" and old.source != "actual"):
            unique[key] = candidate
    selected = list(unique.values())
    if args.limite is not None:
        selected = selected[:max(args.limite, 0)]
    args.salida.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.salida / "checkpoint.ndjson"
    completed = load_checkpoint(checkpoint_path)
    pending = [
        c for c in selected
        if canonical_url(c.original_url) not in completed
        or completed[canonical_url(c.original_url)].estado == "error_descarga"
    ]
    LOG.info(
        "Procesando %s URLs únicas (%s recuperadas del checkpoint, %s pendientes)",
        len(selected), len(completed), len(pending),
    )
    done_now = 0
    if pending:
        with checkpoint_path.open("a", encoding="utf-8") as checkpoint, ThreadPoolExecutor(
            max_workers=max(1, args.trabajadores)
        ) as pool:
            futures = {
                pool.submit(candidate_to_record, c, fetcher, patterns, args.desde, args.hasta): c
                for c in pending
            }
            try:
                for future in as_completed(futures):
                    record = future.result()
                    completed[canonical_url(record.url_original)] = record
                    checkpoint.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
                    checkpoint.flush()
                    done_now += 1
                    if done_now % 100 == 0 or done_now == len(pending):
                        LOG.info("Progreso: %s/%s pendientes procesadas", done_now, len(pending))
            except KeyboardInterrupt:
                LOG.warning("Interrupción recibida; el avance quedó guardado en %s", checkpoint_path)
                for future in futures:
                    future.cancel()
    records = list(completed.values())
    records = deduplicate(records)
    export_results(args.salida, records, args.desde, args.hasta, args)
    LOG.info("Listo: %s", args.salida.resolve())
    if not records:
        LOG.error("No se descubrió ninguna noticia; revise bloqueos, conexión y parámetros")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
