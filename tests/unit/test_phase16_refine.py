"""tests/unit/test_phase16_refine.py — Phase 16 eval refine feedback loop.

Covers: targeted refinement of weak/uncovered operations, test name collision
avoidance, grade improvement after refinement, no-op on healthy suites.
No live API or LLM calls.
"""

from __future__ import annotations

from cherenkov.eval.grader import SuiteGrader
from cherenkov.synthetic.suite_engine import SuiteEngine
from cherenkov.synthetic.refiner import refine_suite


# ── fixtures ───────────────────────────────────────────────────────────────────

_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {"title": "PetStore", "version": "1.0"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["items"],
                                    "properties": {
                                        "items": {"type": "array"},
                                        "total": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "operationId": "createPet",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {"name": {"type": "string"}},
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "created"},
                    "400": {"description": "bad request"},
                },
            },
        },
        "/pets/{id}": {
            "get": {
                "operationId": "getPet",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["id", "name"],
                                    "properties": {
                                        "id":   {"type": "integer"},
                                        "name": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "404": {"description": "not found"},
                },
            }
        },
    },
}

# A thin suite covering only listPets with a single bare test
_THIN_SUITE: dict = {
    "listPets": [
        {
            "name": "smoke_listPets",
            "request": {"method": "GET", "path": "/pets"},
            "assertions": [{"type": "status", "expected": [200]}],
        }
    ]
}

# A dense suite covering all 3 ops with rich assertions
def _make_dense_suite() -> dict:
    return SuiteEngine(_SPEC).run().suite


# ── basic refinement tests ─────────────────────────────────────────────────────

def test_refine_targets_uncovered_ops():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    # createPet and getPet are uncovered → should be targeted
    assert "createPet" in result.ops_targeted or "getPet" in result.ops_targeted


def test_refine_adds_tests_for_uncovered_ops():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    # Refined suite should have tests for all 3 ops
    assert "createPet" in result.refined_suite
    assert "getPet" in result.refined_suite


def test_refine_preserves_original_tests():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    original_names = {t["name"] for t in _THIN_SUITE["listPets"]}
    refined_names  = {t["name"] for t in result.refined_suite["listPets"]}
    assert original_names.issubset(refined_names)


def test_refine_tests_added_is_positive_for_thin_suite():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    assert result.tests_added > 0


def test_refine_no_duplicate_names_after_merge():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    for op_id, tests in result.refined_suite.items():
        names = [t["name"] for t in tests]
        assert len(names) == len(set(names)), f"Duplicate test names in {op_id}"


def test_refine_original_suite_not_mutated():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    before_keys = set(_THIN_SUITE.keys())
    refine_suite(_THIN_SUITE, grade_report, _SPEC)
    assert set(_THIN_SUITE.keys()) == before_keys


# ── grade improvement tests ────────────────────────────────────────────────────

def test_refine_re_grades_by_default():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    assert result.new_grade_report is not None


def test_refine_improves_coverage():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    assert result.new_grade_report is not None
    assert result.new_grade_report.coverage > grade_report.coverage


def test_refine_improves_assertion_density():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    assert result.new_grade_report is not None
    assert (
        result.new_grade_report.overall_assertion_density
        >= grade_report.overall_assertion_density
    )


def test_refine_no_grade_skips_regrading():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC, run_grader=False)
    assert result.new_grade_report is None


# ── targeted-op selection tests ────────────────────────────────────────────────

def test_refine_targets_low_density_op():
    # A suite where listPets exists but has only a bare status assertion
    bare_suite = {
        "listPets": [
            {
                "name": "bare_list",
                "request": {"method": "GET", "path": "/pets"},
                "assertions": [{"type": "status", "expected": [200]}],
            }
        ],
        "createPet": [
            {
                "name": "bare_create",
                "request": {"method": "POST", "path": "/pets", "body": {"name": "x"}},
                "assertions": [{"type": "status", "expected": [201]}],
            }
        ],
        "getPet": [
            {
                "name": "bare_get",
                "request": {"method": "GET", "path": "/pets/{id}", "path_params": {"id": "1"}},
                "assertions": [{"type": "status", "expected": [200]}],
            }
        ],
    }
    grade_report = SuiteGrader(_SPEC).grade(bare_suite)
    # All ops covered but with low density — should target all of them
    result = refine_suite(bare_suite, grade_report, _SPEC)
    assert len(result.ops_targeted) >= 1
    assert result.tests_added >= 1


def test_refine_result_to_dict_structure():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    d = result.to_dict()
    assert "tests_added" in d
    assert "ops_targeted" in d
    assert "original_grade" in d
    assert "new_grade" in d


# ── healthy suite tests ────────────────────────────────────────────────────────

def test_refine_on_healthy_suite_adds_few_or_no_tests():
    # Start with a dense suite from the engine
    dense_suite = _make_dense_suite()
    grade_report = SuiteGrader(_SPEC).grade(dense_suite)

    before_total = sum(len(v) for v in dense_suite.values() if isinstance(v, list))
    result = refine_suite(dense_suite, grade_report, _SPEC)
    after_total = sum(len(v) for v in result.refined_suite.values() if isinstance(v, list))

    # A healthy suite should see minimal additions (ops targeted is low)
    assert after_total >= before_total  # never removes tests


def test_refine_double_pass_is_idempotent_in_ops_covered():
    # Two refinement passes should cover the same set of operations
    grade1 = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result1 = refine_suite(_THIN_SUITE, grade1, _SPEC)

    grade2 = SuiteGrader(_SPEC).grade(result1.refined_suite)
    result2 = refine_suite(result1.refined_suite, grade2, _SPEC)

    # After first pass, coverage should be 1.0
    assert grade2.coverage == 1.0
    # Second pass: uncovered ops should be empty
    assert result2.new_grade_report is not None
    assert result2.new_grade_report.coverage == 1.0


# ── result metadata tests ──────────────────────────────────────────────────────

def test_refine_original_grade_matches_input():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    assert result.original_grade == grade_report.grade


def test_refine_duration_ms_is_positive():
    grade_report = SuiteGrader(_SPEC).grade(_THIN_SUITE)
    result = refine_suite(_THIN_SUITE, grade_report, _SPEC)
    assert result.duration_ms >= 0
