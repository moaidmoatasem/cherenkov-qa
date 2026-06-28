"""
cherenkov/verdict/semantic_judge.py — LLM-as-judge for divergence evidence.

Inspired by DeepEval, Promptfoo, and LangWatch's agent simulation testing.

Uses the Substrate Router to evaluate the *quality* of divergence evidence:
  - Is the claim_a vs claim_b tension meaningful, or trivially obvious?
  - Is the observed diff strong enough to constitute real evidence?
  - Could this be a false positive from a flaky test environment?

Returns a semantic_score (0.0–1.0) and per-finding quality labels.
Falls back gracefully when the substrate is unavailable.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from cherenkov.core.contracts import DivergenceReport, ReasoningRequest


_JUDGE_SCHEMA: dict = {
    "type": "object",
    "required": ["evaluations"],
    "properties": {
        "evaluations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["report_id", "quality_score", "label", "rationale"],
                "properties": {
                    "report_id": {"type": "string"},
                    "quality_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "label": {
                        "type": "string",
                        "enum": ["strong", "weak", "false_positive", "inconclusive"],
                    },
                    "rationale": {"type": "string"},
                    "false_positive_risk": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
            },
        },
        "aggregate_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
    },
}


@dataclass
class EvidenceEvaluation:
    report_id: str
    quality_score: float          # 0.0–1.0
    label: str                    # strong | weak | false_positive | inconclusive
    rationale: str
    false_positive_risk: str = "low"  # low | medium | high


@dataclass
class SemanticJudgeReport:
    aggregate_score: float        # 0.0–1.0 mean quality across all reports
    evaluations: list[EvidenceEvaluation] = field(default_factory=list)
    provider: str = "offline"
    duration_ms: int = 0
    fallback: bool = False        # True = substrate unavailable; used heuristics


class SemanticJudge:
    """
    Evaluates divergence evidence quality using an LLM judge.

    In offline mode (no substrate), falls back to a rule-based heuristic
    that scores evidence based on diff strength and claim specificity.

    Usage::

        judge = SemanticJudge()
        report = judge.evaluate(divergence_reports)
        print(f"Semantic score: {report.aggregate_score:.0%}")
    """

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id

    def evaluate(
        self,
        reports: list[DivergenceReport],
        use_llm: bool = True,
    ) -> SemanticJudgeReport:
        """Evaluate evidence quality across all confirmed divergence reports."""
        if not reports:
            return SemanticJudgeReport(
                aggregate_score=1.0,
                evaluations=[],
                provider="offline",
                fallback=True,
            )

        t0 = time.time()

        if use_llm:
            result = self._llm_evaluate(reports)
            if result is not None:
                return result

        # Fallback to rule-based heuristics
        return self._heuristic_evaluate(reports, t0)

    # ── LLM path ─────────────────────────────────────────────────────────

    def _llm_evaluate(
        self, reports: list[DivergenceReport]
    ) -> SemanticJudgeReport | None:
        try:
            from cherenkov.substrate.router import SubstrateRouter

            router = SubstrateRouter(self.run_id)
            task = self._build_task(reports)
            request = ReasoningRequest(
                task=task,
                output_schema=_JUDGE_SCHEMA,
                capability_tier="fast",
            )
            t0 = time.time()
            result = router.route(request)
            duration_ms = int((time.time() - t0) * 1000)

            content = result.content
            if isinstance(content, str):
                content = json.loads(content)

            evals = [
                EvidenceEvaluation(
                    report_id=e["report_id"],
                    quality_score=float(e["quality_score"]),
                    label=e["label"],
                    rationale=e.get("rationale", ""),
                    false_positive_risk=e.get("false_positive_risk", "low"),
                )
                for e in content.get("evaluations", [])
            ]
            agg = float(
                content.get("aggregate_score", sum(e.quality_score for e in evals) / len(evals))
            )
            return SemanticJudgeReport(
                aggregate_score=agg,
                evaluations=evals,
                provider=result.provider,
                duration_ms=duration_ms,
                fallback=False,
            )
        except Exception:
            return None

    def _build_task(self, reports: list[DivergenceReport]) -> str:
        items = []
        for r in reports:
            items.append(
                f"ID: {r.id}\n"
                f"  claim_a: {r.claim_a}\n"
                f"  claim_b: {r.claim_b}\n"
                f"  evidence diff: {r.evidence.diff[:200]}\n"
                f"  request: {r.evidence.request_summary}"
            )
        evidence_block = "\n\n".join(items)
        return (
            "You are an expert QA judge evaluating API divergence evidence.\n\n"
            "For each divergence report below, assess:\n"
            "  1. quality_score (0.0-1.0): how strong is the evidence?\n"
            "     1.0 = clear, deterministic proof; 0.0 = anecdotal or trivially obvious\n"
            "  2. label: strong | weak | false_positive | inconclusive\n"
            "  3. rationale: one-sentence explanation\n"
            "  4. false_positive_risk: low | medium | high\n\n"
            "Also compute aggregate_score as the mean quality_score across all items.\n\n"
            "Divergence reports:\n\n"
            f"{evidence_block}\n\n"
            'Return JSON matching the schema with an "evaluations" array and "aggregate_score".'
        )

    # ── Heuristic fallback ────────────────────────────────────────────────

    def _heuristic_evaluate(
        self,
        reports: list[DivergenceReport],
        t0: float,
    ) -> SemanticJudgeReport:
        evals: list[EvidenceEvaluation] = []
        for r in reports:
            score, label, rationale, fp_risk = self._score_heuristic(r)
            evals.append(
                EvidenceEvaluation(
                    report_id=r.id,
                    quality_score=score,
                    label=label,
                    rationale=rationale,
                    false_positive_risk=fp_risk,
                )
            )
        agg = sum(e.quality_score for e in evals) / len(evals) if evals else 1.0
        duration_ms = int((time.time() - t0) * 1000)
        return SemanticJudgeReport(
            aggregate_score=agg,
            evaluations=evals,
            provider="heuristic",
            duration_ms=duration_ms,
            fallback=True,
        )

    @staticmethod
    def _score_heuristic(r: DivergenceReport) -> tuple[float, str, str, str]:
        """Score a report on 5 independent heuristic signals."""
        score = 0.0
        signals: list[str] = []

        diff = (r.evidence.diff or "").strip()
        claim_a = r.claim_a or ""
        claim_b = r.claim_b or ""
        req = r.evidence.request_summary or ""

        # Signal 1 — diff is non-trivial (not "no structural diff")
        if diff and diff != "no structural diff":
            score += 0.30
            signals.append("non-trivial diff")

        # Signal 2 — diff mentions a concrete value mismatch
        if any(kw in diff for kw in ("mismatch", "missing", "extra", "expected=", "actual=")):
            score += 0.20
            signals.append("concrete value mismatch")

        # Signal 3 — claim_a and claim_b are specific (mention HTTP codes, field names)
        claim_specific = any(
            kw in claim_a.lower() or kw in claim_b.lower()
            for kw in ("status", "header", "required", "enum", "field", "400", "404", "200")
        )
        if claim_specific:
            score += 0.20
            signals.append("specific claims")

        # Signal 4 — repro steps are present and non-trivial
        if r.repro_steps and len(r.repro_steps) >= 2:
            score += 0.15
            signals.append("repro steps present")

        # Signal 5 — request summary includes a non-200 status
        if req and any(code in req for code in ("400", "404", "401", "403", "422", "500")):
            score += 0.15
            signals.append("non-200 status observed")

        score = min(1.0, score)

        if score >= 0.75:
            label, fp_risk = "strong", "low"
        elif score >= 0.50:
            label, fp_risk = "weak", "medium"
        elif "trivially" in diff.lower() or not diff:
            label, fp_risk = "false_positive", "high"
        else:
            label, fp_risk = "inconclusive", "medium"

        rationale = (
            f"Heuristic signals: {', '.join(signals) if signals else 'none'}"
        )
        return score, label, rationale, fp_risk
