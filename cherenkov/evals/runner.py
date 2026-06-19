from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cherenkov.core.config import Config
from cherenkov.evals.core import EvalMetric, EvalReport, EvalResult, EvalSample, EvalStatus
from cherenkov.evals.judge import judge_sample


def build_samples_from_pipeline(
    scenarios: list[Any],
    generate_outputs: dict[str, Any],
    spec_summaries: dict[str, str],
) -> list[EvalSample]:
    samples: list[EvalSample] = []
    for s in scenarios:
        mutation_id = getattr(s, "mutation_id", getattr(s, "operation_name", "unknown"))
        go = generate_outputs.get(mutation_id)
        if go is None:
            continue
        test_code = getattr(go, "test_code", "") if not isinstance(go, dict) else go.get("test_code", "")
        if not test_code:
            continue
        endpoint = getattr(s, "endpoint", getattr(s, "path", ""))
        method = getattr(s, "method", "GET")
        expected_status = getattr(s, "expected_status", 200)
        spec_key = f"{method.upper()} {endpoint}"
        spec_summary = spec_summaries.get(spec_key, spec_summaries.get(endpoint, ""))
        samples.append(
            EvalSample(
                scenario_id=mutation_id,
                endpoint=endpoint,
                method=method,
                expected_status=expected_status,
                test_code=test_code,
                spec_summary=spec_summary,
            )
        )
    return samples


def run_evals(samples: list[EvalSample], max_workers: int = 2) -> EvalReport:
    results: list[EvalResult] = []
    for sample in samples:
        result = judge_sample(sample)
        results.append(result)

    report = EvalReport(
        results=results,
        model=Config.GEN_MODEL,
        eval_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Optional observability trace
    try:
        from cherenkov.observability.llm_tracer import trace_event
        trace_event(
            "evals-complete",
            pass_rate=report.pass_rate(),
            scenarios=len(report.results),
            model=report.model,
        )
    except Exception:
        pass

    return report


def print_report(report: EvalReport) -> None:
    print(f"\n{'='*60}")
    print("  CHERENKOV EVAL REPORT")
    print(f"{'='*60}")
    print(f"  Model:         {report.model}")
    print(f"  Scenarios:     {report.to_dict()['total_scenarios']}")
    print(f"  Pass rate:     {report.pass_rate():.1%}")
    print(f"  Timestamp:     {report.eval_timestamp}")
    print(f"{'-'*60}")
    avgs = report.metric_averages()
    for metric in EvalMetric:
        avg = avgs.get(metric.value)
        if avg is not None:
            bar = "█" * int(avg * 20) + "░" * (20 - int(avg * 20))
            print(f"  {metric.value:20s} {bar} {avg:.2f}")
    print(f"{'='*60}")
    for r in report.results:
        if not r.passed():
            for s in r.scores:
                if s.status != EvalStatus.PASS:
                    print(f"  ❌ {r.sample.scenario_id}: {s.metric.value}={s.score:.2f} — {s.detail}")
    print(f"{'='*60}\n")
