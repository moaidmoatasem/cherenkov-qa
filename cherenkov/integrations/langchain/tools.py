"""
LangChain Tool classes for exposing CHERENKOV QA capabilities to AI agents.

Install langchain-core to use these tools:
    pip install langchain-core

Or install all LangChain extras with:
    pip install cherenkov-qa[langchain]
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


try:
    from pydantic.v1 import BaseModel, Field
except ImportError:
    from pydantic import BaseModel, Field  # type: ignore[assignment,no-redef]


class GenerateTestsInput(BaseModel):
    spec_path: str = Field(description="Path to the OpenAPI specification file (YAML or JSON).")
    output_dir: str = Field(default="stub/generated_tests", description="Directory to save generated test files.")


class ValidateInput(BaseModel):
    target_url: str = Field(description="The URL of the target API to validate.")
    spec_path: str = Field(description="Path to the OpenAPI specification file.")
    env: str | None = Field(default="dev", description="Target environment.")


class ExplainViolationInput(BaseModel):
    violation_id: str = Field(description="The ID or message of the conformance violation.")
    context: str | None = Field(default="", description="Additional context about the API or the failure.")


def _require_langchain() -> None:
    """Raise a helpful error if langchain-core is not installed."""
    try:
        import langchain_core  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "langchain-core is required to use CHERENKOV LangChain tools. "
            "Install it with: pip install langchain-core"
        ) from exc


class CherenkovTool:
    """
    A LangChain-compatible Tool class that provides access to the full suite of
    CHERENKOV QA engine actions (generate_tests, validate, explain_violation).

    Requires: pip install langchain-core
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> CherenkovTool:
        _require_langchain()
        from langchain_core.tools import BaseTool  # noqa: F401 — deferred import
        return _build_cherenkov_tool()(*args, **kwargs)  # type: ignore[return-value]


def _build_cherenkov_tool():  # type: ignore[return]
    """Build the actual LangChain BaseTool subclass — called only when langchain-core is present."""
    from langchain_core.tools import BaseTool

    class _CherenkovTool(BaseTool):
        name: str = "cherenkov_qa_tool"
        description: str = (
            "A comprehensive QA tool for API testing, test generation, and compliance scanning."
        )

        def _run(self, action: str, **kwargs: Any) -> Any:
            if action == "generate_tests":
                return generate_tests(
                    spec_path=kwargs.get("spec_path", ""),
                    output_dir=kwargs.get("output_dir", "stub/generated_tests"),
                )
            if action == "validate":
                return validate_endpoint(
                    target_url=kwargs.get("target_url", ""),
                    spec_path=kwargs.get("spec_path", ""),
                    env=kwargs.get("env", "dev"),
                )
            return f"Unknown action: {action}"

        async def _arun(self, action: str, **kwargs: Any) -> Any:
            raise NotImplementedError("CherenkovTool does not support async yet.")

    return _CherenkovTool


def generate_tests(spec_path: str, output_dir: str = "stub/generated_tests") -> str:
    """Generate API conformance tests from an OpenAPI specification using CHERENKOV QA.

    Args:
        spec_path: Path to the OpenAPI spec file.
        output_dir: Directory to save generated test files.
    """
    _require_langchain()
    from langchain_core.tools import tool

    @tool("cherenkov_generate_tests", args_schema=GenerateTestsInput)
    def _generate_tests(spec_path: str, output_dir: str = "stub/generated_tests") -> str:
        """Generate API conformance tests from an OpenAPI specification."""
        import os

        try:
            from cherenkov.stages.generate import GenerateStage
            from cherenkov.stages.ingest import IngestStage
            from cherenkov.stages.plan import PlanStage

            ingest_out = IngestStage("langchain_generate").run(spec_path)
            plan_out = PlanStage("langchain_generate").run(ingest_out)
            scenarios = plan_out.scenarios
            ep_map = {f"{ep.path}:{ep.method}": ep for ep in ingest_out.endpoints}

            os.makedirs(output_dir, exist_ok=True)
            success_count = 0
            for sc in scenarios:
                ep = ep_map.get(f"{sc.endpoint}:{sc.method}")
                gen_out = GenerateStage("langchain_generate").run(
                    scenario=sc,
                    path=sc.endpoint,
                    method=sc.method,
                    operation=ep.operation if ep else None,
                    schemas=ep.schemas if ep else None,
                    instruction=getattr(sc, "instruction", ""),
                    source_type="openapi",
                )
                test_file = os.path.join(output_dir, f"{sc.mutation_id}.spec.ts")
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(gen_out.test_code)
                success_count += 1
            return f"Generated {success_count}/{len(scenarios)} test suite(s) in {output_dir}/"
        except Exception as e:
            return f"Error generating tests: {e!s}"

    return _generate_tests.run({"spec_path": spec_path, "output_dir": output_dir})  # type: ignore[return-value]


def validate_endpoint(target_url: str, spec_path: str, env: str = "dev") -> str:
    """Run full CHERENKOV QA validation against a live API endpoint.

    Args:
        target_url: The URL of the target API to validate.
        spec_path: Path to the OpenAPI specification file.
        env: Target environment name.
    """
    _require_langchain()
    try:
        from cherenkov.execution.validate import ValidationEngine

        engine = ValidationEngine(run_id=f"langchain_validate_{env}")
        results = engine.validate_suite(target_url, spec_path=spec_path)
        reports = results.get("reports", [])
        passed = sum(1 for r in reports if r.get("passed"))
        return (
            f"Validation completed. Status: {results.get('status', 'unknown')}. "
            f"{passed}/{len(reports)} scenario(s) passed."
        )
    except Exception as e:
        return f"Error validating endpoint: {e!s}"


def explain_violation(violation_id: str, context: str = "") -> str:
    """Use the CHERENKOV RAG engine to explain an API conformance violation.

    Args:
        violation_id: The violation identifier or message.
        context: Additional context about the API or failure.
    """
    _require_langchain()
    try:
        from cherenkov.knowledge.rag_index import RAGIndex
        rag = RAGIndex()
        res = rag.query_similar_incidents(violation_id + " " + context)
        return f"Explanation for violation '{violation_id}':\n{res}"
    except Exception as e:
        return f"Error explaining violation: {e!s}"


def get_langchain_tools() -> list:
    """
    Return a list of LangChain @tool-decorated callables ready for use
    in a LangChain agent executor.

    Usage::

        from cherenkov.integrations.langchain.tools import get_langchain_tools
        tools = get_langchain_tools()
        agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS)

    Requires: pip install langchain-core
    """
    _require_langchain()
    from langchain_core.tools import tool

    @tool("cherenkov_generate_tests", args_schema=GenerateTestsInput)
    def _gen(spec_path: str, output_dir: str = "stub/generated_tests") -> str:
        """Generate API conformance tests from an OpenAPI specification using CHERENKOV QA."""
        return generate_tests(spec_path, output_dir)

    @tool("cherenkov_validate_endpoint", args_schema=ValidateInput)
    def _val(target_url: str, spec_path: str, env: str = "dev") -> str:
        """Run full CHERENKOV QA validation against a live API endpoint."""
        return validate_endpoint(target_url, spec_path, env)

    @tool("cherenkov_explain_violation", args_schema=ExplainViolationInput)
    def _exp(violation_id: str, context: str = "") -> str:
        """Use CHERENKOV QA to explain the root cause of an API conformance violation."""
        return explain_violation(violation_id, context)

    return [_gen, _val, _exp]


__all__ = [
    "CherenkovTool",
    "ExplainViolationInput",
    "GenerateTestsInput",
    "ValidateInput",
    "explain_violation",
    "generate_tests",
    "get_langchain_tools",
    "validate_endpoint",
]
