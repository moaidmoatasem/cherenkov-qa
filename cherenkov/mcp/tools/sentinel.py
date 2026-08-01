"""
cherenkov/mcp/tools/sentinel.py
MCP Sentinel tools — Pillar 2 of the INNOVATION_ROADMAP_V2.

Real-time integrity sentinel for AI coding IDEs (Cursor, Claude Code, Windsurf).
Exposes integrity audit capabilities as MCP tools so AI agents can get
live integrity warnings during code generation, not after CI runs.

Tools:
  - cherenkov/audit-test-file     : Full integrity audit of a test file
  - cherenkov/check-assertion     : Quick assertion strength check for a single line
  - cherenkov/suggest-spec-fix    : Given an integrity issue, suggest a spec-anchored fix
"""

from __future__ import annotations

from typing import Any

from cherenkov.integrity.api import (
    IntegrityAuditRequest,
    IssueType,
    audit_test_integrity,
)

# ── Tool definitions (MCP tool list schema entries) ───────────────────────────

SENTINEL_TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "cherenkov/audit-test-file",
        "description": (
            "Audit a test file for integrity issues: weakened assertions, tautological checks, "
            "spec mismatches, and AI test-cheating patterns. Returns a verdict (PASS/WEAK/FAIL), "
            "an integrity score, specific issues with line numbers, and a SHA-256 certificate "
            "if the score is >= 0.90. Call this before committing AI-generated test code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "test_content": {
                    "type": "string",
                    "description": "Raw content of the test file to audit",
                },
                "test_format": {
                    "type": "string",
                    "enum": ["playwright", "pytest"],
                    "description": "Test framework format",
                    "default": "playwright",
                },
                "agent_id": {
                    "type": "string",
                    "description": "Optional identifier of the calling AI agent",
                },
            },
            "required": ["test_content"],
        },
    },
    {
        "name": "cherenkov/check-assertion",
        "description": (
            "Quickly check whether a single test assertion line is strong or weak. "
            "Returns 'strong', 'weak', or 'tautological' with a brief explanation. "
            "Use this for real-time CodeLens-style feedback during test authoring."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "line": {
                    "type": "string",
                    "description": "The assertion line to check (e.g. 'expect(response.status()).toBeLessThan(500)')",
                },
                "format": {
                    "type": "string",
                    "enum": ["playwright", "pytest"],
                    "description": "Test framework format",
                    "default": "playwright",
                },
            },
            "required": ["line"],
        },
    },
    {
        "name": "cherenkov/suggest-spec-fix",
        "description": (
            "Given an integrity issue found in a test file, suggest a spec-anchored fix. "
            "Returns the corrected assertion line and a plain-English explanation of why "
            "the original is problematic and how the fix resolves it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "original_line": {
                    "type": "string",
                    "description": "The problematic test line to fix",
                },
                "issue_type": {
                    "type": "string",
                    "enum": [t.value for t in IssueType],
                    "description": "The type of integrity issue identified",
                },
                "expected_status": {
                    "type": "integer",
                    "description": "Expected HTTP status code from the OpenAPI spec (if applicable)",
                },
            },
            "required": ["original_line", "issue_type"],
        },
    },
]


# ── Tool handlers ─────────────────────────────────────────────────────────────

def handle_audit_test_file(params: dict[str, Any]) -> dict[str, Any]:
    """
    MCP handler for cherenkov/audit-test-file.
    Wraps the integrity API's audit_test_integrity() function.
    """
    test_content = params.get("test_content", "")
    test_format = params.get("test_format", "playwright")
    agent_id = params.get("agent_id")

    if not test_content.strip():
        return {
            "error": "test_content is required and cannot be empty",
            "verdict": None,
        }

    try:
        request = IntegrityAuditRequest(
            test_content=test_content,
            test_format=test_format,
            agent_id=agent_id,
        )
        result = audit_test_integrity(request)
    except Exception as exc:
        return {"error": str(exc), "verdict": None}

    # Format issues for MCP consumers (IDEs expect concise, actionable output)
    formatted_issues = [
        {
            "line": issue.line,
            "type": issue.issue_type.value,
            "severity": issue.severity,
            "detail": issue.detail,
            "suggestion": issue.suggestion,
        }
        for issue in result.issues
    ]

    return {
        "audit_id": result.audit_id,
        "verdict": result.verdict.value,
        "integrity_score": result.integrity_score,
        "issues": formatted_issues,
        "certificate": result.certificate,
        "summary": result.summary,
        "duration_ms": result.duration_ms,
    }


def handle_check_assertion(params: dict[str, Any]) -> dict[str, Any]:
    """
    MCP handler for cherenkov/check-assertion.
    Quick single-line assertion strength check for real-time IDE feedback.
    """
    line = params.get("line", "").strip()
    fmt = params.get("format", "playwright")

    if not line:
        return {"strength": "unknown", "explanation": "Empty line provided"}

    # Wrap the single line in a minimal test for analysis
    if fmt == "playwright":
        wrapped = f"test('inline', async () => {{\n  {line}\n}});"
    else:
        wrapped = f"def test_inline():\n    {line}\n"

    try:
        request = IntegrityAuditRequest(test_content=wrapped, test_format=fmt)
        result = audit_test_integrity(request)
    except Exception as exc:
        return {"strength": "unknown", "explanation": str(exc)}

    if not result.issues:
        return {
            "strength": "strong",
            "explanation": "No integrity issues detected. This assertion is spec-honest.",
            "score": result.integrity_score,
        }

    top_issue = result.issues[0]
    strength = "tautological" if top_issue.issue_type == IssueType.EMPTY_ASSERTION else "weak"

    return {
        "strength": strength,
        "issue_type": top_issue.issue_type.value,
        "explanation": top_issue.detail,
        "suggestion": top_issue.suggestion,
        "score": result.integrity_score,
    }


_PLAYWRIGHT_FIX_TEMPLATES: dict[str, str] = {
    IssueType.WEAKENED_ASSERTION.value: (
        "expect(response.status()).toBe({expected_status});"
    ),
    IssueType.EMPTY_ASSERTION.value: (
        "// Replace tautological assertion with real spec-derived check:\n"
        "expect(response.status()).toBe({expected_status});"
    ),
    IssueType.ALWAYS_PASSING.value: (
        "// Remove @ts-ignore and fix the underlying type error instead"
    ),
    IssueType.MISSING_STATUS_CHECK.value: (
        "expect(response.ok()).toBeTruthy();\n"
        "const body = await response.json();"
    ),
}

_PYTEST_FIX_TEMPLATES: dict[str, str] = {
    IssueType.WEAKENED_ASSERTION.value: (
        "assert response.status_code == {expected_status}"
    ),
    IssueType.EMPTY_ASSERTION.value: (
        "# Replace tautological assertion with real check:\n"
        "assert response.status_code == {expected_status}"
    ),
}


def handle_suggest_spec_fix(params: dict[str, Any]) -> dict[str, Any]:
    """
    MCP handler for cherenkov/suggest-spec-fix.
    Returns a corrected assertion anchored to the OpenAPI spec.
    """
    original_line = params.get("original_line", "")
    issue_type = params.get("issue_type", "")
    expected_status = params.get("expected_status", 200)

    # Detect format heuristically from the original line
    is_pytest = (
        original_line.strip().startswith("assert ")
        or "response.status_code" in original_line
    )
    templates = _PYTEST_FIX_TEMPLATES if is_pytest else _PLAYWRIGHT_FIX_TEMPLATES

    template = templates.get(issue_type)
    if not template:
        return {
            "fixed_line": original_line,
            "explanation": (
                f"No automatic fix available for issue type '{issue_type}'. "
                "Please review the assertion manually and anchor it to the spec's expected values."
            ),
        }

    fixed_line = template.format(expected_status=expected_status)

    explanations = {
        IssueType.WEAKENED_ASSERTION.value: (
            f"The original assertion accepts responses that should fail. "
            f"The spec-anchored fix asserts the exact expected status code ({expected_status})."
        ),
        IssueType.EMPTY_ASSERTION.value: (
            "The original assertion is tautological and will always pass, hiding real failures. "
            f"The fix checks the actual API response against the spec's expected status ({expected_status})."
        ),
        IssueType.MISSING_STATUS_CHECK.value: (
            "Always verify response.ok() before parsing the response body "
            "to prevent false positives when the API returns an error."
        ),
    }

    return {
        "original_line": original_line,
        "fixed_line": fixed_line,
        "issue_type": issue_type,
        "explanation": explanations.get(
            issue_type,
            "This fix anchors the assertion to the spec's expected contract.",
        ),
    }


# ── Handler dispatch registry ─────────────────────────────────────────────────

SENTINEL_HANDLERS: dict[str, Any] = {
    "cherenkov/audit-test-file": handle_audit_test_file,
    "cherenkov/check-assertion": handle_check_assertion,
    "cherenkov/suggest-spec-fix": handle_suggest_spec_fix,
}
