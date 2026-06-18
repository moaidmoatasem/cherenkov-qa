# CHERENKOV QA — Architecture Summary for Qwen Code Auto-Memory

## Project Identity
- **Name**: CHERENKOV QA
- **Type**: Spec-driven API conformance testing framework
- **Language**: Python 3.12 (core), Rust/Tauri (desktop), Go (k8s engine), TypeScript (dashboard)
- **Root**: `/home/moaid/cherenkov-qa/`

## Clean Architecture (ADR-004)
All new modules follow this structure:
```
domain/       ← pure business logic, no I/O
ports/        ← interfaces (abstract classes)
adapters/     ← concrete implementations (HTTP, SQLite, Redis, MCP)
use_cases/    ← orchestration layer
api/          ← CLI + MCP surface
```
Never import adapter code into domain. Never import domain code into adapters.

## Module Map
| Module | Path | Role |
|--------|------|------|
| Core runner | `cherenkov.py` | CLI entrypoint (42K lines) |
| MCP server | `cherenkov/mcp/server.py` | MCP JSON-RPC 2.0 over stdio |
| Engine | `engine/` | Go-based k8s conformance engine |
| Desktop | `desktop/` | Tauri 2 app (308MB binary) |
| Dashboard | `packages/` | TypeScript React dashboard |
| Knowledge | `cherenkov/knowledge/` | GraphRAG + SQLite FTS5 + Redis |

## ADR Summary
| ADR | Decision |
|-----|----------|
| ADR-001 | Seam-widening for test isolation |
| ADR-002 | Tauri 2 as desktop sidecar |
| ADR-003 | LocalAI as default VLM backend; tier-aware routing |
| ADR-004 | Clean architecture (Ports/Adapters) — MANDATORY |
| ADR-005 | Event-driven architecture via internal Event Bus |
| ADR-006 | Knowledge Mesh (SQLite FTS5 + Redis vector + GraphRAG) |
| ADR-007 | QA Reasoning Engine |
| ADR-008 | Multi-agent MCP mesh router |
| ADR-009 | Spec Guardian daemon |

## Phase Status
All phases 0–8 are COMPLETE. Phases 9–16 are roadmap (product/market expansion).

## Key Files for Code Tasks
- `cherenkov.py` — CLI commands, MCP tools, test runner
- `cherenkov-mcp.yaml` — MCP tool registry (18 tools)
- `cherenkov.toml` — Project configuration
- `pyproject.toml` — Python deps
- `Makefile` — `make test`, `make k3d-test`, `make mcp-serve`
