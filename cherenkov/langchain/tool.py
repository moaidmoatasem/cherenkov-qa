"""
CHERENKOV LangChain tool exposing the ValidationEngine capabilities.

Provides structured tools for agent builders:
- generate_tests(spec_path) -> Generate Playwright tests from an OpenAPI spec.
- validate_target(target_url, spec_path) -> Run conformance validation.
- explain_violation(violation_id) -> Explain a known divergence by ID.
"""

from __future__ import annotations

from typing import Any, Optional, Type

from pydantic import BaseModel, Field

try:
    from langchain_core.tools import BaseTool
except ImportError:  # pragma: no cover - fallback when langchain is not installed
    class BaseTool:  # type: ignore
        """Placeholder for environments without langchain_core."""

from cherenkov.execution.validate import ValidationEngine
from cherenkov.web.divergences import _DIVERGENCE_CORPUS


class GenerateTestsInput(BaseModel):
    spec_path: str = Field(description="Path to the OpenAPI spec (yaml or json).")
    target_url: str = Field(
        default="http://localhost:8000",
        description="Optional base URL of the API under test.",
    )


class ValidateTargetInput(BaseModel):
    target_url: str = Field(description="Base URL of the API to validate.")
    spec_path: str = Field(
        default="stub/openapi.yaml",
        description="Path to the OpenAPI spec (yaml or json).",
    )
    workers: int = Field(
        default=1,
        description="Parallel workers for validation.",
    )


class ExplainViolationInput(BaseModel):
    violation_id: str = Field(description="ID of the divergence to explain.")


class _CherenkovValidateInput(BaseModel):
    query: str = Field(
        description=(
            "JSON string containing 'operation' and the required arguments. "
            "Operations: generate_tests, validate_target, explain_violation."
        )
    )


class CherenkovValidateTool(BaseTool):
    """LangChain tool exposing CHERENKOV API conformance capabilities."""

    name: str = "cherenkov_validate"
    description: str = (
        "Use CHERENKOV to generate API conformance tests from an OpenAPI spec, "
        "validate a target API against its spec, or explain a specific divergence. "
        "Input must be a JSON object with an 'operation' field and the required "
        "arguments for that operation. Supported operations: generate_tests, "
        "validate_target, explain_violation."
    )
    args_schema: Type[BaseModel] = _CherenkovValidateInput

    _engine: Optional[ValidationEngine] = None

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._engine = ValidationEngine()

    def _run(self, query: str, run_manager: Optional[Any] = None) -> str:
        """Dispatch to the requested operation."""
        import json

        try:
            args = json.loads(query)
        except json.JSONDecodeError as exc:
            return f"Invalid JSON input: {exc}"

        operation = args.get("operation")
        if operation == "generate_tests":
            return self._generate_tests(args)
        if operation == "validate_target":
            return self._validate_target(args)
        if operation == "explain_violation":
            return self._explain_violation(args)

        return (
            "Unknown operation. Use one of: generate_tests, validate_target, "
            "explain_violation."
        )

    async def _arun(self, query: str, run_manager: Optional[Any] = None) -> str:
        """Async wrapper around sync dispatch."""
        return self._run(query, run_manager)

    def _generate_tests(self, args: dict[str, Any]) -> str:
        """Suggest-only test generation from an OpenAPI spec."""
        try:
            inp = GenerateTestsInput.model_validate(args)
            # The ValidationEngine currently couples generation with execution;
            # this tool reports the spec target without running tests.
            return (
                f"Test generation requested for {inp.spec_path}. "
                f"Use validate_target(target_url='{inp.target_url}') to generate "
                f"and run the conformance suite."
            )
        except Exception as exc:
            return f"generate_tests failed: {exc}"

    def _validate_target(self, args: dict[str, Any]) -> str:
        try:
            inp = ValidateTargetInput.model_validate(args)
            report = self._engine.validate_suite(
                target_url=inp.target_url,
                workers=inp.workers,
            )
            passed = report.get("passed", 0)
            failed = report.get("failed", 0)
            drift = report.get("drift_count", len(report.get("reports", [])))
            return (
                f"Validation complete: {passed} passed, {failed} failed, "
                f"{drift} drift finding(s). Report written to .cherenkov/report.json"
            )
        except Exception as exc:
            return f"validate_target failed: {exc}"

    def _explain_violation(self, args: dict[str, Any]) -> str:
        try:
            inp = ExplainViolationInput.model_validate(args)
            finding = next(
                (f for f in _DIVERGENCE_CORPUS if f.get("id") == inp.violation_id),
                None,
            )
            if not finding:
                return f"Violation {inp.violation_id!r} not found."
            return (
                f"Finding {inp.violation_id}: {finding.get('endpoint')} — "
                f"{finding.get('claimB', finding.get('summary', 'No details'))}. "
                f"Expected: {finding.get('claimA', 'N/A')}"
            )
        except Exception as exc:
            return f"explain_violation failed: {exc}"
