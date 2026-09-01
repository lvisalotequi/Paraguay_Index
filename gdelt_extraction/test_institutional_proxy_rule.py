import csv
import json
import unittest
from pathlib import Path
from institutional_proxy_rule import classify


class RuleTests(unittest.TestCase):
    def test_exact_tokens(self):
        self.assertEqual(classify('NOT_SANCTIONS;SANCTIONS_EXTRA;', True)['group'], 'cooccurrence_only')
        self.assertEqual(classify('SANCTIONS;', True)['group'], 'core_proxy')

    def test_conjunction_and_missing(self):
        self.assertEqual(classify('MILITARY;BORDER;', True)['group'], 'core_proxy')
        self.assertEqual(classify('MILITARY;', True)['group'], 'extended_only')
        self.assertEqual(classify(None, True)['group'], 'missing_themes')
        self.assertEqual(classify('SANCTIONS;', None)['group'], 'source_or_language_unresolved')

    def test_saved_diagnostic(self):
        root = Path(__file__).parent
        saved = json.loads((root / 'output/rule_design_v1/pilot_diagnostic.json').read_text(encoding='utf-8'))
        with (root / 'output/gdelt/audit/2025-01-pilot3d_1866e9bca2eaae69a1f2.csv').open(encoding='utf-8-sig', newline='') as f:
            raw = {r['url']: r for r in csv.DictReader(f)}
        self.assertEqual(len(raw), saved['n'])
        for r in saved['rows']:
            result = classify(raw[r['url']]['themes'], r['source_snapshot_ok'])
            self.assertEqual(result['group'], r['group'])
            if r['source_snapshot_ok']:
                self.assertEqual(result['hits'], r['hits'])
