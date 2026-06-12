"""
tests/unit/test_mcp_tools.py — unit tests for MCP conformance tools (#441).

Tests: run_conformance_check, get_last_report, list_drift_findings,
       get_tightening_suggestions, explain_finding.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.mcp import handlers


def _call(name: str, args: dict) -> dict:
    """Helper: call handle_tool_call with policy bypass (tests/full-dev)."""
    with patch.object(handlers._policy, "is_tool_allowed", return_value=True):
        with patch("cherenkov.mcp.handlers.get_guard") as mock_guard:
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
    result = _call("get_tightening_suggestions", {"endpoint": "/users/{id}", "method": "GET"})
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

    result = _call("get_tightening_suggestions", {"endpoint": "/users/1", "method": "GET"})
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

    with patch("cherenkov.chat.tools.explain_divergence", return_value={"explanation": "test"}):
        result = _call("explain_finding", {"finding_id": fid, "detail_level": "concise"})
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

    with patch("cherenkov.mcp.handlers._validate_spec_path", return_value=str(spec)):
        with patch(
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
