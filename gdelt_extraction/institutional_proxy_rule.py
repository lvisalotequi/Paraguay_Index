"""Exploratory offline theme classifier; no network or extraction changes.

Caller must establish country cooccurrence, source panel, language, dates and
URL deduplication. None/False eligibility must never enter proxy metrics.
Outputs are proxy labels, never individual relevance adjudications.
"""
import json
from pathlib import Path


def classify(themes, base_eligible, config=None):
    if base_eligible is not True:
        return {'group': 'source_or_language_unresolved', 'hits': {}}
    if themes is None:
        return {'group': 'missing_themes', 'hits': {}}
    if config is None:
        config = json.loads(Path(__file__).with_name('institutional_proxy_rule_v1.json').read_text(encoding='utf-8'))
    tokens = {t.strip() for t in themes.split(';') if t.strip()}
    hits = {k: [t for t in config[k] if t in tokens] for k in ('D', 'I', 'R')}
    if hits['D'] or (hits['I'] and hits['R']):
        group = 'core_proxy'
    elif hits['I'] or hits['R']:
        group = 'extended_only'
    else:
        group = 'cooccurrence_only'
    return {'group': group, 'hits': hits}
