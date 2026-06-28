"""MCP-based implementation of the AgentConductor (CC-2, ADR-013)."""
from __future__ import annotations

import concurrent.futures
import logging
import time

from cherenkov.agents.conductor.domain.models import (
    ConductorResult,
    ConductorTask,
    SubAgentResult,
    SubAgentTask,
)
from cherenkov.mcp.mesh_router import get_registry

_log = logging.getLogger(__name__)


class MCPConductor:
    """AgentConductor that fans out tasks via the MCP mesh router."""

    def __init__(self, target_tool_name: str = "run_sub_agent_task"):
        """Initialize the conductor.

        Args:
            target_tool_name: The MCP tool name to call for each sub-task.
                The registered MCP server must expose this tool.
        """
        self.target_tool_name = target_tool_name
        self.registry = get_registry()

    def execute(self, task: ConductorTask) -> ConductorResult:
        """Run the conductor task and return the aggregated result."""
        _log.info(
            "Conductor starting task %r with %d sub-tasks (strategy=%s)",
            task.task_id,
            len(task.sub_tasks),
            task.merge_strategy.value,
        )

        start_time = time.time()
        results: list[SubAgentResult] = []

        # Fan-out: execute sub-tasks in parallel using a thread pool.
        # In a fully asynchronous stack this would use asyncio.gather,
        # but the MCPClient uses synchronous requests for now.
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(task.sub_tasks) or 1) as executor:
            future_to_task = {
                executor.submit(self._run_sub_task, sub_task, task.global_timeout_seconds): sub_task
                for sub_task in task.sub_tasks
            }
            for future in concurrent.futures.as_completed(future_to_task):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    sub_task = future_to_task[future]
                    _log.error("Sub-task %s failed with exception: %s", sub_task.task_id, exc)
                    results.append(
                        SubAgentResult(
                            task_id=sub_task.task_id,
                            agent_id="unknown",
                            status="failed",
                            output=None,
                            error_message=str(exc),
                        )
                    )

        duration = time.time() - start_time
        _log.info("Conductor completed in %.2fs", duration)

        total_tokens = sum(r.tokens_used for r in results)

        # Basic aggregation logic delegates to the use cases (which we will wire in shortly),
        # but for now we'll do a simple gather.
        from cherenkov.agents.conductor.use_cases.aggregate import aggregate_results

        aggregated_output = aggregate_results(results, task.merge_strategy)

        # Determine overall status
        failed = sum(1 for r in results if r.status != "success")
        if failed == 0:
            status = "success"
        elif failed < len(results):
            status = "partial"
        else:
            status = "failed"

        return ConductorResult(
            task_id=task.task_id,
            status=status,
            aggregated_output=aggregated_output,
            sub_results=results,
            total_tokens_used=total_tokens,
        )

    def _run_sub_task(self, sub_task: SubAgentTask, _timeout: int) -> SubAgentResult:
        """Execute a single sub-task via the MCP registry."""
        arguments = {
            "instruction": sub_task.instruction,
            "context": sub_task.context,
            "budget": sub_task.budget,
        }

        try:
            # We enforce the global timeout implicitly here or assume the underlying
            # MCPClient handles its own read timeout.
            raw_result = self.registry.forward_tool_call(self.target_tool_name, arguments)

            if raw_result is None:
                return SubAgentResult(
                    task_id=sub_task.task_id,
                    agent_id="none",
                    status="failed",
                    output=None,
                    error_message=f"No MCP server registered for tool '{self.target_tool_name}'",
                )

            return SubAgentResult(
                task_id=sub_task.task_id,
                agent_id=raw_result.get("agent_id", "mcp_agent"),
                status=raw_result.get("status", "success"),
                output=raw_result.get("output"),
                tokens_used=raw_result.get("tokens_used", 0),
                error_message=raw_result.get("error_message"),
            )
        except Exception as exc:
            return SubAgentResult(
                task_id=sub_task.task_id,
                agent_id="none",
                status="failed",
                output=None,
                error_message=f"Transport error: {exc}",
            )
