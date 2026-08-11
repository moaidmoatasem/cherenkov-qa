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
    """AgentConductor that fans out tasks via the MCP mesh router.

    Attributes:
        target_tool_name (str): Tool name invoked for sub-tasks.
        registry (MCPRegistry): Mesh router registry instance.
    """

    def __init__(self, target_tool_name: str = "run_sub_agent_task") -> None:
        """Initialize the conductor.

        Args:
            target_tool_name (str): The MCP tool name to call for each sub-task. Defaults to 'run_sub_agent_task'.

        Returns:
            None
        """
        self.target_tool_name = target_tool_name
        self.registry = get_registry()

    def execute(self, task: ConductorTask) -> ConductorResult:
        """Run the conductor task and return the aggregated result.

        Args:
            task (ConductorTask): Top-level task containing sub-agent tasks.

        Returns:
            ConductorResult: Aggregated result object from sub-agent execution.
        """
        _log.info(
            "Conductor starting task %r with %d sub-tasks (strategy=%s)",
            task.task_id,
            len(task.sub_tasks),
            task.merge_strategy.value,
        )

        start_time = time.monotonic()
        results: list[SubAgentResult] = []

        import asyncio

        async def _run_all():
            tasks = [
                asyncio.to_thread(self._run_sub_task, sub_task, task.global_timeout_seconds)
                for sub_task in task.sub_tasks
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)

        try:
            raw_results = asyncio.run(_run_all())
        except RuntimeError:
            # Fallback if event loop is already running
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _run_all())
                raw_results = future.result()

        for i, res in enumerate(raw_results):
            if isinstance(res, Exception):
                sub_task = task.sub_tasks[i]
                _log.error("Sub-task %s failed with exception: %s", sub_task.task_id, res)
                results.append(
                    SubAgentResult(
                        task_id=sub_task.task_id,
                        agent_id="unknown",
                        status="failed",
                        output=None,
                        error_message=str(res),
                    )
                )
            else:
                results.append(res)

        duration = time.monotonic() - start_time
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
        """Execute a single sub-task via the MCP registry.

        Args:
            sub_task (SubAgentTask): Sub-task model to execute.
            _timeout (int): Global timeout setting in seconds.

        Returns:
            SubAgentResult: Sub-agent execution result model.
        """
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

