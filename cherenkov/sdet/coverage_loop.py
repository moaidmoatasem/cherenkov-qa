"""
CHERENKOV sdet/coverage_loop.py — E11-1 bounded generate→run→read-trace→repair.

Drives a set of coverage targets (typically endpoint+case ids) toward a
configured coverage threshold. For each target the loop:

    1. generate  a candidate test          (generate_fn)
    2. run it against the correct mock and  (run_fn)  → RunOutcome
       read the trace to confirm it actually exercised the target
    3. if it failed or did not exercise the target, repair (repair_fn) and retry
    4. once it passes and exercises the target, gate it through the
       meaningful-assertion gate (E11-2) — only meaningful tests count

The loop is *bounded* on both axes: at most `max_repairs` retries per target,
and it stops as soon as the coverage threshold is met (remaining targets stay
PENDING). All model/server/trace work is injected as callables, so the loop is
deterministic and unit-testable — mirroring `divergence/self_play.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from cherenkov.core.contracts import (
    CoverageItem,
    CoverageItemState,
    CoverageReport,
    Status,
)
from cherenkov.core.errors import get_logger
from cherenkov.sdet.assertion_gate import MeaningfulAssertionGate


@dataclass
class RunOutcome:
    """Result of running one candidate test against a base URL + reading its trace."""
    passed: bool                          # assertions passed against the target server
    exercised: bool = True                # the trace shows the target was actually hit
    output: str = ""                      # captured stdout/diagnostic for repair context
    trace_info: dict[str, Any] | None = None


# generate_fn(target_id) -> artifact (opaque candidate test representation)
GenerateFn = Callable[[str], Any]
# run_fn(artifact, base_url) -> RunOutcome
RunFn = Callable[[Any, str], RunOutcome]
# repair_fn(target_id, artifact, outcome) -> artifact
RepairFn = Callable[[str, Any, RunOutcome], Any]


class CoverageLoop:
    def __init__(
        self,
        generate_fn: GenerateFn,
        run_fn: RunFn,
        repair_fn: RepairFn,
        *,
        correct_mock_url: str,
        broken_mock_url: str | None = None,
        gate: MeaningfulAssertionGate | None = None,
        threshold: float = 0.8,
        max_repairs: int = 2,
        run_id: str | None = None,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be in [0.0, 1.0], got {threshold}")
        if max_repairs < 0:
            raise ValueError(f"max_repairs must be >= 0, got {max_repairs}")

        self.generate_fn = generate_fn
        self.run_fn = run_fn
        self.repair_fn = repair_fn
        self.correct_mock_url = correct_mock_url
        self.broken_mock_url = broken_mock_url
        # Gate is optional; if a broken_mock_url is supplied we default to gating.
        self.gate = gate
        if self.gate is None and broken_mock_url is not None:
            self.gate = MeaningfulAssertionGate(run_id=run_id)
        self.threshold = threshold
        self.max_repairs = max_repairs
        self.log = get_logger("COVERAGE_SDET", run_id)

    def run(self, target_ids: list[str], target_name: str = "target") -> CoverageReport:
        report = CoverageReport(target=target_name, threshold=self.threshold)
        report.items = [CoverageItem(target_id=t) for t in target_ids]

        for item in report.items:
            if report.threshold_met:
                self.log.info(
                    "threshold met early — stopping",
                    coverage=round(report.coverage, 3),
                    threshold=self.threshold,
                )
                break
            self._drive_item(item)

        report.status = Status.OK if report.threshold_met else Status.DEGRADED
        self.log.info(
            "coverage run complete",
            covered=report.covered,
            total=report.total,
            coverage=round(report.coverage, 3),
            threshold_met=report.threshold_met,
        )
        return report

    # ── private ───────────────────────────────────────────────────────────

    def _drive_item(self, item: CoverageItem) -> None:
        """Generate → (run → repair)* → gate, bounded by max_repairs."""
        artifact = self.generate_fn(item.target_id)

        # 1 generate attempt + up to max_repairs repair attempts.
        for attempt in range(self.max_repairs + 1):
            item.attempts = attempt + 1
            outcome = self.run_fn(artifact, self.correct_mock_url)
            item.passed = outcome.passed

            if outcome.passed and outcome.exercised:
                if self._is_meaningful(item, artifact):
                    item.state = CoverageItemState.COVERED
                    item.detail = ""
                    return
                # Passing but tautological — repair toward real assertions.
                item.detail = "passed but assertions vacuous (gate rejected)"
            elif not outcome.exercised:
                item.detail = "test did not exercise the target (trace)"
            else:
                item.detail = (outcome.output or "assertions failed")[:200]

            # Out of repair budget?
            if attempt >= self.max_repairs:
                break
            artifact = self.repair_fn(item.target_id, artifact, outcome)

        item.state = CoverageItemState.UNMET

    def _is_meaningful(self, item: CoverageItem, artifact: Any) -> bool:
        """Gate the (passing) candidate through the broken-impl run, if configured."""
        if self.gate is None or self.broken_mock_url is None:
            item.meaningful = True
            return True

        def run_test(base_url: str) -> tuple[bool, str]:
            res = self.run_fn(artifact, base_url)
            return res.passed, res.output

        verdict = self.gate.evaluate(
            test_id=item.target_id,
            run_test=run_test,
            correct_mock_url=self.correct_mock_url,
            broken_mock_url=self.broken_mock_url,
        )
        item.meaningful = verdict.meaningful
        if not verdict.meaningful and verdict.reason:
            item.detail = verdict.reason
        return verdict.meaningful
