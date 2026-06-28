"""Ports for the Multi-Agent Conductor (CC-2, ADR-013)."""
from __future__ import annotations

from typing import Protocol

from cherenkov.agents.conductor.domain.models import ConductorResult, ConductorTask


class AgentConductor(Protocol):
    """Protocol for orchestrating parallel sub-agents to solve a complex task.

    The Conductor is responsible for:
    1. Taking a decomposed ConductorTask containing multiple SubAgentTasks.
    2. Fanning out the sub-tasks to available agents (e.g., over MCP).
    3. Enforcing token budgets and timeouts.
    4. Aggregating the SubAgentResults back into a final ConductorResult.
    """

    def execute(self, task: ConductorTask) -> ConductorResult:
        """Run the conductor task and return the aggregated result."""
        ...
