"""Team templates for standard Conductor workflows (CC-2)."""
from __future__ import annotations

from cherenkov.agents.conductor.domain.models import ConductorTask, MergeStrategy
from cherenkov.agents.conductor.use_cases.decompose import split_by_role


def create_review_team(
    code_snippet: str,
    roles: list[str] | None = None,
    budget: int = 4000,
) -> ConductorTask:
    """Create a ConductorTask that delegates code review to specialized roles.

    Args:
        code_snippet (str): The code snippet to review.
        roles (list[str] | None): List of reviewer roles. Defaults to None (Security, Performance, and Style).
        budget (int): Token budget per reviewer. Defaults to 4000.

    Returns:
        ConductorTask: A ConductorTask configured for the review team.
    """

    if roles is None:
        roles = ["Security Auditor", "Performance Expert", "Style Consistency Checker"]

    instruction = (
        "Review the following code and provide your findings.\n\n"
        f"```\n{code_snippet}\n```"
    )

    sub_tasks = split_by_role(
        base_instruction=instruction,
        roles=roles,
        budget_per_role=budget,
    )

    return ConductorTask(
        objective="Multi-perspective code review",
        payload={"code": code_snippet},
        sub_tasks=sub_tasks,
        merge_strategy=MergeStrategy.UNION,
        global_timeout_seconds=300,
    )
