"""Build the 9-record valid-only selection, offline; emit JSON to stdout only.

Original CSVs and the complete review are never changed. No Google libraries.
"""
import csv
import hashlib
import json
import math
from collections import Counter

from validate_pilot_review import ROOT, read_json, validate, domain

AUDIT = ROOT / "output/gdelt/audit/2025-01-pilot3d_1866e9bca2eaae69a1f2.csv"


def number(value):
    if value in (None, ""):
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite tone value")
    return result


def build_selection(review, catalogue, original, audit_rows):
    validate(review, catalogue, original)
    by_url = {row["url"]: row for row in audit_rows}
    if len(by_url) != len(audit_rows) or set(by_url) != {
        row["url"] for row in review["articles"]
    }:
        raise ValueError("Audit and reviewed URLs must match one-to-one")
    sources = {s["domain"]: s for s in catalogue["sources"]}
    selected = []
    for row in review["articles"]:
        if row["decision"] != "include":
            continue
        raw = by_url[row["url"]]
        source = sources[domain(row["url"])]
        unresolved = []
        selected.append({
            "review_id": row["id"],
            "url": raw["url"], "url_key": raw["url_key"],
            "domain": domain(raw["url"]), "domain_gdelt": raw["domain"],
            "observed_at_gdelt": raw["observed_at"],
            "publication_date_verified": None,
            "month": raw["month"], "language_gdelt": raw["language"],
            "source_country_gdelt": raw["source_country"],
            "source_country_verified": row["country_verified"],
            "country_status": source["verification_status"],
            "decision": row["decision"],
            "eligible_for_confirmed_metrics": row["decision"] == "include",
            "focus": row["focus"], "reason_code": row["reason_code"],
            "content_access": row["content_access"],
            "historical_focus": row["historical_focus"],
            "related_article_ids": row["related_article_ids"],
            "reviewed_on": row["reviewed_on"],
            "evidence_urls": row["evidence_urls"],
            "unresolved": unresolved,
            "tone": {name: number(raw[name]) for name in (
                "tone", "positive_score", "negative_score", "polarity"
            )},
        })
    return {
        "schema_version": 1,
        "selection": "include_only",
        "selection_revision": 2,
        "period_start": review["period_start"],
        "period_end_exclusive": review["period_end_exclusive"],
        "partial_month": True,
        "counts": dict(Counter(r["decision"] for r in selected)),
        "note": "Only the 9 reviewed inclusions; 4 central and 5 contextual. Doubtful and excluded records remain in the complete audit, outside this selection. Tone describes the whole article. No cloud queries.",
        "review_reference": "classification_v1.json",
        "catalogue_reference": "media_catalogue_v1.json",
        "articles": selected,
    }


def prepare():
    with AUDIT.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    result = build_selection(read_json("classification_v1.json"),
                             read_json("media_catalogue_v1.json"),
                             read_json("pilot_review.json"), rows)
    result["input_audit"] = AUDIT.relative_to(ROOT).as_posix()
    result["input_audit_sha256"] = hashlib.sha256(AUDIT.read_bytes()).hexdigest()
    return result


if __name__ == "__main__":
    print(json.dumps(prepare(), ensure_ascii=True, indent=2, allow_nan=False))
