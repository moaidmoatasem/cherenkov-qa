"""Unit tests for cherenkov/execution/demo_mode.py — MOCK_FINDINGS and generate_demo_findings."""
import unittest
from unittest.mock import MagicMock, patch


class TestMockFindings(unittest.TestCase):
    def setUp(self):
        from cherenkov.execution.demo_mode import MOCK_FINDINGS
        self.findings = MOCK_FINDINGS

    def test_three_findings_defined(self):
        self.assertEqual(len(self.findings), 3)

    def test_all_findings_have_required_fields(self):
        required = {"id", "endpoint", "method", "mutation_id", "diff", "rationale"}
        for f in self.findings:
            self.assertEqual(required, required & f.keys(), msg=f"Finding {f.get('id')} missing fields")

    def test_finding_ids_are_unique(self):
        ids = [f["id"] for f in self.findings]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_endpoints_are_nonempty_strings(self):
        for f in self.findings:
            self.assertIsInstance(f["endpoint"], str)
            self.assertTrue(f["endpoint"])

    def test_diff_strings_contain_expected_and_received(self):
        for f in self.findings:
            diff = f["diff"]
            self.assertTrue(
                "Expected" in diff or "Received" in diff,
                msg=f"Finding {f['id']} diff does not mention Expected/Received",
            )


class TestGenerateDemoFindings(unittest.TestCase):
    @patch("cherenkov.execution.demo_mode.HitlQueue")
    def test_generate_demo_findings_enqueues_items(self, mock_queue_cls):
        from cherenkov.execution.demo_mode import generate_demo_findings, MOCK_FINDINGS

        mock_queue = MagicMock()
        mock_queue_cls.return_value = mock_queue

        generate_demo_findings()

        self.assertEqual(mock_queue.enqueue.call_count, len(MOCK_FINDINGS))

    @patch("cherenkov.execution.demo_mode.HitlQueue")
    def test_generate_demo_findings_does_not_raise(self, mock_queue_cls):
        mock_queue_cls.return_value = MagicMock()
        from cherenkov.execution.demo_mode import generate_demo_findings
        try:
            generate_demo_findings()
        except Exception as e:
            self.fail(f"generate_demo_findings raised unexpectedly: {e}")
