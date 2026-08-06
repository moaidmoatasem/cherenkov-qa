---
title: LangChain Integration
description: Use CHERENKOV-QA as a LangChain tool inside AI agents. Generate tests, validate APIs, and explain violations programmatically.
---

# LangChain Integration

CHERENKOV provides LangChain-compatible tools so you can embed API conformance testing inside AI agent workflows. An agent can generate tests, run validations, and explain violations — all as tool calls.

---

## Prerequisites

`langchain-core` is a core dependency of CHERENKOV. Install it with the LangChain extras:

```bash
git clone https://github.com/moaidmoatasem/cherenkov-qa.git && cd cherenkov-qa
pip install -e .
pip install langchain-core
```

---

## Quick Start

```python
from cherenkov.integrations.langchain.tools import CherenkovTool

# Create the tool — it wraps generate, validate, and explain actions
tool = CherenkovTool()

# Use it in a LangChain agent
from langchain_core.agents import AgentExecutor

agent = AgentExecutor(
    tools=[tool],
    # ... your agent config
)
```

---

## Available Actions

The `CherenkovTool` is a single LangChain `BaseTool` that dispatches to different CHERENKOV actions based on the `action` parameter.

### `generate_tests`

Generate Playwright E2E tests from an OpenAPI specification.

```python
result = tool._run(
    action="generate_tests",
    spec_path="./openapi.yaml",
    output_dir="./tests/generated"
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `spec_path` | `str` | (required) | Path to the OpenAPI spec (YAML or JSON) |
| `output_dir` | `str` | `stub/generated_tests` | Directory to save generated test files |

### `validate`

Validate a live API against its OpenAPI specification.

```python
result = tool._run(
    action="validate",
    target_url="http://localhost:8080",
    spec_path="./openapi.yaml",
    env="staging"
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_url` | `str` | (required) | URL of the API to validate |
| `spec_path` | `str` | (required) | Path to the OpenAPI spec |
| `env` | `str` | `dev` | Target environment label |

### `explain_violation`

Get a natural-language explanation of a conformance violation.

```python
result = tool._run(
    action="explain_violation",
    violation_id="GET /pets/{petId} returned 404 instead of 200",
    context="The pet was just created in the previous test"
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `violation_id` | `str` | (required) | The violation ID or message |
| `context` | `str` | `""` | Additional context about the failure |

---

## Using with a LangChain Agent

Here is a complete example that creates a LangChain agent capable of testing APIs:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from cherenkov.integrations.langchain.tools import CherenkovTool

# Create the CHERENKOV tool
cherenkov = CherenkovTool()

# Define a prompt that teaches the agent about CHERENKOV
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a QA assistant. You can:
    1. Generate tests from OpenAPI specs (action: generate_tests)
    2. Validate live APIs against specs (action: validate)
    3. Explain conformance violations (action: explain_violation)
    
    Always validate after generating tests to catch drift."""),
    ("human", "{input}"),
])

# Build the agent with your preferred LLM
from langchain_community.llms import Ollama

llm = Ollama(model="qwen2.5-coder:7b")

# Use with any LangChain agent framework
# (AgentExecutor, LangGraph, etc.)
```

---

## Input Schemas

The tool uses Pydantic models for input validation. These are available for type checking:

```python
from cherenkov.integrations.langchain.tools import (
    GenerateTestsInput,
    ValidateInput,
    ExplainViolationInput,
)

# Use in typed code
input_data = GenerateTestsInput(
    spec_path="./openapi.yaml",
    output_dir="./tests"
)
```

---

## Limitations

- **Async not supported** — `CherenkovTool._arun()` raises `NotImplementedError`. Use synchronous execution only.
- **Local execution** — the tool runs CHERENKOV locally. The LLM provider configured in your environment (Ollama by default) must be available.
- **Single tool pattern** — all three actions are bundled into one tool. This works well with most agents but may require explicit action routing in some frameworks.

---

## Next Steps

- [Test Generation & Repair](../guides/test-generation.md) — understand what `generate_tests` does under the hood
- [API Conformance Testing](../guides/api-conformance.md) — understand what `validate` does
- [MCP Integration](mcp.md) — alternative integration via Model Context Protocol
- [Configuration](../getting-started/configuration.md) — configure the LLM provider the tool uses
