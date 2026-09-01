import unittest
from estimate_history import batches


class HistoricalEstimateTests(unittest.TestCase):
    def test_batches_are_chronological_and_skip_completed_usage(self):
        rows = [dict(month='a', status='dry_run', estimated_bytes=60),
                dict(month='b', status='completed', estimated_bytes=80),
                dict(month='c', status='dry_run', estimated_bytes=50)]
        result = batches(rows, 100)
        self.assertEqual(result, [dict(months=['a', 'b'], estimated_new_bytes=60),
                                  dict(months=['c'], estimated_new_bytes=50)])

    def test_single_month_over_cap_fails(self):
        with self.assertRaises(ValueError):
            batches([dict(month='x', status='dry_run', estimated_bytes=101)], 100)
