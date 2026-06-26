"""cherenkov/drift/reconcile.py — reconcile() → DriftReport.

Emits GateSignal into aggregate() (the CANDOR oracle contract).
This module does NOT define new verdict logic — it feeds the oracle.

Two orthogonal axes (from MetaHarness):
  magnitude  — structural distance (similarity score ladder)
  severity   — worst finding severity (any FAIL blocks, regardless of magnitude)

block = (magnitude_verdict == major-drift) OR (gate_verdict == FAIL)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cherenkov.drift.detect import DriftKind, DriftFinding


# ── Gate verdict (PASS / WARN / FAIL) ────────────────────────────────────────

class DriftVerdict(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class GateSignal:
    name: str
    verdict: DriftVerdict
    detail: Any = None


def aggregate(signals: list[GateSignal]) -> DriftVerdict:
    """Roll a list of GateSignals into a single verdict.

    FAIL beats WARN beats PASS. Empty list → PASS.
    """
    if not signals:
        return DriftVerdict.PASS
    verdicts = {s.verdict for s in signals}
    if DriftVerdict.FAIL in verdicts:
        return DriftVerdict.FAIL
    if DriftVerdict.WARN in verdicts:
        return DriftVerdict.WARN
    return DriftVerdict.PASS


# ── Finding → severity mapping ────────────────────────────────────────────────

SEVERITY: dict[DriftKind, DriftVerdict] = {
    DriftKind.BREAKING_SCHEMA_CHANGE:    DriftVerdict.FAIL,
    DriftKind.STATUS_CONTRACT_VIOLATION: DriftVerdict.FAIL,
    DriftKind.REMOVED_OP_STILL_TESTED:   DriftVerdict.FAIL,
    DriftKind.NEW_OP_UNTESTED:           DriftVerdict.WARN,
    DriftKind.DEPRECATED_OP_TESTED:      DriftVerdict.WARN,
    DriftKind.ADDED_OPTIONAL_PARAM:      DriftVerdict.PASS,
}


# ── Magnitude ladder ──────────────────────────────────────────────────────────

class MagnitudeVerdict(str, Enum):
    NEAR_IDENTICAL  = "near-identical"   # overall >= 0.95
    MINOR_DRIFT     = "minor-drift"      # overall >= 0.85
    MODERATE_DRIFT  = "moderate-drift"   # overall >= 0.50
    MAJOR_DRIFT     = "major-drift"      # overall < 0.50


def magnitude_verdict(overall: float) -> MagnitudeVerdict:
    if overall >= 0.95:
        return MagnitudeVerdict.NEAR_IDENTICAL
    if overall >= 0.85:
        return MagnitudeVerdict.MINOR_DRIFT
    if overall >= 0.50:
        return MagnitudeVerdict.MODERATE_DRIFT
    return MagnitudeVerdict.MAJOR_DRIFT


# ── DriftReport ───────────────────────────────────────────────────────────────

@dataclass
class DriftReport:
    """The output of reconcile() — human-readable + machine-actionable.

    magnitude:    structural similarity score [0, 1] and its ladder verdict.
    gate_verdict: worst-case severity from findings (CANDOR oracle rollup).
    findings:     ordered list of DriftFinding from detect_findings().
    blocked:      True if this report should prevent auto-reconcile / CI merge.
    """

    magnitude: float
    magnitude_label: MagnitudeVerdict
    gate_verdict: DriftVerdict
    findings: list[DriftFinding] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return (
            self.magnitude_label == MagnitudeVerdict.MAJOR_DRIFT
            or self.gate_verdict == DriftVerdict.FAIL
        )

    @property
    def has_drift(self) -> bool:
        return bool(self.findings)

    def summary(self) -> str:
        lines = [
            f"magnitude={self.magnitude:.3f} ({self.magnitude_label.value})",
            f"gate={self.gate_verdict.value}",
            f"findings={len(self.findings)}",
            f"blocked={self.blocked}",
        ]
        if self.findings:
            lines.append("--- findings ---")
            for f in self.findings:
                lines.append(f"  [{SEVERITY[f.kind].value.upper()}] {f.kind.value}: {f.detail}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "magnitude": self.magnitude,
            "magnitude_label": self.magnitude_label.value,
            "gate_verdict": self.gate_verdict.value,
            "blocked": self.blocked,
            "findings": [
                {
                    "kind": f.kind.value,
                    "operation_id": f.operation_id,
                    "detail": f.detail,
                    "severity": SEVERITY[f.kind].value,
                }
                for f in self.findings
            ],
        }


# ── reconcile() ───────────────────────────────────────────────────────────────

def reconcile(
    baseline: "SpecSuiteSnapshot",  # noqa: F821
    current_spec: dict[str, Any],
    current_suite: dict[str, Any],
    runner_violations: list[dict] | None = None,
) -> DriftReport:
    """Detect drift and emit a DriftReport by feeding GateSignals into aggregate().

    Detection is deterministic (no LLM). The LLM is only invoked by loop.py
    during the reconciliation proposal step, and only on confirmed drift.

    Args:
        baseline:          The frozen SpecSuiteSnapshot baseline to diff against.
        current_spec:      Parsed OpenAPI spec dict (current state).
        current_suite:     Suite manifest: {operationId: [test_dicts]}.
        runner_violations: Optional axis-C signals from benchmark_harness.

    Returns:
        DriftReport with magnitude, gate_verdict, findings, and blocked flag.
    """
    from cherenkov.drift.detect import detect_findings
    from cherenkov.drift.fingerprint import fingerprint_of, similarity

    findings = detect_findings(baseline, current_spec, current_suite, runner_violations)
    signals = [
        GateSignal(name=f.kind.value, verdict=SEVERITY[f.kind], detail=f)
        for f in findings
    ]

    current_fp = fingerprint_of(current_spec, current_suite)
    overall = similarity(baseline.fingerprint, current_fp)
    mag_label = magnitude_verdict(overall)

    return DriftReport(
        magnitude=overall,
        magnitude_label=mag_label,
        gate_verdict=aggregate(signals),
        findings=findings,
    )
