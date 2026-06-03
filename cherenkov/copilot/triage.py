"""
CHERENKOV copilot/triage.py — E10-4 Triage UX over healing/diagnose.

A manual tester doesn't want a stack trace; they want to know which of four
buckets a failure belongs in — bug | flaky | env | intended — and what to do
next. This maps the existing healing/diagnose FailureClass taxonomy onto those
four tester-facing categories, with a recommended action per case.

It reuses the diagnosis the pipeline already produces (healing/diagnose.py);
it does not re-run or re-diagnose. When a Reflector is attached, prior human
verdicts on the same endpoint nudge the category (e.g. previously-confirmed
"intended" drift stays "intended").
"""
from __future__ import annotations

from typing import Any

from cherenkov.core.contracts import TriageCategory, TriageResult
from cherenkov.core.errors import get_logger
from cherenkov.healing.diagnose import FailureClass

# FailureClass → (category, base_confidence, suggested_action)
_TRIAGE_MAP: dict[str, tuple[TriageCategory, float, str]] = {
    FailureClass.AUTH_EXPIRY.value: (
        TriageCategory.ENV, 0.85,
        "Refresh credentials / token and re-run — not a product defect.",
    ),
    FailureClass.STATE_SEQUENCE.value: (
        TriageCategory.ENV, 0.65,
        "Ensure prerequisite resources exist before this step (test data/order).",
    ),
    FailureClass.FLAKY_SUCCESS.value: (
        TriageCategory.FLAKY, 0.9,
        "Passed on retry — quarantine and stabilise; don't file as a bug yet.",
    ),
    FailureClass.CONTRACT_DRIFT.value: (
        TriageCategory.BUG, 0.6,
        "Response shape changed vs baseline. Confirm with the team: file a bug, "
        "or if the change was intended, accept and update the test.",
    ),
    FailureClass.DETERMINISTIC_FAILURE.value: (
        TriageCategory.BUG, 0.75,
        "Fails every time — reproduce and file with the repro steps + evidence.",
    ),
    FailureClass.GENERIC_FAILURE.value: (
        TriageCategory.BUG, 0.4,
        "Unclassified assertion failure — review the captured response manually.",
    ),
}

_DEFAULT = (TriageCategory.BUG, 0.3, "Review the failure manually.")


class Triage:
    """Pre-classifies failures into bug | flaky | env | intended for a tester."""

    def __init__(self, reflector: Any | None = None, run_id: str | None = None) -> None:
        self.reflector = reflector
        self.run_id = run_id
        self.log = get_logger("COPILOT_TRIAGE", run_id)

    def triage(
        self,
        scenario_id: str,
        failure_class: FailureClass | str,
        detail: str = "",
        evidence: str = "",
        endpoint: str | None = None,
        retried_pass: bool | None = None,
    ) -> TriageResult:
        """Classify one failure.

        Args:
            failure_class: a healing/diagnose FailureClass (or its value).
            retried_pass: if the runner re-ran and it passed, force FLAKY.
            endpoint: used for reflector-informed refinement.
        """
        fc = failure_class.value if isinstance(failure_class, FailureClass) else str(failure_class)

        # A pass-on-retry is the strongest flaky signal there is.
        if retried_pass is True:
            return TriageResult(
                scenario_id=scenario_id,
                category=TriageCategory.FLAKY,
                confidence=0.95,
                failure_class=fc,
                rationale="Re-ran and passed — non-deterministic.",
                suggested_action="Quarantine and stabilise before filing a bug.",
                evidence=evidence,
            )

        category, confidence, action = _TRIAGE_MAP.get(fc, _DEFAULT)
        rationale = detail or f"Diagnosed as {fc}."

        result = TriageResult(
            scenario_id=scenario_id,
            category=category,
            confidence=confidence,
            failure_class=fc,
            rationale=rationale,
            suggested_action=action,
            evidence=evidence,
        )
        return self._refine_with_memory(result, endpoint)

    def from_diagnosis(
        self,
        scenario_id: str,
        diagnosis: Any,
        evidence: str = "",
        endpoint: str | None = None,
        retried_pass: bool | None = None,
    ) -> TriageResult:
        """Convenience: triage directly from a healing/diagnose DiagnosisResult."""
        return self.triage(
            scenario_id=scenario_id,
            failure_class=getattr(diagnosis, "failure_class", FailureClass.GENERIC_FAILURE),
            detail=getattr(diagnosis, "detail", ""),
            evidence=evidence,
            endpoint=endpoint,
            retried_pass=retried_pass,
        )

    def _refine_with_memory(self, result: TriageResult, endpoint: str | None) -> TriageResult:
        """Let prior verdicts nudge the category. Best-effort, never raises."""
        if self.reflector is None or endpoint is None:
            return result
        try:
            # If the team has repeatedly accepted drift on this endpoint as
            # intended, lean toward INTENDED rather than BUG.
            idioms = self.reflector.idioms_for(endpoint)  # may not exist on all stores
        except Exception:
            return result
        if not idioms:
            return result
        if result.category == TriageCategory.BUG and any(
            "intended" in (getattr(i, "pattern", "") or "").lower() for i in idioms
        ):
            result.category = TriageCategory.INTENDED
            result.confidence = min(result.confidence, 0.6)
            result.rationale += " (Reflector: this endpoint has accepted drift before.)"
            result.suggested_action = "Likely an intended change — update the test, confirm with owner."
        return result


def render_triage(results: list[TriageResult]) -> str:
    """Human-readable triage summary, grouped by category."""
    if not results:
        return "Triage: no failures to classify."
    order = [TriageCategory.BUG, TriageCategory.FLAKY, TriageCategory.ENV, TriageCategory.INTENDED]
    by_cat: dict[TriageCategory, list[TriageResult]] = {c: [] for c in order}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)
    lines = ["Triage summary:"]
    for cat in order:
        items = by_cat.get(cat, [])
        if not items:
            continue
        lines.append(f"  {cat.value.upper()} ({len(items)}):")
        for r in items:
            lines.append(f"    - {r.scenario_id}  (conf={r.confidence:.2f})  {r.rationale}")
            lines.append(f"        -> {r.suggested_action}")
    return "\n".join(lines)
