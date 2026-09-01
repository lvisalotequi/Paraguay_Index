"""Offline integrity checks for the second pilot's review and valid-only output."""
import csv
import json
import unittest
from pathlib import Path
from review_candidate_gate import select

ROOT = Path(__file__).resolve().parent / 'output/pilot_2025_01_04_06'


class SecondReviewTests(unittest.TestCase):
    def setUp(self):
        self.review = json.loads((ROOT / 'review_complete_v1.json').read_text(encoding='utf-8'))
        self.catalogue = json.loads((ROOT / 'media_catalogue_v2.json').read_text(encoding='utf-8'))
        with (ROOT / 'candidates/monthly_2025-01_2025-01_pilot3d_from04.csv').open(encoding='utf-8-sig', newline='') as handle:
            self.rows = list(csv.DictReader(handle))

    def test_coverage_and_evidence(self):
        reviewed = self.review['articles']
        self.assertEqual(len(reviewed), 86)
        self.assertEqual({r['url'] for r in reviewed}, {r['url'] for r in self.rows})
        self.assertEqual({r['id'] for r in reviewed}, set(range(1, 87)))
        sources = {s['domain']: s for s in self.catalogue['sources']}
        self.assertEqual(len(sources), len(self.catalogue['sources']))
        for r in reviewed:
            self.assertTrue(r['reason'] and r['evidence_urls'])
            self.assertIn(r['domain'], sources)
            if r['reason_code'] == 'foreign_source':
                source = sources[r['domain']]
                self.assertEqual(source['verification_status'], 'verified')
                self.assertNotIn(source['country_verified'], ('PY', 'US', None))
            elif r['content_access'] in ('unavailable', 'changed'):
                self.assertEqual(r['decision'], 'doubtful')

    def test_selection_reproducible(self):
        result = select(self.rows, self.review, self.catalogue)
        self.assertEqual(result['counts'], {'include': 1, 'exclude': 51, 'doubtful': 34})
        self.assertEqual([r['review']['id'] for r in result['articles']], [22])
        saved = json.loads((ROOT / 'valid_only_v1.json').read_text(encoding='utf-8'))
        self.assertEqual(result['articles'], saved['articles'])
        self.assertEqual(result['counts'], saved['counts'])

    def test_original_receipt_matches(self):
        import hashlib
        folder = ROOT / 'candidates'
        receipt = next(folder.glob('*.complete.json'))
        raw = receipt.with_name(receipt.name.replace('.complete.json', '.csv'))
        info = json.loads(receipt.read_text(encoding='utf-8'))
        self.assertEqual(info['csv_sha256'], hashlib.sha256(raw.read_bytes()).hexdigest())
