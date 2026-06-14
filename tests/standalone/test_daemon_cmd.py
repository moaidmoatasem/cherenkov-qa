"""Tests for E4-4: Daemon mode."""

import unittest
import unittest.mock
import tempfile
from pathlib import Path

from cherenkov.stages.daemon_cmd import DivergenceQueue, run_daemon


class TestDivergenceQueue(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.queue_path = Path(self.tmpdir.name) / "queue.jsonl"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_push_and_pop(self):
        queue = DivergenceQueue(path=self.queue_path)
        queue.push({"id": "div-1", "severity": "high"})
        entries = queue.pop_all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], "div-1")
        self.assertEqual(entries[0]["severity"], "high")

    def test_pop_all_empty(self):
        queue = DivergenceQueue(path=self.queue_path)
        entries = queue.pop_all()
        self.assertEqual(entries, [])

    def test_count(self):
        queue = DivergenceQueue(path=self.queue_path)
        self.assertEqual(queue.count, 0)
        queue.push({"id": "div-1"})
        self.assertEqual(queue.count, 1)
        queue.push({"id": "div-2"})
        self.assertEqual(queue.count, 2)

    def test_pop_all_removes_file(self):
        queue = DivergenceQueue(path=self.queue_path)
        queue.push({"id": "div-1"})
        self.assertTrue(self.queue_path.exists())
        queue.pop_all()
        self.assertFalse(self.queue_path.exists())

    def test_multiple_entries(self):
        queue = DivergenceQueue(path=self.queue_path)
        queue.push({"id": "d1"})
        queue.push({"id": "d2"})
        queue.push({"id": "d3"})
        entries = queue.pop_all()
        self.assertEqual(len(entries), 3)

    def test_count_nonexistent_file(self):
        queue = DivergenceQueue(
            path=self.queue_path.parent / "nonexistent" / "queue.jsonl"
        )
        self.assertEqual(queue.count, 0)


class TestRunDaemon(unittest.TestCase):
    @unittest.mock.patch("cherenkov.core.config_loader.load_effective_config")
    @unittest.mock.patch("cherenkov.stages.daemon_cmd.DivergenceQueue")
    def test_run_daemon_zero_loops(self, mock_queue, mock_cfg):
        mock_cfg.return_value.autodetect_spec.return_value = []
        mock_queue.return_value = unittest.mock.MagicMock()
        result = run_daemon(interval_seconds=1, max_loops=1)
        self.assertEqual(result, 0)

    @unittest.mock.patch("cherenkov.core.config_loader.load_effective_config")
    @unittest.mock.patch("cherenkov.stages.daemon_cmd.DivergenceQueue")
    def test_run_daemon_multiple_loops(self, mock_queue, mock_cfg):
        mock_cfg.return_value.autodetect_spec.return_value = []
        mock_queue.return_value = unittest.mock.MagicMock()
        result = run_daemon(interval_seconds=1, max_loops=2)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
