"""Result aggregation strategies for the Conductor (CC-2)."""
from __future__ import annotations

from collections import Counter
from typing import Any

from cherenkov.agents.conductor.domain.models import MergeStrategy, SubAgentResult


def aggregate_results(results: list[SubAgentResult], strategy: MergeStrategy) -> Any:
    """Aggregate multiple SubAgentResults into a single output based on the strategy.

    Args:
        results: The list of results returned from parallel sub-agents.
        strategy: The MergeStrategy to apply.

    Returns:
        The aggregated output payload.
    """
    successful_results = [r for r in results if r.status == "success" and r.output is not None]

    if not successful_results:
        return None

    if strategy == MergeStrategy.UNION:
        # If output is a list, extend it. If dict, update it. Otherwise, collect in list.
        first_output = successful_results[0].output
        if isinstance(first_output, list):
            aggregated_list = []
            for r in successful_results:
                if isinstance(r.output, list):
                    aggregated_list.extend(r.output)
                else:
                    aggregated_list.append(r.output)
            return aggregated_list
        if isinstance(first_output, dict):
            aggregated_dict = {}
            for r in successful_results:
                if isinstance(r.output, dict):
                    aggregated_dict.update(r.output)
            return aggregated_dict
        return [r.output for r in successful_results]

    if strategy == MergeStrategy.CONSENSUS:
        # Find the most common output (requires hashable outputs like strings or tuples).
        # Fallback to list collection if not hashable.
        try:
            counts = Counter(r.output for r in successful_results)
            most_common, _ = counts.most_common(1)[0]
            return most_common
        except TypeError:
            # Unhashable type
            return [r.output for r in successful_results]

    elif strategy == MergeStrategy.WEIGHTED:
        # Placeholder for weighted aggregation (e.g. LLM judge evaluating results)
        # Defaults to returning the union for now.
        return [r.output for r in successful_results]

    return None
