"""Unit tests for the Agent Conductor (CC-2)."""
from __future__ import annotations

from cherenkov.agents.conductor.adapters.mcp_conductor import MCPConductor
from cherenkov.agents.conductor.domain.models import (
    ConductorTask,
    MergeStrategy,
    SubAgentResult,
    SubAgentTask,
)
from cherenkov.agents.conductor.templates.review_team import create_review_team
from cherenkov.agents.conductor.use_cases.aggregate import aggregate_results
from cherenkov.agents.conductor.use_cases.decompose import split_by_item, split_by_role


class MockRegistry:
    def __init__(self, responses: dict[str, dict]):
        self.responses = responses
        self.calls = []

    def forward_tool_call(self, tool_name: str, arguments: dict) -> dict | None:
        self.calls.append((tool_name, arguments))
        instr = arguments.get("instruction", "")
        for key, response in self.responses.items():
            if key in instr:
                return response
        return {"agent_id": "default", "status": "success", "output": "ok", "tokens_used": 10}


class TestMCPConductor:
    def test_conductor_executes_sub_tasks_and_aggregates(self, monkeypatch) -> None:
        mock_reg = MockRegistry({
            "agent A": {"agent_id": "a1", "status": "success", "output": ["A"], "tokens_used": 50},
            "agent B": {"agent_id": "b1", "status": "success", "output": ["B"], "tokens_used": 60},
        })
        monkeypatch.setattr("cherenkov.agents.conductor.adapters.mcp_conductor.get_registry", lambda: mock_reg)

        conductor = MCPConductor()
        task = ConductorTask(
            objective="Test Fan-out",
            payload={},
            sub_tasks=[
                SubAgentTask(instruction="I am agent A"),
                SubAgentTask(instruction="I am agent B"),
            ],
            merge_strategy=MergeStrategy.UNION,
        )

        result = conductor.execute(task)

        assert result.status == "success"
        assert result.total_tokens_used == 110
        assert len(result.sub_results) == 2

        # Output could be in any order due to parallel execution
        assert sorted(result.aggregated_output) == ["A", "B"]
        assert len(mock_reg.calls) == 2

    def test_conductor_handles_partial_failures(self, monkeypatch) -> None:
        mock_reg = MockRegistry({
            "agent A": {"agent_id": "a1", "status": "success", "output": "A", "tokens_used": 10},
            "agent B": {"agent_id": "b1", "status": "failed", "error_message": "crash", "tokens_used": 5},
        })
        monkeypatch.setattr("cherenkov.agents.conductor.adapters.mcp_conductor.get_registry", lambda: mock_reg)

        conductor = MCPConductor()
        task = ConductorTask(
            objective="Test Partial",
            payload={},
            sub_tasks=[
                SubAgentTask(instruction="I am agent A"),
                SubAgentTask(instruction="I am agent B"),
            ],
            merge_strategy=MergeStrategy.UNION,
        )

        result = conductor.execute(task)

        assert result.status == "partial"
        assert result.aggregated_output == ["A"]  # only successful results are aggregated
        assert result.total_tokens_used == 15


class TestAggregateResults:
    def test_union_strategy_with_lists(self) -> None:
        results = [
            SubAgentResult(task_id="1", agent_id="a", status="success", output=[1, 2]),
            SubAgentResult(task_id="2", agent_id="b", status="success", output=[3, 4]),
        ]
        assert aggregate_results(results, MergeStrategy.UNION) == [1, 2, 3, 4]

    def test_union_strategy_with_dicts(self) -> None:
        results = [
            SubAgentResult(task_id="1", agent_id="a", status="success", output={"a": 1}),
            SubAgentResult(task_id="2", agent_id="b", status="success", output={"b": 2}),
        ]
        assert aggregate_results(results, MergeStrategy.UNION) == {"a": 1, "b": 2}

    def test_union_strategy_with_strings(self) -> None:
        results = [
            SubAgentResult(task_id="1", agent_id="a", status="success", output="str1"),
            SubAgentResult(task_id="2", agent_id="b", status="success", output="str2"),
        ]
        assert aggregate_results(results, MergeStrategy.UNION) == ["str1", "str2"]

    def test_consensus_strategy(self) -> None:
        results = [
            SubAgentResult(task_id="1", agent_id="a", status="success", output="yes"),
            SubAgentResult(task_id="2", agent_id="b", status="success", output="no"),
            SubAgentResult(task_id="3", agent_id="c", status="success", output="yes"),
        ]
        assert aggregate_results(results, MergeStrategy.CONSENSUS) == "yes"


class TestDecompose:
    def test_split_by_item(self) -> None:
        tasks = split_by_item(
            instruction_template="Check {item}",
            items=["login", "logout"],
            budget_per_item=1000,
        )
        assert len(tasks) == 2
        assert tasks[0].instruction == "Check login"
        assert tasks[0].budget == 1000
        assert tasks[0].context["item"] == "login"
        assert tasks[1].instruction == "Check logout"

    def test_split_by_role(self) -> None:
        tasks = split_by_role(
            base_instruction="Review PR",
            roles=["Security", "Style"],
        )
        assert len(tasks) == 2
        assert "Security" in tasks[0].instruction
        assert "Style" in tasks[1].instruction


class TestTemplates:
    def test_review_team_template(self) -> None:
        task = create_review_team(code_snippet="def foo(): pass")
        assert len(task.sub_tasks) == 3
        roles = [t.context.get("role") for t in task.sub_tasks]
        assert "Security Auditor" in roles
        assert task.merge_strategy == MergeStrategy.UNION
        assert "def foo(): pass" in task.sub_tasks[0].instruction
