"""cherenkov/bench/metrics.py — data containers for benchmark results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

COMPILE_GATE = "tsc"


@dataclass
class GateSummary:
    gate: str
    pass_count: int = 0
    fail_count: int = 0
    skip_count: int = 0

    @property
    def pass_rate(self) -> float | None:
        """None when the gate was always skipped (infra not available)."""
        total = self.pass_count + self.fail_count
        if total == 0:
            return None
        return self.pass_count / total

    def to_dict(self) -> dict[str, Any]:
        rate = self.pass_rate
        return {
            "gate": self.gate,
            "pass_rate": round(rate, 4) if rate is not None else None,
            "pass": self.pass_count,
            "fail": self.fail_count,
            "skip": self.skip_count,
        }


@dataclass
class SpecBenchResult:
    """Aggregated REVIEW metrics for one test directory."""

    spec_path: str
    scenario_count: int
    gate_summaries: dict[str, GateSummary]
    avg_quality_score: float
    verdict_distribution: dict[str, int]  # keys: auto_approve / hitl / regenerate
    elapsed_s: float
    errors: list[str] = field(default_factory=list)

    @property
    def compile_rate(self) -> float | None:
        """tsc gate pass rate; None when tsc was not available."""
        gate = self.gate_summaries.get(COMPILE_GATE)
        return gate.pass_rate if gate else None

    @property
    def overall_gate_pass_rate(self) -> float:
        rates = [g.pass_rate for g in self.gate_summaries.values() if g.pass_rate is not None]
        return sum(rates) / len(rates) if rates else 0.0

    def to_dict(self) -> dict[str, Any]:
        cr = self.compile_rate
        return {
            "spec_path": self.spec_path,
            "scenario_count": self.scenario_count,
            "compile_rate": round(cr, 4) if cr is not None else None,
            "avg_quality_score": round(self.avg_quality_score, 4),
            "verdict_distribution": self.verdict_distribution,
            "gate_summaries": {k: v.to_dict() for k, v in self.gate_summaries.items()},
            "elapsed_s": round(self.elapsed_s, 2),
            "errors": self.errors,
        }


@dataclass
class BenchReport:
    """Aggregated benchmark report across all test directories."""

    results: list[SpecBenchResult]
    thresholds: dict[str, float]

    @property
    def total_scenarios(self) -> int:
        return sum(r.scenario_count for r in self.results)

    @property
    def overall_compile_rate(self) -> float | None:
        rates = [r.compile_rate for r in self.results if r.compile_rate is not None]
        return sum(rates) / len(rates) if rates else None

    @property
    def overall_quality_score(self) -> float:
        scores = [r.avg_quality_score for r in self.results if r.scenario_count > 0]
        return sum(scores) / len(scores) if scores else 0.0

    def passed(self) -> bool:
        thr_compile = self.thresholds.get("compile_rate", 0.9)
        thr_quality = self.thresholds.get("quality_score", 0.85)
        cr = self.overall_compile_rate
        if cr is not None and cr < thr_compile:
            return False
        return self.overall_quality_score >= thr_quality

    def to_dict(self) -> dict[str, Any]:
        cr = self.overall_compile_rate
        return {
            "total_scenarios": self.total_scenarios,
            "overall_compile_rate": round(cr, 4) if cr is not None else None,
            "overall_quality_score": round(self.overall_quality_score, 4),
            "passed": self.passed(),
            "thresholds": self.thresholds,
            "specs": [r.to_dict() for r in self.results],
        }
