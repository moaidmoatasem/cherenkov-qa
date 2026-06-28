"""Task decomposition strategies for the Agent Conductor (CC-2)."""
from __future__ import annotations

import copy
from typing import Any

from cherenkov.agents.conductor.domain.models import SubAgentTask


def split_by_item(
    instruction_template: str,
    items: list[Any],
    context: dict[str, Any] | None = None,
    budget_per_item: int = 5000,
) -> list[SubAgentTask]:
    """Split a task by distributing a list of items to parallel sub-tasks.

    Args:
        instruction_template: The prompt template (must contain `{item}`).
        items: The list of items to distribute.
        context: Shared context dictionary.
        budget_per_item: Token budget for each sub-task.

    Returns:
        A list of SubAgentTasks.
    """
    ctx = context or {}
    tasks = []
    for item in items:
        # Shallow copy context and inject the current item
        task_ctx = copy.copy(ctx)
        task_ctx["item"] = item
        instruction = instruction_template.format(item=item)

        tasks.append(
            SubAgentTask(
                instruction=instruction,
                context=task_ctx,
                budget=budget_per_item,
            )
        )
    return tasks


def split_by_role(
    base_instruction: str,
    roles: list[str],
    context: dict[str, Any] | None = None,
    budget_per_role: int = 5000,
) -> list[SubAgentTask]:
    """Split a task by assigning it to different specialized agent roles.

    Args:
        base_instruction: The core task description.
        roles: The list of role strings (e.g. "Security Reviewer", "Performance Expert").
        context: Shared context dictionary.
        budget_per_role: Token budget for each sub-task.

    Returns:
        A list of SubAgentTasks.
    """
    ctx = context or {}
    tasks = []
    for role in roles:
        instruction = (
            f"You are acting as the {role}.\n\n"
            f"Task: {base_instruction}\n\n"
            f"Focus solely on aspects relevant to your role."
        )

        task_ctx = copy.copy(ctx)
        task_ctx["role"] = role

        tasks.append(
            SubAgentTask(
                instruction=instruction,
                context=task_ctx,
                budget=budget_per_role,
            )
        )
    return tasks
