#!/usr/bin/env python3
"""
smoke_test_copilot_e10.py — Kill-criteria exit demo for Epoch 10 Explorer + Copilot v1.

Covers:
  C8 (#123): E10 Explorer crawl -> Skeptic hypotheses (5xx/JS/visual)
  C9 (#124): E10 NL-intent -> artifact (cherenkov author)
  C10 (#125): E10 second-pair-of-eyes digest + triage UX

Uses mock router and probes for deterministic offline verification.
Exit code 0 = all kill criteria passed.
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.core.contracts import (
    DivergenceClass,
    ExplorerFinding,
    ExplorerFindingKind,
    ReasoningResult,
    Severity,
    Status,
    TriageCategory,
)
from cherenkov.divergence.explorer import Explorer
from cherenkov.copilot.intent import IntentAuthor
from cherenkov.copilot.digest import SecondPairOfEyes
from cherenkov.copilot.triage import Triage
from cherenkov.healing.diagnose import FailureClass

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label} — {detail}")
        FAIL += 1


def _probe_map(mapping):
    def probe(url, method):
        for suffix, val in mapping.items():
            if url.endswith(suffix):
                return val
        return 200, 10, "ok"

    return probe


def test_c8_explorer():
    """C8 (#123): Explorer crawl and Skeptic hypothesis generation."""
    print("\n--- C8 (#123): Explorer Crawl & Hypothesis Generation ---")

    # Seed different endpoints to probe
    probe_config = {
        "/boom": (500, 15, "Internal Server Error"),
        "/notfound": (404, 8, "Not Found"),
        "/slow": (200, 3000, "Slow Page"),
        "/unreachable": (None, 0, "Connection refused"),
    }

    # Optional UI probe function to simulate JS error
    def mock_ui_probe(url):
        if "js_err" in url:
            return [
                (
                    ExplorerFindingKind.JS_ERROR,
                    "Uncaught ReferenceError: x is not defined",
                    "at index.js:10",
                )
            ]
        return []

    ex = Explorer(
        base_url="http://localhost:8000",
        http_probe=_probe_map(probe_config),
        ui_probe=mock_ui_probe,
        slow_ms=1000,
    )

    # 1. Test crawling different kinds of HTTP anomalies
    findings = ex.crawl(["/boom", "/notfound", "/slow", "/unreachable", "/js_err"])
    check("Explorer returned expected number of findings", len(findings) == 5)

    kinds = {f.kind for f in findings}
    check("SERVER_ERROR kind detected", ExplorerFindingKind.SERVER_ERROR in kinds)
    check("CLIENT_ERROR kind detected", ExplorerFindingKind.CLIENT_ERROR in kinds)
    check("SLOW_RESPONSE kind detected", ExplorerFindingKind.SLOW_RESPONSE in kinds)
    check("UNREACHABLE kind detected", ExplorerFindingKind.UNREACHABLE in kinds)
    check("JS_ERROR kind detected", ExplorerFindingKind.JS_ERROR in kinds)

    # 2. Conversion to Skeptic hypotheses
    hyps = ex.to_hypotheses(findings)
    check("Hypotheses generated from findings successfully", len(hyps) == len(findings))

    classes = {h.divergence_class for h in hyps}
    check(
        "DivergenceClass D2_CODE_PROD assigned to 5xx/slow/unreachable",
        DivergenceClass.D2_CODE_PROD in classes,
    )
    check(
        "DivergenceClass D5_SPEC_PROD assigned to 4xx client errors",
        DivergenceClass.D5_SPEC_PROD in classes,
    )
    check(
        "DivergenceClass D3_UI_SPEC assigned to JS errors",
        DivergenceClass.D3_UI_SPEC in classes,
    )


def test_c9_intent_author():
    """C9 (#124): Plain-language NL-intent to ejectable Playwright artifact."""
    print("\n--- C9 (#124): Plain-Language Intent to Playwright Test ---")

    # Model payload for intent spec parse
    payload = {
        "title": "Add to Cart and Check Discount",
        "kind": "ui",
        "target_url": "http://localhost:8000",
        "data_hints": {"promo": "SAVE20"},
        "steps": [
            {"action": "navigate", "value": "http://localhost:8000/cart"},
            {"action": "fill", "target": "the Promo Code input", "value": "SAVE20"},
            {"action": "click", "target": "the Apply Discount button"},
            {"action": "expect", "value": "Discount applied successfully"},
        ],
    }

    mock_router = MagicMock()
    mock_router.route.return_value = ReasoningResult(
        content=json.dumps(payload), provider="mock", model="mock-model"
    )

    author = IntentAuthor(router=mock_router)

    # 1. Parsing intent text
    spec = author.parse(
        "verify cart discount apply with SAVE20", target_url="http://localhost:8000"
    )
    check(
        "Intent Spec parsed correctly from router",
        spec.title == "Add to Cart and Check Discount",
    )
    check("Steps mapped correctly", len(spec.steps) == 4)
    check("Data hints extracted successfully", spec.data_hints.get("promo") == "SAVE20")

    # 2. Test fallback mode when router raises/fails
    broken_router = MagicMock()
    broken_router.route.side_effect = RuntimeError("Mock router error")
    broken_author = IntentAuthor(router=broken_router)
    fallback_spec = broken_author.parse(
        "smoke test", target_url="http://localhost:8000"
    )
    check("Fallback spec status is DEGRADED", fallback_spec.status == Status.DEGRADED)
    check("Fallback spec contains executable steps", len(fallback_spec.steps) > 0)

    # 3. Code Generation (Playwright TypeScript)
    pw_code = author.to_playwright(spec)
    check(
        "Emitted code contains playwright imports",
        'import { test, expect } from "@playwright/test"' in pw_code,
    )
    check(
        "Emitted code uses selector-free getByLabel role locator",
        'page.getByLabel("Promo Code")' in pw_code,
    )
    check(
        "Emitted code uses selector-free getByRole button locator",
        'page.getByRole("button", { name: "Apply Discount" })' in pw_code,
    )
    check(
        "Emitted code contains expected assertions",
        'expect(page.getByText("Discount applied successfully")).toBeVisible()'
        in pw_code,
    )

    # Ejectability validations
    check(
        "Ejectable code contains zero cherenkov imports",
        "import { cherenkov }" not in pw_code and 'from "cherenkov' not in pw_code,
    )
    check(
        "Ejectable code does not require cherenkov module",
        'require("cherenkov")' not in pw_code,
    )

    # 4. Unsupported action surfaces a warning (#158)
    author2 = IntentAuthor(router=mock_router)
    unsupported_steps = [
        {"action": "swipe", "target": "the menu", "note": "swipe left"},
        {"action": "longpress", "target": "the icon", "note": "press and hold"},
    ]
    payload2 = {**payload, "steps": unsupported_steps}
    mock_router2 = MagicMock()
    mock_router2.route.return_value = ReasoningResult(
        content=json.dumps(payload2), provider="mock", model="mock-model"
    )
    author2.router = mock_router2
    spec2 = author2.parse("swipe menu and longpress icon")
    # Unsupported actions are tracked during rendering (to_playwright), where each
    # step's action is mapped to Playwright code — so assert after rendering.
    pw_code2 = author2.to_playwright(spec2)
    check("Unsupported actions tracked", len(author2._unsupported_actions) > 0)
    check(
        "Unsupported actions include 'swipe'", "swipe" in author2._unsupported_actions
    )
    check(
        "Unsupported actions include 'longpress'",
        "longpress" in author2._unsupported_actions,
    )
    check(
        "Unsupported action emits UNSUPPORTED comment (not TODO)",
        "// UNSUPPORTED:" in pw_code2,
    )
    check("No // TODO emitted for unsupported actions", "// TODO" not in pw_code2)
    check(
        "Supported actions listed in comment",
        "navigate, click, fill, expect, request" in pw_code2,
    )

    # 5. Durable file writing
    with tempfile.TemporaryDirectory() as temp_dir:
        written_spec, file_path = author.author(
            "verify cart discount apply with SAVE20",
            output_dir=temp_dir,
            target_url="http://localhost:8000",
        )
        check("Test file exists", file_path.exists())
        check(
            "Test file has correct filename extension",
            file_path.name.endswith(".spec.ts"),
        )
        content = file_path.read_text(encoding="utf-8")
        check("File content matches Playwright code", "await page.goto" in content)


def test_c10_digest_and_triage():
    """C10 (#125): Risk Digest ranking & Failure Triage UX."""
    print("\n--- C10 (#125): Risk Digest & Triage UX ---")

    # 1. SecondPairOfEyes pre-session digest tests
    mock_reflector = MagicMock()
    # Mocking rerank to return hypotheses unchanged
    mock_reflector.rerank.side_effect = lambda h, endpoint=None: h

    # Mocking get_top_idioms to return a known idiom pattern
    mock_idiom = MagicMock()
    mock_idiom.pattern = "tenant isolation on order endpoints"
    mock_idiom.decay_score = 0.95
    mock_idiom.confirm_count = 5
    mock_idiom.endpoint = "GET /orders"
    mock_reflector.get_top_idioms.return_value = [mock_idiom]

    findings = [
        ExplorerFinding(
            id="f1",
            kind=ExplorerFindingKind.SERVER_ERROR,
            url="http://localhost:8000/boom",
            method="GET",
            status=500,
            latency_ms=10,
            detail="Server error on boom",
            evidence="stacktrace",
            severity=Severity.CRITICAL,
        ),
        ExplorerFinding(
            id="f2",
            kind=ExplorerFindingKind.SLOW_RESPONSE,
            url="http://localhost:8000/slow",
            method="GET",
            status=200,
            latency_ms=2500,
            detail="Slow endpoint response",
            evidence="",
            severity=Severity.LOW,
        ),
    ]

    digest = SecondPairOfEyes(reflector=mock_reflector).build(
        target="http://localhost:8000", findings=findings
    )

    check("Digest contains mapped items", len(digest.items) > 0)
    check(
        "Digest ranked critical item first",
        digest.items[0].severity == Severity.CRITICAL,
    )
    check(
        "Digest items contain Reflector idioms source",
        any(it.source == "idiom" for it in digest.items),
    )

    rendered_digest = digest.render()
    check(
        "Rendered digest lists target URL", "http://localhost:8000" in rendered_digest
    )
    check("Rendered digest lists severity label", "CRITICAL" in rendered_digest)

    # 2. Triage Category mapping and Reflector memory interaction
    triage_engine = Triage()
    env_triage = triage_engine.triage("scen-1", FailureClass.AUTH_EXPIRY)
    check(
        "FailureClass.AUTH_EXPIRY triaged as ENV",
        env_triage.category == TriageCategory.ENV,
    )

    flaky_triage = triage_engine.triage(
        "scen-2", FailureClass.DETERMINISTIC_FAILURE, retried_pass=True
    )
    check(
        "Passed-on-retry forces category to FLAKY",
        flaky_triage.category == TriageCategory.FLAKY,
    )

    # Reflector memory nudge: if endpoint has accepted drift, triage BUG to INTENDED
    reflector_with_accepted_drift = MagicMock()
    mock_drift_idiom = MagicMock()
    mock_drift_idiom.pattern = "intended drift accepted on endpoint"
    reflector_with_accepted_drift.idioms_for.return_value = [mock_drift_idiom]

    triage_with_memory = Triage(reflector=reflector_with_accepted_drift)
    nudged_triage = triage_with_memory.triage(
        "scen-3", FailureClass.CONTRACT_DRIFT, endpoint="GET /new-api"
    )
    check(
        "BUG category nudged to INTENDED via Reflector memory",
        nudged_triage.category == TriageCategory.INTENDED,
    )


def main():
    global PASS, FAIL
    print("=" * 72)
    print("     CHERENKOV E10 Explorer + Copilot v1 Kill-Criteria Exit Demo")
    print("=" * 72)

    test_c8_explorer()
    test_c9_intent_author()
    test_c10_digest_and_triage()

    print("\n" + "=" * 72)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} checks passed, {FAIL} failed")
    if FAIL == 0:
        print("STATUS: ALL KILL CRITERIA MET — Epoch 10 Explorer + Copilot is green.")
        print("=" * 72)
        return 0
    else:
        print(f"STATUS: {FAIL} checks FAILED — review logs above.")
        print("=" * 72)
        return 1


if __name__ == "__main__":
    sys.exit(main())
