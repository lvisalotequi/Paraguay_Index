import unittest
from review_candidate_gate import select


class GateTests(unittest.TestCase):
    def test_fail_closed(self):
        row = {'url': 'https://example.com/article', 'language': 'spa'}
        source = {'domain': 'example.com', 'country_verified': 'PY', 'verification_status': 'verified'}
        review = {'url': row['url'], 'decision': 'include', 'content_access': 'full',
                  'focus': 'central', 'reason': 'Evidence of relation', 'evidence_urls': [row['url']]}
        def count(r, s=source):
            return select([row], {'articles': r}, {'sources': [s]})['selected_count']
        self.assertEqual(count([review]), 1)
        self.assertEqual(count([]), 0)
        for change in [{'decision': 'doubtful'}, {'content_access': 'partial'}, {'focus': 'none'}, {'evidence_urls': []}]:
            self.assertEqual(count([{**review, **change}]), 0)
        self.assertEqual(count([review], {**source, 'country_verified': 'DO'}), 0)
        self.assertEqual(count([review], {**source, 'verification_status': 'unknown'}), 0)
