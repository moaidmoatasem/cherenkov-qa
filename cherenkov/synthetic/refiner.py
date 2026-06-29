"""cherenkov/synthetic/refiner.py — Targeted suite refinement (Phase 16).

Closes the generate → grade → optimize → refine feedback loop.

Analogous to Co-STORM's iterative discourse: the optimizer acts as the
'moderator' that identifies weak areas, and refine() runs a second-pass
generation focused exclusively on those areas, then merges the additions
into the existing suite.

Usage:
    from cherenkov.synthetic.refiner import refine_suite
    result = refine_suite(suite, grade_report, spec, suggestion)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from cherenkov.eval.grader import GradeReport
from cherenkov.synthetic.personas import (
    DEFAULT_PERSONAS,
    HAPPY_PATH,
    SCHEMA_PEDANT,
    ERROR_PATH,
    TesterPersona,
    build_spec_contexts,
)
from cherenkov.synthetic.persona_generator import generate_for_persona
from cherenkov.synthetic.merge import merge_suites


# Thresholds that trigger targeted persona selection
_LOW_DENSITY    = 2.5   # assertions/test below this → add SCHEMA_PEDANT
_LOW_MEANINGFUL = 0.70  # meaningful ratio below this → add SCHEMA_PEDANT
_WEAK_GRADES    = frozenset(("F", "D"))


@dataclass
class RefineResult:
    """Outcome of a refinement pass."""

    original_suite: dict[str, Any]
    refined_suite: dict[str, Any]
    tests_added: int
    ops_targeted: list[str]
    original_grade: str
    duration_ms: int
    new_grade_report: Any = None  # GradeReport | None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tests_added": self.tests_added,
            "ops_targeted": self.ops_targeted,
            "original_grade": self.original_grade,
            "duration_ms": self.duration_ms,
        }
        if self.new_grade_report is not None:
            d["new_grade"] = self.new_grade_report.grade
            d["new_score"] = round(self.new_grade_report.overall_score, 4)
            d["delta_score"] = round(
                self.new_grade_report.overall_score
                - _grade_report_score_for(self.original_grade),
                4,
            )
        return d


def _grade_report_score_for(grade: str) -> float:
    """Approximate score midpoint for a letter grade (used for delta display only)."""
    return {"A": 0.925, "B": 0.775, "C": 0.625, "D": 0.475, "F": 0.20}.get(grade, 0.0)


def _personas_for_op(op_grade: Any, spec_ctx: Any) -> list[TesterPersona]:
    """Choose which personas to run for a single weak operation."""
    personas: list[TesterPersona] = []

    if op_grade.grade in _WEAK_GRADES or op_grade.overall_score < 0.40:
        # Worst operations: full persona sweep
        return list(DEFAULT_PERSONAS)

    if op_grade.assertion_density < _LOW_DENSITY:
        personas.append(SCHEMA_PEDANT)
        personas.append(HAPPY_PATH)

    if op_grade.meaningful_ratio < _LOW_MEANINGFUL:
        if SCHEMA_PEDANT not in personas:
            personas.append(SCHEMA_PEDANT)

    if op_grade.schema_conformance < 1.0:
        if ERROR_PATH not in personas:
            personas.append(ERROR_PATH)

    return personas or [SCHEMA_PEDANT]


def refine_suite(
    suite: dict[str, Any],
    grade_report: GradeReport,
    spec: dict[str, Any],
    *,
    run_grader: bool = True,
) -> RefineResult:
    """Run a targeted second-pass generation on weak operations and merge results.

    Args:
        suite:        Existing test suite (operation_id → list[test]).
        grade_report: GradeReport from a prior `eval grade` run.
        spec:         OpenAPI spec dict.
        run_grader:   Re-grade after refinement to measure improvement.

    Returns:
        RefineResult with the enriched suite and change summary.
    """
    t0 = time.time()

    contexts = build_spec_contexts(spec)

    # Identify operations that need attention
    op_map = {op.operation_id: op for op in grade_report.operations}

    # Also target entirely uncovered operations
    covered_ids = set(op_map)
    uncovered_ids = set(contexts) - covered_ids

    targeted_ops: list[str] = []
    new_persona_suites: list[dict[str, Any]] = []

    # Uncovered ops → run all personas
    if uncovered_ids:
        uncovered_contexts = {k: contexts[k] for k in uncovered_ids if k in contexts}
        if uncovered_contexts:
            targeted_ops.extend(sorted(uncovered_contexts))
            for persona in DEFAULT_PERSONAS:
                partial = generate_for_persona(persona, uncovered_contexts, spec)
                if partial:
                    new_persona_suites.append(partial)

    # Covered but weak ops
    for op_id, op_grade in op_map.items():
        needs_work = (
            op_grade.grade in _WEAK_GRADES
            or op_grade.assertion_density < _LOW_DENSITY
            or op_grade.meaningful_ratio < _LOW_MEANINGFUL
            or op_grade.schema_conformance < 1.0
        )
        if not needs_work:
            continue

        ctx = contexts.get(op_id)
        if ctx is None:
            continue

        targeted_ops.append(op_id)
        personas = _personas_for_op(op_grade, ctx)
        single_ctx = {op_id: ctx}
        for persona in personas:
            partial = generate_for_persona(persona, single_ctx, spec)
            if partial:
                # Suffix test names to avoid collision with existing tests
                for tests in partial.values():
                    for test in tests:
                        test["name"] = test["name"] + "_r2"
                new_persona_suites.append(partial)

    # Merge new tests into existing suite
    before_counts = {k: len(v) for k, v in suite.items() if isinstance(v, list)}
    merged = merge_suites([suite, *new_persona_suites])
    after_counts = {k: len(v) for k, v in merged.items() if isinstance(v, list)}

    tests_added = sum(
        after_counts.get(k, 0) - before_counts.get(k, 0)
        for k in after_counts
    )

    # Re-grade
    new_grade_report = None
    if run_grader:
        from cherenkov.eval.grader import SuiteGrader
        new_grade_report = SuiteGrader(spec).grade(merged)

    return RefineResult(
        original_suite=suite,
        refined_suite=merged,
        tests_added=tests_added,
        ops_targeted=list(dict.fromkeys(targeted_ops)),  # deduplicate, preserve order
        original_grade=grade_report.grade,
        duration_ms=int((time.time() - t0) * 1000),
        new_grade_report=new_grade_report,
    )
