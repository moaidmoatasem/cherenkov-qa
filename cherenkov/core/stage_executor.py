from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from cherenkov.core.contracts import GenerateOutput, IngestOutput, PlanOutput, ReviewOutput
from cherenkov.core.errors import ContractError


class CircuitBreaker:
    """Simple stateful circuit breaker. Trips if error count exceeds threshold."""

    def __init__(self, threshold: int = 2):
        self.threshold = threshold
        self.error_count = 0
        self.tripped = False
        self._lock = threading.Lock()

    def record_failure(self):
        with self._lock:
            self.error_count += 1
            if self.error_count >= self.threshold:
                self.tripped = True

    def reset(self):
        with self._lock:
            self.error_count = 0
            self.tripped = False


_PIPELINE_OUTPUT_TYPES = (IngestOutput, PlanOutput, GenerateOutput, ReviewOutput)


class StageExecutor:
    """Executes a pipeline stage with retry ladder and circuit breaker."""

    def __init__(self, breaker: CircuitBreaker, logger: Any):
        self.breaker = breaker
        self.log = logger

    def execute(
        self,
        stage_name: str,
        stage_func: Callable[[], Any],
        fallback_factory: Callable[[], Any],
    ) -> Any:
        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            try:
                result = stage_func()

                if not isinstance(result, _PIPELINE_OUTPUT_TYPES):
                    raise ContractError(
                        f"Stage {stage_name} returned unvalidated raw types."
                    )

                self.log.info(
                    "stage success",
                    stage=stage_name,
                    duration_ms=result.metadata.duration_ms,
                )
                return result

            except (ValidationError, ContractError, Exception) as e:
                attempts += 1
                self.log.warning(
                    "stage boundary violation",
                    stage=stage_name,
                    attempt=attempts,
                    error=str(e),
                )

                if attempts >= max_attempts:
                    self.log.error(
                        "retry ladder exhausted",
                        stage=stage_name,
                        detail="triggering fallback schema",
                    )
                    self.breaker.record_failure()
                    return fallback_factory()

                wait = (2**attempts) * 0.5 + random.uniform(0, 0.5)
                time.sleep(wait)

        return None

    def execute_with_vlm_retry(
        self,
        stage_name: str,
        slices: list[Any],
        stage_factory: Callable[[], Any],
        run_slice: Callable,
        fallback_report_factory: Callable[[str, str], Any],
        report_type: type,
        contract_error_msg: str,
    ) -> list[Any]:
        """Shared retry ladder for visual/perf stages (eliminates code clone)."""
        stage = stage_factory()
        results: list[Any] = []

        for sl in slices:
            attempts = 0
            max_attempts = 3
            report: Any = None

            while attempts < max_attempts:
                try:
                    candidate = run_slice(stage, sl)
                    if not isinstance(candidate, report_type):
                        raise ContractError(
                            contract_error_msg.format(slice_name=sl.name)
                        )
                    self.log.info(
                        "stage success",
                        stage=stage_name,
                        slice=sl.name,
                        duration_ms=candidate.metadata.duration_ms,
                    )
                    report = candidate
                    break
                except (ValidationError, ContractError, Exception) as e:
                    attempts += 1
                    self.log.warning(
                        "stage boundary violation",
                        stage=stage_name,
                        slice=sl.name,
                        attempt=attempts,
                        error=str(e),
                    )
                    if attempts >= max_attempts:
                        self.log.error(
                            "retry ladder exhausted",
                            stage=stage_name,
                            slice=sl.name,
                            detail="triggering fallback report",
                        )
                        self.breaker.record_failure()
                        report = fallback_report_factory(sl.name, stage_name)
                        break
                    wait = (2**attempts) * 0.5 + random.uniform(0, 0.5)
                    time.sleep(wait)

            if report is not None:
                results.append(report)

        return results
