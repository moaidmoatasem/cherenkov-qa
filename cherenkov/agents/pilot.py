"""
cherenkov/agents/pilot.py — Autonomous testing pilot agent and runner primitives.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal


@dataclass
class PilotStep:
    """Represents a single step executed by the PilotAgent during test intent execution.

    Attributes:
        step_id: Unique identifier for the step.
        action: Name of the action being performed.
        target: Target entity or UI component for the action.
        expected: Expected outcome string.
        actual: Actual outcome string after execution, if available.
        status: Execution status of the step ("pending", "running", "done", "failed").
    """

    step_id: str
    action: str
    target: str
    expected: str
    actual: str | None = None
    status: Literal["pending", "running", "done", "failed"] = "pending"


class InMemoryRunner:
    """In-memory test step runner executing PilotStep operations for testing."""

    def __init__(self):
        """Initialize InMemoryRunner with an empty steps list."""
        self.steps: list[PilotStep] = []

    def execute_step(self, step: PilotStep) -> PilotStep:
        """Execute a single pilot step and record its execution state.

        Args:
            step: PilotStep instance to execute.

        Returns:
            PilotStep: Updated step with actual results and completed status.
        """
        step.status = "running"
        time.sleep(0.1)
        step.actual = step.expected
        step.status = "done"
        self.steps.append(step)
        return step


class PilotAgent:
    """Autonomous agent orchestrating test execution from intent specifications with safety limits.

    Args:
        runner: InMemoryRunner instance responsible for step execution.
        max_observations: Maximum allowed observations before triggering circuit breaker.
        timeout_seconds: Maximum allowed execution time in seconds.
    """

    def __init__(
        self,
        runner: InMemoryRunner,
        max_observations: int = 20,
        timeout_seconds: int = 300,
    ):
        """Initialize PilotAgent with runner and safety thresholds.

        Args:
            runner: InMemoryRunner instance responsible for step execution.
            max_observations: Maximum allowed observations before triggering circuit breaker.
            timeout_seconds: Maximum allowed execution time in seconds.
        """
        self.runner = runner
        self.max_observations = max_observations
        self.timeout_seconds = timeout_seconds
        self.observations = 0
        self.start_time: float | None = None

    def run(self, intent: str) -> list[PilotStep]:
        """Execute test intent steps, enforcing observation count and timeout limits.

        Args:
            intent: Description or plan specification for the test intent.

        Returns:
            list[PilotStep]: List of executed PilotStep results.
        """
        self.start_time = time.monotonic()
        self.observations = 0
        steps = self._parse_intent(intent)
        for step in steps:
            if self.observations >= self.max_observations:
                step.status = "failed"
                step.actual = "Circuit breaker: max observations reached"
                break
            if time.monotonic() - self.start_time > self.timeout_seconds:
                step.status = "failed"
                step.actual = "Circuit breaker: timeout reached"
                break
            result = self.runner.execute_step(step)
            self.observations += 1
            if result.status == "failed":
                self._recover(result)
                break
        return self.runner.steps

    def _parse_intent(self, _intent: str) -> list[PilotStep]:
        """Parse test intent string into a list of executable PilotStep objects.

        Args:
            _intent (str): Description string of test intent.

        Returns:
            list[PilotStep]: Parsed list of step objects.
        """
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

    def _recover(self, failed_step: PilotStep) -> None:
        """Log recovery message when a pilot step fails during execution.

        Args:
            failed_step (PilotStep): The failed PilotStep object.

        Returns:
            None
        """
        print(f"Pilot recovery: {failed_step.action} failed - {failed_step.actual}")


