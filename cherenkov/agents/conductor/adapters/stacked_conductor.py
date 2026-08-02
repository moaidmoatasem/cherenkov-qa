"""Stacked PR Conductor implementation for CHERENKOV (CC-2 extension)."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from cherenkov.agents.conductor.domain.models import (
    ConductorResult,
    PRSubTask,
    StackedPRTask,
    StackStrategy,
    SubAgentResult,
    SubAgentTask,
)
from cherenkov.mcp.mesh_router import get_registry

_log = logging.getLogger(__name__)


class StackedPRConductor:
    """Coordinates multi-layer PR stacks with SDD context inheritance."""

    def __init__(
        self,
        repo_root: str | None = None,
        mcp_target_tool: str = "run_sub_agent_task",
    ):
        """Initialize the conductor with repository context.

        Args:
            repo_root: Project root directory (defaults to CHERENKOV_ROOT env var).
            mcp_target_tool: MCP tool name for sub-agent execution.
        """
        self.repo_root = Path(repo_root) if repo_root else Path(
            os.environ.get("CHERENKOV_ROOT", Path.cwd().parent)
        )
        self.target_tool_name = mcp_target_tool
        self.registry = get_registry()

    def orchestrate_stack(
        self, epic_issue_id: str, title: str, strategy: StackStrategy, layers: list[PRSubTask]
    ) -> StackedPRTask:
        """Generate a complete StackedPRTask with topological PR ordering.

        Args:
            epic_issue_id: GitHub issue ID for tracking.
            title: Human-readable title for the stack.
            strategy: Stack slicing strategy.
            layers: Individual layer specifications (must be sorted by layer_index).

        Returns:
            A fully configured StackedPRTask ready for execution.
        """
        layers = sorted(layers, key=lambda x: x.layer_index)

        # Apply strategy-specific orchestration
        if strategy == StackStrategy.FUNCTIONAL:
            self._orchestrate_functional(layers)
        elif strategy == StackStrategy.REFACTOR_FIRST:
            self._orchestrate_refactor_first(layers)
        elif strategy == StackStrategy.RISK_ISOLATED:
            self._orchestrate_risk_isolated(layers)

        stacked_task = StackedPRTask(
            epic_issue_id=epic_issue_id,
            title=title,
            strategy=strategy,
            layers=layers,
        )

        _log.info(
            "Generated StackedPRTask %s with %d layers",
            stacked_task.stack_id,
            len(stacked_task.layers),
        )
        return stacked_task

    def _orchestrate_functional(self, layers: list[PRSubTask]) -> None:
        """Apply functional layering: contracts -> adapters -> use_cases -> api -> tests."""
        for i, layer in enumerate(layers):
            if i == 0:
                layer.layer_name = "01-contracts"
                layer.branch_name = f"feat/{layer.layer_name}"
                layer.base_branch = "main"
            else:
                layer.layer_name = f"{i+1:02d}-functional"
                layer.branch_name = f"feat/{layer.layer_name}"
                layer.base_branch = f"feat/{(i-1):02d}-functional"

    def _orchestrate_refactor_first(self, layers: list[PRSubTask]) -> None:
        """Interleave refactor and feature layers."""
        refactor_count = sum(1 for l in layers if l.instruction.startswith("refactor"))
        feature_count = len(layers) - refactor_count

        for i, layer in enumerate(layers):
            if layer.instruction.startswith("refactor"):
                layer.layer_name = f"{i+1:02d}-refactor"
                layer.branch_name = f"refactor/{layer.layer_name}"
                layer.base_branch = "main"
            else:
                layer.layer_name = f"{i+1:02d}-feature"
                layer.branch_name = f"feat/{layer.layer_name}"
                layer.base_branch = f"refactor/{(i if i > 0 else 0):02d}-refactor"

    def _orchestrate_risk_isolated(self, layers: list[PRSubTask]) -> None:
        """Isolate high-risk elements into dedicated layers."""
        risk_layers = [l for l in layers if l.instruction.startswith(("auth", "security", "payment"))]
        normal_layers = [l for l in layers if l not in risk_layers]

        combined = []
        for i, layer in enumerate(risk_layers + normal_layers):
            layer.layer_name = f"{i+1:02d}-{'risk' if i < len(risk_layers) else 'normal'}"
            layer.branch_name = f"{layer.layer_name}"
            layer.base_branch = "main" if i == 0 else f"{(i-1):02d}-{'risk' if i-1 < len(risk_layers) else 'normal'}"
            combined.append(layer)

        layers.clear()
        layers.extend(combined)

    def execute_stack(self, stacked_task: StackedPRTask) -> ConductorResult:
        """Execute the stack in topological order, layer by layer.

        Each layer's sub-task receives the complete context and artifacts from
        the previous layer, preserving full continuity across the stack.
        """
        _log.info(
            "Executing StackedPRTask %s with %d layers",
            stacked_task.stack_id,
            len(stacked_task.layers),
        )

        aggregated_outputs: list[dict[str, Any]] = []
        all_sub_results: list[SubAgentResult] = []
        total_tokens = 0

        for i, layer in enumerate(stacked_task.layers):
            _log.info("Executing layer %s: %s", layer.layer_name, layer.instruction)

            sub_task = SubAgentTask(
                instruction=layer.instruction,
                context=self._build_layer_context(layer, stacked_task, aggregated_outputs),
                budget=layer.sdd_budget,
            )

            try:
                result = self._run_sub_agent_task(sub_task)
                aggregated_outputs.append(result.output)
                all_sub_results.append(result)
                total_tokens += result.tokens_used

                _log.info(
                    "Layer %s completed with status: %s",
                    layer.layer_name,
                    result.status,
                )

            except Exception as e:
                _log.error("Layer %s failed: %s", layer.layer_name, e)
                all_sub_results.append(
                    SubAgentResult(
                        task_id=sub_task.task_id,
                        agent_id="conductor",
                        status="failed",
                        output=None,
                        error_message=str(e),
                    )
                )
                aggregated_outputs.append(None)

        # Determine overall stack status based on individual layer results
        failed = sum(1 for r in all_sub_results if r.status != "success")
        if failed == 0:
            status = "success"
        elif failed < len(all_sub_results):
            status = "partial"
        else:
            status = "failed"

        return ConductorResult(
            task_id=stacked_task.stack_id,
            status=status,
            aggregated_output=aggregated_outputs,
            sub_results=all_sub_results,
            total_tokens_used=total_tokens,
        )

    def _build_layer_context(
        self,
        layer: PRSubTask,
        stacked_task: StackedPRTask,
        previous_outputs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Construct context for the current layer based on previous layers."""
        context = {
            "stack_id": stacked_task.stack_id,
            "epic_issue_id": stacked_task.epic_issue_id,
            "layer_index": layer.layer_index,
            "layer_name": layer.layer_name,
            "layer_instruction": layer.instruction,
            "target_paths": layer.target_paths,
            "base_branch": layer.base_branch,
        }

        # Include outputs from previous layers (architectural artifacts)
        if previous_outputs:
            context["layer_previous_outputs"] = previous_outputs[-1]
            context["stack_complete_outputs"] = previous_outputs

        # Inject SDD context for this layer
        sdd_context_path = self.repo_root / "agent_memory" / "sync" / "context.json"
        if sdd_context_path.exists():
            with open(sdd_context_path) as f:
                context["sdd_context"] = json.load(f)

        return context

    def _run_sub_agent_task(self, sub_task: SubAgentTask) -> SubAgentResult:
        """Execute a single sub-agent task via the MCP mesh."""
        arguments = {
            "instruction": sub_task.instruction,
            "context": sub_task.context,
            "budget": sub_task.budget,
        }

        try:
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


# Convenience function for creating and executing a stack in one call
def create_and_execute_stack(
    epic_issue_id: str,
    title: str,
    strategy: StackStrategy,
    layers: list[PRSubTask],
    repo_root: str | None = None,
) -> ConductorResult:
    """High-level convenience function for creating and executing a stack."""
    conductor = StackedPRConductor(repo_root=repo_root)
    stacked_task = conductor.orchestrate_stack(epic_issue_id, title, strategy, layers)
    return conductor.execute_stack(stacked_task)
