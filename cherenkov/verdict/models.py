"""
cherenkov/verdict/models.py — Rich verdict contracts.

Replaces the binary PASS/FAIL with a multi-dimensional, graded verdict
inspired by the Qodo multi-agent model, QA.tech's confidence bands, and
Promptfoo's LLM-as-judge scoring.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class VerdictGrade(str, Enum):
    A = "A"   # ≥90  — excellent
    B = "B"   # ≥75  — good, minor issues
    C = "C"   # ≥60  — acceptable, notable gaps
    D = "D"   # ≥40  — poor, significant issues
    F = "F"   # <40  — critical failures


class OverallVerdict(str, Enum):
    CERTIFIED  = "CERTIFIED"    # Grade A, no HIGH/CRITICAL divergences
    DIVERGENT  = "DIVERGENT"    # Active divergences confirmed
    SUSPECT    = "SUSPECT"      # Low confidence or partial coverage
    INCONCLUSIVE = "INCONCLUSIVE"  # Engine could not form a verdict


class RiskFlag(str, Enum):
    SECURITY_RISK      = "SECURITY_RISK"       # auth bypass, injection surface
    SCHEMA_DRIFT       = "SCHEMA_DRIFT"        # spec ≠ prod shape/headers
    VACUOUS_ASSERTIONS = "VACUOUS_ASSERTIONS"  # tests pass broken impls
    LOW_COVERAGE       = "LOW_COVERAGE"        # <60% spec endpoints probed
    PERF_ANOMALY       = "PERF_ANOMALY"        # latency outlier observed
    MISSING_HEADERS    = "MISSING_HEADERS"     # documented headers absent
    ENUM_VIOLATION     = "ENUM_VIOLATION"      # server ignores enum constraints
    REQUIRED_FIELD_GAP = "REQUIRED_FIELD_GAP"  # required fields not validated


class ActionableFinding(BaseModel):
    """One concrete finding with a remediation hint."""

    rank: int           # 1 = highest priority
    severity: str       # low | medium | high | critical
    divergence_class: str
    endpoint: str
    summary: str        # ≤120 chars, human-readable
    remediation: str    # concrete fix recommendation
    estimated_fix_minutes: int = 30


class VerdictDimension(BaseModel):
    """Result from one specialised agent in the parallel fleet."""

    name: str                              # "divergence_probe" | "mutation_oracle" | ...
    score: float                           # 0.0–1.0
    grade: VerdictGrade
    passed: bool
    findings: list[str] = Field(default_factory=list)
    detail: str = ""
    duration_ms: int = 0


class RichVerdict(BaseModel):
    """
    The full multi-dimensional verdict produced by VerdictEngine.

    Inspired by:
    - TestSprite's parallel-agent fleet model
    - Qodo's per-dimension specialised agents
    - QA.tech's confidence band output
    - Promptfoo/DeepEval's LLM-as-judge semantic scoring
    """

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    target_url: str
    spec_source: str = "built-in"

    # ── Overall verdict ──────────────────────────────────────────────────
    overall: OverallVerdict
    grade: VerdictGrade
    confidence: float             # 0.0–1.0; how much data we have to be sure

    # ── Per-agent dimensions ─────────────────────────────────────────────
    dimensions: list[VerdictDimension] = Field(default_factory=list)

    # ── Aggregate metrics ────────────────────────────────────────────────
    divergence_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    coverage_pct: float = 0.0     # % of spec endpoints probed
    mutation_score: float | None = None   # % of mutations the detector caught
    semantic_score: float | None = None   # LLM-judge quality of evidence
    captured_fixtures: int = 0    # golden fixtures promoted from real traffic

    # ── Risk profile ─────────────────────────────────────────────────────
    risk_flags: list[RiskFlag] = Field(default_factory=list)

    # ── Findings ─────────────────────────────────────────────────────────
    top_findings: list[ActionableFinding] = Field(default_factory=list)

    # ── Meta ─────────────────────────────────────────────────────────────
    duration_ms: int = 0
    time_to_fix_estimate: str = ""   # "~2h", "~1 sprint", "none needed"

    # ── Rendered output ───────────────────────────────────────────────────
    def render(self) -> str:
        """Rich CLI-ready verdict card."""
        w = 68
        grade_colour = _grade_colour(self.grade)
        verdict_colour = _verdict_colour(self.overall)

        lines: list[str] = []
        lines.append("╔" + "═" * (w - 2) + "╗")
        lines.append(_row("CHERENKOV VERDICT", w))
        lines.append("╠" + "═" * (w - 2) + "╣")
        lines.append(_row(f"Target : {self.target_url}", w))
        lines.append(
            _row(
                f"Grade  : {self.grade.value}   "
                f"Confidence : {self.confidence:.0%}   "
                f"Overall : {self.overall.value}",
                w,
            )
        )
        lines.append("╠" + "═" * (w - 2) + "╣")

        for dim in self.dimensions:
            bar = _bar(dim.score, 14)
            status = "PASS" if dim.passed else "FAIL"
            lines.append(_row(f"  {dim.name:<22} {bar}  {status}", w))

        lines.append("╠" + "═" * (w - 2) + "╣")

        extra_metrics = []
        if self.mutation_score is not None:
            extra_metrics.append(f"Mutation score : {self.mutation_score:.0%}")
        if self.semantic_score is not None:
            extra_metrics.append(f"Semantic score : {self.semantic_score:.0%}")
        if self.coverage_pct:
            extra_metrics.append(f"Coverage       : {self.coverage_pct:.1f}%")
        if self.captured_fixtures:
            extra_metrics.append(f"Golden fixtures: {self.captured_fixtures}")
        for m in extra_metrics:
            lines.append(_row(f"  {m}", w))
        if extra_metrics:
            lines.append("╠" + "═" * (w - 2) + "╣")

        if self.risk_flags:
            flags_str = "  ".join(f"! {f.value}" for f in self.risk_flags)
            lines.append(_row(f"  Risk : {flags_str}", w))
            lines.append("╠" + "═" * (w - 2) + "╣")

        if self.top_findings:
            lines.append(_row("  Top findings:", w))
            for f in self.top_findings[:5]:
                lines.append(_row(f"    {f.rank}. [{f.severity.upper()}] {f.summary[:56]}", w))
                lines.append(_row(f"       Fix: {f.remediation[:54]}", w))
            lines.append("╠" + "═" * (w - 2) + "╣")

        lines.append(_row(f"  Est. fix time : {self.time_to_fix_estimate}", w))
        lines.append("╚" + "═" * (w - 2) + "╝")
        return "\n".join(lines)


# ── helpers ──────────────────────────────────────────────────────────────────


def _row(text: str, width: int) -> str:
    padded = text.ljust(width - 4)
    if len(padded) > width - 4:
        padded = padded[: width - 7] + "..."
    return f"║ {padded} ║"


def _bar(score: float, length: int = 14) -> str:
    filled = round(score * length)
    return "█" * filled + "░" * (length - filled)


def _grade_colour(grade: VerdictGrade) -> str:
    return {"A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red"}.get(
        grade.value, "white"
    )


def _verdict_colour(verdict: OverallVerdict) -> str:
    return {
        "CERTIFIED": "green",
        "DIVERGENT": "red",
        "SUSPECT": "yellow",
        "INCONCLUSIVE": "white",
    }.get(verdict.value, "white")


def score_to_grade(score: float) -> VerdictGrade:
    """Map a 0.0-1.0 score to a letter grade."""
    if score >= 0.90:
        return VerdictGrade.A
    if score >= 0.75:
        return VerdictGrade.B
    if score >= 0.60:
        return VerdictGrade.C
    if score >= 0.40:
        return VerdictGrade.D
    return VerdictGrade.F


def _estimate_fix_time(findings: list[ActionableFinding]) -> str:
    if not findings:
        return "none needed"
    total_min = sum(f.estimated_fix_minutes for f in findings)
    if total_min <= 60:
        return f"~{total_min}min"
    if total_min <= 480:
        hours = total_min / 60
        return f"~{hours:.0f}h"
    return "~1 sprint"


def assemble_verdict(
    target_url: str,
    spec_source: str,
    dimensions: list[VerdictDimension],
    divergence_reports: list,
    coverage_pct: float,
    mutation_score: float | None,
    semantic_score: float | None,
    captured_fixtures: int,
    duration_ms: int,
) -> RichVerdict:
    """Assemble a RichVerdict from dimension results and raw metrics."""
    from cherenkov.core.contracts import Severity

    # ── severity counts ───────────────────────────────────────────────────
    critical_count = sum(
        1 for r in divergence_reports
        if getattr(r, "severity", None) in (Severity.CRITICAL, "critical")
    )
    high_count = sum(
        1 for r in divergence_reports
        if getattr(r, "severity", None) in (Severity.HIGH, "high")
    )
    medium_count = sum(
        1 for r in divergence_reports
        if getattr(r, "severity", None) in (Severity.MEDIUM, "medium")
    )
    low_count = sum(
        1 for r in divergence_reports
        if getattr(r, "severity", None) in (Severity.LOW, "low")
    )

    # ── risk flags ────────────────────────────────────────────────────────
    risk_flags: list[RiskFlag] = []
    if critical_count > 0 or high_count > 0:
        risk_flags.append(RiskFlag.SECURITY_RISK)
    if any(
        "header" in getattr(r, "claim_b", "").lower() or
        "X-" in getattr(r, "claim_a", "")
        for r in divergence_reports
    ):
        risk_flags.append(RiskFlag.MISSING_HEADERS)
    if any(
        "enum" in getattr(r, "claim_a", "").lower() or
        "status" in getattr(r, "claim_a", "").lower()
        for r in divergence_reports
    ):
        risk_flags.append(RiskFlag.ENUM_VIOLATION)
    if any(
        "required" in getattr(r, "claim_a", "").lower()
        for r in divergence_reports
    ):
        risk_flags.append(RiskFlag.REQUIRED_FIELD_GAP)
    if any(
        "D5_spec_prod" in str(getattr(r, "divergence_class", ""))
        or "drift" in str(getattr(r, "divergence_class", ""))
        for r in divergence_reports
    ):
        risk_flags.append(RiskFlag.SCHEMA_DRIFT)
    if coverage_pct < 60.0:
        risk_flags.append(RiskFlag.LOW_COVERAGE)
    if mutation_score is not None and mutation_score < 0.7:
        risk_flags.append(RiskFlag.VACUOUS_ASSERTIONS)

    # deduplicate
    risk_flags = list(dict.fromkeys(risk_flags))

    # ── actionable findings ───────────────────────────────────────────────
    top_findings = _build_findings(divergence_reports)

    # ── overall grade and verdict ─────────────────────────────────────────
    # Weighted composite score
    dim_scores = [d.score for d in dimensions if d.score >= 0]
    base_score = sum(dim_scores) / len(dim_scores) if dim_scores else 0.5

    penalty = 0.0
    if critical_count:
        penalty += 0.3
    if high_count:
        penalty += 0.15 * min(high_count, 3)
    composite_score = max(0.0, base_score - penalty)

    grade = score_to_grade(composite_score)

    if critical_count == 0 and high_count == 0 and grade in (VerdictGrade.A,):
        overall = OverallVerdict.CERTIFIED
    elif divergence_reports:
        overall = OverallVerdict.DIVERGENT
    elif coverage_pct < 40.0:
        overall = OverallVerdict.SUSPECT
    else:
        overall = OverallVerdict.CERTIFIED if grade == VerdictGrade.A else OverallVerdict.SUSPECT

    # ── confidence ───────────────────────────────────────────────────────
    # More probes + higher coverage + mutation score = more confident
    confidence_factors = [
        min(1.0, coverage_pct / 100.0),
        1.0 if mutation_score is not None else 0.7,
        1.0 if semantic_score is not None else 0.8,
        min(1.0, len(divergence_reports) / 3 * 0.5 + 0.5) if divergence_reports else 0.9,
    ]
    confidence = sum(confidence_factors) / len(confidence_factors)

    return RichVerdict(
        target_url=target_url,
        spec_source=spec_source,
        overall=overall,
        grade=grade,
        confidence=confidence,
        dimensions=dimensions,
        divergence_count=len(divergence_reports),
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        coverage_pct=coverage_pct,
        mutation_score=mutation_score,
        semantic_score=semantic_score,
        captured_fixtures=captured_fixtures,
        risk_flags=risk_flags,
        top_findings=top_findings,
        duration_ms=duration_ms,
        time_to_fix_estimate=_estimate_fix_time(top_findings),
    )


_REMEDIATION_MAP: dict[str, str] = {
    "D1_spec_code": "Add server-side validation matching OpenAPI constraints",
    "D2_code_prod": "Check env configuration and deployment; code vs prod mismatch",
    "D3_ui_spec": "Update client to send data in spec-mandated format",
    "D4_db_code": "Add application-layer validation mirroring DB constraints",
    "D5_spec_prod": "Update spec to reflect current prod, or restore the missing behaviour",
}

_FIX_MINUTES: dict[str, int] = {
    "critical": 120, "high": 60, "medium": 30, "low": 15,
}


def _build_findings(reports: list) -> list[ActionableFinding]:
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_reports = sorted(
        reports,
        key=lambda r: priority_order.get(
            str(getattr(r, "severity", "medium")).lower().split(".")[-1], 3
        ),
    )
    findings: list[ActionableFinding] = []
    for rank, r in enumerate(sorted_reports, 1):
        sev_raw = str(getattr(r, "severity", "medium"))
        sev = sev_raw.split(".")[-1].lower()
        dc = str(getattr(r, "divergence_class", ""))
        dc_key = dc.split(".")[-1] if "." in dc else dc
        ep = str(getattr(r, "endpoint", "unknown"))
        claim_a = str(getattr(r, "claim_a", ""))[:80]
        remediation = _REMEDIATION_MAP.get(dc_key, "Investigate and fix divergence")
        findings.append(
            ActionableFinding(
                rank=rank,
                severity=sev,
                divergence_class=dc_key,
                endpoint=ep,
                summary=f"{dc_key} on {ep}: {claim_a}",
                remediation=remediation,
                estimated_fix_minutes=_FIX_MINUTES.get(sev, 30),
            )
        )
    return findings
