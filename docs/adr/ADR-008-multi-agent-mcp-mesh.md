# ADR-008: Multi-Agent MCP Mesh

**Date:** 2026-06-14
**Status:** Accepted

## Context

As CHERENKOV QA scales beyond a single-purpose CLI testing tool, the software testing paradigm is shifting toward a "Mesh" of specialized agents. Different capabilities—such as DAST security scanning, k6 performance testing, accessibility validation, and functional API testing—require distinct models, contexts, and runtimes.

Currently, CHERENKOV integrates knowledge internally via a monolithic Chat Agent (Phase 4). However, tightly coupling external agents (or external IDEs like Cursor and GitHub Copilot) directly into our core codebase violates the open-architecture principles of the project and creates unmanageable maintenance overhead. We need a standardized way to share context (GraphRAG index) and expose tools to an ecosystem of agents.

## Decision

We will implement a **Multi-Agent MCP (Model Context Protocol) Mesh**.

1. **CHERENKOV as an MCP Server**: We will upgrade the existing `cherenkov.mcp.server` to expose the full suite of CHERENKOV capabilities (test generation, execution, healing, GraphRAG querying) via the standardized Anthropic MCP protocol (JSON-RPC over stdio/SSE).
2. **Mesh Router Module**: We will introduce a new `MeshRouter` component (`cherenkov/mcp/mesh_router.py`) that handles capability discovery, rate limiting, and access control for external agents.
3. **Playwright MCP Standard**: We will deprecate custom visual processing loops for web testing and standardize on the open-source **Playwright MCP** schema, allowing agents to interact with the DOM via semantic accessibility trees rather than token-heavy screenshots.

## Consequences

### Positive
- **Ecosystem Extensibility**: Any external agent (Claude Desktop, custom enterprise agents) can plug into CHERENKOV natively without custom integration code.
- **Token Efficiency**: Moving to Playwright MCP for browser interaction reduces token usage by 10x-100x compared to visual oracles.
- **Separation of Concerns**: Security and Performance agents can remain entirely separate projects, only interacting with CHERENKOV's API test payloads via the MCP interface.

### Negative
- **Operational Complexity**: Maintaining a robust MCP server requires strict schema versioning and robust error handling to prevent external agents from crashing the server.
- **Security Posture**: Exposing execution tools via MCP necessitates an explicit RBAC/Permission layer to prevent malicious agents from running destructive OS commands. (Addressed via strict tool constraints).
