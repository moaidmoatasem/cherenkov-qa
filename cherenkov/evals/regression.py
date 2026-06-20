"""
cherenkov/evals/regression.py — LLM/prompt quality regression detector.

Compares a freshly-produced EvalReport against a committed baseline
(stored as JSON in bench/eval-baseline.json) and raises RegressionError
when any metric drops below its allowed floor.

Usage in CI:
    from cherenkov.evals.regression import RegressionGuard

    guard = RegressionGuard()
    guard.assert_no_regression(current_report)   # raises on regression

Usage from CLI (cherenkov bench --check-regression):
    python -m cherenkov.evals.regression --report path/to/report.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from cherenkov.evals.core import EvalReport
from cherenkov.evals.prompt_version import get_prompt_fingerprint, prompt_changed


_BASELINE_PATH = Path("bench/eval-baseline.json")

# Per-metric absolute tolerance: allow this many points drop before failing.
# E.g. 0.05 means a drop from 0.90 → 0.86 is OK but 0.90 → 0.84 is not.
_DEFAULT_TOLERANCE: dict[str, float] = {
    "pass_rate": 0.05,
    "faithfulness": 0.05,
    "hallucination": 0.05,
    "assertion_quality": 0.05,
    "spec_alignment": 0.05,
    "completeness": 0.05,
}


@dataclass
class RegressionFinding:
    metric: str
    baseline: float
    current: float
    delta: float        # current - baseline (negative = regression)
    tolerance: float
    exceeded_by: float  # how far past the tolerance the drop went


class RegressionError(Exception):
    """Raised when one or more metrics regress beyond tolerance."""

    def __init__(self, findings: list[RegressionFinding]) -> None:
        self.findings = findings
        lines = [
            f"  {f.metric}: {f.baseline:.3f} → {f.current:.3f} "
            f"(drop={abs(f.delta):.3f}, tolerance={f.tolerance:.3f}, "
            f"exceeded_by={f.exceeded_by:.3f})"
            for f in findings
        ]
        super().__init__(
            f"LLM quality regression detected ({len(findings)} metric(s)):\n"
            + "\n".join(lines)
        )


class RegressionGuard:
    """Compares eval reports against a stored baseline.

    Args:
        baseline_path: Path to the baseline JSON file.
            Defaults to ``bench/eval-baseline.json``.
        tolerance: Per-metric absolute drop tolerance. Values not listed
            fall back to 0.05.
    """

    def __init__(
        self,
        baseline_path: Path = _BASELINE_PATH,
        tolerance: dict[str, float] | None = None,
    ) -> None:
        self.baseline_path = baseline_path
        self.tolerance = {**_DEFAULT_TOLERANCE, **(tolerance or {})}

    def load_baseline(self) -> dict[str, float] | None:
        """Load baseline metrics from disk. Returns None if no baseline exists yet."""
        if not self.baseline_path.exists():
            return None
        raw = json.loads(self.baseline_path.read_text(encoding="utf-8"))
        return raw.get("metrics", {})

    def save_baseline(self, report: EvalReport) -> None:
        """Write the current report as the new baseline (call after a green run)."""
        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        metrics = {"pass_rate": report.pass_rate(), **report.metric_averages()}
        pf = report.prompt_fingerprint or get_prompt_fingerprint()
        baseline = {
            "metrics": metrics,
            "model": report.model,
            "timestamp": report.eval_timestamp,
            "total_scenarios": report.total_scenarios(),
            "prompt_fingerprint": pf,
        }
        self.baseline_path.write_text(
            json.dumps(baseline, indent=2), encoding="utf-8"
        )

    def check(self, report: EvalReport) -> list[RegressionFinding]:
        """Return a list of RegressionFindings for metrics that dropped too far.

        Returns an empty list (no regression) if no baseline exists.
        """
        baseline_metrics = self.load_baseline()
        if baseline_metrics is None:
            return []

        current_metrics: dict[str, float] = {
            "pass_rate": report.pass_rate(),
            **report.metric_averages(),
        }

        findings: list[RegressionFinding] = []
        for metric, baseline_val in baseline_metrics.items():
            current_val = current_metrics.get(metric)
            if current_val is None:
                continue
            tol = self.tolerance.get(metric, 0.05)
            delta = current_val - baseline_val
            if delta < -tol:
                findings.append(
                    RegressionFinding(
                        metric=metric,
                        baseline=baseline_val,
                        current=current_val,
                        delta=delta,
                        tolerance=tol,
                        exceeded_by=abs(delta) - tol,
                    )
                )
        return findings

    def assert_no_regression(self, report: EvalReport) -> None:
        """Raise RegressionError if any metric regressed beyond tolerance."""
        findings = self.check(report)
        if findings:
            raise RegressionError(findings)

    def report_dict(self, report: EvalReport) -> dict[str, Any]:
        """Return a structured summary dict (for CI JSON outputs)."""
        findings = self.check(report)
        baseline = self.load_baseline() or {}
        current = {"pass_rate": report.pass_rate(), **report.metric_averages()}
        baseline_pf = (self.load_baseline() or {}).get("prompt_fingerprint", {}) if self.baseline_path.exists() else {}
        current_pf = report.prompt_fingerprint or get_prompt_fingerprint()
        changed_prompts = prompt_changed(baseline_pf, current_pf) if baseline_pf else []
        return {
            "regression_detected": bool(findings),
            "prompt_changed": changed_prompts,
            "prompt_change_warning": (
                f"Prompt files changed since baseline: {changed_prompts}. "
                "Metric shift may reflect prompt change, not model regression."
            ) if changed_prompts else None,
            "findings": [asdict(f) for f in findings],
            "baseline": baseline,
            "current": current,
            "model": report.model,
            "timestamp": report.eval_timestamp,
        }


# ── CLI entry point ──────────────────────────────────────────────────────────
def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check an eval report JSON for metric regression."
    )
    parser.add_argument("--report", required=True, help="Path to EvalReport JSON file")
    parser.add_argument(
        "--baseline",
        default=str(_BASELINE_PATH),
        help="Path to baseline JSON (default: bench/eval-baseline.json)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="If no regression, update the baseline to the current report",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.05,
        help="Global drop tolerance (default 0.05)",
    )
    args = parser.parse_args()

    raw = json.loads(Path(args.report).read_text(encoding="utf-8"))
    report = EvalReport.from_dict(raw)

    guard = RegressionGuard(
        baseline_path=Path(args.baseline),
        tolerance={k: args.tolerance for k in _DEFAULT_TOLERANCE},
    )

    result = guard.report_dict(report)
    print(json.dumps(result, indent=2))

    if result["regression_detected"]:
        print("\nREGRESSION DETECTED — failing.", file=sys.stderr)
        sys.exit(1)

    if args.update_baseline:
        guard.save_baseline(report)
        print(f"\nBaseline updated → {args.baseline}")


if __name__ == "__main__":
    _main()
