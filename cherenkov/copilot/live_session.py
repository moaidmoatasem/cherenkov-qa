"""
CHERENKOV copilot/live_session.py — live agent-driven scenario results → HITL.

Closes the loop for the "agentic exploration" workflow (see
skills/agentic-exploration/SKILL.md): a Claude Code session/subagent drives a
real browser against a plain-language scenario (an `IntentSpec`, the same
structure `cherenkov author` already produces) and judges pass/fail live —
something no crawler can do, since it requires reading the page and deciding
whether "a visible confirmation" actually appeared.

This module does NOT drive a browser itself (that's the agent's job, using
its own Bash/Playwright/Read tools). It only converts an agent's *finished*
judgment into the same `DivergenceHypothesis` shape the Skeptic already
produces, and enqueues it into the existing HITL queue — no new schema, no
new queue, no auto-confirmed defects (same invariant `divergence/explorer.py`
already documents: findings are hypotheses for a human to confirm or reject).
"""

from __future__ import annotations

import uuid

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    IntentSpec,
    Severity,
)
from cherenkov.hitl.contracts import HitlItem
from cherenkov.hitl.store import HitlQueue


def hypothesis_from_scenario(
    spec: IntentSpec,
    expected: str,
    actual: str,
    severity: Severity = Severity.MEDIUM,
) -> DivergenceHypothesis:
    """Build a D3 (ui<->spec) hypothesis from a live agent's scenario judgment."""
    repro_steps = [
        f"{s.action} {s.target or s.value}".strip() for s in spec.steps
    ] or [spec.raw_intent]
    return DivergenceHypothesis(
        id=str(uuid.uuid4()),
        divergence_class=DivergenceClass.D3_UI_SPEC,
        claim_a=f"Scenario {spec.title!r} expects: {expected}",
        claim_b=f"Observed instead: {actual}",
        predicted_evidence=actual,
        severity=severity,
        endpoint=spec.target_url or None,
        repro_steps=repro_steps,
    )


def enqueue_scenario_finding(
    hypothesis: DivergenceHypothesis,
    run_id: str | None = None,
    queue: HitlQueue | None = None,
) -> HitlItem:
    """Enqueue a scenario-derived hypothesis into the HITL queue for triage."""
    queue = queue or HitlQueue()
    item = HitlItem(
        id=hypothesis.id,
        endpoint=hypothesis.endpoint,
        mutation_label=hypothesis.divergence_class.value,
        confidence_reason=f"{hypothesis.claim_a} | {hypothesis.claim_b}"[:400],
        severity=hypothesis.severity,
        run_id=run_id,
    )
    return queue.enqueue(item)
