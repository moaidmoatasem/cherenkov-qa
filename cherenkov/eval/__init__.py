"""cherenkov/eval — Phase 14: Test Suite Evaluation Pipeline.

Inspired by google/agents-cli's generate → grade → compare → optimize lifecycle.

Four stages:
  runner   — execute suite against a live API, emit JSONL traces
  grader   — static quality analysis (assertion density, schema conformance, coverage)
  compare  — diff two grade results (before/after spec change)
  optimizer — suggest generation profile improvements from grade data
"""

from cherenkov.eval.compare import CompareReport, compare_grades
from cherenkov.eval.grader import GradeReport, OperationGrade, SuiteGrader
from cherenkov.eval.optimizer import OptimizeSuggestion, optimize_profile
from cherenkov.eval.runner import EvalRunner, RunTrace, TestResult

__all__ = [
    "CompareReport",
    "EvalRunner",
    "GradeReport",
    "OperationGrade",
    "OptimizeSuggestion",
    "RunTrace",
    "SuiteGrader",
    "TestResult",
    "compare_grades",
    "optimize_profile",
]
