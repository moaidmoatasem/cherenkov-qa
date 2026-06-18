#!/usr/bin/env python3
"""
demos/catch-the-ai-cheating/run_demo.py

Demonstrates CHERENKOV's integrity gates catching three AI agent cheat patterns:
  1. Weakened assertion  — caught by Gate 4 (static assertion analysis)
  2. Deleted check       — caught by Gate 4 (static assertion analysis)
  3. Hallucinated oracle — caught by Gate 6 (Prism dynamic dry-run, requires Docker)

Usage:
    python demos/catch-the-ai-cheating/run_demo.py

No cloud dependencies. Gate 6 (Prism) requires Docker on the PATH; if unavailable
the gate is skipped and that is reported honestly.

This run is Gate G0 / E0.2 evidence — "Catch the AI Cheating."
Capture the output the first time all three cheats are caught.
"""

from __future__ import annotations

import os
import sys
import time

# ── Repo root on path ───────────────────────────────────────────────────────
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, REPO_ROOT)

from cherenkov.core.errors import LoggerConfig  # noqa: E402
from cherenkov.stages.review import ReviewStage  # noqa: E402
from cherenkov.core.contracts import GenerateOutput, StageMeta, Status  # noqa: E402

# Silence JSON-lines log output — demo terminal should show only formatted output
LoggerConfig.suppress_stderr = True

# ── Paths ───────────────────────────────────────────────────────────────────
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SPEC_PATH = os.path.join(REPO_ROOT, "stub", "openapi_3_1.yaml")

# ── ANSI colours ────────────────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _colour(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def _load_fixture(filename: str) -> str:
    with open(os.path.join(FIXTURES_DIR, filename)) as f:
        return f.read()


def _verdict_colour(verdict: str) -> str:
    if verdict == "auto_approve":
        return _colour("PASS ✓", GREEN)
    if verdict == "regenerate":
        return _colour("FAIL ✗", RED)
    return _colour("HITL ↑", YELLOW)


def _run_and_print(
    label: str,
    filename: str,
    scenario_id: str,
    endpoint: str = "/users",
    method: str = "POST",
) -> None:
    """Run one fixture through the REVIEW stage and print a formatted report."""
    print()
    print(_colour("─" * 70, DIM))
    print(_colour(f"  FIXTURE: {label}", BOLD))
    print(_colour(f"  File:    fixtures/{filename}", DIM))
    print(_colour("─" * 70, DIM))

    code = _load_fixture(filename)

    generate_out = GenerateOutput(
        scenario_id=scenario_id,
        test_code=code,
        endpoint=endpoint,
        method=method,
        status=Status.OK,
        metadata=StageMeta(stage="GENERATE"),
    )

    stage = ReviewStage(run_id=f"demo-{scenario_id}")
    t0 = time.time()
    result = stage.run(generate_out, spec_path=SPEC_PATH)
    elapsed = int((time.time() - t0) * 1000)

    # Gate breakdown
    for gate in result.gates:
        if gate.skipped:
            icon = _colour("○ SKIP", DIM)
        elif gate.passed:
            icon = _colour("✓ PASS", GREEN)
        else:
            icon = _colour("✗ FAIL", RED)
        print(f"  Gate [{gate.gate:<18}]  {icon}")
        if not gate.passed and not gate.skipped:
            print(_colour(f"             ↳ {gate.detail}", RED))

    print()
    print(f"  Verdict : {_verdict_colour(result.verdict.value)}")
    print(f"  Score   : {result.quality_score:.0%}  ({elapsed}ms)")


def main() -> None:
    print()
    print(_colour("=" * 70, BOLD))
    print(_colour("  CHERENKOV — 'Catch the AI Cheating' Demo", BOLD))
    print(_colour("  Gate G0 / E0.2 — integrity catch proof", DIM))
    print(_colour("=" * 70, BOLD))
    print()
    print("  We let an AI write the tests.  Then we let it cheat.")
    print("  Watch CHERENKOV catch it — using the same 6-gate REVIEW stage")
    print("  that runs in production on every generated suite.")
    print()
    print(
        _colour(
            "  Beat 1 — Baseline: what a correct spec-derived test looks like", CYAN
        )
    )

    _run_and_print(
        label="Correct test (spec-derived baseline)",
        filename="correct_test.spec.ts",
        scenario_id="demo_correct",
    )

    print()
    print(
        _colour("  Beat 2+3 — The cheats: suite is 'green' — but should it be?", CYAN)
    )

    _run_and_print(
        label="Cheat 1: Weakened assertion  [toBeLessThan(500) instead of toBe(201)]",
        filename="cheat_weakened_assertion.spec.ts",
        scenario_id="demo_weakened",
    )

    _run_and_print(
        label="Cheat 2: Deleted check  [body assertions removed]",
        filename="cheat_deleted_check.spec.ts",
        scenario_id="demo_deleted",
    )

    _run_and_print(
        label="Cheat 3: Hallucinated oracle  ['auth_token' not in spec]",
        filename="cheat_hallucinated_oracle.spec.ts",
        scenario_id="demo_hallucinated",
    )

    print()
    print(_colour("─" * 70, DIM))
    print()
    print("  Verdicts: PASS = suite is trustworthy | HITL = flagged for human review")
    print(
        "            (HITL = Human-In-The-Loop — goes to review queue, not auto-merged)"
    )
    print()
    print("  Cheats 1 + 2: caught STATICALLY by Gate 4 — zero server, zero runtime.")
    print("  Gate 4 re-derives what assertions a spec-derived test MUST contain.")
    print("  If the check is loosened or deleted, the gate flags it for human review.")
    print()
    print("  Cheat 3: passes all static gates — 'auth_token' looks structurally valid.")
    print("  Caught by Gate 6 (Prism dynamic dry-run) when Docker is available.")
    print(
        "  If Docker is absent, the gate is skipped — reported honestly, never faked."
    )
    print()
    print("  Core property: CHERENKOV re-derives truth from the spec — it does NOT")
    print("  trust what the suite's own assertions claim. It goes back to the source.")
    print()
    print(_colour("  Generation is free now. Trust isn't.", BOLD))
    print(_colour("  CHERENKOV is the part that doesn't let the AI lie to you.", BOLD))
    print()
    print(_colour("─" * 70, DIM))
    print(
        _colour(
            "  Gate G0 / E0.2 evidence: screenshot or `asciinema rec` this output.", DIM
        )
    )
    print(_colour("─" * 70, DIM))
    print()


if __name__ == "__main__":
    main()
