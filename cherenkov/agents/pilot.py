from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal


@dataclass
class PilotStep:
    step_id: str
    action: str
    target: str
    expected: str
    actual: str | None = None
    status: Literal["pending", "running", "done", "failed"] = "pending"


class InMemoryRunner:
    def __init__(self):
        self.steps: list[PilotStep] = []

    def execute_step(self, step: PilotStep) -> PilotStep:
        step.status = "running"
        time.sleep(0.1)
        step.actual = step.expected
        step.status = "done"
        self.steps.append(step)
        return step


class PilotAgent:
    def __init__(
        self,
        runner: InMemoryRunner,
        max_observations: int = 20,
        timeout_seconds: int = 300,
    ):
        self.runner = runner
        self.max_observations = max_observations
        self.timeout_seconds = timeout_seconds
        self.observations = 0
        self.start_time = None

    def run(self, intent: str) -> list[PilotStep]:
        self.start_time = time.time()
        self.observations = 0
        steps = self._parse_intent(intent)
        for step in steps:
            if self.observations >= self.max_observations:
                step.status = "failed"
                step.actual = "Circuit breaker: max observations reached"
                break
            if time.time() - self.start_time > self.timeout_seconds:
                step.status = "failed"
                step.actual = "Circuit breaker: timeout reached"
                break
            result = self.runner.execute_step(step)
            self.observations += 1
            if result.status == "failed":
                self._recover(result)
                break
        return self.runner.steps

    def _parse_intent(self, intent: str) -> list[PilotStep]:
        return [
            PilotStep(
                step_id="1", action="open_app", target="app", expected="app_opened"
            ),
            PilotStep(
                step_id="2",
                action="navigate",
                target="screen",
                expected="screen_visible",
            ),
            PilotStep(
                step_id="3",
                action="verify",
                target="element",
                expected="element_present",
            ),
        ]

    def _recover(self, failed_step: PilotStep):
        print(f"Pilot recovery: {failed_step.action} failed - {failed_step.actual}")
