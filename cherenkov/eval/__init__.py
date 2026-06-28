"""cherenkov/eval — Phase 14: Test Suite Evaluation Pipeline.

Inspired by google/agents-cli's generate → grade → compare → optimize lifecycle.

Four stages:
  runner   — execute suite against a live API, emit JSONL traces
  grader   — static quality analysis (assertion density, schema conformance, coverage)
  compare  — diff two grade results (before/after spec change)
  optimizer — suggest generation profile improvements from grade data
"""

from cherenkov.eval.grader import SuiteGrader, GradeReport, OperationGrade
from cherenkov.eval.runner import EvalRunner, TestResult, RunTrace
from cherenkov.eval.compare import compare_grades, CompareReport
from cherenkov.eval.optimizer import optimize_profile, OptimizeSuggestion

__all__ = [
    "SuiteGrader",
    "GradeReport",
    "OperationGrade",
    "EvalRunner",
    "TestResult",
    "RunTrace",
    "compare_grades",
    "CompareReport",
    "optimize_profile",
    "OptimizeSuggestion",
]
