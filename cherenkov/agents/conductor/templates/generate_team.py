"""Generate team template for Conductor (CC-2)."""
from __future__ import annotations

from cherenkov.agents.conductor.domain.models import ConductorTask, MergeStrategy
from cherenkov.agents.conductor.use_cases.decompose import split_by_item


def create_generate_team(
    openapi_spec: dict,
    endpoints: list[str],
    budget_per_endpoint: int = 15000,
) -> ConductorTask:
    """Create a ConductorTask to generate tests for multiple endpoints in parallel.

    Args:
        openapi_spec: The parsed OpenAPI spec dictionary.
        endpoints: List of endpoint paths to generate tests for.
        budget_per_endpoint: Token budget for each endpoint generation.

    Returns:
        A ConductorTask configured for parallel test generation.
    """
    instruction_template = (
        "Generate a Playwright conformance test for the following endpoint:\n"
        "Endpoint: {item}\n\n"
        "Ensure the test covers happy paths and 4xx errors as defined in the spec."
    )

    sub_tasks = split_by_item(
        instruction_template=instruction_template,
        items=endpoints,
        context={"spec": openapi_spec},
        budget_per_item=budget_per_endpoint,
    )

    return ConductorTask(
        objective="Parallel API test generation",
        payload={"endpoints": endpoints},
        sub_tasks=sub_tasks,
        merge_strategy=MergeStrategy.UNION,
        global_timeout_seconds=600,
    )
