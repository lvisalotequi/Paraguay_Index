"""Offline safety/regression tests. All BigQuery calls are mocked."""
import contextlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import bilateral_media_extractor as app


class Tests(unittest.TestCase):
    def args(self, output, *extra):
        return app.parser().parse_args([
            'gdelt', '--project', 'leandro-gdelt-2026-abc', '--start', '2025-01',
            '--end', '2025-01', '--output', output, '--profile', 'articles',
            '--max-gib', '5', '--max-total-gib', '5', *extra])

    def dry(self, size=1024):
        return MagicMock(total_bytes_processed=size)

    def run_with(self, args, responses, billing_error=None):
        client = MagicMock()
        client.query.side_effect = responses
        with patch('google.cloud.bigquery.Client', return_value=client), \
             patch.object(app, 'require_unbilled_project', side_effect=billing_error), \
             contextlib.redirect_stdout(io.StringIO()):
            app.run_gdelt(args)
        return client

    def test_default_dry_run(self):
        with tempfile.TemporaryDirectory() as folder:
            c = self.run_with(self.args(folder), [self.dry()])
            self.assertEqual(c.query.call_count, 1)
            self.assertTrue(c.query.call_args.kwargs['job_config'].dry_run)

    def test_no_queries_above_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'max-gib'):
                self.run_with(self.args(folder, '--execute'), [self.dry(6 * app.GIB)])
            self.assertFalse(list(Path(folder).rglob('*.reserved.json')))

    def test_total_cap_checked_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            args = self.args(folder, '--execute', '--end', '2025-02')
            with self.assertRaisesRegex(ValueError, 'max-total-gib'):
                self.run_with(args, [self.dry(3 * app.GIB), self.dry(3 * app.GIB)])
            self.assertFalse(list(Path(folder).rglob('*.reserved.json')))

    def test_unknown_estimate_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'estimate'):
                self.run_with(self.args(folder, '--execute'), [self.dry(None)])

    def test_billing_check_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'billing unavailable'):
                self.run_with(self.args(folder, '--execute'), [self.dry()],
                              RuntimeError('billing unavailable'))
            self.assertFalse(list(Path(folder).rglob('*.reserved.json')))

    def test_cache_prevents_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            job = MagicMock(total_bytes_processed=1024, total_bytes_billed=1024)
            job.result.return_value.to_dataframe.return_value = pd.DataFrame([
                dict(month='2025-01-01', source_country='BOTH', unique_articles=1)])
            c = self.run_with(self.args(folder, '--execute'), [self.dry(), job])
            executed = c.query.call_args.kwargs
            self.assertLessEqual(executed['job_config'].maximum_bytes_billed, 5 * app.GIB)
            self.assertIsNone(executed['job_retry'])
            c = self.run_with(self.args(folder, '--execute'), [])
            c.query.assert_not_called()

    def test_ambiguous_submission_not_repeated(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                self.run_with(self.args(folder, '--execute'),
                              [self.dry(), RuntimeError('interrupted')])
            with self.assertRaisesRegex(RuntimeError, 'Previous job'):
                self.run_with(self.args(folder, '--execute'), [])

    def test_sql_profiles_and_units(self):
        w = app.MonthWindow('2025-01', date(2025, 1, 1), date(2025, 1, 31))
        articles = app.build_gdelt_sql(w)
        events = app.build_gdelt_sql(w, 'events')
        self.assertNotIn('eventmentions_partitioned', articles)
        self.assertIn('g.Locations', articles)
        self.assertIn('GROUPING(corpus.source_country)', articles)
        self.assertNotIn('V2Locations', articles)
        self.assertIn("r'#.*$'", articles)
        self.assertNotIn("r'[?#]", articles)
        self.assertIn("'PRY'", events)
        self.assertIn("'USA'", events)
        self.assertNotIn('e.AvgTone', events)
        self.assertIn('FROM per_event', events)
        self.assertIn('first_recorded_same_month', events)

    def test_partial_pilot(self):
        w = app.MonthWindow('pilot', date(2025, 1, 1), date(2025, 1, 3))
        for profile in ('articles', 'events', 'audit', 'candidates'):
            sql = app.build_gdelt_sql(w, profile)
            self.assertIn('TRUE partial_month', sql)
            self.assertIn("TIMESTAMP('2025-01-04')", sql)

    def test_candidates_are_explicitly_unvalidated(self):
        w = app.MonthWindow('2025-01', date(2025, 1, 1), date(2025, 1, 31))
        sql = app.build_gdelt_sql(w, 'candidates')
        self.assertIn('geographic_cooccurrence_unvalidated', sql)
        self.assertIn('WHERE mentions_py AND mentions_us', sql)

    def test_calendar(self):
        self.assertEqual(app.last_complete_month(date(2026, 1, 1)), date(2025, 12, 1))
        self.assertEqual(len(list(app.month_windows(date(2025, 12, 1), date(2026, 1, 1)))), 2)

    def test_billing_response(self):
        project = 'leandro-gdelt-2026-abc'
        app.validate_billing_info(dict(projectId=project, billingEnabled=False,
                                       billingAccountName=''), project)
        for info in ({}, dict(projectId=project, billingEnabled=True),
                     dict(projectId=project, billingEnabled=False, billingAccountName='linked'),
                     dict(projectId='other', billingEnabled=False)):
            with self.assertRaises(RuntimeError):
                app.validate_billing_info(info, project)


if __name__ == '__main__':
    unittest.main()
