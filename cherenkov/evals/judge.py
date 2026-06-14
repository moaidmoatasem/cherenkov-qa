from __future__ import annotations

import json
import time
from typing import Any

from cherenkov.ai import get_client
from cherenkov.ai.ollama_client import strip_think
from cherenkov.core.config import Config
from cherenkov.evals.core import (
    EvalMetric,
    EvalResult,
    EvalSample,
    EvalScore,
    EvalStatus,
)


_JUDGE_SYSTEM_PROMPT = """You are a CHERENKOV test quality judge. Evaluate Playwright API tests generated from OpenAPI specs.

Rate each test on 5 metrics (score 0.0–1.0):

1. FAITHFULNESS — Does the test assert the CORRECT HTTP status per the spec? (expected_status)
2. HALLUCINATION — Does the test avoid asserting properties/behaviors NOT in the spec?
3. ASSERTION_QUALITY — Are the assertions meaningful (specific values/patterns, not just toHaveProperty)?
4. SPEC_ALIGNMENT — Does the test structure (path, method, body) match the endpoint spec?
5. COMPLETENESS — Does the test adequately cover the scenario?

Respond ONLY with valid JSON:
{"scores": [{"metric": "faithfulness", "score": 0.95, "detail": "...", "status": "pass"}, ...], "evidence": "..."}
"""


def _build_judge_prompt(sample: EvalSample) -> str:
    return (
        f"Evaluate this generated test:\n\n"
        f"Endpoint: {sample.method} {sample.endpoint}\n"
        f"Expected status: {sample.expected_status}\n"
        f"Spec summary: {sample.spec_summary}\n"
        f"Scenario: {sample.scenario_id}\n\n"
        f"Test code:\n```typescript\n{sample.test_code}\n```\n\n"
        f"Rate each metric 0.0–1.0."
    )


def _parse_score(name: str, entry: dict[str, Any]) -> EvalScore:
    metric_map = {
        "faithfulness": EvalMetric.FAITHFULNESS,
        "hallucination": EvalMetric.HALLUCINATION,
        "assertion_quality": EvalMetric.ASSERTION_QUALITY,
        "spec_alignment": EvalMetric.SPEC_ALIGNMENT,
        "completeness": EvalMetric.COMPLETENESS,
    }
    metric = metric_map.get(name.lower(), EvalMetric.FAITHFULNESS)
    score = float(entry.get("score", 0.0))
    status_str = entry.get("status", "fail")
    if status_str == "pass" and score >= 0.7:
        status = EvalStatus.PASS
    elif status_str == "warn" or (status_str == "pass" and score < 0.7):
        status = EvalStatus.WARN
    else:
        status = EvalStatus.FAIL
    return EvalScore(
        metric=metric,
        score=score,
        status=status,
        detail=entry.get("detail", ""),
        evidence=entry.get("evidence"),
    )


def judge_sample(sample: EvalSample) -> EvalResult:
    t0 = time.time()
    try:
        client = get_client()
        prompt = _build_judge_prompt(sample)
        raw = client.complete_code(
            system_prompt=_JUDGE_SYSTEM_PROMPT,
            user_prompt=prompt,
            model=Config.GEN_MODEL,
            temperature=0.1,
            run_id="eval-judge",
        )
        cleaned = strip_think(raw)
        parsed = json.loads(cleaned)
        scores_raw = parsed.get("scores", [])
        scores = [_parse_score(s.get("metric", ""), s) for s in scores_raw]
        duration = int((time.time() - t0) * 1000)
        return EvalResult(sample=sample, scores=scores, duration_ms=duration)
    except Exception as e:
        duration = int((time.time() - t0) * 1000)
        return EvalResult(
            sample=sample,
            scores=[],
            duration_ms=duration,
            error=str(e),
        )
