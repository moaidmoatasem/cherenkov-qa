# TODO: convert to pytest — complex file (>150 lines with setUp/tearDown)
"""
Tests for Suggest-Only Jira Exporter (Issue #250).
"""

import os
import tempfile
import unittest

from cherenkov.validate.jira_exporter import JiraExporter


class TestJiraExporter(unittest.TestCase):
    """Tests for copy-ready Jira ticket generation."""

    def setUp(self):
        self.exporter = JiraExporter("test_run")
        self.tmpdir = tempfile.mkdtemp()
        # Override ticket dir to use temp
        self.exporter.ticket_dir = os.path.join(self.tmpdir, "jira_tickets")

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_format_ticket_basic(self):
        """Test basic ticket formatting with required fields."""
        content = self.exporter.format_ticket(
            scenario_id="SCN-001",
            failure_class="HTTP_500",
            error_message="Internal server error",
        )
        self.assertIn("SCN-001", content)
        self.assertIn("HTTP_500", content)
        self.assertIn("Internal server error", content)
        self.assertIn("CHERENKOV QA", content)

    def test_format_ticket_with_http_status(self):
        """Test ticket includes expected/received status codes."""
        content = self.exporter.format_ticket(
            scenario_id="SCN-002",
            failure_class="STATUS_MISMATCH",
            error_message="Expected 201 got 500",
            expected_status=201,
            received_status=500,
        )
        self.assertIn("Expected `201`", content)
        self.assertIn("Received `500`", content)

    def test_format_ticket_with_hypothesis(self):
        """Test ticket includes AI root-cause hypothesis."""
        content = self.exporter.format_ticket(
            scenario_id="SCN-003",
            failure_class="TIMEOUT",
            error_message="Request timed out",
            hypothesis="Database connection pool exhausted",
        )
        self.assertIn("AI Root-Cause Hypothesis", content)
        self.assertIn("Database connection pool exhausted", content)

    def test_format_ticket_with_resolution_steps(self):
        """Test ticket includes actionable resolution steps."""
        content = self.exporter.format_ticket(
            scenario_id="SCN-004",
            failure_class="VALIDATION_ERROR",
            error_message="Invalid email format",
            resolution_steps=["Add email validation", "Return 400 with details"],
        )
        self.assertIn("Actionable Resolution Steps", content)
        self.assertIn("1. Add email validation", content)
        self.assertIn("2. Return 400 with details", content)

    def test_format_ticket_with_rag_correlation(self):
        """Test ticket includes RAG incident correlation."""
        content = self.exporter.format_ticket(
            scenario_id="SCN-005",
            failure_class="RATE_LIMIT",
            error_message="Too many requests",
            similar_cases_count=3,
        )
        self.assertIn("RAG Incident Correlation", content)
        self.assertIn("**3** similar historical failure(s)", content)

    def test_format_ticket_zero_rag_cases(self):
        """Test ticket handles zero similar cases honestly."""
        content = self.exporter.format_ticket(
            scenario_id="SCN-006",
            failure_class="UNKNOWN",
            error_message="Something broke",
            similar_cases_count=0,
        )
        self.assertIn("No similar historical failure cases detected", content)

    def test_format_ticket_with_compliance_score(self):
        """Test ticket includes MENA compliance score."""
        content = self.exporter.format_ticket(
            scenario_id="SCN-007",
            failure_class="AUTH_FAILURE",
            error_message="Invalid token",
            compliance_score=60,
        )
        self.assertIn("Cybersecurity Compliance Status", content)
        self.assertIn("60%", content)
        self.assertIn("SAMA CCSF", content)

    def test_export_ticket_writes_file(self):
        """Test export_ticket writes markdown file to disk."""
        path = self.exporter.export_ticket(
            scenario_id="SCN-008",
            failure_class="TEST_FAILURE",
            error_message="Test error",
        )
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith(".md"))
        with open(path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("SCN-008", content)

    def test_export_ticket_creates_directory(self):
        """Test export_ticket creates ticket directory if missing."""
        new_dir = os.path.join(self.tmpdir, "new_tickets")
        self.exporter.ticket_dir = new_dir

        path = self.exporter.export_ticket(
            scenario_id="SCN-009",
            failure_class="TEST_FAILURE",
            error_message="Test error",
        )
        self.assertTrue(os.path.exists(new_dir))
        self.assertTrue(os.path.exists(path))

    def test_filename_includes_timestamp(self):
        """Test exported filename includes timestamp for uniqueness."""
        import time

        original_time = time.time

        call_count = [0]

        def mock_time():
            call_count[0] += 1
            return 1000000 + call_count[0]

        time.time = mock_time
        try:
            path1 = self.exporter.export_ticket(
                scenario_id="SCN-010", failure_class="TEST", error_message="Error 1"
            )
            path2 = self.exporter.export_ticket(
                scenario_id="SCN-010", failure_class="TEST", error_message="Error 2"
            )
            self.assertNotEqual(path1, path2)
            self.assertTrue(os.path.exists(path1))
            self.assertTrue(os.path.exists(path2))
        finally:
            time.time = original_time


if __name__ == "__main__":
    unittest.main()
