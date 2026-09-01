"""Offline experimental alternatives; never alters extraction or review labels."""
import json
from pathlib import Path
from institutional_proxy_rule import classify


def compare(themes, base_eligible):
    config = json.loads(Path(__file__).with_name('institutional_proxy_alternatives.json').read_text(encoding='utf-8'))
    original = classify(themes, base_eligible)
    tokens = {t.strip() for t in (themes or '').split(';') if t.strip()}
    economic = [t for t in config['E'] if t in tokens]
    hits = original['hits']
    d, i, r = (bool(hits.get(k)) for k in ('D', 'I', 'R'))
    enabled = base_eligible is True and themes is not None
    return dict(selected=dict(A=enabled and (d or (i and r)),
                              B=enabled and (d or (i and (r or bool(economic)))),
                              C=enabled and (d or i or r)), economic_hits=economic)
