# SubAgent per Spec Workflow

## Context
When dealing with a large repository of OpenAPI specs (e.g., Stripe's 800+ endpoints), generating tests for all of them in a single Qwen Code session exceeds the context window and token budget.

## Solution: Qwen Code SubAgents + CHERENKOV Mesh
We can combine Qwen Code's SubAgent capabilities with CHERENKOV's Multi-Agent Mesh (ADR-008).

### Workflow
1. The **Main Qwen Code Agent** scans the `specs/` directory.
2. For each `spec_*.json` file, it spawns a SubAgent:
   ```bash
   qwen --agent subagent_test_gen -p "Process specs/stripe_spec.json"
   ```
3. The **SubAgent**:
   - Reads the specific spec file.
   - Calls the `api-test-gen` skill to generate standalone Python tests.
   - Saves the tests in `tests/generated/stripe/`.
   - Calls the `run_conformance_check` MCP tool to verify the tests compile and run against the spec.
   - Reports back to the Main Agent.
4. The **Main Agent** aggregates the results and updates the `agent_memory/sync/` token counts.

## Benefits
- **Token Efficiency**: Each SubAgent only loads the context it needs.
- **Parallelism**: SubAgents can run concurrently.
- **Isolation**: A hallucination in one SubAgent does not poison the main context.
- **SDD Integration**: Each SubAgent gets a distinct `session_id` in `agent_sync.py`, allowing precise token tracking per spec.
