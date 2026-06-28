# ADR-013: Agent Conductor Protocol

**Date:** 2026-06-28
**Status:** Accepted
**Phase:** CC-2 (Claude Code-Inspired Enhancements)

## Context

CHERENKOV has a pilot agent (`cherenkov/agents/pilot.py`) capable of running sequential steps, and a robust MCP routing mesh (`cherenkov/mcp/mesh_router.py`). However, for complex QA reasoning tasks, generation tasks, or exhaustive security reviews, sequential processing is too slow.

Inspired by Claude Code's multi-agent Sub-agents concept, we need a mechanism to decompose large tasks, fan out sub-tasks to multiple agents in parallel, and aggregate their results into a cohesive output.

Crucially, ADR-008 already established that all cross-agent and external communications should happen over the MCP mesh. We need a `Conductor` that acts as an orchestrator *on top* of the existing MCP mesh.

## Decision

We will implement an **Agent Conductor Protocol** that provides fan-out/fan-in orchestration for sub-agents:

1. **MCP Substrate:** The Conductor will spawn and communicate with sub-agents by routing requests through the existing `mesh_router.py`. Sub-agents will expose themselves as dynamic MCP servers (or tools on a local meta-server).
2. **Decomposition:** The Conductor will use explicit strategies (e.g., "by endpoint", "by security aspect") to split a `ConductorTask` into multiple `SubAgentTask` payloads.
3. **Budget Caps:** To prevent token explosions (a common risk with multi-agent orchestration), the Conductor will assign strict token budgets to each sub-agent. If a sub-agent exhausts its budget, it is aborted, and the Conductor aggregates whatever partial results it returned.
4. **Aggregation (Fan-in):** Merge strategies (Union, Consensus, Weighted) will reconcile the results from the parallel sub-agents into a final `SubAgentResult`.
5. **Team Templates:** We will define standard "Team" topologies (e.g., `ReviewTeam`, `GenerateTeam`) that pre-configure the decomposition and aggregation logic for common QA workflows.

## Consequences

- **Performance:** Complex validation and generation tasks will complete significantly faster due to parallel execution.
- **Complexity:** Managing parallel agent state, potential hallucination loops, and timeouts requires careful error handling.
- **Cost Control:** Strict budget caps per sub-agent are non-negotiable to maintain operational predictability.
- **Architecture:** `cherenkov/agents/conductor/` will strictly follow the domain/ports/adapters/use_cases Clean Architecture structure.
