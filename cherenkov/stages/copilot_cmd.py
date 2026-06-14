"""
cherenkov/stages/copilot_cmd.py — E10 CLI surface for the manual-QA pillar.

  cherenkov explore --target URL [--path /a --path /b ...]
      Crawl a live surface, surface anomalies, and print a "second pair of
      eyes" risk digest before the tester starts.

  cherenkov author "plain language intent" --output DIR [--target URL]
      Turn plain-language intent into an ejectable Playwright test (no selectors).
"""

from __future__ import annotations


from cherenkov.core.config import Config


def run_explore(
    target: str,
    paths: list[str] | None = None,
    method: str = "GET",
) -> int:
    """Crawl `target` and print a ranked pre-session risk digest."""
    from cherenkov.divergence.explorer import Explorer
    from cherenkov.copilot.digest import SecondPairOfEyes

    paths = paths or ["/"]
    print("=" * 72)
    print("  CHERENKOV explore - second pair of eyes (E10)")
    print("=" * 72)
    print(f"  Target:   {target}")
    print(f"  Autonomy: {Config.COPILOT_AUTONOMY}")
    print(f"  Probing:  {len(paths)} path(s)\n")

    explorer = Explorer(
        base_url=target, run_id="cli_explore", slow_ms=Config.EXPLORER_SLOW_MS
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


def _maybe_reflector():
    """Attach a Reflector if verdict memory is available; never hard-fail."""
    try:
        from cherenkov.reflector.reflector import Reflector

        return Reflector(run_id="cli_explore")
    except Exception:
        return None
