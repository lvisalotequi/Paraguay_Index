import unittest

from historical_campaign import pending_units


class HistoricalCampaignTests(unittest.TestCase):
    def test_completed_month_splits_and_is_skipped(self):
        estimate = {
            'batches': [{'months': ['2025-02', '2025-03', '2025-04', '2025-05']}],
            'months': [
                {'month': '2025-02', 'status': 'dry_run', 'sql_sha256': 'a'},
                {'month': '2025-03', 'status': 'dry_run', 'sql_sha256': 'b'},
                {'month': '2025-04', 'status': 'dry_run', 'sql_sha256': 'c'},
                {'month': '2025-05', 'status': 'dry_run', 'sql_sha256': 'd'},
            ],
        }
        self.assertEqual(pending_units(estimate, {'c'}), [(1, ['2025-02', '2025-03']), (1, ['2025-05'])])


if __name__ == '__main__':
    unittest.main()
