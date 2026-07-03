"""cherenkov/eval/compare.py — Diff two GradeReports (before/after).

Produces a CompareReport that highlights regressions and improvements per
operation, plus overall delta metrics. Inspired by agents-cli eval compare.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cherenkov.eval.grader import GradeReport, OperationGrade


_GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}


@dataclass
class OperationDelta:
    operation_id: str
    before_grade: str
    after_grade: str
    before_score: float
    after_score: float
    delta_score: float
    direction: str  # "improved" | "regressed" | "unchanged" | "added" | "removed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "before_grade": self.before_grade,
            "after_grade": self.after_grade,
            "before_score": round(self.before_score, 3),
            "after_score": round(self.after_score, 3),
            "delta_score": round(self.delta_score, 3),
            "direction": self.direction,
        }


@dataclass
class CompareReport:
    before_grade: str
    after_grade: str
    delta_score: float
    delta_coverage: float
    delta_assertion_density: float
    delta_meaningful_ratio: float
    improved: list[OperationDelta] = field(default_factory=list)
    regressed: list[OperationDelta] = field(default_factory=list)
    added: list[OperationDelta] = field(default_factory=list)
    removed: list[OperationDelta] = field(default_factory=list)
    unchanged: list[OperationDelta] = field(default_factory=list)

    @property
    def has_regressions(self) -> bool:
        return bool(self.regressed)

    def summary(self) -> str:
        lines = [
            f"overall: {self.before_grade} → {self.after_grade}  "
            f"(Δscore={self.delta_score:+.3f})",
            f"coverage Δ={self.delta_coverage:+.3f}  "
            f"density Δ={self.delta_assertion_density:+.2f}  "
            f"meaningful Δ={self.delta_meaningful_ratio:+.3f}",
        ]
        if self.improved:
            lines.append(f"improved : {len(self.improved)} operation(s)")
        if self.regressed:
            lines.append(f"regressed: {len(self.regressed)} operation(s) ⚠")
        if self.added:
            lines.append(f"added    : {len(self.added)} new operation(s)")
        if self.removed:
            lines.append(f"removed  : {len(self.removed)} operation(s)")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_grade": self.before_grade,
            "after_grade": self.after_grade,
            "delta_score": round(self.delta_score, 4),
            "delta_coverage": round(self.delta_coverage, 4),
            "delta_assertion_density": round(self.delta_assertion_density, 3),
            "delta_meaningful_ratio": round(self.delta_meaningful_ratio, 3),
            "has_regressions": self.has_regressions,
            "improved": [d.to_dict() for d in self.improved],
            "regressed": [d.to_dict() for d in self.regressed],
            "added": [d.to_dict() for d in self.added],
            "removed": [d.to_dict() for d in self.removed],
            "unchanged": [d.to_dict() for d in self.unchanged],
        }


def compare_grades(before: GradeReport, after: GradeReport) -> CompareReport:
    """Diff two GradeReports, highlighting regressions and improvements."""
    before_map = {op.operation_id: op for op in before.operations}
    after_map  = {op.operation_id: op for op in after.operations}

    all_ids = set(before_map) | set(after_map)
    improved, regressed, added, removed, unchanged = [], [], [], [], []

    for op_id in sorted(all_ids):
        b = before_map.get(op_id)
        a = after_map.get(op_id)

        if b is None and a is not None:
            added.append(OperationDelta(
                operation_id=op_id,
                before_grade="-", after_grade=a.grade,
                before_score=0.0, after_score=a.overall_score,
                delta_score=a.overall_score,
                direction="added",
            ))
        elif b is not None and a is None:
            removed.append(OperationDelta(
                operation_id=op_id,
                before_grade=b.grade, after_grade="-",
                before_score=b.overall_score, after_score=0.0,
                delta_score=-b.overall_score,
                direction="removed",
            ))
        else:
            if b is None or a is None:
                raise ValueError("Cannot compare: both before and after scores must be present")
            delta = a.overall_score - b.overall_score
            before_rank = _GRADE_ORDER.get(b.grade, 0)
            after_rank  = _GRADE_ORDER.get(a.grade, 0)
            if after_rank > before_rank:
                direction = "improved"
            elif after_rank < before_rank:
                direction = "regressed"
            else:
                direction = "unchanged"

            od = OperationDelta(
                operation_id=op_id,
                before_grade=b.grade, after_grade=a.grade,
                before_score=b.overall_score, after_score=a.overall_score,
                delta_score=delta,
                direction=direction,
            )
            if direction == "improved":
                improved.append(od)
            elif direction == "regressed":
                regressed.append(od)
            else:
                unchanged.append(od)

    return CompareReport(
        before_grade=before.grade,
        after_grade=after.grade,
        delta_score=after.overall_score - before.overall_score,
        delta_coverage=after.coverage - before.coverage,
        delta_assertion_density=after.overall_assertion_density - before.overall_assertion_density,
        delta_meaningful_ratio=after.overall_meaningful_ratio - before.overall_meaningful_ratio,
        improved=improved,
        regressed=regressed,
        added=added,
        removed=removed,
        unchanged=unchanged,
    )
