"""cherenkov/bench/runner.py — REVIEW-stage benchmark runner.

Scans a directory for .spec.ts files, runs each through ReviewStage,
and aggregates gate-level pass rates and quality scores.

No LLM, no network, no Docker required for the static gates (1–4).
Gate 5 (tsc) requires node/tsc on PATH; Gate 6 (prism) requires Docker.
Both are automatically skipped and reported as N/A when unavailable.
"""

from __future__ import annotations

import os
import time
from typing import Sequence

from cherenkov.core.contracts import GenerateOutput, StageMeta, Status
from cherenkov.core.errors import LoggerConfig
from cherenkov.stages.review import ReviewStage
from cherenkov.bench.metrics import BenchReport, GateSummary, SpecBenchResult

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_DEFAULT_SPEC = os.path.join(_REPO_ROOT, "stub", "openapi_3_1.yaml")
_GOLDEN_DIR = os.path.join(_REPO_ROOT, "bench", "fixtures", "golden_tests")


def _find_spec_ts(directory: str) -> list[str]:
    found: list[str] = []
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            if f.endswith(".spec.ts"):
                found.append(os.path.join(root, f))
    return found


def bench_directory(
    test_dir: str,
    spec_path: str | None = None,
    run_id_prefix: str = "bench",
) -> SpecBenchResult:
    """Run the REVIEW stage against every .spec.ts in test_dir.

    Returns aggregated gate pass rates, quality scores, and verdict distribution.
    """
    LoggerConfig.suppress_stderr = True
    effective_spec = spec_path or _DEFAULT_SPEC

    test_files = _find_spec_ts(test_dir)
    if not test_files:
        return SpecBenchResult(
            spec_path=effective_spec,
            scenario_count=0,
            gate_summaries={},
            avg_quality_score=0.0,
            verdict_distribution={"AUTO_APPROVE": 0, "HITL": 0, "REGENERATE": 0},
            elapsed_s=0.0,
            errors=["No .spec.ts files found in directory"],
        )

    gate_summaries: dict[str, GateSummary] = {}
    quality_scores: list[float] = []
    verdict_counts: dict[str, int] = {"auto_approve": 0, "hitl": 0, "regenerate": 0}
    errors: list[str] = []

    t0 = time.monotonic()

    for test_file in test_files:
        scenario_id = os.path.splitext(os.path.basename(test_file))[0]
        try:
            with open(test_file, encoding="utf-8") as fh:
                code = fh.read()

            generate_out = GenerateOutput(
                scenario_id=scenario_id,
                test_code=code,
                endpoint="/bench",
                method="GET",
                status=Status.OK,
                metadata=StageMeta(stage="GENERATE"),
            )

            stage = ReviewStage(run_id=f"{run_id_prefix}-{scenario_id}")
            result = stage.run(generate_out, spec_path=effective_spec)

            quality_scores.append(result.quality_score)
            verdict_key = result.verdict.value
            if verdict_key not in verdict_counts:
                verdict_counts[verdict_key] = 0
            verdict_counts[verdict_key] += 1

            for gate in result.gates:
                if gate.gate not in gate_summaries:
                    gate_summaries[gate.gate] = GateSummary(gate=gate.gate)
                summary = gate_summaries[gate.gate]
                if gate.skipped:
                    summary.skip_count += 1
                elif gate.passed:
                    summary.pass_count += 1
                else:
                    summary.fail_count += 1

        except Exception as exc:
            errors.append(f"{scenario_id}: {exc}")

    elapsed = time.monotonic() - t0
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    return SpecBenchResult(
        spec_path=effective_spec,
        scenario_count=len(test_files),
        gate_summaries=gate_summaries,
        avg_quality_score=avg_quality,
        verdict_distribution=verdict_counts,
        elapsed_s=elapsed,
        errors=errors,
    )


def run_bench(
    test_dirs: Sequence[str],
    spec_path: str | None = None,
    thresholds: dict[str, float] | None = None,
) -> BenchReport:
    """Run bench across multiple directories and aggregate into a BenchReport."""
    effective_thresholds = thresholds or {"compile_rate": 0.9, "quality_score": 0.85}
    results = [
        bench_directory(d, spec_path=spec_path, run_id_prefix=f"bench-{i}")
        for i, d in enumerate(test_dirs)
    ]
    return BenchReport(results=results, thresholds=effective_thresholds)


def run_golden_bench(spec_path: str | None = None) -> BenchReport:
    """Convenience: run bench against the bundled golden test fixtures."""
    return run_bench([_GOLDEN_DIR], spec_path=spec_path)
