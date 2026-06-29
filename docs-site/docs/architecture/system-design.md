---
title: System Design
description: CHERENKOV-QA system design — module layers, dependency graph, Clean Architecture overview.
---

# System Design

CHERENKOV-QA follows Clean Architecture (Ports/Adapters pattern, ADR-004). Dependencies flow strictly inward — outer layers depend on inner layers, never the reverse.

---

## Module Dependency Layers

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACES (web/, mcp/, chat/, copilot/)                   │
├─────────────────────────────────────────────────────────────┤
│  EXTENDED CAPABILITIES                                       │
│  governance/ · federation/ · divergence/ · compliance/      │
│  continuity/ · openclaw/ · sdet/ · rag/                     │
├─────────────────────────────────────────────────────────────┤
│  DOMAIN SERVICES                                            │
│  healing/ · coverage/ · reflector/ · hitl/ · truth/         │
│  knowledge/ · oracle/ · sources/ · validate/                │
├─────────────────────────────────────────────────────────────┤
│  PIPELINE STAGES                                            │
│  stages/ · execution/                                       │
├─────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                             │
│  ai/ · substrate/ · security/ · ports/ · dashboard/        │
├─────────────────────────────────────────────────────────────┤
│  CORE (no upstream deps)                                    │
│  core/contracts.py · core/config.py · core/orchestrator.py │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Modules

| Module | Purpose | Location |
|--------|---------|----------|
| `core/` | Orchestrator, config, contracts, errors | `cherenkov/core/` |
| `substrate/` | Model providers, routing, certification | `cherenkov/substrate/` |
| `stages/` | Pipeline stages (ingest, plan, generate, review) | `cherenkov/stages/` |
| `execution/` | Test execution, ejection | `cherenkov/execution/` |
| `healing/` | Failure diagnosis, suggestions | `cherenkov/healing/` |

---

## Extended Modules

| Module | Phase | Purpose |
|--------|-------|---------|
| `knowledge/` | Phase 1 | GraphRAG second brain — verdicts, idioms, incidents |
| `ai/substrate/` | Phase 2 | LocalAI/VLM tier routing |
| `chat/` | Phase 4 | Tool-calling agent, SSE streaming, persona registry |
| `mobile/` | Phase 5-6 | Maestro/Appium device execution |
| `memory/` | CC-1 | SQLite FTS5 auto-memory |
| `hooks/` | CC-1 | HookRegistry, SubprocessHookExecutor |
| `agents/conductor/` | CC-2 | Multi-agent fan-out/fan-in |

---

## Key Design Decisions

| Decision | ADR | Choice |
|----------|-----|--------|
| Clean Architecture | [ADR-004](clean-architecture.md) | Ports/Adapters, no framework coupling in domain |
| Event-driven coordination | ADR-005 | EventBus (asyncio.Queue → Redis Streams) |
| Knowledge storage | ADR-006 | SQLite (default) + Redis (upgrade path) |
| VLM/LLM routing | ADR-003 | LocalAI as default, tier-aware (small/deep/vision) |
| Multi-agent protocol | ADR-013 | MCP JSON-RPC 2.0 mesh |
| Memory storage | ADR-011 | SQLite FTS5 with auto-promote |
| Hook execution | ADR-012 | cherenkov.toml defined, warn/abort fail modes |

---

## System Context

```
┌─────────────────────────────────────┐
│  CHERENKOV-QA                       │
│  - API conformance testing          │
│  - Mobile testing (Maestro/Appium)  │
│  - Chat agents (tool-calling)       │
│  - Second Brain (knowledge mesh)    │
│  - Desktop host (Tauri 2)           │
└──────────────┬──────────────────────┘
               │
               ├─→ OpenAPI specs (input)
               ├─→ Target APIs (validation)
               ├─→ LocalAI/Ollama (LLM)
               ├─→ Redis (optional, vector search)
               ├─→ Docker (optional, LocalAI)
               ├─→ Maestro/Appium (mobile testing)
               └─→ Playwright (test execution)
```

---

## Most-Imported Modules

Demand on each module (import count across codebase):

| Module | Count | Role |
|--------|-------|------|
| `core` | 203 | Foundation — most imported |
| `ai` | 34 | LLM clients |
| `substrate` | 29 | Model routing |
| `knowledge` | 25 | GraphRAG mesh |
| `stages` | 23 | Pipeline stage definitions |
| `reflector` | 22 | Verdict memory + suppression |
