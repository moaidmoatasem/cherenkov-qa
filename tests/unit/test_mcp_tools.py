"""
tests/unit/test_mcp_tools.py — unit tests for MCP conformance tools (#441).

Tests: run_conformance_check, get_last_report, list_drift_findings,
       get_tightening_suggestions, explain_finding.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.mcp import handlers


def _call(name: str, args: dict) -> dict:
    """Helper: call handle_tool_call with policy bypass (tests/full-dev)."""
    with patch.object(handlers._policy, "is_tool_allowed", return_value=True), patch("cherenkov.mcp.handlers.get_guard") as mock_guard:
        mock_guard.return_value.check_tool_call.return_value = MagicMock(
            allowed=True
        )
        return handlers.handle_tool_call({"name": name, "arguments": args})


# ── get_last_report ────────────────────────────────────────────────────────────


def test_get_last_report_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = _call("get_last_report", {})
    payload = json.loads(result["content"][0]["text"])
    assert "error" in payload or "hint" in payload
    assert result["isError"] is False


def test_get_last_report_with_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report_dir = tmp_path / ".cherenkov"
    report_dir.mkdir()
    report_data = {"status": "complete", "passed": 5, "failed": 1}
    (report_dir / "report.json").write_text(json.dumps(report_data))

    result = _call("get_last_report", {})
    payload = json.loads(result["content"][0]["text"])
    assert payload["passed"] == 5
    assert payload["failed"] == 1
    assert result["isError"] is False


# ── list_drift_findings ────────────────────────────────────────────────────────


def test_list_drift_findings_all():
    result = _call("list_drift_findings", {})
    payload = json.loads(result["content"][0]["text"])
    assert "findings" in payload
    assert "total" in payload
    assert isinstance(payload["findings"], list)


def test_list_drift_findings_severity_filter():
    result = _call("list_drift_findings", {"severity": "high"})
    payload = json.loads(result["content"][0]["text"])
    for f in payload["findings"]:
        assert f.get("severity") == "high"


def test_list_drift_findings_endpoint_filter():
    result = _call("list_drift_findings", {"endpoint": "/pet"})
    payload = json.loads(result["content"][0]["text"])
    for f in payload["findings"]:
        assert "/pet" in f.get("endpoint", "")


def test_list_drift_findings_limit():
    result = _call("list_drift_findings", {"limit": 2})
    payload = json.loads(result["content"][0]["text"])
    assert len(payload["findings"]) <= 2


# ── get_tightening_suggestions ────────────────────────────────────────────────


def test_get_tightening_suggestions_no_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = _call(
        "get_tightening_suggestions", {"endpoint": "/users/{id}", "method": "GET"}
    )
    payload = json.loads(result["content"][0]["text"])
    assert payload["endpoint"] == "/users/{id}"
    assert payload["method"] == "GET"
    assert isinstance(payload["suggestions"], list)
    assert result["isError"] is False


def test_get_tightening_suggestions_with_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ev_dir = tmp_path / ".cherenkov" / "evidence"
    ev_dir.mkdir(parents=True)
    ev = {
        "endpoint": "/users/1",
        "method": "GET",
        "request_body": '{"name": "Alice"}',
        "response_body": '{"name": "Alice", "id": 1}',
    }
    (ev_dir / "ev001.json").write_text(json.dumps(ev))

    result = _call(
        "get_tightening_suggestions", {"endpoint": "/users/1", "method": "GET"}
    )
    payload = json.loads(result["content"][0]["text"])
    assert isinstance(payload["suggestions"], list)


# ── explain_finding ────────────────────────────────────────────────────────────


def test_explain_finding_not_found():
    result = _call("explain_finding", {"finding_id": "NONEXISTENT"})
    assert result["isError"] is True
    payload = json.loads(result["content"][0]["text"])
    assert "not found" in payload["error"].lower()


def test_explain_finding_exists():
    from cherenkov.web.divergences import _DIVERGENCE_CORPUS

    if not _DIVERGENCE_CORPUS:
        pytest.skip("No divergence corpus available")
    fid = _DIVERGENCE_CORPUS[0]["id"]

    with patch(
        "cherenkov.chat.tools.explain_divergence", return_value={"explanation": "test"}
    ):
        result = _call(
            "explain_finding", {"finding_id": fid, "detail_level": "concise"}
        )
    payload = json.loads(result["content"][0]["text"])
    assert payload["finding_id"] == fid
    assert "explanation" in payload
    assert result["isError"] is False


# ── run_conformance_check ──────────────────────────────────────────────────────


def test_run_conformance_check_invalid_spec():
    result = _call(
        "run_conformance_check",
        {"target_url": "http://localhost:9999", "spec_path": "../../../etc/passwd"},
    )
    payload = json.loads(result["content"][0]["text"])
    assert result["isError"] is True
    assert "spec_path" in payload.get("error", "").lower()


def test_run_conformance_check_missing_tests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Create a minimal valid spec file
    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\npaths: {}\n")

    with patch("cherenkov.mcp.handlers._validate_spec_path", return_value=str(spec)), patch(
        "cherenkov.execution.validate.ValidationEngine.validate_suite",
        return_value={"status": "empty", "message": "No tests", "reports": []},
    ):
        result = _call(
            "run_conformance_check",
            {"target_url": "http://localhost:9999", "spec_path": str(spec)},
        )
    payload = json.loads(result["content"][0]["text"])
    assert result["isError"] is False
    assert "status" in payload


# ── Tool manifest ─────────────────────────────────────────────────────────────


def test_new_tools_in_manifest():
    result = handlers.handle_tools_list({})
    tool_names = {t["name"] for t in result["tools"]}
    expected = {
        "run_conformance_check",
        "get_last_report",
        "list_drift_findings",
        "get_tightening_suggestions",
        "explain_finding",
    }
    assert expected.issubset(tool_names), f"Missing: {expected - tool_names}"


# ── Issue #457: Enhanced Visual Diff Baseline Tool ─────────────────────────────


def test_visual_diff_baseline_enhanced_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "cherenkov.execution.visual_diff.VisualDiffEngine.run_visual_validation",
        return_value={"passed": True, "exit_code": 0, "mismatch_detected": False},
    ):
        result = _call(
            "visual_diff_baseline_enhanced",
            {
                "target_url": "http://localhost:3000",
                "diff_threshold": 0.3,
                "comparison_mode": "pixel",
            },
        )
    payload = json.loads(result["content"][0]["text"])
    assert payload["target_url"] == "http://localhost:3000"
    assert payload["diff_threshold"] == 0.3
    assert payload["comparison_mode"] == "pixel"
    assert payload["passed"] is True
    assert result["isError"] is False


def test_visual_diff_baseline_enhanced_with_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "cherenkov.execution.visual_diff.VisualDiffEngine.run_visual_validation",
        return_value={"passed": True, "exit_code": 0, "mismatch_detected": False},
    ):
        result = _call("visual_diff_baseline_enhanced", {})
    payload = json.loads(result["content"][0]["text"])
    assert "target_url" in payload
    assert "diff_threshold" in payload
    assert "report_path" in payload
    assert result["isError"] is False


def test_visual_diff_baseline_enhanced_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "cherenkov.execution.visual_diff.VisualDiffEngine.run_visual_validation",
        return_value={"passed": False, "exit_code": 1, "mismatch_detected": True},
    ):
        result = _call(
            "visual_diff_baseline_enhanced", {"target_url": "http://localhost:3000"}
        )
    payload = json.loads(result["content"][0]["text"])
    assert payload["mismatch_detected"] is True
    assert payload["passed"] is False
    assert result["isError"] is False


# ── Issue #458: Compliance and Governance MCP Tools ────────────────────────────


def test_scan_mena_compliance_enhanced_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Create minimal spec
    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\npaths: {}\n")

    from cherenkov.compliance.mena_scanner import MENAComplianceScanner

    with patch.object(handlers, "_validate_spec_path", return_value=str(spec)), patch.object(
        MENAComplianceScanner,
        "run_compliance_audit",
        return_value={
            "overall_compliance_score": 80,
            "audit_results": {},
            "framework_mappings": {
                "SAMA_CCSF": {
                    "Domain 3.1": {"status": "COMPLIANT", "remediation": ""}
                },
                "EGYPT_FinCSF": {
                    "Section 4.2": {"status": "COMPLIANT", "remediation": ""}
                },
            },
        },
    ):
        result = _call(
            "scan_mena_compliance_enhanced",
            {
                "target_url": "http://localhost:8000",
                "spec_path": str(spec),
                "framework": "sama_ccsf",
            },
        )
    payload = json.loads(result["content"][0]["text"])
    assert payload["framework"] == "sama_ccsf"
    assert payload["compliance_score"] == 80
    assert "SAMA_CCSF" in payload["mappings"]
    assert result["isError"] is False


def test_scan_mena_compliance_enhanced_invalid_spec():
    result = _call(
        "scan_mena_compliance_enhanced",
        {
            "target_url": "http://localhost:8000",
            "spec_path": "../../../etc/passwd",
            "framework": "sama_ccsf",
        },
    )
    assert result["isError"] is True
    payload = json.loads(result["content"][0]["text"])
    assert "spec_path" in payload.get("error", "").lower()


def test_validate_governance_certification(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from cherenkov.governance.kpi import GovernanceKPI, GovernanceReport

    mock_kpi = GovernanceKPI(
        escape_rate=0.05,
        false_positive_rate=0.08,
        coverage=0.75,
        maintenance_score=0.9,
        total_tests=100,
        passed_tests=80,
        failed_tests=15,
        escaped_defects=5,
        false_positives=8,
        idiom_count=3,
        total_endpoints=20,
        covered_endpoints=15,
    )
    with patch("cherenkov.governance.kpi.GovernanceCollector") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.collect.return_value = GovernanceReport(kpi=mock_kpi, history=[])
        mock_cls.return_value = mock_instance

        result = _call(
            "validate_governance_certification",
            {
                "cert_id": "CERT-001",
                "validation_criteria": "health_score >= 0.7, escape_rate < 0.1",
            },
        )
    payload = json.loads(result["content"][0]["text"])
    assert payload["cert_id"] == "CERT-001"
    assert payload["certified"] is True
    assert payload["health_score"] == mock_kpi.health_score
    assert result["isError"] is False


def test_validate_governance_certification_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from cherenkov.governance.kpi import GovernanceKPI, GovernanceReport

    mock_kpi = GovernanceKPI(
        escape_rate=0.25,
        false_positive_rate=0.3,
        coverage=0.2,
    )
    with patch("cherenkov.governance.kpi.GovernanceCollector") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.collect.return_value = GovernanceReport(kpi=mock_kpi, history=[])
        mock_cls.return_value = mock_instance

        result = _call(
            "validate_governance_certification",
            {
                "cert_id": "CERT-002",
                "validation_criteria": "strict",
            },
        )
    payload = json.loads(result["content"][0]["text"])
    assert payload["certified"] is False
    assert len(payload["findings"]) > 0
    assert result["isError"] is False


def test_report_compliance_findings_all(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "cherenkov.compliance.mena_scanner.MENAComplianceScanner.run_compliance_audit",
        return_value={
            "overall_compliance_score": 60,
            "framework_mappings": {
                "SAMA_CCSF": {"Domain 3.1": {"status": "COMPLIANT", "remediation": ""}},
                "EGYPT_FinCSF": {
                    "Section 4.2": {
                        "status": "NON-COMPLIANT",
                        "remediation": "Fix auth",
                    }
                },
            },
        },
    ):
        result = _call("report_compliance_findings", {})
    payload = json.loads(result["content"][0]["text"])
    assert "total_findings" in payload
    assert "findings" in payload
    assert payload["compliance_score"] == 60
    assert result["isError"] is False


def test_report_compliance_findings_filtered(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "cherenkov.compliance.mena_scanner.MENAComplianceScanner.run_compliance_audit",
        return_value={
            "overall_compliance_score": 60,
            "framework_mappings": {
                "SAMA_CCSF": {"Domain 3.1": {"status": "COMPLIANT", "remediation": ""}},
                "EGYPT_FinCSF": {
                    "Section 4.2": {
                        "status": "NON-COMPLIANT",
                        "remediation": "Fix auth",
                    }
                },
            },
        },
    ):
        result = _call("report_compliance_findings", {"severity": "high", "limit": 5})
    payload = json.loads(result["content"][0]["text"])
    assert payload["filters_applied"]["severity"] == "high"
    assert result["isError"] is False


# ── Issue #457+#458: New tools in manifest ─────────────────────────────────────


def test_issue_457_458_tools_in_manifest():
    result = handlers.handle_tools_list({})
    tool_names = {t["name"] for t in result["tools"]}
    expected = {
        "visual_diff_baseline_enhanced",
        "scan_mena_compliance_enhanced",
        "validate_governance_certification",
        "report_compliance_findings",
        "export_jira_ticket",
        "run_k6_perf",
        "scan_mena_compliance",
    }
    assert expected.issubset(tool_names), f"Missing: {expected - tool_names}"


# ── Milestone 1: export_jira_ticket, run_k6_perf, scan_mena_compliance ──────


def test_export_jira_ticket_direct_export():
    result = _call(
        "export_jira_ticket",
        {
            "summary": "Custom Jira Ticket Summary",
            "description": "Custom description of drift",
            "project_key": "TEST",
            "sandbox_only": True,
        },
    )
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["summary"] == "Custom Jira Ticket Summary"
    assert payload["description"] == "Custom description of drift"
    assert payload["project_key"] == "TEST"
    assert payload["sandbox_only"] is True
    assert payload["status"] == "exported"


def test_export_jira_ticket_queue_lookup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from cherenkov.hitl.contracts import HitlItem
    from cherenkov.hitl.store import HitlQueue

    q = HitlQueue()
    item = HitlItem(
        id="hitl_test_001",
        run_id="run_001",
        stage="GENERATE",
        endpoint="/test",
        status="pending",
        review_gate_failed="assertion",
        confidence_reason="Assertion failed",
    )
    q.enqueue(item)

    result = _call(
        "export_jira_ticket",
        {
            "item_id": "hitl_test_001",
            "project_key": "CHER",
            "sandbox_only": True,
        },
    )
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["item_id"] == "hitl_test_001"
    assert payload["status"] == "exported"
    assert "hitl_test_001" in payload["summary"]


def test_run_k6_perf_with_full_params(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from cherenkov.core.contracts import (
        PerfGateResult,
        PerfReport,
        StageMeta,
        Status,
        Verdict,
    )

    mock_report = PerfReport(
        scenario_id="perf_custom_scenario",
        gates=[
            PerfGateResult(
                gate="latency_baseline",
                passed=True,
                latency_ms=42.0,
                baseline_count=5,
                baseline_mean_ms=40.0,
                baseline_stddev_ms=2.0,
                threshold_limit_ms=44.0,
                anomaly_detected=False,
                k6_available=False,
            )
        ],
        verdict=Verdict.AUTO_APPROVE,
        status=Status.OK,
        errors=[],
        metadata=StageMeta(stage="perf"),
    )

    with patch(
        "cherenkov.stages.perf.perf_stage.PerfStage.run", return_value=mock_report
    ) as mock_run, patch("cherenkov.stages.perf.perf_stage._BaselineDB"):
        result = _call(
            "run_k6_perf",
            {
                "target_url": "http://localhost:9000",
                "scenario_name": "custom_scenario",
                "duration": "10s",
                "vus": 20,
                "endpoint": "/api/v1/resource",
                "method": "POST",
                "use_ml": True,
            },
        )
        assert result["isError"] is False
        payload = json.loads(result["content"][0]["text"])
        assert payload["scenario_id"] == "perf_custom_scenario"
        assert payload["verdict"].upper() == "AUTO_APPROVE"
        mock_run.assert_called_once()
        sl_arg = mock_run.call_args[0][0]
        assert sl_arg.name == "custom_scenario"
        assert sl_arg.target_url == "http://localhost:9000"
        assert sl_arg.endpoint == "/api/v1/resource"
        assert sl_arg.method == "POST"
        assert sl_arg.vus == 20
        assert sl_arg.duration_sec == 10
        assert mock_run.call_args[1].get("use_ml") is True


def test_scan_mena_compliance_yaml_spec(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_file = tmp_path / "openapi.yaml"
    spec_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
"""
    spec_file.write_text(spec_content, encoding="utf-8")

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        }
        mock_get.return_value = mock_resp
        result = _call(
            "scan_mena_compliance",
            {
                "target_url": "http://localhost:8000",
                "spec_path": str(spec_file),
            },
        )
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert "compliance_score" in payload
    assert "violations" in payload
    assert "mappings" in payload
    assert "sama_ccsf" in payload
    assert "egypt_fincsf" in payload


def test_export_jira_ticket_defaults():
    result = _call(
        "export_jira_ticket",
        {
            "summary": "Default Jira Ticket",
            "description": "Default Description",
        },
    )
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["summary"] == "Default Jira Ticket"
    assert payload["project_key"] == "QA"
    assert payload["sandbox_only"] is True


def test_run_k6_perf_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from cherenkov.core.contracts import (
        PerfReport,
        StageMeta,
        Status,
        Verdict,
    )

    mock_report = PerfReport(
        scenario_id="perf_soak",
        gates=[],
        verdict=Verdict.AUTO_APPROVE,
        status=Status.OK,
        errors=[],
        metadata=StageMeta(stage="perf"),
    )

    with patch(
        "cherenkov.stages.perf.perf_stage.PerfStage.run", return_value=mock_report
    ) as mock_run, patch("cherenkov.stages.perf.perf_stage._BaselineDB"):
        result = _call("run_k6_perf", {"target_url": "http://localhost:8000"})
        assert result["isError"] is False
        payload = json.loads(result["content"][0]["text"])
        assert payload["scenario_id"] == "perf_soak"
        mock_run.assert_called_once()
        sl_arg = mock_run.call_args[0][0]
        assert sl_arg.name == "soak"
        assert sl_arg.vus == 10
        assert sl_arg.duration_sec == 30


def test_scan_mena_compliance_json_spec(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_file = tmp_path / "openapi.json"
    spec_dict = {
        "openapi": "3.0.0",
        "info": {"title": "Test JSON API", "version": "1.0.0"},
        "paths": {},
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
    }
    spec_file.write_text(json.dumps(spec_dict), encoding="utf-8")

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        }
        mock_get.return_value = mock_resp
        result = _call(
            "scan_mena_compliance",
            {
                "target_url": "http://localhost:8000",
                "spec_path": str(spec_file),
            },
        )
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["compliance_score"] >= 20
    assert payload["sama_ccsf"]["SAMA CCSF Domain 3.1 (Cyber Security Governance)"]["status"] == "COMPLIANT"

