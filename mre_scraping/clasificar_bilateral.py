#!/usr/bin/env python3
"""Clasificación bilateral Paraguay–EE.UU. determinista, explicable y sin IA."""
import argparse, csv, json, re
from collections import Counter
from pathlib import Path

from scraper_mre import canonical_url, clean_text, load_patterns

FIELDS = ["es_bilateral", "puntaje_bilateral", "nivel_relevancia", "tipo_relacion",
          "actores_detectados", "acciones_detectadas", "evidencia_clasificacion"]

TYPES = {
    "seguridad_defensa": r"\b(seguridad|defensa|terrorismo|narcotr[aá]fico|crimen)\b",
    "comercio_inversion": r"\b(comercio|inversion(?:es)?|mercado|exportaci[oó]n|arancel)\b",
    "migracion_consular": r"\b(migraci[oó]n|visa|consular|refugio|conare)\b",
    "acuerdo_cooperacion": r"\b(acuerdo|memorando|cooperaci[oó]n|asistencia|financiamiento)\b",
    "reunion_diplomatica": r"\b(reuni[oó]n|audiencia|di[aá]logo|visita|encuentro|agenda bilateral)\b"
}

def compile_rules(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw, {k: [re.compile(p, re.I) for p in v] for k, v in raw["grupos"].items()}

def hits(text, patterns):
    return sorted({m.group(0) for p in patterns for m in p.finditer(text)}, key=str.casefold)

def classify(row, us_patterns, config, rules):
    title, body = row.get("titulo", ""), row.get("texto", "")
    text = clean_text(title + " " + body)
    lead = clean_text(title + " " + body[:1200])
    us = hits(text, us_patterns)
    found = {name: hits(text, pats) for name, pats in rules.items()}
    score = 0
    evidence = []
    if us: score += 2; evidence.append("EE.UU.: " + ", ".join(us[:4]))
    if found["paraguay"]: score += 1; evidence.append("Paraguay: " + ", ".join(found["paraguay"][:3]))
    if found["accion_bilateral"]: score += 2; evidence.append("acción: " + ", ".join(found["accion_bilateral"][:3]))
    if found["instrumento"]: score += 2; evidence.append("instrumento: " + ", ".join(found["instrumento"][:3]))
    if found["alto_nivel"]: score += 2; evidence.append("alto nivel: " + ", ".join(found["alto_nivel"][:3]))
    if found["areas_sustantivas"]: score += 1; evidence.append("área: " + ", ".join(found["areas_sustantivas"][:3]))
    title_us = bool(hits(title, us_patterns))
    if title_us: score += 1; evidence.append("EE.UU. aparece en el título")
    # Una noticia puramente multilateral necesita otra evidencia bilateral fuerte.
    if found["multilateral"] and not (found["instrumento"] or title_us):
        score = max(0, score - 2); evidence.append("ajuste multilateral: -2")
    explicit = bool(re.search(r"\b(agenda|relaci[oó]n|cooperaci[oó]n|di[aá]logo) bilateral\b", text, re.I))
    core = False
    for pattern in us_patterns:
        for match in pattern.finditer(lead):
            window = lead[max(0, match.start() - 350):match.end() + 350]
            if hits(window, rules["paraguay"]) and hits(window, rules["accion_bilateral"]):
                core = True
                break
        if core: break
    multilateral_only = bool(found["multilateral"] and not (explicit or found["instrumento"]))
    identified_us_actor = bool(hits(lead, rules["actor_eeuu"]))
    third_party_title = bool(re.search(
        r"\b(argentina|brasil|ecuador|españa|reino unido|corea|qatar|afganist[aá]n|talib[aá]n|rusia|china|jap[oó]n|italia|alemania|francia)\b",
        title, re.I))
    direct_pair_title = bool(re.search(r"paraguay.{0,80}(?:estados unidos|ee\s*\.?\s*uu)|(?:estados unidos|ee\s*\.?\s*uu).{0,80}paraguay", title, re.I))
    bilateral = bool(core and (title_us or identified_us_actor) and not multilateral_only
                     and (not third_party_title or direct_pair_title)
                     and score >= config["umbral_bilateral"])
    evidence.append("núcleo próximo: " + ("sí" if core else "no"))
    evidence.append("actor estadounidense: " + ("sí" if identified_us_actor else "no"))
    if not bilateral: level = "mención simple" if us else "sin mención"
    elif score >= config["umbral_peso_alto"]: level = "bilateral de peso"
    else: level = "bilateral"
    kind = next((name for name, pattern in TYPES.items() if re.search(pattern, text, re.I)), "otra")
    return {
        "es_bilateral": int(bilateral), "puntaje_bilateral": score,
        "nivel_relevancia": level, "tipo_relacion": kind if bilateral else "",
        "actores_detectados": " | ".join((us + found["paraguay"] + found["alto_nivel"])[:10]),
        "acciones_detectadas": " | ".join((found["accion_bilateral"] + found["instrumento"])[:10]),
        "evidencia_clasificacion": "; ".join(evidence)
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entrada", type=Path, required=True)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--reglas", type=Path, default=Path(__file__).with_name("reglas_bilaterales.json"))
    p.add_argument("--terminos", type=Path, default=Path(__file__).with_name("terminos_eeuu.json"))
    a = p.parse_args()
    config, rules = compile_rules(a.reglas); us = load_patterns(a.terminos)
    if a.entrada.suffix.lower() == ".ndjson":
        latest = {}
        with a.entrada.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    latest[canonical_url(row["url_original"])] = row
        rows = list(latest.values())
    else:
        with a.entrada.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    out = [dict(row, **classify(row, us, config, rules)) for row in rows]
    a.salida.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) + FIELDS if rows else FIELDS
    with (a.salida / "noticias_clasificadas.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    valid = [r for r in out if r.get("estado") == "ok"]
    months = sorted({r.get("mes", "") for r in valid if r.get("mes")})
    summary = []
    for month in months:
        group = [r for r in valid if r.get("mes") == month]
        summary.append({"mes": month, "noticias_validas": len(group),
                        "mencion_simple": sum(r["nivel_relevancia"] == "mención simple" for r in group),
                        "bilaterales": sum(int(r["es_bilateral"]) for r in group),
                        "bilaterales_de_peso": sum(r["nivel_relevancia"] == "bilateral de peso" for r in group)})
    with (a.salida / "resumen_bilateral_mensual.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields2 = ["mes", "noticias_validas", "mencion_simple", "bilaterales", "bilaterales_de_peso"]
        w = csv.DictWriter(f, fieldnames=fields2); w.writeheader(); w.writerows(summary)
    print(json.dumps(Counter(r["nivel_relevancia"] for r in valid), ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
