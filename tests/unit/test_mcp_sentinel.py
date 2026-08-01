"""
tests/unit/test_mcp_sentinel.py
Unit tests for the MCP Sentinel tools (Pillar 2 — INNOVATION_ROADMAP_V2).
"""

from __future__ import annotations

from cherenkov.mcp.tools.sentinel import (
    SENTINEL_HANDLERS,
    SENTINEL_TOOL_DEFS,
    handle_audit_test_file,
    handle_check_assertion,
    handle_suggest_spec_fix,
)

# ── sentinel tool definitions ─────────────────────────────────────────────────

def test_sentinel_tool_defs_structure():
    """All three sentinel tools are defined with required schema fields."""
    names = {t["name"] for t in SENTINEL_TOOL_DEFS}
    assert "cherenkov/audit-test-file" in names
    assert "cherenkov/check-assertion" in names
    assert "cherenkov/suggest-spec-fix" in names
    for tool in SENTINEL_TOOL_DEFS:
        assert "description" in tool
        assert "inputSchema" in tool


def test_sentinel_handlers_registered():
    """All tools are registered in SENTINEL_HANDLERS."""
    assert "cherenkov/audit-test-file" in SENTINEL_HANDLERS
    assert "cherenkov/check-assertion" in SENTINEL_HANDLERS
    assert "cherenkov/suggest-spec-fix" in SENTINEL_HANDLERS


# ── audit-test-file ───────────────────────────────────────────────────────────

def test_audit_test_file_clean_returns_pass():
    """Clean test → verdict PASS, certificate issued."""
    result = handle_audit_test_file({
        "test_content": "expect(response.status()).toBe(201);",
        "test_format": "playwright",
    })
    assert result["verdict"] == "PASS"
    assert result["integrity_score"] >= 0.90
    assert result["certificate"] is not None


def test_audit_test_file_weak_returns_verdict():
    """Weakened assertion → non-PASS verdict with issues."""
    result = handle_audit_test_file({
        "test_content": "expect(response.status()).toBeLessThan(500);",
        "test_format": "playwright",
    })
    assert result["verdict"] in ("WEAK", "FAIL")
    assert len(result["issues"]) > 0
    assert result["certificate"] is None


def test_audit_test_file_empty_content_error():
    """Empty test_content returns error response."""
    result = handle_audit_test_file({"test_content": ""})
    assert "error" in result


def test_audit_test_file_agent_id_preserved():
    """agent_id is passed through to the audit."""
    result = handle_audit_test_file({
        "test_content": "expect(response.status()).toBe(200);",
        "agent_id": "test-sentinel-agent",
    })
    # No error, audit completed
    assert "verdict" in result
    assert result.get("error") is None


# ── check-assertion ───────────────────────────────────────────────────────────

def test_check_assertion_strong():
    """Tight assertion → 'strong'."""
    result = handle_check_assertion({
        "line": "expect(response.status()).toBe(201);",
        "format": "playwright",
    })
    assert result["strength"] == "strong"


def test_check_assertion_weak():
    """Weakened assertion → 'weak'."""
    result = handle_check_assertion({
        "line": "expect(response.status()).toBeLessThan(500);",
        "format": "playwright",
    })
    assert result["strength"] == "weak"
    assert "suggestion" in result


def test_check_assertion_tautological():
    """Tautological assertion → 'tautological'."""
    result = handle_check_assertion({
        "line": "expect(true).toBe(true);",
        "format": "playwright",
    })
    assert result["strength"] == "tautological"


def test_check_assertion_empty():
    """Empty line → returns unknown."""
    result = handle_check_assertion({"line": ""})
    assert result["strength"] == "unknown"


def test_check_assertion_pytest_format():
    """Weakened pytest assertion → 'weak'."""
    result = handle_check_assertion({
        "line": "assert response.status_code < 500",
        "format": "pytest",
    })
    assert result["strength"] == "weak"


# ── suggest-spec-fix ──────────────────────────────────────────────────────────

def test_suggest_spec_fix_weakened_playwright():
    """WEAKENED_ASSERTION → playwright fix with correct status code."""
    result = handle_suggest_spec_fix({
        "original_line": "expect(response.status()).toBeLessThan(500);",
        "issue_type": "WEAKENED_ASSERTION",
        "expected_status": 201,
    })
    assert result["fixed_line"] == "expect(response.status()).toBe(201);"
    assert "201" in result["fixed_line"]
    assert "explanation" in result


def test_suggest_spec_fix_weakened_pytest():
    """WEAKENED_ASSERTION for pytest → uses correct template."""
    result = handle_suggest_spec_fix({
        "original_line": "assert response.status_code < 500",
        "issue_type": "WEAKENED_ASSERTION",
        "expected_status": 200,
    })
    assert "status_code == 200" in result["fixed_line"]


def test_suggest_spec_fix_unknown_issue_type():
    """Unknown issue_type → returns original line with manual review message."""
    result = handle_suggest_spec_fix({
        "original_line": "some_assertion()",
        "issue_type": "UNKNOWN_TYPE",
    })
    assert result["fixed_line"] == "some_assertion()"
    assert "manual" in result["explanation"].lower()
