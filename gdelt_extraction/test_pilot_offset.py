import unittest
from datetime import date
from bilateral_media_extractor import MonthWindow, pilot_window, build_gdelt_sql


class OffsetTests(unittest.TestCase):
    def test_offset_and_light_fields(self):
        window = pilot_window(MonthWindow('2025-01', date(2025, 1, 1), date(2025, 1, 31)), 3, 4)
        self.assertEqual(window.end, date(2025, 1, 6))
        sql = build_gdelt_sql(window, 'candidates')
        for value in ["DATE('2025-01-01') month", "TIMESTAMP('2025-01-04')",
                      "TIMESTAMP('2025-01-07')", 'TRUE partial_month']:
            self.assertIn(value, sql)
        for value in ['g.Persons', 'g.Organizations', 'g.Themes']:
            self.assertNotIn(value, sql)

    def test_invalid_dates(self):
        window = MonthWindow('2025-02', date(2025, 2, 1), date(2025, 2, 28))
        for days, start in [(3, 27), (3, 0), (None, 4)]:
            with self.assertRaises(ValueError):
                pilot_window(window, days, start)

    def test_offset_ending_at_month_end_still_partial(self):
        window = pilot_window(MonthWindow('2025-01', date(2025, 1, 1), date(2025, 1, 31)), 3, 29)
        self.assertIn('TRUE partial_month', build_gdelt_sql(window, 'candidates'))
