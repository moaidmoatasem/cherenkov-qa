"""Audit team template for Conductor (CC-2)."""
from __future__ import annotations

from cherenkov.agents.conductor.domain.models import ConductorTask, MergeStrategy
from cherenkov.agents.conductor.use_cases.decompose import split_by_role


def create_audit_team(
    spec_content: str,
    budget: int = 5000,
) -> ConductorTask:
    """Create a ConductorTask to audit an OpenAPI spec across multiple dimensions.

    Args:
        spec_content: The raw OpenAPI spec YAML/JSON string.
        budget: Token budget per auditor.

    Returns:
        A ConductorTask configured for a multi-dimensional spec audit.
    """
    roles = [
        "Security Architect (focus on auth, rate limiting, and input validation)",
        "API Designer (focus on REST conventions, naming, and pagination)",
        "Documentation Specialist (focus on descriptions, examples, and clarity)",
    ]

    instruction = (
        "Audit the following OpenAPI specification.\n\n"
        f"```\n{spec_content}\n```"
    )

    sub_tasks = split_by_role(
        base_instruction=instruction,
        roles=roles,
        budget_per_role=budget,
    )

    return ConductorTask(
        objective="Multi-dimensional OpenAPI spec audit",
        payload={"spec": spec_content},
        sub_tasks=sub_tasks,
        merge_strategy=MergeStrategy.UNION,
        global_timeout_seconds=300,
    )
