import unittest
from recovery_sampling import sample, manifest, outcome_bounds


class RecoveryTests(unittest.TestCase):
    def test_second_review_preserves_sample_and_missingness(self):
        import json
        from recovery_sampling import ROOT
        from summarize_recovery import summarize
        old = summarize()
        new = summarize(ROOT / 'output/recovery_pilots_v2')
        self.assertEqual(sum(p['recovered_texts'] for p in old['pilots']), 3)
        self.assertEqual(sum(p['recovered_texts'] for p in new['pilots']), 5)
        self.assertEqual(new['new_confirmed_articles'], old['new_confirmed_articles'])
        self.assertIsNone(new['general_recovery_percentage'])
        folder = ROOT / 'output/recovery_pilots_v2'
        self.assertEqual(new, json.loads((folder / 'summary.json').read_text(encoding='utf-8')))
        rows = json.loads((folder / 'sample_review.json').read_text(encoding='utf-8'))['articles']
        pending = [r for r in rows if r['decision'] == 'doubtful']
        self.assertEqual(len(pending), 17)
        self.assertEqual(sum(r['content_access'] not in ('full', 'recovered') for r in pending), 12)
        january = {r['id']: r for r in rows if r['pilot'] == '2025-01-04_06'}
        self.assertEqual(january[17]['decision'], 'doubtful')
        self.assertEqual(january[64]['decision'], 'exclude')
        self.assertEqual(january[47]['content_access'], 'changed')

    def test_order_independent(self):
        rows = [dict(url=f'https://example.org/{i}') for i in range(30)]
        self.assertEqual(sample(rows, 10, 'x'), sample(rows[::-1], 10, 'x'))
        self.assertEqual(len(sample(rows, 10, 'x')), 10)

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            sample([dict(url='a'), dict(url='a')], 1, 'x')

    def test_bounds_not_zero_for_missing(self):
        self.assertEqual(outcome_bounds(4, 10, 6)['possible_fraction'], .5)
        self.assertEqual(outcome_bounds(4, 10, 6)['confirmed_fraction'], .2)
        self.assertIsNone(outcome_bounds(0, 0, 0)['confirmed_fraction'])

    def test_sampling_frame(self):
        m = manifest()
        self.assertEqual(sum(s['sample_size'] for s in m['strata'] if s['pilot'] != '2025-01-04_06'), 40)
        for r in m['articles']:
            if r['pilot'] == '2025-01-04_06':
                self.assertIn(r['previous_review']['content_access'], ('unavailable', 'changed'))
            else:
                self.assertEqual(r['initial_decision'], 'unreviewed')
            self.assertTrue(0 < r['inclusion_probability'] <= 1)

    def test_summary_integrity(self):
        from summarize_recovery import summarize
        result = summarize()
        self.assertEqual([p['downloaded_candidates'] for p in result['pilots']], [86, 88, 91])
        self.assertEqual([p['sample_size'] for p in result['pilots']], [6, 20, 20])
        self.assertEqual(result['new_query_bytes_billed'], 628097024)
        self.assertEqual(len(result['new_confirmed_articles']), 3)
        self.assertIsNone(result['general_recovery_percentage'])
        self.assertEqual(sum(p['recovery_attempted'] for p in result['pilots']), 17)
        self.assertEqual(sum(p['recovered_texts'] for p in result['pilots']), 3)
