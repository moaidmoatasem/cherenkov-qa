"""
CHERENKOV copilot/digest.py — E10-3 "second pair of eyes" pre-session digest.

Before a tester starts a session, the Copilot already did the legwork: the
Explorer crawled the build and the Skeptic reasoned over the spec. This module
fuses those signals (plus any accumulated Idioms from the Reflector) into a
single ranked RiskDigest — "here's what I'd check first if I were you."

Pure ranking/assembly: it runs nothing live. Callers pass in the findings,
hypotheses, and (optionally) a Reflector.
"""
from __future__ import annotations

from typing import Any

from cherenkov.core.contracts import (
    DivergenceHypothesis,
    ExplorerFinding,
    RiskDigest,
    RiskItem,
    Severity,
)
from cherenkov.core.errors import get_logger

_SEVERITY_WEIGHT: dict[Severity, float] = {
    Severity.CRITICAL: 1.0,
    Severity.HIGH: 0.75,
    Severity.MEDIUM: 0.5,
    Severity.LOW: 0.25,
}


class SecondPairOfEyes:
    """Assembles a ranked pre-session risk digest from observed + reasoned signals."""

    def __init__(self, reflector: Any | None = None, run_id: str | None = None) -> None:
        self.reflector = reflector
        self.run_id = run_id
        self.log = get_logger("COPILOT_DIGEST", run_id)

    def build(
        self,
        target: str,
        findings: list[ExplorerFinding] | None = None,
        hypotheses: list[DivergenceHypothesis] | None = None,
        generated_for: str = "",
        limit: int = 20,
    ) -> RiskDigest:
        """Fuse Explorer findings + Skeptic hypotheses (+ idioms) into a digest."""
        findings = findings or []
        hypotheses = list(hypotheses or [])

        # Reflector reranks hypotheses by accumulated memory (suppress rejected,
        # boost idiom-matching) before we score them.
        if self.reflector is not None and hypotheses:
            try:
                endpoint = hypotheses[0].endpoint
                hypotheses = self.reflector.rerank(hypotheses, endpoint=endpoint)
            except Exception as e:
                self.log.warning("reflector rerank skipped", error=str(e))

        items: list[RiskItem] = []
        items.extend(self._items_from_findings(findings))
        items.extend(self._items_from_hypotheses(hypotheses))
        items.extend(self._items_from_idioms())

        items = self._dedupe(items)
        items.sort(key=lambda it: it.score, reverse=True)
        items = items[:limit]

        self.log.info("digest built", target=target, items=len(items),
                      findings=len(findings), hypotheses=len(hypotheses))
        return RiskDigest(target=target, generated_for=generated_for, items=items)

    # ── sources → items ──────────────────────────────────────────────────────

    def _items_from_findings(self, findings: list[ExplorerFinding]) -> list[RiskItem]:
        out: list[RiskItem] = []
        for f in findings:
            base = _SEVERITY_WEIGHT.get(f.severity, 0.5)
            # observed > merely hypothesised: Explorer findings get a real signal.
            score = min(1.0, base + 0.15)
            out.append(RiskItem(
                title=f"{f.kind.value.replace('_', ' ')} at {f.url}",
                score=score,
                severity=f.severity,
                source="explorer",
                detail=f.detail,
                endpoint=f"{f.method.upper()} {f.url}",
            ))
        return out

    def _items_from_hypotheses(self, hypotheses: list[DivergenceHypothesis]) -> list[RiskItem]:
        out: list[RiskItem] = []
        n = len(hypotheses)
        for rank, h in enumerate(hypotheses):
            base = _SEVERITY_WEIGHT.get(h.severity, 0.5)
            # preserve rerank order with a small positional bonus
            order_bonus = 0.1 * (1.0 - (rank / n)) if n else 0.0
            out.append(RiskItem(
                title=f"{h.divergence_class.value}: {h.claim_b[:80]}",
                score=min(1.0, base + order_bonus),
                severity=h.severity,
                source="skeptic",
                detail=h.predicted_evidence,
                endpoint=h.endpoint,
                hypothesis_id=h.id,
            ))
        return out

    def _items_from_idioms(self) -> list[RiskItem]:
        if self.reflector is None:
            return []
        try:
            idioms = self.reflector.get_top_idioms(min_decay=0.3, limit=10)
        except Exception as e:
            self.log.warning("idiom surfacing skipped", error=str(e))
            return []
        out: list[RiskItem] = []
        for idiom in idioms:
            out.append(RiskItem(
                title=f"Known idiom: {getattr(idiom, 'pattern', '')[:80]}",
                # idioms are priors, not live signals → mid weight scaled by decay
                score=min(0.7, 0.4 + 0.3 * float(getattr(idiom, "decay_score", 0.0))),
                severity=Severity.MEDIUM,
                source="idiom",
                detail=f"Confirmed {getattr(idiom, 'confirm_count', 1)}x previously.",
                endpoint=getattr(idiom, "endpoint", None),
            ))
        return out

    @staticmethod
    def _dedupe(items: list[RiskItem]) -> list[RiskItem]:
        """Collapse items that point at the same endpoint+title, keeping the highest score."""
        best: dict[tuple[str | None, str], RiskItem] = {}
        for it in items:
            key = (it.endpoint, it.title)
            cur = best.get(key)
            if cur is None or it.score > cur.score:
                best[key] = it
        return list(best.values())
