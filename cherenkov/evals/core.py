from __future__ import annotations

import dataclasses
import enum
from typing import Any


class EvalMetric(enum.Enum):
    FAITHFULNESS = "faithfulness"
    HALLUCINATION = "hallucination"
    ASSERTION_QUALITY = "assertion_quality"
    SPEC_ALIGNMENT = "spec_alignment"
    COMPLETENESS = "completeness"


class EvalStatus(enum.Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    ERROR = "error"


@dataclasses.dataclass
class EvalSample:
    scenario_id: str
    endpoint: str
    method: str
    expected_status: int
    test_code: str
    spec_summary: str


@dataclasses.dataclass
class EvalScore:
    metric: EvalMetric
    score: float
    status: EvalStatus
    detail: str
    evidence: str | None = None


@dataclasses.dataclass
class EvalResult:
    sample: EvalSample
    scores: list[EvalScore]
    duration_ms: int
    error: str | None = None

    def passed(self) -> bool:
        return all(s.status == EvalStatus.PASS for s in self.scores)

    def summary(self) -> dict[str, Any]:
        return {
            "scenario_id": self.sample.scenario_id,
            "endpoint": f"{self.sample.method} {self.sample.endpoint}",
            "passed": self.passed(),
            "scores": {s.metric.value: {"score": s.score, "status": s.status.value} for s in self.scores},
            "duration_ms": self.duration_ms,
        }


@dataclasses.dataclass
class EvalReport:
    results: list[EvalResult]
    model: str
    eval_timestamp: str
    prompt_fingerprint: dict = dataclasses.field(default_factory=dict)

    def pass_rate(self) -> float:
        if not self.results:
            return 1.0
        return sum(1 for r in self.results if r.passed()) / len(self.results)

    def metric_averages(self) -> dict[str, float]:
        averages: dict[str, list[float]] = {}
        for r in self.results:
            for s in r.scores:
                averages.setdefault(s.metric.value, []).append(s.score)
        return {k: sum(v) / len(v) for k, v in averages.items()}

    def total_scenarios(self) -> int:
        return len(self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_rate": self.pass_rate(),
            "metric_averages": self.metric_averages(),
            "total_scenarios": self.total_scenarios(),
            "passed": sum(1 for r in self.results if r.passed()),
            "failed": sum(1 for r in self.results if not r.passed()),
            "results": [r.summary() for r in self.results],
            "model": self.model,
            "timestamp": self.eval_timestamp,
            "prompt_fingerprint": self.prompt_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalReport":
        """Reconstruct a lightweight EvalReport from a to_dict() snapshot.

        Note: individual EvalResult scores are not fully reconstructed (only
        pass/fail per result), which is sufficient for regression comparison.
        """
        results: list[EvalResult] = []
        for r in data.get("results", []):
            sample = EvalSample(
                scenario_id=r.get("scenario_id", ""),
                endpoint=r.get("endpoint", ""),
                method="",
                expected_status=200,
                test_code="",
                spec_summary="",
            )
            passed = r.get("passed", True)
            score_val = 1.0 if passed else 0.0
            scores = [
                EvalScore(
                    metric=EvalMetric.FAITHFULNESS,
                    score=score_val,
                    status=EvalStatus.PASS if passed else EvalStatus.FAIL,
                    detail="",
                )
            ]
            results.append(EvalResult(sample=sample, scores=scores, duration_ms=0))
        return cls(
            results=results,
            model=data.get("model", "unknown"),
            eval_timestamp=data.get("timestamp", ""),
            prompt_fingerprint=data.get("prompt_fingerprint", {}),
        )
