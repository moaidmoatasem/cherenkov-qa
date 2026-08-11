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
    """A decomposed piece of work given to a single sub-agent.

    Attributes:
        instruction (str): Specific task instruction string.
        context (dict[str, Any]): Context dictionary. Defaults to empty dict.
        budget (int): Token budget limit. Defaults to 5000.
        task_id (str): Unique sub-task identifier. Defaults to UUID.
    """

    instruction: str
    context: dict[str, Any] = field(default_factory=dict)
    budget: int = 5000  # Strict token budget cap
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SubAgentResult:
    """The result returned from a single sub-agent.

    Attributes:
        task_id (str): Associated sub-task identifier.
        agent_id (str): Identifier of the executing sub-agent.
        status (str): Outcome status ("success", "failed", "timeout", "budget_exceeded").
        output (Any): Output payload.
        tokens_used (int): Tokens consumed during execution. Defaults to 0.
        error_message (str | None): Optional error details. Defaults to None.
    """

    task_id: str
    agent_id: str
    status: str  # "success", "failed", "timeout", "budget_exceeded"
    output: Any
    tokens_used: int = 0
    error_message: str | None = None


@dataclass
class ConductorTask:
    """The top-level task given to the Conductor.

    Attributes:
        objective (str): High-level task objective description.
        payload (Any): Objective payload or input data.
        sub_tasks (list[SubAgentTask]): List of decomposed sub-agent tasks. Defaults to empty list.
        merge_strategy (MergeStrategy): Aggregation strategy. Defaults to UNION.
        global_timeout_seconds (int): Execution timeout cap in seconds. Defaults to 300.
        task_id (str): Unique conductor task identifier. Defaults to UUID.
    """

    objective: str
    payload: Any
    sub_tasks: list[SubAgentTask] = field(default_factory=list)
    merge_strategy: MergeStrategy = MergeStrategy.UNION
    global_timeout_seconds: int = 300
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ConductorResult:
    """The final aggregated result from the Conductor.

    Attributes:
        task_id (str): Associated ConductorTask identifier.
        status (str): Overall completion status ("success", "partial", "failed").
        aggregated_output (Any): Merged output from sub-agent results.
        sub_results (list[SubAgentResult]): List of individual sub-agent results.
        total_tokens_used (int): Total token count used across all sub-tasks.
    """

    task_id: str
    status: str  # "success", "partial", "failed"
    aggregated_output: Any
    sub_results: list[SubAgentResult] = field(default_factory=list)
    total_tokens_used: int = 0


class StackStrategy(str, Enum):
    """Stack slicing strategies for multi-layer PR coordination."""

    FUNCTIONAL = "functional"
    REFACTOR_FIRST = "refactor_first"
    RISK_ISOLATED = "risk_isolated"


@dataclass
class PRSubTask:
    """A piece of work attached to a specific PR layer in a stack.

    Attributes:
        layer_index (int): Index position of PR layer in stack.
        layer_name (str): Display name for the PR layer.
        branch_name (str): Git branch name for layer PR.
        base_branch (str): Base target branch for layer PR.
        instruction (str): Layer modification instructions.
        target_paths (list[str]): File paths targeted by layer.
        sdd_budget (int): Token budget for layer execution. Defaults to 25000.
        pr_number (int | None): Created PR number if created. Defaults to None.
        task_id (str): Sub-task UUID. Defaults to UUID.
    """

    layer_index: int
    layer_name: str
    branch_name: str
    base_branch: str
    instruction: str
    target_paths: list[str]
    sdd_budget: int = 25000
    pr_number: int | None = None
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class StackedPRTask:
    """Top-level task for coordinating a stack of dependent PRs.

    Attributes:
        epic_issue_id (str): Parent epic GitHub issue identifier.
        title (str): Stacked PR title summary.
        strategy (StackStrategy): Stack slicing strategy.
        layers (list[PRSubTask]): Ordered list of PR sub-tasks.
        global_sdd_budget (int): Overall token budget cap. Defaults to 100000.
        stack_id (str): Unique stack identifier string.
    """

    epic_issue_id: str
    title: str
    strategy: StackStrategy
    layers: list[PRSubTask]
    global_sdd_budget: int = 100000
    stack_id: str = field(default_factory=lambda: f"stack_{uuid.uuid4().hex[:8]}")

