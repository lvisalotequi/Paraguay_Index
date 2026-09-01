import csv
import json
import unittest
from collections import Counter
from pathlib import Path
from institutional_proxy_alternatives import compare


class AlternativesTests(unittest.TestCase):
    def test_economy_needs_institution(self):
        self.assertFalse(compare('EPU_ECONOMY;', True)['selected']['B'])
        self.assertTrue(compare('EPU_ECONOMY;GENERAL_GOVERNMENT;', True)['selected']['B'])
        self.assertFalse(compare('EPU_ECONOMY_EXTRA;GENERAL_GOVERNMENT;', True)['selected']['B'])
        self.assertFalse(any(compare('SANCTIONS;', False)['selected'].values()))
        self.assertFalse(any(compare(None, True)['selected'].values()))

    def test_reproduce_saved_results(self):
        root = Path(__file__).parent
        result = json.loads((root / 'output/rule_alternatives_v1/comparison.json').read_text(encoding='utf-8'))
        paths = {'jan': 'output/gdelt/audit/2025-01-pilot3d_1866e9bca2eaae69a1f2.csv',
                 'apr': 'output/theme_estimates_v1/april_pilot/candidates_themes/2025-04-pilot3d-from04_efc7321c426cb3c7babe.csv'}
        raw = {}
        for pilot, path in paths.items():
            with (root / path).open(encoding='utf-8-sig', newline='') as f:
                raw[pilot] = {r['url']: r for r in csv.DictReader(f)}
        self.assertEqual(len(result['rows']), 155)
        for r in result['rows']:
            actual = compare(raw[r['pilot']][r['url']]['themes'], r['base'])
            self.assertEqual(actual['selected'], r['selected'])
            self.assertEqual(set(actual['economic_hits']), set(r['economic_hits']))
            self.assertFalse(r['selected']['A'] and not r['selected']['B'])
            self.assertFalse(r['selected']['B'] and not r['selected']['C'])
        for item in result['summary']:
            subset = [r for r in result['rows'] if r['pilot'] == item['pilot'] and r['selected'][item['option']]]
            self.assertEqual(len(subset), item['selected'])
            counts = Counter(r['reference'] for r in subset)
            for key, value in item['counts'].items():
                self.assertEqual(counts[key], value)
