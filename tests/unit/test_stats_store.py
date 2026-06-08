import os
import tempfile
import unittest
from cherenkov.core.stats_store import StatsStore


class TestStatsStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.store = StatsStore(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_record_run(self):
        self.store.record_run(run_id="test-run", success=True,
                              scenarios_passed=3, scenarios_total=3,
                              total_duration_ms=45)
        summary = self.store.get_run_summary()
        self.assertGreaterEqual(summary["total_runs"], 1)

    def test_record_fail(self):
        self.store.record_run(run_id="fail-run", success=False,
                              scenarios_passed=1, scenarios_total=3)
        summary = self.store.get_run_summary()
        self.assertEqual(summary["total_runs"], 1)
        self.assertEqual(summary["successful_runs"], 0)

    def test_get_run_summary_empty(self):
        summary = self.store.get_run_summary()
        self.assertEqual(summary["total_runs"], 0)
        self.assertEqual(summary["successful_runs"], 0)

    def test_get_recent_runs(self):
        self.store.record_run(run_id="r1", success=True)
        self.store.record_run(run_id="r2", success=True)
        runs = self.store.get_recent_runs(limit=10)
        self.assertEqual(len(runs), 2)

    def test_get_recent_runs_limit(self):
        for i in range(5):
            self.store.record_run(run_id=f"r{i}", success=True)
        runs = self.store.get_recent_runs(limit=3)
        self.assertEqual(len(runs), 3)

    def test_snapshot(self):
        self.store.snapshot(verdict_count=10, idiom_count=5, source="cli")
