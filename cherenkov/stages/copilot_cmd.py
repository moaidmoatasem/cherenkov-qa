"""
cherenkov/stages/copilot_cmd.py — E10 CLI surface for the manual-QA pillar.

  cherenkov explore --target URL [--path /a --path /b ...]
      Crawl a live surface, surface anomalies, and print a "second pair of
      eyes" risk digest before the tester starts.

  cherenkov author "plain language intent" --output DIR [--target URL]
      Turn plain-language intent into an ejectable Playwright test (no selectors).

  cherenkov record RESULTS.json [--run-id ID]
      Ingest live agent-driven scenario judgments (see
      skills/agentic-exploration/SKILL.md) into the HITL queue as D3
      (ui<->spec) hypotheses for human triage.
"""

from __future__ import annotations

import json

from cherenkov.core.settings import get_settings


def run_explore(
    target: str,
    paths: list[str] | None = None,
    method: str = "GET",
) -> int:
    """Crawl `target` and print a ranked pre-session risk digest."""
    from cherenkov.copilot.digest import SecondPairOfEyes
    from cherenkov.divergence.explorer import Explorer

    paths = paths or ["/"]
    print("=" * 72)
    print("  CHERENKOV explore - second pair of eyes (E10)")
    print("=" * 72)
    print(f"  Target:   {target}")
    print(f"  Autonomy: {get_settings().COPILOT_AUTONOMY}")
    print(f"  Probing:  {len(paths)} path(s)\n")

    explorer = Explorer(
        base_url=target, run_id="cli_explore", slow_ms=get_settings().EXPLORER_SLOW_MS
    )
    findings = explorer.crawl(paths, method=method)
    hypotheses = explorer.to_hypotheses(findings)

    reflector = _maybe_reflector()
    digest = SecondPairOfEyes(reflector=reflector, run_id="cli_explore").build(
        target=target,
        findings=findings,
        hypotheses=hypotheses,
    )

    print(digest.render())
    print("\n" + "=" * 72)
    print(f"  {len(findings)} finding(s) observed -> fed to the Skeptic as hypotheses.")
    print(
        '  Next: cherenkov author "<your test intent>" --output ./tests --target '
        + target
    )
    print("=" * 72)
    # Non-zero only on unreachable target so this stays a digest, not a gate.
    unreachable = any(f.kind.value == "unreachable" for f in findings)
    return 1 if unreachable else 0


def run_author(
    intent: str,
    output: str,
    target: str = "",
) -> int:
    """Author an ejectable Playwright test from plain-language intent."""
    from cherenkov.copilot.intent import IntentAuthor

    print("=" * 72)
    print("  CHERENKOV author - intent -> ejectable test (E10)")
    print("=" * 72)
    print(f"  Intent: {intent!r}")
    if target:
        print(f"  Target: {target}")
    print()

    author = IntentAuthor(run_id="cli_author")
    spec, path = author.author(intent, output_dir=output, target_url=target)

    unsupported = author._unsupported_actions
    if unsupported:
        print("  ⚠ WARNING: Some actions were not supported and could not be rendered.")
        for action in sorted(set(unsupported)):
            print(
                f"    - {action!r} (supported: navigate, click, fill, expect, request)"
            )
        print()

    print(f"  Title:  {spec.title}")
    print(
        f"  Steps:  {len(spec.steps)}  (kind={spec.kind}, status={spec.status.value})"
    )
    for i, step in enumerate(spec.steps, 1):
        tgt = f" -> {step.target}" if step.target else ""
        val = f" = {step.value!r}" if step.value else ""
        print(f"    {i}. {step.action}{tgt}{val}")
    print(f"\n  [OK] Wrote standard Playwright test: {path}")
    print("  This file is yours - runs standalone, no CHERENKOV runtime required.")
    print("=" * 72)
    return 1 if unsupported else 0


def run_record(result_path: str, run_id: str | None = None) -> int:
    """Ingest a live agentic-exploration results file into the HITL queue.

    Expects {"scenarios": [{title, target_url, raw_intent, steps, expected,
    actual, severity, passed}, ...]}. Only failed scenarios are enqueued —
    passes are just summarised, mirroring the Explorer's "findings are
    anomalies" contract.
    """
    from cherenkov.core.contracts import IntentSpec, IntentStep, Severity
    from cherenkov.copilot.live_session import (
        enqueue_scenario_finding,
        hypothesis_from_scenario,
    )

    print("=" * 72)
    print("  CHERENKOV record - agentic scenario results -> HITL (E10)")
    print("=" * 72)

    with open(result_path, encoding="utf-8") as f:
        data = json.load(f)

    scenarios = data.get("scenarios", [])
    passed = 0
    enqueued: list[str] = []
    for s in scenarios:
        if s.get("passed", False):
            passed += 1
            continue
        spec = IntentSpec(
            id=s.get("id", ""),
            raw_intent=s.get("raw_intent", s.get("title", "")),
            title=s.get("title", "Untitled scenario"),
            target_url=s.get("target_url", ""),
            steps=[
                IntentStep(
                    action=st.get("action", "expect"),
                    target=st.get("target", ""),
                    value=st.get("value", ""),
                    note=st.get("note", ""),
                )
                for st in s.get("steps", [])
            ],
        )
        severity = Severity(s.get("severity", "medium"))
        hypothesis = hypothesis_from_scenario(
            spec,
            expected=s.get("expected", ""),
            actual=s.get("actual", ""),
            severity=severity,
        )
        enqueue_scenario_finding(hypothesis, run_id=run_id)
        enqueued.append(spec.title)

    print(f"  Scenarios: {len(scenarios)} total, {passed} passed, {len(enqueued)} failed")
    for title in enqueued:
        print(f"    - {title}  -> queued for HITL review")
    print("\n  Next: cherenkov hitl list --status pending")
    print("=" * 72)
    return 0


def _maybe_reflector():
    """Attach a Reflector if verdict memory is available; never hard-fail."""
    try:
        from cherenkov.reflector.reflector import Reflector

        return Reflector(run_id="cli_explore")
    except Exception:
        return None
