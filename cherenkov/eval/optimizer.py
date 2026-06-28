"""cherenkov/eval/optimizer.py — Suggest generation profile improvements.

Analyzes a GradeReport and produces actionable OptimizeSuggestions.
Inspired by agents-cli eval optimize — auto-tune without requiring LLM calls.

The suggested_profile is a dict that can be passed to the synthetic generator
as overrides (e.g. target_assertion_count, require_schema_assertions, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cherenkov.eval.grader import GradeReport


# Thresholds that trigger a suggestion
_TARGET_DENSITY    = 3.0   # assertions per test
_TARGET_COVERAGE   = 0.90  # fraction of spec ops tested
_TARGET_MEANINGFUL = 0.80  # fraction of assertions that are meaningful
_TARGET_SCORE      = 0.75  # overall score for overall health suggestion


@dataclass
class OptimizeSuggestion:
    """Actionable improvement suggestion derived from a GradeReport."""

    current_grade: str
    suggestions: list[str] = field(default_factory=list)
    weakest_operations: list[str] = field(default_factory=list)
    suggested_profile: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_grade": self.current_grade,
            "suggestions": self.suggestions,
            "weakest_operations": self.weakest_operations,
            "suggested_profile": self.suggested_profile,
        }

    def summary(self) -> str:
        lines = [f"Current grade: {self.current_grade}"]
        if self.suggestions:
            lines.append("\nSuggestions:")
            for s in self.suggestions:
                lines.append(f"  • {s}")
        if self.weakest_operations:
            lines.append(f"\nWeakest operations (address first):")
            for op in self.weakest_operations:
                lines.append(f"  • {op}")
        return "\n".join(lines)


def optimize_profile(report: GradeReport) -> OptimizeSuggestion:
    """Derive improvement suggestions from a GradeReport.

    Returns an OptimizeSuggestion with human-readable text and a
    suggested_profile dict for the synthetic generator.
    """
    suggestions: list[str] = []
    profile: dict[str, Any] = {}

    # Coverage gap
    if report.coverage < _TARGET_COVERAGE:
        missing = report.spec_op_count - report.suite_op_count
        suggestions.append(
            f"Coverage is {report.coverage:.0%} ({missing} spec operation(s) untested). "
            f"Run `cherenkov drift reconcile --level L2` to generate skeletons for missing ops."
        )
        profile["target_coverage"] = _TARGET_COVERAGE

    # Low assertion density
    if report.overall_assertion_density < _TARGET_DENSITY:
        suggestions.append(
            f"Assertion density is {report.overall_assertion_density:.1f}/test "
            f"(target: {_TARGET_DENSITY:.0f}). "
            f"Increase assertions per test to improve mutation-kill rate."
        )
        profile["target_assertion_count"] = int(_TARGET_DENSITY)

    # Low meaningful ratio
    if report.overall_meaningful_ratio < _TARGET_MEANINGFUL:
        vacuous_pct = (1 - report.overall_meaningful_ratio) * 100
        suggestions.append(
            f"{vacuous_pct:.0f}% of assertions are vacuous (tautological or empty). "
            f"Add schema-aware assertions that check specific response fields and types."
        )
        profile["require_schema_assertions"] = True

    # Schema-aware assertion hint
    if report.overall_meaningful_ratio >= _TARGET_MEANINGFUL and report.overall_assertion_density < _TARGET_DENSITY:
        suggestions.append(
            "Assertions are meaningful — increase count by adding field-level and "
            "header assertions (Content-Type, pagination fields, required properties)."
        )
        profile["assertion_types"] = ["status", "json_key", "header"]

    # Overall health
    if report.overall_score >= _TARGET_SCORE and not suggestions:
        suggestions.append(
            f"Suite quality is good (grade {report.current_grade if hasattr(report, 'current_grade') else report.grade}). "
            f"Focus on edge-case coverage: error paths (4xx), boundary values, and auth flows."
        )
        profile["include_error_cases"] = True

    if not suggestions:
        suggestions.append("No significant improvements identified — suite is healthy.")

    # Weakest operations (bottom 20% by score, or grade F/D)
    weak_ops = [
        op.operation_id
        for op in report.operations
        if op.grade in ("F", "D") or op.overall_score < 0.40
    ]
    if not weak_ops and report.operations:
        # Bottom 2 if nothing below threshold
        sorted_ops = sorted(report.operations, key=lambda o: o.overall_score)
        weak_ops = [o.operation_id for o in sorted_ops[:2]]

    return OptimizeSuggestion(
        current_grade=report.grade,
        suggestions=suggestions,
        weakest_operations=weak_ops,
        suggested_profile=profile,
    )
