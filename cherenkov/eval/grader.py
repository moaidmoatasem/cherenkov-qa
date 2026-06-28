"""cherenkov/eval/grader.py — Static quality grader for test suites.

Scores a suite manifest against the OpenAPI spec using four metrics:
  - assertion_density    : assertions per test (raw count, not normalized)
  - schema_conformance   : fraction of assertions targeting spec-valid operations
  - meaningful_ratio     : fraction of assertions passing the banned-pattern check
  - coverage             : fraction of spec operations with at least one test

Grades A–F mirror school grading: makes results immediately human-readable.

No live API required — all analysis is against the suite JSON + spec.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_GRADE_THRESHOLDS = [
    (0.90, "A"),
    (0.75, "B"),
    (0.60, "C"),
    (0.45, "D"),
    (0.00, "F"),
]


def _letter_grade(score: float) -> str:
    for threshold, letter in _GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "F"


def _extract_spec_op_ids(spec: dict[str, Any]) -> frozenset[str]:
    ops: set[str] = set()
    _http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _http_methods or not isinstance(operation, dict):
                continue
            op_id = operation.get("operationId", f"{method.upper()}:{path}")
            ops.add(op_id)
    return frozenset(ops)


def _is_meaningful_assertion(assertion: dict[str, Any]) -> bool:
    """Re-use the same banned-pattern check from cherenkov.drift.checker."""
    from cherenkov.drift.checker import is_meaningful_assertion
    ok, _ = is_meaningful_assertion(assertion)
    return ok


@dataclass
class OperationGrade:
    operation_id: str
    test_count: int
    assertion_density: float        # assertions / test
    schema_conformance: float       # op exists in spec → 1.0, else 0.0
    meaningful_ratio: float         # fraction of meaningful assertions
    overall_score: float
    grade: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "test_count": self.test_count,
            "assertion_density": round(self.assertion_density, 3),
            "schema_conformance": round(self.schema_conformance, 3),
            "meaningful_ratio": round(self.meaningful_ratio, 3),
            "overall_score": round(self.overall_score, 3),
            "grade": self.grade,
        }


@dataclass
class GradeReport:
    spec_op_count: int
    suite_op_count: int
    coverage: float                 # suite_ops_in_spec / spec_ops
    overall_assertion_density: float
    overall_meaningful_ratio: float
    overall_score: float
    grade: str
    operations: list[OperationGrade] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_op_count": self.spec_op_count,
            "suite_op_count": self.suite_op_count,
            "coverage": round(self.coverage, 4),
            "overall_assertion_density": round(self.overall_assertion_density, 3),
            "overall_meaningful_ratio": round(self.overall_meaningful_ratio, 3),
            "overall_score": round(self.overall_score, 4),
            "grade": self.grade,
            "created_at": self.created_at,
            "operations": [op.to_dict() for op in self.operations],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "GradeReport":
        data = json.loads(path.read_text())
        ops = [
            OperationGrade(
                operation_id=o["operation_id"],
                test_count=o["test_count"],
                assertion_density=o["assertion_density"],
                schema_conformance=o["schema_conformance"],
                meaningful_ratio=o["meaningful_ratio"],
                overall_score=o["overall_score"],
                grade=o["grade"],
            )
            for o in data.get("operations", [])
        ]
        return cls(
            spec_op_count=data["spec_op_count"],
            suite_op_count=data["suite_op_count"],
            coverage=data["coverage"],
            overall_assertion_density=data["overall_assertion_density"],
            overall_meaningful_ratio=data["overall_meaningful_ratio"],
            overall_score=data["overall_score"],
            grade=data["grade"],
            created_at=data.get("created_at", ""),
            operations=ops,
        )


class SuiteGrader:
    """Score a suite manifest against a parsed OpenAPI spec.

    Usage:
        grader = SuiteGrader(spec)
        report = grader.grade(suite)
    """

    # Weight distribution for per-operation score
    _W_DENSITY      = 0.30  # assertion density (normalized)
    _W_CONFORMANCE  = 0.40  # schema conformance
    _W_MEANINGFUL   = 0.30  # meaningful assertion ratio

    # Density normalization cap (5 assertions/test → 1.0)
    _DENSITY_CAP = 5.0

    def __init__(self, spec: dict[str, Any]) -> None:
        self._spec = spec
        self._spec_op_ids = _extract_spec_op_ids(spec)

    def grade(self, suite: dict[str, Any]) -> GradeReport:
        from datetime import datetime, timezone

        suite_ops = {k: v for k, v in suite.items() if not k.startswith("_")}
        op_grades: list[OperationGrade] = []

        total_assertions = 0
        total_meaningful = 0
        total_tests = 0

        for op_id, tests in suite_ops.items():
            if not isinstance(tests, list):
                continue

            schema_conformance = 1.0 if op_id in self._spec_op_ids else 0.0
            assertion_count = 0
            meaningful_count = 0
            test_count = len(tests)
            total_tests += test_count

            for test in tests:
                if not isinstance(test, dict):
                    continue
                for assertion in test.get("assertions", []):
                    if not isinstance(assertion, dict):
                        continue
                    assertion_count += 1
                    if _is_meaningful_assertion(assertion):
                        meaningful_count += 1

            total_assertions += assertion_count
            total_meaningful += meaningful_count

            raw_density = assertion_count / test_count if test_count else 0.0
            norm_density = min(raw_density / self._DENSITY_CAP, 1.0)
            meaningful_ratio = meaningful_count / assertion_count if assertion_count else 0.0

            score = (
                self._W_DENSITY     * norm_density
                + self._W_CONFORMANCE * schema_conformance
                + self._W_MEANINGFUL  * meaningful_ratio
            )

            op_grades.append(OperationGrade(
                operation_id=op_id,
                test_count=test_count,
                assertion_density=raw_density,
                schema_conformance=schema_conformance,
                meaningful_ratio=meaningful_ratio,
                overall_score=score,
                grade=_letter_grade(score),
            ))

        # Overall metrics
        spec_count = len(self._spec_op_ids)
        suite_count = len(suite_ops)
        covered_count = sum(1 for op_id in suite_ops if op_id in self._spec_op_ids)
        coverage = covered_count / spec_count if spec_count else 1.0

        overall_density = total_assertions / total_tests if total_tests else 0.0
        overall_meaningful = total_meaningful / total_assertions if total_assertions else 0.0

        # Overall score blends coverage with per-test quality
        norm_overall_density = min(overall_density / self._DENSITY_CAP, 1.0)
        overall_score = (
            0.40 * coverage
            + 0.30 * norm_overall_density
            + 0.30 * overall_meaningful
        )

        return GradeReport(
            spec_op_count=spec_count,
            suite_op_count=suite_count,
            coverage=coverage,
            overall_assertion_density=overall_density,
            overall_meaningful_ratio=overall_meaningful,
            overall_score=overall_score,
            grade=_letter_grade(overall_score),
            operations=sorted(op_grades, key=lambda g: g.overall_score),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
