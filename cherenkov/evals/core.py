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

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_rate": self.pass_rate(),
            "metric_averages": self.metric_averages(),
            "total_scenarios": len(self.results),
            "passed": sum(1 for r in self.results if r.passed()),
            "failed": sum(1 for r in self.results if not r.passed()),
            "results": [r.summary() for r in self.results],
            "model": self.model,
            "timestamp": self.eval_timestamp,
        }
