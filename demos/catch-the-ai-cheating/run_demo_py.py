#!/usr/bin/env python3
"""
CHERENKOV demo — "Catch the AI Cheating"

Runs four beats (Gate G0 / E0.2 evidence):

  Beat 1  AI generates a test suite — all green.
  Beat 2  The AI "cheats" by weakening an assertion — still green.
  Beat 3  CHERENKOV catches it via the MeaningfulAssertionGate.
  Beat 4  Fix it for real — gate passes; certificate issued.

Usage:
    python demos/catch-the-ai-cheating/run_demo.py

No external services required: uses CHERENKOV's BrokenImplServer as the
target, so the demo is reproducible offline.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

# Make sure cherenkov is importable when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cherenkov.core.errors import LoggerConfig
from cherenkov.divergence.self_play import BrokenImplServer
from cherenkov.sdet import MeaningfulAssertionGate

# Keep the terminal output clean for the demo recording
LoggerConfig.suppress_stderr = True

# ---------------------------------------------------------------------------
# Simulated target API responses (what a correct implementation returns)
# ---------------------------------------------------------------------------
CORRECT_RESPONSES: dict[str, tuple[int, dict]] = {
    "/users": (201, {"id": "u1", "email": "alice@example.com"}),
    "/health": (200, {"status": "ok"}),
    "/orders": (201, {"id": "o1", "product_id": "p42", "quantity": 2}),
}

# A "broken" implementation — wrong status codes, missing fields
BROKEN_RESPONSES: dict[str, tuple[int, dict]] = {
    "/users": (200, {"id": "u1"}),  # 200 instead of 201, email field missing
    "/health": (200, {"status": "ok"}),  # health is still fine (not broken)
    "/orders": (500, {"error": "gone"}),  # orders endpoint is broken
}


# ---------------------------------------------------------------------------
# Test implementations — each returns (passed: bool, output: str)
# ---------------------------------------------------------------------------


def _http_post(base_url: str, path: str, expect_status: int) -> tuple[bool, str]:
    """Minimal HTTP POST against base_url+path; returns (status==expect, detail)."""
    import http.client
    import json as _json
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
    body = _json.dumps({"email": "alice@example.com", "password": "s3cr3t"})
    try:
        conn.request("POST", path, body, {"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = resp.read().decode()
        passed = resp.status == expect_status
        return passed, f"HTTP {resp.status} body={data}"
    except Exception as exc:
        return False, f"Connection error: {exc}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Three test fixtures (as callable run_test functions)
# ---------------------------------------------------------------------------


def test_create_user_strict(base_url: str) -> tuple[bool, str]:
    """MEANINGFUL: asserts status==201 (correct) and email field present."""
    import http.client
    import json as _json
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
    body = _json.dumps({"email": "alice@example.com", "password": "s3cr3t"})
    try:
        conn.request("POST", "/users", body, {"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = _json.loads(resp.read().decode())
        status_ok = resp.status == 201
        email_ok = data.get("email") == "alice@example.com"
        passed = status_ok and email_ok
        return passed, f"HTTP {resp.status}, email_present={email_ok}"
    except Exception as exc:
        return False, f"Error: {exc}"
    finally:
        conn.close()


def test_create_user_weakened(base_url: str) -> tuple[bool, str]:
    """WEAKENED (cheat): AI changed assert status==201 to status < 500.
    This passes even when the broken impl returns 200 with a missing field."""
    import http.client
    import json as _json
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
    body = _json.dumps({"email": "alice@example.com", "password": "s3cr3t"})
    try:
        conn.request("POST", "/users", body, {"Content-Type": "application/json"})
        resp = conn.getresponse()
        resp.read()
        # Weakened: any 2xx/4xx "success" — doesn't check 201 or email field
        passed = resp.status < 500
        return passed, f"HTTP {resp.status} (weakened: < 500)"
    except Exception as exc:
        return False, f"Error: {exc}"
    finally:
        conn.close()


def test_create_order_strict(base_url: str) -> tuple[bool, str]:
    """MEANINGFUL: asserts status==201 for order creation."""
    import http.client
    import json as _json
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
    body = _json.dumps({"product_id": "p42", "quantity": 2})
    try:
        conn.request("POST", "/orders", body, {"Content-Type": "application/json"})
        resp = conn.getresponse()
        resp.read()
        passed = resp.status == 201
        return passed, f"HTTP {resp.status}"
    except Exception as exc:
        return False, f"Error: {exc}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _banner(title: str) -> None:
    line = "─" * 60
    print(f"\n{line}\n  {title}\n{line}")


def _print_verdict(result) -> None:
    status = "✓ MEANINGFUL" if result.meaningful else "✗ WEAKENED — CAUGHT"
    print(f"  {result.test_id}: {status}")
    if not result.meaningful:
        print(f"    Reason: {result.reason}")
        print(
            f"    Correct mock: {result.passed_correct}  |  Broken impl: {result.failed_broken}"
        )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def main() -> int:
    correct_port = 18800
    broken_port = 18801

    with (
        BrokenImplServer(port=correct_port, responses=CORRECT_RESPONSES) as _correct,
        BrokenImplServer(port=broken_port, responses=BROKEN_RESPONSES) as _broken,
    ):
        correct_url = f"http://127.0.0.1:{correct_port}"
        broken_url = f"http://127.0.0.1:{broken_port}"

        gate = MeaningfulAssertionGate(run_id="demo")

        # ── Beat 1: AI generates a suite, all green ────────────────────────
        _banner("Beat 1 — AI generates a suite (all green)")
        print("  [AI output] Generated 3 tests. Running against target… 3 passed.")
        print("  Coverage: 100%  |  Status: ✓ DONE  ← what every other tool shows you")

        # ── Beat 2: the cheat ──────────────────────────────────────────────
        _banner("Beat 2 — The cheat (AI weakens an assertion to fake green)")
        print("  test_create_user: assert status == 201 and email present")
        print("    → changed to: assert status < 500          # still green!")
        print("  Suite is still green. The AI made it green. Not the software.")

        # ── Beat 3: CHERENKOV catches it ───────────────────────────────────
        _banner("Beat 3 — CHERENKOV catches the cheats")
        print("  Running MeaningfulAssertionGate on each test…\n")

        candidates = [
            ("test_create_user [WEAKENED]", test_create_user_weakened),
            ("test_create_user [STRICT]", test_create_user_strict),
            ("test_create_order [STRICT]", test_create_order_strict),
        ]

        verdicts = gate.filter_meaningful(candidates, correct_url, broken_url)
        for v in verdicts:
            _print_verdict(v)

        caught = [v for v in verdicts if not v.meaningful]
        passed_gate = [v for v in verdicts if v.meaningful]

        print(f"\n  Gate summary: {len(passed_gate)} meaningful, {len(caught)} caught")
        print(f"  Kill rate: {gate.kill_rate():.0%}")

        # ── Beat 4: fix it, get the certificate ───────────────────────────
        _banner("Beat 4 — Fix it for real → CHERENKOV Certificate")
        print("  Applying suggested fix: restore assert status == 201 + email check")
        print("  Re-running gate…\n")

        gate2 = MeaningfulAssertionGate(run_id="demo-fixed")
        fixed_candidates = [
            ("test_create_user [FIXED]", test_create_user_strict),
            ("test_create_order [FIXED]", test_create_order_strict),
        ]
        fixed_verdicts = gate2.filter_meaningful(
            fixed_candidates, correct_url, broken_url
        )
        for v in fixed_verdicts:
            _print_verdict(v)

        all_pass = all(v.meaningful for v in fixed_verdicts)
        cert_status = "PASS" if all_pass else "FAIL"

        print(
            textwrap.dedent(f"""
  ┌─ CHERENKOV Certificate ───────────────────────────────────┐
  │  Status:    {cert_status}                                           │
  │  Verified:  test_create_user, test_create_order           │
  │  Method:    adversarial self-play (broken-impl kill test)  │
  │  NOT_checked: authentication flows, pagination, rate-limit │
  └────────────────────────────────────────────────────────────┘
        """).rstrip()
        )

        print("\n  \"Generation is free now. Trust isn't.")
        print("   CHERENKOV is the part that doesn't let the AI lie to you.\"\n")

        if len(caught) == 0:
            print(
                "ERROR: demo did not catch any cheats — check fixture setup",
                file=sys.stderr,
            )
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
