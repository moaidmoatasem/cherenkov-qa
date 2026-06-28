"""tests/unit/test_eval_pipeline.py — Phase 14 eval pipeline gate tests.

Covers: grader, runner (dry-run), compare, optimizer.
No live API or LLM calls.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cherenkov.eval.grader import SuiteGrader, GradeReport
from cherenkov.eval.runner import EvalRunner, RunTrace
from cherenkov.eval.compare import compare_grades
from cherenkov.eval.optimizer import optimize_profile


# ── fixtures ───────────────────────────────────────────────────────────────────

_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "1.0"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "responses": {"200": {"description": "ok"}},
            },
            "post": {
                "operationId": "createPet",
                "responses": {"201": {"description": "created"}},
            },
        },
        "/pets/{id}": {
            "get": {
                "operationId": "getPet",
                "responses": {"200": {"description": "ok"}},
            },
        },
    },
}

_GOOD_SUITE: dict = {
    "listPets": [
        {
            "name": "list_pets_smoke",
            "request": {"method": "GET", "path": "/pets"},
            "assertions": [
                {"type": "status", "expected": [200]},
                {"type": "header", "name": "Content-Type", "contains": "json"},
            ],
        }
    ],
    "createPet": [
        {
            "name": "create_pet_smoke",
            "request": {"method": "POST", "path": "/pets", "body": {"name": "Fido"}},
            "assertions": [
                {"type": "status", "expected": [201]},
                {"type": "json_key", "field": "id", "exists": True},
            ],
        }
    ],
    "getPet": [
        {
            "name": "get_pet_smoke",
            "request": {"method": "GET", "path": "/pets/{id}", "path_params": {"id": "1"}},
            "assertions": [
                {"type": "status", "expected": [200]},
            ],
        }
    ],
}

_THIN_SUITE: dict = {
    "listPets": [
        {
            "name": "list_pets_thin",
            "request": {"method": "GET", "path": "/pets"},
            "assertions": [
                {"type": "status", "expected": [200]},
            ],
        }
    ],
    # createPet and getPet not covered
}

_VACUOUS_SUITE: dict = {
    "listPets": [
        {
            "name": "vacuous_test",
            "request": {"method": "GET", "path": "/pets"},
            "assertions": [
                {},  # empty — banned
                {"type": "status", "expected": []},  # no expected codes — banned
            ],
        }
    ],
}


# ── grader tests ───────────────────────────────────────────────────────────────

def test_grader_full_coverage_good_suite():
    report = SuiteGrader(_SPEC).grade(_GOOD_SUITE)
    assert report.spec_op_count == 3
    assert report.suite_op_count == 3
    assert report.coverage == 1.0
    assert report.grade in ("A", "B")
    assert len(report.operations) == 3


def test_grader_partial_coverage_thin_suite():
    report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    assert report.suite_op_count == 1
    assert report.coverage < 1.0
    assert report.grade in ("C", "D", "F")


def test_grader_vacuous_assertions_lower_score():
    good = SuiteGrader(_SPEC).grade(_GOOD_SUITE)
    vacuous = SuiteGrader(_SPEC).grade(_VACUOUS_SUITE)
    assert vacuous.overall_meaningful_ratio < good.overall_meaningful_ratio


def test_grader_unknown_op_penalizes_schema_conformance():
    suite_with_unknown = {
        "unknownOp": [
            {
                "name": "unknown_test",
                "request": {"method": "GET", "path": "/unknown"},
                "assertions": [{"type": "status", "expected": [200]}],
            }
        ]
    }
    report = SuiteGrader(_SPEC).grade(suite_with_unknown)
    unknown_op = next(o for o in report.operations if o.operation_id == "unknownOp")
    assert unknown_op.schema_conformance == 0.0


def test_grader_report_roundtrip():
    report = SuiteGrader(_SPEC).grade(_GOOD_SUITE)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    try:
        report.save(path)
        loaded = GradeReport.load(path)
        assert loaded.grade == report.grade
        assert loaded.coverage == report.coverage
        assert len(loaded.operations) == len(report.operations)
    finally:
        path.unlink(missing_ok=True)


# ── runner tests ───────────────────────────────────────────────────────────────

def test_runner_dry_run_records_all_tests():
    runner = EvalRunner(target_url=None)
    trace = runner.run(_GOOD_SUITE)
    assert trace.total == 3
    assert trace.passed == 3  # dry-run always passes
    assert all(r.response_status is None for r in trace.results)


def test_runner_trace_jsonl_roundtrip():
    runner = EvalRunner(target_url=None)
    trace = runner.run(_GOOD_SUITE)
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = Path(f.name)
    try:
        trace.to_jsonl(path)
        loaded = RunTrace.from_jsonl(path)
        assert loaded.total == trace.total
        assert loaded.passed == trace.passed
    finally:
        path.unlink(missing_ok=True)


def test_runner_skips_meta_keys():
    suite_with_meta = {**_GOOD_SUITE, "_generation_profile": "default"}
    runner = EvalRunner(target_url=None)
    trace = runner.run(suite_with_meta)
    assert trace.total == 3  # _generation_profile not counted


# ── compare tests ──────────────────────────────────────────────────────────────

def test_compare_detects_improvement():
    thin_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    good_report  = SuiteGrader(_SPEC).grade(_GOOD_SUITE)
    cmp = compare_grades(thin_report, good_report)

    assert cmp.delta_coverage > 0
    assert cmp.delta_score > 0
    assert not cmp.has_regressions


def test_compare_detects_regression():
    good_report = SuiteGrader(_SPEC).grade(_GOOD_SUITE)
    thin_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    cmp = compare_grades(good_report, thin_report)

    assert cmp.delta_coverage < 0
    assert cmp.has_regressions or cmp.removed


def test_compare_added_operations():
    thin_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    good_report  = SuiteGrader(_SPEC).grade(_GOOD_SUITE)
    cmp = compare_grades(thin_report, good_report)

    added_ids = {d.operation_id for d in cmp.added}
    assert "createPet" in added_ids or "getPet" in added_ids


def test_compare_same_suite_no_delta():
    report = SuiteGrader(_SPEC).grade(_GOOD_SUITE)
    cmp = compare_grades(report, report)
    assert cmp.delta_score == 0.0
    assert not cmp.has_regressions
    assert not cmp.improved


# ── optimizer tests ────────────────────────────────────────────────────────────

def test_optimizer_suggests_coverage_fix_for_thin_suite():
    report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    suggestion = optimize_profile(report)
    assert any("coverage" in s.lower() or "untested" in s.lower() for s in suggestion.suggestions)
    assert "target_coverage" in suggestion.suggested_profile


def test_optimizer_suggests_density_increase():
    report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    suggestion = optimize_profile(report)
    density_suggestions = [s for s in suggestion.suggestions if "density" in s.lower() or "assertion" in s.lower()]
    assert len(density_suggestions) >= 1


def test_optimizer_identifies_weakest_operations():
    report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    suggestion = optimize_profile(report)
    # Uncovered ops should be among the weakest
    assert len(suggestion.weakest_operations) >= 1


def test_optimizer_healthy_suite_gives_positive_message():
    # Build a very good suite (high density, full coverage)
    dense_suite = {
        op_id: [
            {
                "name": f"test_{op_id}_{i}",
                "request": {"method": "GET", "path": "/pets"},
                "assertions": [
                    {"type": "status", "expected": [200]},
                    {"type": "json_key", "field": "id", "exists": True},
                    {"type": "json_key", "field": "name", "exists": True},
                    {"type": "header", "name": "Content-Type", "contains": "json"},
                    {"type": "status", "expected": [200]},
                ],
            }
            for i in range(2)
        ]
        for op_id in ["listPets", "createPet", "getPet"]
    }
    report = SuiteGrader(_SPEC).grade(dense_suite)
    suggestion = optimize_profile(report)
    # Should not flag coverage or density as major problems
    assert suggestion.current_grade in ("A", "B", "C")
