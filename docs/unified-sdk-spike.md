# Unified SDK Evaluation Spike

## Objective
Evaluate the feasibility of creating a single Python SDK (`cherenkov-qwen-sdk`) that wraps both CHERENKOV's testing/validation APIs and Qwen Code's generation/planning capabilities.

## Current Landscape
1. **CHERENKOV**: Provides a robust internal Python API for running test validations, querying GraphRAG, and interfacing with the Event Bus.
2. **Qwen Code**: Provides an NPM SDK (`@qwen-code/sdk`) and a Python MCP client. It can also be controlled headlessly via `subprocess.run(["qwen", "-p", ...])`.

## Proposed Unified API Surface

```python
from cherenkov_unified import UnifiedAgent

agent = UnifiedAgent(
    test_mode="strict",  # CHERENKOV bounds
    llm="qwen2.5-coder:7b" # Qwen Code backend
)

# Delegates to Qwen Code SubAgent
agent.generate_tests(spec_path="specs/stripe.json", output_dir="tests/stripe/")

# Delegates to CHERENKOV Engine
report = agent.validate(target="http://localhost:8080")

# Cross-agent workflow
if report.failed:
    # CHERENKOV identifies failure -> Qwen Code suggests fix
    suggestions = agent.suggest_fixes(report.failures)
```

## Challenges
1. **Language Barrier**: Qwen Code is Node.js-based. Python bindings must rely on MCP, stdio subprocessing, or HTTP/daemon mode (`qwen serve`).
2. **State Sync**: SDK would need to internally call `agent_sync.py` to maintain SDD protocol compliance across both agents.

## Recommendation
Do NOT build a monolithic SDK package right now. Instead, rely on the **MCP Bridge** (`run_qwen_code_agent` tool and `cherenkov-mcp.yaml`). MCP is language-agnostic and provides the exact loose coupling we need without rebuilding Qwen Code in Python.
