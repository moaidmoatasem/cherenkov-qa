"""Unit tests for the verify_system MCP tool (E2.1)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cherenkov.mcp import handlers
from cherenkov.mcp.handlers import TOOLS
from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)


def _make_report(
    dc: DivergenceClass = DivergenceClass.D1_SPEC_CODE,
    sev: Severity = Severity.HIGH,
    endpoint: str = "POST /pet",
) -> DivergenceReport:
    ev = DivergenceEvidence(
        request_summary=f"POST https://example.com/pet → 500",
        diff="status mismatch: expected=400, actual=500",
        response_actual="500",
        response_expected="400",
    )
    return DivergenceReport(
        id="abc123",
        divergence_class=dc,
        claim_a="spec says 400",
        claim_b="impl returns 500",
        severity=sev,
        endpoint=endpoint,
        evidence=ev,
        repro_steps=["curl -X POST http://example.com/pet", "expect 400"],
        metadata=StageMeta(stage="proof_run"),
    )


def _call(args: dict) -> dict:
    with patch.object(handlers._policy, "is_tool_allowed", return_value=True):
        with patch("cherenkov.mcp.handlers.get_guard") as mock_guard:
            mock_guard.return_value.check_tool_call.return_value = MagicMock(allowed=True)
            return handlers.handle_tool_call({"name": "verify_system", "arguments": args})


class TestVerifySystemRegistration:
    def test_tool_registered(self) -> None:
        names = [t.name for t in TOOLS]
        assert "verify_system" in names

    def test_tool_description_mentions_divergence(self) -> None:
        tool = next(t for t in TOOLS if t.name == "verify_system")
        assert "divergence" in tool.description.lower()

    def test_tool_requires_base_url(self) -> None:
        tool = next(t for t in TOOLS if t.name == "verify_system")
        assert "base_url" in tool.inputSchema.required


class TestVerifySystemDispatch:
    def test_missing_base_url_returns_error(self) -> None:
        result = _call({})
        content = result.get("content", [{}])
        text = content[0].get("text", "") if content else ""
        assert "error" in text.lower() or result.get("isError")

    def test_no_divergences_returns_pass(self) -> None:
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]):
            result = _call({"base_url": "http://localhost:9999"})
        content = result.get("content", [{}])
        import json
        report = json.loads(content[0]["text"])
        assert report["verdict"] == "pass"
        assert report["summary"]["total"] == 0
        assert report["schema_version"] == "verify/v1"

    def test_divergences_returned_as_fail(self) -> None:
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[_make_report()]):
            result = _call({"base_url": "http://localhost:9999"})
        import json
        report = json.loads(result["content"][0]["text"])
        assert report["verdict"] == "fail"
        assert report["summary"]["total"] == 1
        assert report["summary"]["high"] == 1

    def test_finding_fields_present(self) -> None:
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[_make_report()]):
            result = _call({"base_url": "http://localhost:9999"})
        import json
        report = json.loads(result["content"][0]["text"])
        f = report["divergences"][0]
        assert f["severity"] == "high"
        assert "claim_a" in f
        assert "claim_b" in f
        assert "evidence" in f
        assert "reproduction" in f

    def test_use_llm_default_false(self) -> None:
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]) as mock:
            _call({"base_url": "http://localhost:9999"})
        _, kwargs = mock.call_args
        assert kwargs.get("use_llm") is False

    def test_use_llm_true_passed_through(self) -> None:
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]) as mock:
            _call({"base_url": "http://localhost:9999", "use_llm": True})
        _, kwargs = mock.call_args
        assert kwargs.get("use_llm") is True

    def test_meta_local_only(self) -> None:
        with patch("cherenkov.mcp.handlers.run_proof", return_value=[]):
            result = _call({"base_url": "http://localhost:9999"})
        import json
        report = json.loads(result["content"][0]["text"])
        assert report["meta"]["local_only"] is True

    def test_engine_error_returns_error_result(self) -> None:
        with patch("cherenkov.mcp.handlers.run_proof", side_effect=RuntimeError("boom")):
            result = _call({"base_url": "http://localhost:9999"})
        content = result.get("content", [{}])
        text = content[0].get("text", "")
        assert "boom" in text or result.get("isError")
