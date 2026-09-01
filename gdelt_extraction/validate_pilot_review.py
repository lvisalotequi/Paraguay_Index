"""Validate the curated pilot review locally. No network, credentials or writes."""

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "output" / "gdelt" / "review"


def domain(url):
    host = urlsplit(url).hostname or ""
    return host.removeprefix("www.")


def validate(review, catalogue, original):
    articles = review["articles"]
    sources = catalogue["sources"]
    urls = [row["url"] for row in articles]
    original_urls = [row["url"] for row in original["annotations"]]
    if len(articles) != 67 or len(set(urls)) != 67:
        raise ValueError("Expected exactly 67 unique pilot URLs")
    if set(urls) != set(original_urls):
        raise ValueError("Review and original pilot URL sets differ")
    if {row["id"] for row in articles} != set(range(1, 68)):
        raise ValueError("Review IDs must cover 1..67")
    by_domain = {row["domain"]: row for row in sources}
    if len(by_domain) != len(sources) or set(by_domain) != {domain(u) for u in urls}:
        raise ValueError("Catalogue must cover every observed domain exactly once")
    counts = Counter(row["decision"] for row in articles)
    if set(counts) - {"include", "exclude", "doubtful"}:
        raise ValueError("Unknown review decision")
    if dict(counts) != review["counts"]:
        raise ValueError("Stored totals do not match reviewed records")
    for source in sources:
        if source["verification_status"] not in {
            "verified", "historical_evidence", "unverified"
        }:
            raise ValueError("Unknown country verification status")
        if source["verification_status"] != "verified" and source["country_verified"]:
            raise ValueError("Unverified country cannot be reported as verified")
        if source["verification_status"] == "verified" and not source["country_verified"]:
            raise ValueError("Verified sources require a country")
    for row in articles:
        source = by_domain[domain(row["url"])]
        if not row["reason"] or not row["evidence_urls"] or not row["content_access"]:
            raise ValueError("Every review needs a reason, evidence and access status")
        if row["country_verified"] != source["country_verified"]:
            raise ValueError("Article and catalogue country mismatch")
        if row["decision"] == "include":
            if row["country_verified"] not in {"PY", "US"}:
                raise ValueError("Included articles need an in-scope verified source")
            if row["content_access"] not in {
                "current_text", "prior_text_review", "search_full_text", "publisher_mirror"
            }:
                raise ValueError("Inclusion cannot rely on an inaccessible article")
            if row["focus"] not in {"central", "contextual"}:
                raise ValueError("Included articles need a focus category")
        if row["content_access"] in {"unavailable", "partial_text", "changed_redirect"}:
            if row["decision"] != "doubtful":
                raise ValueError("Unresolved text must remain doubtful")
        if row["reason_code"] == "foreign_source":
            if row["country_verified"] in {None, "PY", "US"}:
                raise ValueError("Foreign-source exclusion requires country evidence")
    return {
        "records": len(articles),
        "decisions": dict(counts),
        "domains": len(sources),
        "country_status": dict(Counter(s["verification_status"] for s in sources)),
        "included_focus": dict(Counter(r["focus"] for r in articles if r["decision"] == "include")),
        "note": "Integrity checks only; not independent methodological validation. No network calls.",
    }


def read_json(name):
    return json.loads((REVIEW / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    result = validate(
        read_json("classification_v1.json"),
        read_json("media_catalogue_v1.json"),
        read_json("pilot_review.json"),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
