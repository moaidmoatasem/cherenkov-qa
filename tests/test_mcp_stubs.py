from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.mcp.handlers import (
    handle_tool_call,
    _tool_run_perf,
    _tool_export_jira,
    _tool_scan_mena,
)
from cherenkov.mcp.contracts import MCPToolCallResult
from cherenkov.hitl.contracts import HitlItem, HitlStatus


class TestMCPStubs(unittest.TestCase):
    """Unit tests for newly implemented MCP stub tools (Issue #447)."""

    def setUp(self):
        # Enforce profile and policy allowing all tools
        os.environ["MCP_PROFILE"] = "full-dev"

    @patch("cherenkov.core.orchestrator.OrchestrationEngine.run_perf_stage")
    def test_tool_run_perf_success(self, mock_run_perf_stage):
        from cherenkov.core.contracts import PerfReport, StageMeta, Verdict, Status
        
        # Mocking the report returned by the perf stage
        mock_report = PerfReport(
            scenario_id="perf_mcp_run",
            gates=[],
            verdict=Verdict.AUTO_APPROVE,
            status=Status.OK,
            metadata=StageMeta(stage="perf", duration_ms=10)
        )
        mock_run_perf_stage.return_value = [mock_report]

        result = _tool_run_perf({"target_url": "http://localhost:8000"})
        self.assertIsInstance(result, MCPToolCallResult)
        self.assertFalse(result.isError)
        
        payload = json.loads(result.content[0].text)
        self.assertEqual(payload["scenario_id"], "perf_mcp_run")
        self.assertEqual(payload["verdict"], "auto_approve")
        mock_run_perf_stage.assert_called_once()

    @patch("cherenkov.core.orchestrator.OrchestrationEngine.run_perf_stage")
    def test_tool_run_perf_empty_report(self, mock_run_perf_stage):
        mock_run_perf_stage.return_value = []
        result = _tool_run_perf({})
        self.assertTrue(result.isError)
        payload = json.loads(result.content[0].text)
        self.assertIn("No reports returned", payload["error"])

    @patch("cherenkov.core.orchestrator.OrchestrationEngine.run_perf_stage", side_effect=Exception("Failed executing k6"))
    def test_tool_run_perf_exception(self, mock_run_perf_stage):
        result = _tool_run_perf({})
        self.assertTrue(result.isError)
        payload = json.loads(result.content[0].text)
        self.assertIn("PerfStage error: Failed executing k6", payload["error"])

    @patch("cherenkov.hitl.store.HitlQueue.get")
    @patch("cherenkov.validate.jira_exporter.JiraExporter.export_ticket")
    def test_tool_export_jira_success(self, mock_export_ticket, mock_hitl_get):
        # Setup HitlItem mock
        mock_item = HitlItem(
            id="item-123",
            status=HitlStatus.PENDING,
            endpoint="/users",
            method="POST",
            mutation_id="mut-abc",
            review_gate_failed="HTTP_500",
            confidence_reason="Simulated failure details",
            run_id="run-456"
        )
        mock_hitl_get.return_value = mock_item
        
        # Temp file for exporter mock output
        fd, temp_path = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write("# Jira Ticket Output\nDescription text.")
            
        mock_export_ticket.return_value = temp_path

        try:
            result = _tool_export_jira({"item_id": "item-123"})
            self.assertIsInstance(result, MCPToolCallResult)
            self.assertFalse(result.isError)
            
            payload = json.loads(result.content[0].text)
            self.assertEqual(payload["status"], "exported")
            self.assertEqual(payload["file_path"], temp_path)
            self.assertIn("Jira Ticket Output", payload["ticket_content"])
            
            mock_hitl_get.assert_called_once_with("item-123")
            mock_export_ticket.assert_called_once_with(
                scenario_id="mut-abc",
                failure_class="HTTP_500",
                error_message="Simulated failure details",
                hypothesis="Simulated failure details"
            )
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("cherenkov.hitl.store.HitlQueue.get", return_value=None)
    def test_tool_export_jira_not_found(self, mock_hitl_get):
        result = _tool_export_jira({"item_id": "missing-id"})
        self.assertTrue(result.isError)
        payload = json.loads(result.content[0].text)
        self.assertIn("not found", payload["error"])

    @patch("cherenkov.compliance.mena_scanner.MENAComplianceScanner.run_compliance_audit")
    def test_tool_scan_mena_success(self, mock_run_compliance_audit):
        mock_report = {
            "timestamp": 1234567,
            "overall_compliance_score": 80,
            "framework_mappings": {}
        }
        mock_run_compliance_audit.return_value = mock_report

        result = _tool_scan_mena({"target_url": "http://127.0.0.1:8000", "spec_path": "stub/target_spec.json"})
        self.assertIsInstance(result, MCPToolCallResult)
        self.assertFalse(result.isError)
        
        payload = json.loads(result.content[0].text)
        self.assertEqual(payload["overall_compliance_score"], 80)
        mock_run_compliance_audit.assert_called_once_with(
            target_url="http://127.0.0.1:8000",
            spec_path="stub/target_spec.json"
        )

    @patch("cherenkov.compliance.mena_scanner.MENAComplianceScanner.run_compliance_audit", side_effect=Exception("Scan failed"))
    def test_tool_scan_mena_exception(self, mock_run_compliance_audit):
        result = _tool_scan_mena({})
        self.assertTrue(result.isError)
        payload = json.loads(result.content[0].text)
        self.assertIn("MENA compliance scanner error: Scan failed", payload["error"])

    @patch("cherenkov.core.orchestrator.OrchestrationEngine.run_perf_stage")
    def test_handle_tool_call_routing(self, mock_run_perf_stage):
        from cherenkov.core.contracts import PerfReport, StageMeta, Verdict, Status
        mock_report = PerfReport(
            scenario_id="perf_mcp_run",
            gates=[],
            verdict=Verdict.AUTO_APPROVE,
            status=Status.OK,
            metadata=StageMeta(stage="perf", duration_ms=10)
        )
        mock_run_perf_stage.return_value = [mock_report]

        result = handle_tool_call({"name": "run_k6_perf", "arguments": {}})
        self.assertFalse(result.get("isError", False))
        payload = json.loads(result["content"][0]["text"])
        self.assertEqual(payload["scenario_id"], "perf_mcp_run")


if __name__ == "__main__":
    unittest.main()
