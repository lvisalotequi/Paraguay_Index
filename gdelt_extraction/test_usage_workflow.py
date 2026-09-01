import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from usage_ledger import build, refresh
import extraction_workflow as workflow


class UsageLedgerTests(unittest.TestCase):
    def test_ledger_deduplicates_jobs_and_sums_month(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, job, value in [('a', 'job-a', 100), ('b', 'job-b', 250)]:
                path = root / name
                path.mkdir()
                (path / f'{name}.sql').write_text(f'SELECT {value}', encoding='utf-8')
                (path / f'{name}.complete.json').write_text(json.dumps(dict(
                    job_id=job, bytes_billed=value, completed_at='2026-08-30T10:00:00-05:00',
                    csv_sha256=name)), encoding='utf-8')
            result = build(root)
            self.assertEqual(result['job_count'], 2)
            self.assertEqual(result['total_bytes_billed'], 350)
            self.assertEqual(result['totals_by_calendar_month']['2026-08'], 350)
            self.assertTrue(all(e['sql_sha256'] for e in result['entries']))

    def test_invalid_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.complete.json'
            path.write_text('{"bytes_billed": 1}', encoding='utf-8')
            with self.assertRaises(ValueError):
                build(folder)

    def test_refresh_writes_machine_readable_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / 'ledger.json'
            result = refresh(Path(folder) / 'empty', ledger)
            self.assertEqual(result, json.loads(ledger.read_text(encoding='utf-8')))


class WorkflowTests(unittest.TestCase):
    def test_config_is_low_intervention_and_safe(self):
        config = workflow.load(workflow.CONFIG_PATH)
        self.assertEqual(config['profile'], 'proxy_b_metrics')
        self.assertEqual(config['project'], 'us-py-engagement-idx')
        self.assertLessEqual(config['per_query_gib'], config['per_run_gib'])
        self.assertLessEqual(config['per_run_gib'], config['monthly_ledger_gib'])

    def test_execute_rejects_modified_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'plan.json'
            path.write_text(json.dumps(dict(status='planned_not_executed', config={},
                                            config_sha256='wrong')), encoding='utf-8')
            with self.assertRaises(RuntimeError):
                workflow.execute_plan(path)

    def test_execute_rechecks_monthly_budget(self):
        config = workflow.load(workflow.CONFIG_PATH)
        plan = dict(status='planned_not_executed', config=config,
                    config_sha256=workflow.digest(config), start='2025-01', end='2025-01',
                    sql=[], reserved_maximum_bytes=config['monthly_ledger_gib'] * 1024**3)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'plan.json'
            path.write_text(json.dumps(plan), encoding='utf-8')
            ledger = dict(job_count=1, total_bytes_billed=1,
                          totals_by_calendar_month={workflow.datetime.now().astimezone().strftime('%Y-%m'): 1})
            with patch.object(workflow, 'sql_items', return_value=[]), \
                 patch.object(workflow, 'refresh', return_value=ledger):
                with self.assertRaisesRegex(RuntimeError, 'monthly ledger'):
                    workflow.execute_plan(path)
