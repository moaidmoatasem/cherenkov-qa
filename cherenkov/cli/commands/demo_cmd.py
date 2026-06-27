import sys
import textwrap

import click

from cherenkov.core.errors import LoggerConfig
from cherenkov.divergence.self_play import BrokenImplServer
from cherenkov.sdet import MeaningfulAssertionGate

CORRECT_RESPONSES: dict[str, tuple[int, dict]] = {
    "/users":  (201, {"id": "u1", "email": "alice@example.com"}),
    "/health": (200, {"status": "ok"}),
    "/orders": (201, {"id": "o1", "product_id": "p42", "quantity": 2}),
}

BROKEN_RESPONSES: dict[str, tuple[int, dict]] = {
    "/users":  (200, {"id": "u1"}),          # 200 instead of 201, email missing
    "/health": (200, {"status": "ok"}),
    "/orders": (500, {"error": "gone"}),
}


def _post(base_url: str, path: str, body: dict) -> tuple[int, dict]:
    import http.client
    import json as _json
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
    try:
        conn.request("POST", path, _json.dumps(body), {"Content-Type": "application/json"})
        resp = conn.getresponse()
        try:
            data = _json.loads(resp.read().decode())
        except Exception:
            data = {}
        return resp.status, data
    finally:
        conn.close()


def test_create_user_strict(base_url: str) -> tuple[bool, str]:
    status, data = _post(base_url, "/users", {"email": "alice@example.com", "password": "s3cr3t"})
    email_ok = data.get("email") == "alice@example.com"
    return status == 201 and email_ok, f"HTTP {status}, email_present={email_ok}"


def test_create_user_weakened(base_url: str) -> tuple[bool, str]:
    status, _ = _post(base_url, "/users", {"email": "alice@example.com", "password": "s3cr3t"})
    return status < 500, f"HTTP {status} (weakened: < 500)"


def test_create_order_strict(base_url: str) -> tuple[bool, str]:
    status, _ = _post(base_url, "/orders", {"product_id": "p42", "quantity": 2})
    return status == 201, f"HTTP {status}"


def _banner(title: str) -> None:
    click.echo(f"\n{'─' * 60}\n  {title}\n{'─' * 60}")


def _verdict(result) -> None:
    if result.meaningful:
        click.echo(f"  {result.test_id}: ✓ MEANINGFUL")
    else:
        click.echo(f"  {result.test_id}: ✗ WEAKENED — CAUGHT")
        click.echo(f"    Reason: {result.reason}")
        click.echo(f"    Correct mock: {result.passed_correct}  |  Broken impl: {result.failed_broken}")


@click.command("demo")
def demo_cmd():
    """60-second offline demo — watch CHERENKOV catch the AI cheating."""
    LoggerConfig.suppress_stderr = True

    correct_port, broken_port = 18800, 18801

    with (
        BrokenImplServer(port=correct_port, responses=CORRECT_RESPONSES) as _c,
        BrokenImplServer(port=broken_port,  responses=BROKEN_RESPONSES)  as _b,
    ):
        correct_url = f"http://127.0.0.1:{correct_port}"
        broken_url  = f"http://127.0.0.1:{broken_port}"

        gate = MeaningfulAssertionGate(run_id="demo")

        _banner("Beat 1 — AI generates a suite (all green)")
        click.echo("  [AI output] Generated 3 tests. Running against target… 3 passed.")
        click.echo("  Coverage: 100%  |  Status: ✓ DONE  ← what every other tool shows you")

        _banner("Beat 2 — The cheat (AI weakens an assertion to fake green)")
        click.echo("  test_create_user: assert status == 201 and email present")
        click.echo("    → changed to: assert status < 500          # still green!")
        click.echo("  Suite is still green. The AI made it green. Not the software.")

        _banner("Beat 3 — CHERENKOV catches the cheats")
        click.echo("  Running MeaningfulAssertionGate on each test…\n")

        candidates = [
            ("test_create_user [WEAKENED]", test_create_user_weakened),
            ("test_create_user [STRICT]",   test_create_user_strict),
            ("test_create_order [STRICT]",  test_create_order_strict),
        ]
        verdicts = gate.filter_meaningful(candidates, correct_url, broken_url)
        for v in verdicts:
            _verdict(v)

        caught  = [v for v in verdicts if not v.meaningful]
        passing = [v for v in verdicts if v.meaningful]
        click.echo(f"\n  Gate summary: {len(passing)} meaningful, {len(caught)} caught")
        click.echo(f"  Kill rate: {gate.kill_rate():.0%}")

        _banner("Beat 4 — Fix it for real → CHERENKOV Certificate")
        click.echo("  Applying suggested fix: restore assert status == 201 + email check")
        click.echo("  Re-running gate…\n")

        gate2 = MeaningfulAssertionGate(run_id="demo-fixed")
        fixed_verdicts = gate2.filter_meaningful(
            [
                ("test_create_user [FIXED]",  test_create_user_strict),
                ("test_create_order [FIXED]", test_create_order_strict),
            ],
            correct_url,
            broken_url,
        )
        for v in fixed_verdicts:
            _verdict(v)

        cert_status = "PASS" if all(v.meaningful for v in fixed_verdicts) else "FAIL"

        click.echo(textwrap.dedent(f"""
  ┌─ CHERENKOV Certificate ───────────────────────────────────┐
  │  Status:    {cert_status}                                           │
  │  Verified:  test_create_user, test_create_order           │
  │  Method:    adversarial self-play (broken-impl kill test)  │
  │  NOT_checked: authentication flows, pagination, rate-limit │
  └────────────────────────────────────────────────────────────┘
        """).rstrip())

        click.echo('\n  "Generation is free now. Trust isn\'t.')
        click.echo('   CHERENKOV is the part that doesn\'t let the AI lie to you."\n')

        if caught:
            sys.exit(0)
        click.echo("ERROR: demo did not catch any cheats — check fixture setup", err=True)
        sys.exit(1)
