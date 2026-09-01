import unittest
from datetime import date
from bilateral_media_extractor import MonthWindow, build_gdelt_sql, parser


class ThemeExtractionTests(unittest.TestCase):
    def test_only_adds_theme_column(self):
        window = MonthWindow('2025-04', date(2025, 4, 1), date(2025, 4, 30))
        plain = build_gdelt_sql(window, 'candidates')
        rich = build_gdelt_sql(window, 'candidates_themes')
        self.assertEqual(rich.replace('    g.Themes themes,\n', '').replace('polarity, themes\n', 'polarity\n'), plain)
        self.assertNotIn('g.Persons', rich)
        self.assertNotIn('g.Organizations', rich)
        self.assertIn('geographic_cooccurrence_unvalidated', rich)

    def test_cli_dry_by_default(self):
        args = parser().parse_args(['gdelt', '--project', 'test', '--profile', 'candidates_themes'])
        self.assertFalse(args.execute)

    def test_proxy_metrics_are_aggregate_and_use_b(self):
        window = MonthWindow('2025-04', date(2025, 4, 4), date(2025, 4, 6))
        sql = build_gdelt_sql(window, 'proxy_b_metrics')
        self.assertIn("hit_d OR (hit_i AND (hit_r OR hit_e))", sql)
        self.assertIn("COUNT(*) proxy_articles", sql)
        self.assertIn("NET.HOST(g.DocumentIdentifier)", sql)
        self.assertNotIn('g.Persons', sql)
        self.assertNotIn('g.Organizations', sql)
        self.assertNotIn('SELECT g.Themes', sql)
