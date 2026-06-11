"""Tests for E4-5: Behavioral diff on PR."""
import unittest
import tempfile
from pathlib import Path

from cherenkov.continuity.pr_diff_action import BehavioralDiff, run_pr_diff


class TestBehavioralDiff(unittest.TestCase):
    def setUp(self):
        self.base_sources: dict[str, list[str]] = {}
        self.pr_sources: dict[str, list[str]] = {}

    def test_identical_sources_no_diff(self):
        sources = {"openapi": ["stripe_spec.json"]}
        diff = BehavioralDiff(sources, sources)
        result = diff.compute()
        self.assertIsInstance(result, list)

    def test_empty_sources(self):
        diff = BehavioralDiff({}, {})
        result = diff.compute()
        self.assertEqual(result, [])

    def test_render_markdown_empty(self):
        diff = BehavioralDiff({}, {})
        md = diff.render_markdown([])
        self.assertIn("CHERENKOV Behavioral Diff Report", md)

    def test_render_markdown_with_diffs(self):
        diffs = [
            {
                "endpoint": "GET /users",
                "change": "status",
                "base": 200,
                "pr": 500,
                "intended": False,
                "description": "Status changed from 200 to 500",
            }
        ]
        diff = BehavioralDiff({}, {})
        md = diff.render_markdown(diffs)
        self.assertIn("GET /users", md)
        self.assertIn("200", md)
        self.assertIn("500", md)
        self.assertIn("No", md)  # intended=False


class TestRunPrDiff(unittest.TestCase):
    def test_run_with_temp_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.md"
            result = run_pr_diff(output_path=str(output))
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())
            content = output.read_text(encoding="utf-8")
            self.assertIn("CHERENKOV Behavioral Diff Report", content)

    def test_run_with_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.md"
            result = run_pr_diff(
                base_spec="stripe_spec.json",
                pr_spec="stripe_spec.json",
                output_path=str(output),
            )
            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
