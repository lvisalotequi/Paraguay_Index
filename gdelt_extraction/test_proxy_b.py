import csv
import json
import tempfile
import unittest
from pathlib import Path
from bilateral_media_extractor import parser
from proxy_b import ROOT, process, process_csv


class AcceptedProxyTests(unittest.TestCase):
    def test_future_extraction_runs_proxy_and_checks_billing_twice(self):
        import contextlib
        import io
        import pandas as pd
        from unittest.mock import MagicMock, patch
        from bilateral_media_extractor import run_gdelt
        path = ROOT / 'output/theme_estimates_v1/april_pilot/candidates_themes/2025-04-pilot3d-from04_efc7321c426cb3c7babe.csv'
        dry = MagicMock(total_bytes_processed=1024)
        job = MagicMock(total_bytes_processed=1024, total_bytes_billed=1024)
        job.result.return_value.to_dataframe.return_value = pd.read_csv(path)
        client = MagicMock()
        client.query.side_effect = [dry, job]
        with tempfile.TemporaryDirectory() as folder:
            args = parser().parse_args(['gdelt', '--project', 'leandro-gdelt-2026-abc',
                                       '--start', '2025-04', '--end', '2025-04',
                                       '--pilot-days', '3', '--pilot-start-day', '4',
                                       '--output', folder, '--execute'])
            with patch('google.cloud.bigquery.Client', return_value=client), \
                 patch('bilateral_media_extractor.require_unbilled_project') as check, \
                 contextlib.redirect_stdout(io.StringIO()):
                run_gdelt(args)
            self.assertEqual(check.call_count, 2)
            self.assertEqual(len(list(Path(folder).rglob('proxy_b_*.json'))), 1)
            self.assertTrue(list(Path(folder).rglob('*.complete.json')))

    def test_defaults(self):
        args = parser().parse_args(['gdelt', '--project', 'leandro-gdelt-2026-abc'])
        self.assertEqual(args.profile, 'candidates_themes')
        self.assertEqual((args.max_gib, args.max_total_gib), (1, 1))
        self.assertFalse(args.execute)

    def test_local_pilots(self):
        for path, expected in [('output/gdelt/audit/2025-01-pilot3d_1866e9bca2eaae69a1f2.csv', 14),
                               ('output/theme_estimates_v1/april_pilot/candidates_themes/2025-04-pilot3d-from04_efc7321c426cb3c7babe.csv', 20)]:
            result = process_csv(ROOT / path)
            self.assertEqual(result['selected_count'], expected)
            self.assertEqual(result['metrics'][-1]['proxy_articles'], expected)
            self.assertTrue(all(r['selection_status'] == 'proxy_b_unvalidated' for r in result['articles']))
            self.assertTrue(all(m['partial_month'] for m in result['metrics']))

    def test_aggregate_pilot_matches_local_proxy(self):
        aggregate = ROOT / 'output/cost_efficiency_v1/april_pilot/proxy_b_metrics/monthly_2025-04_2025-04_pilot3d_from04.csv'
        with aggregate.open(encoding='utf-8-sig', newline='') as f:
            remote = {r['source_country']: r for r in csv.DictReader(f)}
        local = json.loads((ROOT / 'output/proxy_b_accepted_v1/april.json').read_text(encoding='utf-8'))
        for metric in local['metrics']:
            row = remote[metric['source_country']]
            self.assertEqual(int(row['proxy_articles']), metric['proxy_articles'])
            self.assertEqual(int(row['unique_domains']), metric['unique_domains'])
            for field in ('tone_mean', 'positive_score_mean', 'negative_score_mean'):
                self.assertAlmostEqual(float(row[field]), metric[field])

    def test_completed_month_aggregate_consistency(self):
        path = ROOT / 'output/cost_efficiency_v1/april_month/proxy_b_metrics/monthly_2025-04_2025-04.csv'
        with path.open(encoding='utf-8-sig', newline='') as f:
            rows = {r['source_country']: r for r in csv.DictReader(f)}
        self.assertEqual(set(rows), {'PY', 'US', 'BOTH'})
        self.assertEqual(int(rows['BOTH']['proxy_articles']),
                         int(rows['PY']['proxy_articles']) + int(rows['US']['proxy_articles']))
        self.assertEqual(rows['BOTH']['partial_month'], 'False')
        self.assertEqual(rows['BOTH']['period_start'], '2025-04-01')
        self.assertEqual(rows['BOTH']['period_end'], '2025-04-30')
        for row in rows.values():
            self.assertEqual(int(row['proxy_articles']), int(row['tone_n']))
            self.assertEqual(int(row['proxy_articles']), int(row['positive_score_n']))
            self.assertEqual(int(row['proxy_articles']), int(row['negative_score_n']))

    def test_no_overwrite_or_missing_fields(self):
        with self.assertRaises(ValueError):
            process([{'url': 'https://example.org'}])
        path = ROOT / 'output/gdelt/audit/2025-01-pilot3d_1866e9bca2eaae69a1f2.csv'
        with self.assertRaises(FileExistsError):
            process_csv(path, path)
        with path.open(encoding='utf-8-sig', newline='') as f:
            row = next(csv.DictReader(f))
        row['themes'] = ''
        result = process([row, row])
        self.assertEqual(result['deduplicated_rows'], 1)
        self.assertEqual(result['selected_count'], 0)
        self.assertIsNone(result['metrics'][-1]['tone_mean'])
