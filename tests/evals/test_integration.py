from __future__ import annotations


from cherenkov.evals.core import (
    EvalMetric,
    EvalReport,
    EvalResult,
    EvalSample,
    EvalScore,
    EvalStatus,
)
from cherenkov.evals.runner import build_samples_from_pipeline, print_report
from cherenkov.evals.judge import judge_sample

# ── Fixtures ──────────────────────────────────────────────────────────────────


class FakeScenario:
    def __init__(
        self, mutation_id: str, endpoint: str, method: str, expected_status: int
    ):
        self.mutation_id = mutation_id
        self.endpoint = endpoint
        self.method = method
        self.expected_status = expected_status


class FakeGenOutput:
    def __init__(self, test_code: str):
        self.test_code = test_code


SPEC_SUMMARIES = {
    "POST /api/users": "Creates a user, returns 201 with id, name, email",
    "GET /api/users": "Lists users, returns 200 with array of user objects",
}

SCENARIOS = [
    FakeScenario("create_user_happy", "/api/users", "POST", 201),
    FakeScenario("list_users", "/api/users", "GET", 200),
]

GEN_OUTPUTS = {
    "create_user_happy": FakeGenOutput(
        'test("creates user", async () => {\n  const res = await api.post("/api/users", {name: "Alice"});\n  expect(res.status).toBe(201);\n  expect(res.body).toHaveProperty("id");\n});'
    ),
    "list_users": FakeGenOutput(
        'test("lists users", async () => {\n  const res = await api.get("/api/users");\n  expect(res.status).toBe(200);\n  expect(Array.isArray(res.body)).toBe(true);\n});'
    ),
}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_build_samples():
    samples = build_samples_from_pipeline(SCENARIOS, GEN_OUTPUTS, SPEC_SUMMARIES)
    assert len(samples) == 2
    assert samples[0].scenario_id == "create_user_happy"
    assert samples[0].method == "POST"
    assert samples[0].expected_status == 201
    assert "Alice" in samples[0].test_code
    assert samples[1].scenario_id == "list_users"
    assert samples[1].method == "GET"
    assert samples[1].expected_status == 200


def test_build_samples_missing_scenario():
    samples = build_samples_from_pipeline(
        [FakeScenario("orphan", "/x", "GET", 200)], {}, SPEC_SUMMARIES
    )
    assert samples == []


def test_build_samples_missing_code():
    class EmptyGenOutput:
        test_code = ""

    samples = build_samples_from_pipeline(
        [FakeScenario("empty", "/x", "GET", 200)],
        {"empty": EmptyGenOutput()},
        SPEC_SUMMARIES,
    )
    assert samples == []


def test_print_report(capsys):
    sample = EvalSample(
        scenario_id="t1",
        endpoint="/x",
        method="GET",
        expected_status=200,
        test_code="",
        spec_summary="",
    )
    scores = [
        EvalScore(
            metric=EvalMetric.FAITHFULNESS,
            score=0.95,
            status=EvalStatus.PASS,
            detail="correct status",
        ),
        EvalScore(
            metric=EvalMetric.HALLUCINATION,
            score=0.8,
            status=EvalStatus.PASS,
            detail="no hallucination",
        ),
    ]
    result = EvalResult(sample=sample, scores=scores, duration_ms=50)
    report = EvalReport(
        results=[result], model="test-model", eval_timestamp="2026-01-01T00:00:00"
    )
    print_report(report)
    captured = capsys.readouterr()
    assert "CHERENKOV EVAL REPORT" in captured.out
    assert "100.0%" in captured.out or "100.0 %" in captured.out
    assert "test-model" in captured.out
    assert "faithfulness" in captured.out


def test_print_report_with_failures(capsys):
    sample = EvalSample(
        scenario_id="t1",
        endpoint="/x",
        method="GET",
        expected_status=200,
        test_code="",
        spec_summary="",
    )
    passed = EvalScore(
        metric=EvalMetric.FAITHFULNESS,
        score=0.3,
        status=EvalStatus.FAIL,
        detail="wrong status",
    )
    result = EvalResult(sample=sample, scores=[passed], duration_ms=10)
    report = EvalReport(results=[result], model="test", eval_timestamp="now")
    print_report(report)
    captured = capsys.readouterr()
    assert "wrong status" in captured.out


def test_judge_sample_without_llm():
    """judge_sample should either return scores (if LLM available) or error (if not)."""
    sample = EvalSample(
        scenario_id="no_llm",
        endpoint="/test",
        method="GET",
        expected_status=200,
        test_code="expect(res.status).toBe(200)",
        spec_summary="returns 200",
    )
    result = judge_sample(sample)
    # Either LLM is available and returns scores, or it's not and returns error
    if result.error is not None:
        assert result.scores == []
    else:
        assert len(result.scores) > 0
