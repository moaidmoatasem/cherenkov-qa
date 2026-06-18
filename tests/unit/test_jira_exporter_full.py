"""Unit tests for JiraExporter enhanced methods."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from cherenkov.validate.jira_exporter import JiraExporter


def _mock_response(data=None, status=200):
    """Create a mock urllib response."""
    resp = MagicMock()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    resp.read.return_value = json.dumps(data or {}).encode("utf-8")
    resp.status = status
    return resp


class TestJiraExporterFull(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(
            os.environ,
            {
                "CHERENKOV_JIRA_URL": "https://jira.example.com",
                "CHERENKOV_JIRA_TOKEN": "user:pass123",
                "CHERENKOV_JIRA_PROJECT": "QA",
            },
        )
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    def test_create_jira_issue_full_with_labels(self):
        captured_payload = {}

        def capture_request(url, data=None, headers={}, method="GET"):
            nonlocal captured_payload
            captured_payload = json.loads(data.decode("utf-8"))
            return _mock_response({"key": "QA-101"})

        with patch("urllib.request.Request", side_effect=capture_request):
            with patch(
                "urllib.request.urlopen", return_value=_mock_response({"key": "QA-101"})
            ):
                exporter = JiraExporter()
                result = exporter.create_jira_issue_full(
                    summary="Test with labels",
                    description="desc",
                    labels=["regression", "api"],
                )

        called_url = captured_payload.get("fields", {}).get("labels", [])
        self.assertEqual(called_url, ["regression", "api"])
        self.assertEqual(result, "QA-101")

    def test_create_jira_issue_full_with_priority(self):
        captured_payload = {}

        def capture_request(url, data=None, headers={}, method="GET"):
            nonlocal captured_payload
            captured_payload = json.loads(data.decode("utf-8"))
            return _mock_response({"key": "QA-102"})

        with patch("urllib.request.Request", side_effect=capture_request):
            with patch(
                "urllib.request.urlopen", return_value=_mock_response({"key": "QA-102"})
            ):
                exporter = JiraExporter()
                result = exporter.create_jira_issue_full(
                    summary="Test with priority",
                    description="desc",
                    priority="High",
                )

        self.assertEqual(captured_payload["fields"]["priority"], {"name": "High"})
        self.assertEqual(result, "QA-102")

    def test_create_jira_issue_full_with_components(self):
        captured_payload = {}

        def capture_request(url, data=None, headers={}, method="GET"):
            nonlocal captured_payload
            captured_payload = json.loads(data.decode("utf-8"))
            return _mock_response({"key": "QA-103"})

        with patch("urllib.request.Request", side_effect=capture_request):
            with patch(
                "urllib.request.urlopen", return_value=_mock_response({"key": "QA-103"})
            ):
                exporter = JiraExporter()
                result = exporter.create_jira_issue_full(
                    summary="Test with components",
                    description="desc",
                    components=["Backend", "API"],
                )

        self.assertEqual(
            captured_payload["fields"]["components"],
            [{"name": "Backend"}, {"name": "API"}],
        )
        self.assertEqual(result, "QA-103")

    def test_create_jira_issue_full_missing_env_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            exporter = JiraExporter()
            result = exporter.create_jira_issue_full(
                summary="No env",
                description="desc",
            )
        self.assertIsNone(result)

    def test_bulk_create(self):
        items = [
            {"summary": "Item 1", "description": "desc1", "labels": ["bug"]},
            {"summary": "Item 2", "description": "desc2"},
        ]
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return f"QA-{100 + call_count}"

        with patch.object(
            JiraExporter, "create_jira_issue_full", side_effect=mock_create
        ):
            exporter = JiraExporter()
            results = exporter.bulk_create(items)

        self.assertEqual(results, ["QA-101", "QA-102"])
        self.assertEqual(call_count, 2)

    def test_bulk_create_partial_failure(self):
        items = [
            {"summary": "Good", "description": "desc1"},
            {"summary": "Bad", "description": "desc2"},
            {"summary": "Good2", "description": "desc3"},
        ]
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Jira error")
            return f"QA-{100 + call_count}"

        with patch.object(
            JiraExporter, "create_jira_issue_full", side_effect=mock_create
        ):
            exporter = JiraExporter()
            results = exporter.bulk_create(items)

        self.assertEqual(results, ["QA-101", "QA-103"])

    def test_add_comment(self):
        captured_data = {}

        def capture_request(url, data=None, headers={}, method="GET"):
            nonlocal captured_data
            captured_data = json.loads(data.decode("utf-8"))
            return _mock_response({})

        with patch("urllib.request.Request", side_effect=capture_request):
            with patch("urllib.request.urlopen", return_value=_mock_response({})):
                exporter = JiraExporter()
                result = exporter.add_comment("QA-100", "This is a test comment")

        self.assertTrue(result)
        self.assertEqual(
            captured_data["body"]["content"][0]["content"][0]["text"],
            "This is a test comment",
        )

    def test_add_attachment_file_not_found(self):
        exporter = JiraExporter()
        result = exporter.add_comment("QA-100", "test comment")  # sanity check works
        result = exporter.add_attachment("QA-100", "/nonexistent/path/to/file.txt")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
