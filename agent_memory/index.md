# CHERENKOV Agent Memory Wiki

Welcome to the Agent Memory Wiki (`agent_memory/`). This directory solves "AI amnesia" by serving as a persistent, compounding knowledge base for CHERENKOV autonomous agents.

## Standard Operating Procedure

1. **Read Before Crawling**: Agents MUST read this index and relevant sub-pages before beginning an exploration or testing task to understand historical context, known bugs, and current application state.
2. **Write After Task**: Agents MUST document their findings, updated states, and newly discovered endpoints/UI components back into this directory upon task completion.
3. **Link Everything**: Build cross-references between pages (e.g., linking a discovered `500 Server Error` to an `endpoint-auth.md` concept page).

## Global Context
*   **Current Framework Focus**: `PydanticAI` for orchestration, `DeepEval` for testing, `Logfire` for tracing.
*   **Vision Model**: Ready for MiniGPT/Qwen-VL integration for UI audits.

*(Agents: create new markdown files in this directory to track specific application flows, bugs, or component states.)*
