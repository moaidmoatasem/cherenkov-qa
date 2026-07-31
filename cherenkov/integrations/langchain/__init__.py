"""
LangChain Integration for CHERENKOV QA.

Provides LangChain-compatible tools for exposing CHERENKOV capabilities to AI agents.

Requires: pip install langchain-core

Usage::

    from cherenkov.integrations.langchain import get_langchain_tools
    tools = get_langchain_tools()

    # Or use the standalone functions directly:
    from cherenkov.integrations.langchain import validate_endpoint
    result = validate_endpoint("http://localhost:8000", "openapi.yaml")
"""

from .tools import (
    CherenkovTool,
    validate_endpoint,
    generate_tests,
    explain_violation,
    get_langchain_tools,
    GenerateTestsInput,
    ValidateInput,
    ExplainViolationInput,
)

__all__ = [
    "CherenkovTool",
    "validate_endpoint",
    "generate_tests",
    "explain_violation",
    "get_langchain_tools",
    "GenerateTestsInput",
    "ValidateInput",
    "ExplainViolationInput",
]
