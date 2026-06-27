"""cherenkov/drift/checker.py — Phase 13 proposal checker (CANDOR lite).

Validates ReconciliationProposals before human approval or auto-commit.
This is a banned-pattern linter: it rejects proposals whose test skeletons
contain vacuous, tautological, or structurally broken assertions.

No LLM is called here. Full CANDOR oracle (mutation-testing harness) is
Phase 14+.
"""

from __future__ import annotations

import re
from typing import Any

from cherenkov.drift.loop import ReconciliationProposal


# ── banned assertion patterns ──────────────────────────────────────────────────

# Each entry is (description, predicate) where predicate(assertion) -> bool.
# If ANY predicate matches, the assertion is considered tautological/vacuous.
_BANNED: list[tuple[str, Any]] = [
    # Empty assertion (no constraint at all)
    ("empty assertion dict", lambda a: not a),
    # No 'type' field — unrecognizable assertion
    ("assertion missing 'type'", lambda a: "type" not in a),
    # Status assertion with empty expected list
    (
        "status assertion with no expected codes",
        lambda a: a.get("type") == "status" and not a.get("expected"),
    ),
    # Tautological field comparison: field == same_field
    (
        "tautological self-comparison",
        lambda a: (
            a.get("type") == "equals"
            and a.get("field") is not None
            and a.get("field") == a.get("expected")
        ),
    ),
    # Assertion that only checks 'status_code' equals itself
    (
        "tautological status_code self-comparison",
        lambda a: (
            a.get("field") == "status_code"
            and str(a.get("expected", "")) == "status_code"
        ),
    ),
    # Wildcard-only schema assertion (matches anything)
    (
        "wildcard schema assertion",
        lambda a: a.get("type") == "schema" and a.get("schema") in ({}, None),
    ),
]


def is_meaningful_assertion(assertion: dict[str, Any]) -> tuple[bool, str]:
    """Return (is_meaningful, reason) for a single assertion dict."""
    for label, predicate in _BANNED:
        try:
            if predicate(assertion):
                return False, label
        except Exception:
            pass
    return True, "ok"


def _extract_assertions(patch: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull assertions list from an "add_test" patch, if present."""
    if patch.get("op") != "add_test":
        return []
    test = patch.get("test", {})
    return test.get("assertions", []) if isinstance(test, dict) else []


def check_proposal(proposal: ReconciliationProposal) -> bool:
    """Return True iff the proposal passes the banned-pattern check.

    Rules:
    1. Proposals with no patch are accepted (metadata-only, e.g. annotate_param).
    2. "add_test" proposals must have at least one assertion.
    3. All assertions must pass is_meaningful_assertion().
    """
    patch = proposal.patch

    if not patch:
        return True  # metadata-only proposal

    if patch.get("op") == "annotate_param":
        return True  # no test content to validate

    if patch.get("op") == "add_test":
        assertions = _extract_assertions(patch)
        if not assertions:
            return False  # rejected: must have at least one assertion

        for assertion in assertions:
            ok, reason = is_meaningful_assertion(assertion)
            if not ok:
                return False

        # Verify request has method + path
        test = patch.get("test", {})
        request = test.get("request", {}) if isinstance(test, dict) else {}
        if not request.get("method") or not isinstance(request.get("path"), str):
            return False

        return True

    # Unknown op — accept (don't block unknown future patch types)
    return True
