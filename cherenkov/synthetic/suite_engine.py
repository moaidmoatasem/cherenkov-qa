"""cherenkov/synthetic/suite_engine.py — STORM-inspired SuiteEngine orchestrator.

Analogous to STORM's Engine class: coordinates four stages
(context extraction → parallel persona generation → merge → enrich → grade)
and surfaces per-persona timing for observability.

Usage:
    engine = SuiteEngine(spec=spec_dict)
    result = engine.run()
    suite_json = result.suite          # write this to disk
    grade      = result.grade_report   # GradeReport from Phase 14 eval pipeline
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from cherenkov.synthetic.personas import (
    TesterPersona,
    DEFAULT_PERSONAS,
    build_spec_contexts,
    OperationContext,
)
from cherenkov.synthetic.persona_generator import generate_for_persona
from cherenkov.synthetic.merge import merge_suites
from cherenkov.synthetic.enricher import enrich_suite


# ── result dataclasses ─────────────────────────────────────────────────────────

@dataclass
class PersonaRunResult:
    persona_name: str
    op_count: int
    test_count: int
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_name": self.persona_name,
            "op_count": self.op_count,
            "test_count": self.test_count,
            "duration_ms": self.duration_ms,
        }


@dataclass
class SuiteEngineResult:
    suite: dict[str, list[dict[str, Any]]]
    persona_runs: list[PersonaRunResult] = field(default_factory=list)
    total_tests: int = 0
    operations_covered: int = 0
    duration_ms: int = 0
    grade_report: Any = None  # GradeReport | None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "total_tests": self.total_tests,
            "operations_covered": self.operations_covered,
            "duration_ms": self.duration_ms,
            "persona_runs": [r.to_dict() for r in self.persona_runs],
        }
        if self.grade_report is not None:
            d["grade"] = self.grade_report.grade
            d["coverage"] = round(self.grade_report.coverage, 4)
            d["overall_score"] = round(self.grade_report.overall_score, 4)
        return d


# ── engine ─────────────────────────────────────────────────────────────────────

class SuiteEngine:
    """Orchestrates multi-persona test suite generation.

    Args:
        spec:        OpenAPI spec dict.
        personas:    List of TesterPersona to run. Defaults to all five.
        run_grader:  Grade the merged suite via SuiteGrader after generation.
        parallel:    Run personas concurrently (ThreadPoolExecutor). Default True.
        enricher:    Apply assertion enrichment polish pass. Default True.
    """

    def __init__(
        self,
        spec: dict[str, Any],
        personas: list[TesterPersona] | None = None,
        *,
        run_grader: bool = True,
        parallel: bool = True,
        enricher: bool = True,
    ) -> None:
        self.spec = spec
        self.personas = personas if personas is not None else list(DEFAULT_PERSONAS)
        self.run_grader = run_grader
        self.parallel = parallel
        self.enricher = enricher

    def run(self) -> SuiteEngineResult:
        t0 = time.time()

        contexts: dict[str, OperationContext] = build_spec_contexts(self.spec)

        # ── Stage 1: parallel persona generation ──────────────────────────────
        persona_suites: list[dict[str, Any]] = []
        persona_runs: list[PersonaRunResult] = []

        if self.parallel and len(self.personas) > 1:
            futures = {}
            with ThreadPoolExecutor(max_workers=len(self.personas)) as ex:
                for p in self.personas:
                    fut = ex.submit(self._run_one_persona, p, contexts)
                    futures[fut] = p
                for fut in as_completed(futures):
                    suite, run = fut.result()
                    persona_suites.append(suite)
                    persona_runs.append(run)
        else:
            for p in self.personas:
                suite, run = self._run_one_persona(p, contexts)
                persona_suites.append(suite)
                persona_runs.append(run)

        # ── Stage 2: merge ────────────────────────────────────────────────────
        merged = merge_suites(persona_suites)

        # ── Stage 3: enrich ───────────────────────────────────────────────────
        if self.enricher:
            merged = enrich_suite(merged, self.spec)

        # ── Stage 4: grade ────────────────────────────────────────────────────
        grade_report = None
        if self.run_grader:
            from cherenkov.eval.grader import SuiteGrader
            grade_report = SuiteGrader(self.spec).grade(merged)

        total_tests = sum(
            len(v) for v in merged.values() if isinstance(v, list)
        )

        return SuiteEngineResult(
            suite=merged,
            persona_runs=persona_runs,
            total_tests=total_tests,
            operations_covered=len(merged),
            duration_ms=int((time.time() - t0) * 1000),
            grade_report=grade_report,
        )

    def _run_one_persona(
        self,
        persona: TesterPersona,
        contexts: dict[str, OperationContext],
    ) -> tuple[dict[str, Any], PersonaRunResult]:
        t0 = time.time()
        suite = generate_for_persona(persona, contexts, self.spec)
        test_count = sum(len(v) for v in suite.values() if isinstance(v, list))
        return suite, PersonaRunResult(
            persona_name=persona.name,
            op_count=len(suite),
            test_count=test_count,
            duration_ms=int((time.time() - t0) * 1000),
        )
