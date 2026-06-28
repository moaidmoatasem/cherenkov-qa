"""Domain models for the Multi-Agent Conductor (CC-2, ADR-013)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MergeStrategy(str, Enum):
    """How to aggregate results from parallel sub-agents."""

    UNION = "union"
    CONSENSUS = "consensus"
    WEIGHTED = "weighted"


@dataclass
class SubAgentTask:
    """A decomposed piece of work given to a single sub-agent."""

    instruction: str
    context: dict[str, Any] = field(default_factory=dict)
    budget: int = 5000  # Strict token budget cap
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SubAgentResult:
    """The result returned from a single sub-agent."""

    task_id: str
    agent_id: str
    status: str  # "success", "failed", "timeout", "budget_exceeded"
    output: Any
    tokens_used: int = 0
    error_message: str | None = None


@dataclass
class ConductorTask:
    """The top-level task given to the Conductor."""

    objective: str
    payload: Any
    sub_tasks: list[SubAgentTask] = field(default_factory=list)
    merge_strategy: MergeStrategy = MergeStrategy.UNION
    global_timeout_seconds: int = 300
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ConductorResult:
    """The final aggregated result from the Conductor."""

    task_id: str
    status: str  # "success", "partial", "failed"
    aggregated_output: Any
    sub_results: list[SubAgentResult] = field(default_factory=list)
    total_tokens_used: int = 0
