# Capability Matrix: Qwen Code vs CHERENKOV

| Feature | Qwen Code | CHERENKOV |
|---------|-----------|-----------|
| Focus | General-purpose coding, planning | Spec-driven QA, test execution, governance |
| Architecture | JS/TS, Auto-memory, Tool/MCP client | Python, Ports/Adapters, MCP Server |
| Memory | `.qwen/memory/` | `agent_memory/sync/` (SQLite + FTS5) |
| SDD | Not built-in | Built-in via `agent_sync.py` |
| Test Gen | Prompt-based | Spec-driven (via API) |
| Gate Enforcement | No | Yes (6-gate review) |

## Alignment Strategy
1. **MCP**: Qwen Code connects to CHERENKOV via MCP to fetch spec knowledge and trigger test validation.
2. **Tokens**: Qwen Code delegates its memory to CHERENKOV's FTS5 store via bridging scripts to avoid diverging memories.
3. **SDD Diff**: Qwen Code's Auto-Memory is static seed-driven, whereas CHERENKOV's SDD is event-driven. We merge them via `memory_sync.py`.
