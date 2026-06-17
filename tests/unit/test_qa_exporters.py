"""
Unit tests for Xray Cloud and Zephyr Scale exporters.

All external HTTP calls are mocked — no live network required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

from cherenkov.adapters.exporters.xray_exporter import XrayExporter
from cherenkov.adapters.exporters.zephyr_exporter import ZephyrExporter


# ── Shared fixture ────────────────────────────────────────────────────────────

_RESULTS_MIXED = {
    "run_id": "test-run-001",
    "reports": [
        {"scenario_id": "sc-pass", "method": "GET", "endpoint": "/health", "passed": True, "error": ""},
        {"scenario_id": "sc-fail", "method": "POST", "endpoint": "/payments", "passed": False,
         "error": "Expected 201 got 400"},
    ],
}

_RESULTS_ALL_PASS = {
    "run_id": "test-run-002",
    "reports": [
        {"scenario_id": "sc-ok", "method": "GET", "endpoint": "/items", "passed": True, "error": ""},
    ],
}


# ── XrayExporter tests ────────────────────────────────────────────────────────

class TestXrayExporter:

    @pytest.fixture
    def configured(self) -> XrayExporter:
        return XrayExporter(client_id="cid", client_secret="csecret", project_key="QA")

    @pytest.fixture
    def unconfigured(self) -> XrayExporter:
        return XrayExporter(client_id="", client_secret="", project_key="QA")

    def test_is_configured_true(self, configured: XrayExporter):
        assert configured.is_configured is True

    def test_is_configured_false(self, unconfigured: XrayExporter):
        assert unconfigured.is_configured is False

    def test_import_execution_raises_when_unconfigured(self, unconfigured: XrayExporter):
        with pytest.raises(ValueError, match="credentials not configured"):
            unconfigured.import_execution(_RESULTS_MIXED)

    @patch("cherenkov.adapters.exporters.xray_exporter.requests.post")
    def test_authenticate_caches_token(self, mock_post: MagicMock, configured: XrayExporter):
        mock_auth_resp = MagicMock()
        mock_auth_resp.json.return_value = "my-bearer-token"
        mock_import_resp1 = MagicMock()
        mock_import_resp1.json.return_value = {"key": "QA-EX-1"}
        mock_import_resp2 = MagicMock()
        mock_import_resp2.json.return_value = {"key": "QA-EX-2"}
        # 1 auth call + 2 import calls = 3 total
        mock_post.side_effect = [mock_auth_resp, mock_import_resp1, mock_import_resp2]

        configured.import_execution(_RESULTS_MIXED)
        configured.import_execution(_RESULTS_ALL_PASS)

        # Token should be fetched only once (cached), so total calls = 3
        assert mock_post.call_count == 3
        # First call is auth
        first_url = mock_post.call_args_list[0][0][0]
        assert "authenticate" in first_url
        # Subsequent calls are imports, not auth
        second_url = mock_post.call_args_list[1][0][0]
        assert "import" in second_url


    @patch("cherenkov.adapters.exporters.xray_exporter.requests.post")
    def test_import_execution_success(self, mock_post: MagicMock, configured: XrayExporter):
        mock_auth = MagicMock()
        mock_auth.json.return_value = "bearer-token"
        mock_import = MagicMock()
        mock_import.json.return_value = {"key": "QA-EX-42", "self": "https://xray/42"}
        mock_post.side_effect = [mock_auth, mock_import]

        result = configured.import_execution(_RESULTS_MIXED, test_plan_key="QA-TP-1", environment="CI")

        assert result["key"] == "QA-EX-42"
        # Import call should include project key param
        import_call = mock_post.call_args_list[1]
        assert import_call[1]["params"]["projectKey"] == "QA"
        assert import_call[1]["params"]["testPlanKey"] == "QA-TP-1"
        assert import_call[1]["params"]["testEnvironments"] == "CI"

    @patch("cherenkov.adapters.exporters.xray_exporter.requests.post")
    def test_import_sends_junit_xml(self, mock_post: MagicMock, configured: XrayExporter):
        mock_auth = MagicMock()
        mock_auth.json.return_value = "token"
        mock_import = MagicMock()
        mock_import.json.return_value = {"key": "QA-EX-1"}
        mock_post.side_effect = [mock_auth, mock_import]

        configured.import_execution(_RESULTS_MIXED)

        import_call = mock_post.call_args_list[1]
        body = import_call[1]["data"]
        assert b"<testsuites" in body or b"<?xml" in body


# ── ZephyrExporter tests ──────────────────────────────────────────────────────

class TestZephyrExporter:

    @pytest.fixture
    def configured(self) -> ZephyrExporter:
        return ZephyrExporter(token="zephyr-api-token", project_key="QA")

    @pytest.fixture
    def unconfigured(self) -> ZephyrExporter:
        return ZephyrExporter(token="", project_key="QA")

    def test_is_configured_true(self, configured: ZephyrExporter):
        assert configured.is_configured is True

    def test_is_configured_false(self, unconfigured: ZephyrExporter):
        assert unconfigured.is_configured is False

    def test_import_execution_raises_when_unconfigured(self, unconfigured: ZephyrExporter):
        with pytest.raises(ValueError, match="token not configured"):
            unconfigured.import_execution(_RESULTS_MIXED)

    @patch("cherenkov.adapters.exporters.zephyr_exporter.requests.post")
    def test_import_execution_success(self, mock_post: MagicMock, configured: ZephyrExporter):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "testCycle": {"key": "QA-C1", "name": "CHERENKOV Conformance Run"},
            "testResults": []
        }
        mock_post.return_value = mock_resp

        result = configured.import_execution(
            _RESULTS_MIXED,
            test_cycle_name="Sprint 3 Run",
            environment_name="staging"
        )

        assert result["testCycle"]["key"] == "QA-C1"
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["params"]["projectKey"] == "QA"
        assert call_kwargs["params"]["testCycleName"] == "Sprint 3 Run"
        assert call_kwargs["params"]["environmentName"] == "staging"

    @patch("cherenkov.adapters.exporters.zephyr_exporter.requests.post")
    def test_import_sends_xml_content_type(self, mock_post: MagicMock, configured: ZephyrExporter):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"testCycle": {"key": "QA-C2"}}
        mock_post.return_value = mock_resp

        configured.import_execution(_RESULTS_ALL_PASS)

        call_kwargs = mock_post.call_args[1]
        assert "application/xml" in call_kwargs["headers"]["Content-Type"]
        assert "Bearer zephyr-api-token" == call_kwargs["headers"]["Authorization"]

    @patch("cherenkov.adapters.exporters.zephyr_exporter.requests.post")
    def test_import_sends_junit_xml(self, mock_post: MagicMock, configured: ZephyrExporter):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"testCycle": {"key": "QA-C3"}}
        mock_post.return_value = mock_resp

        configured.import_execution(_RESULTS_MIXED)

        call_kwargs = mock_post.call_args[1]
        body = call_kwargs["data"]
        assert b"<testsuites" in body or b"<?xml" in body

    @patch("cherenkov.adapters.exporters.zephyr_exporter.requests.post")
    def test_custom_base_url(self, mock_post: MagicMock):
        exporter = ZephyrExporter(token="tok", project_key="QA", base_url="https://custom.zephyr.example.com/v2")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"testCycle": {"key": "QA-C4"}}
        mock_post.return_value = mock_resp

        exporter.import_execution(_RESULTS_ALL_PASS)

        url_called = mock_post.call_args[0][0]
        assert "custom.zephyr.example.com" in url_called
