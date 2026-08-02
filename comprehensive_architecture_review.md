# Comprehensive Technical & Architecture Review — CHERENKOV-QA

**Document Version:** 1.0.0  
**Date:** 2026-08-02  
**Target System:** CHERENKOV-QA (AI-Native API Testing, Verification & Governance Platform)  
**Project Root:** `Z:\home\moaid\cherenkov-qa`  
**Author:** Worker Architecture Reviewer (`worker_report_writer`)  

---

## Executive Summary

**CHERENKOV-QA** is an enterprise-grade, AI-native API testing, verification, and autonomous governance platform built for microservice ecosystems, heterogeneous API specifications (OpenAPI, GraphQL, gRPC, Postman), visual UI testing, and multi-agent AI mesh orchestration. Designed around **Clean Architecture (Hexagonal / Ports & Adapters per ADR-004)** and strict software engineering invariants (notably **Invariant D7: Suggest-Only / Anti-Lock-In**, ensuring generated suites remain 100% standalone and executable without CHERENKOV), the platform provides an end-to-end framework for autonomous quality assurance.

This authoritative document synthesizes architectural, code-level, and operational findings across all five core subsystems of CHERENKOV-QA:
1. **Subsystem 1: Core CLI, Execution Engine & Clean Architecture** — Command invocation pipeline, DAG workflow engine, configuration provenance, retry ladders, and stage boundary contracts.
2. **Subsystem 2: Second Brain, Memory Layer, SQLite FTS5 & GraphRAG** — Zero-dependency keyword and semantic retrieval, multi-source knowledge mesh, automatic pattern promotion, Milvus/MemSearch vector indexing, and the Sync-Driven Development (SDD) protocol.
3. **Subsystem 3: MCP Server, Marketplace, Push Events & Hooks Infrastructure** — Zero-dependency JSON-RPC 2.0 stdio server, tool definition catalog, IDE Sentinel hooks, pip-sandboxed marketplace installer, JWT authentication, and the 10-event pipeline hook engine (Phase CC-1).
4. **Subsystem 4: Multi-Agent Conductor, Chat Agent & VLM / LocalAI Tier Routing** — Multi-agent mesh fan-out/fan-in conductor (Phase CC-2), tool-calling QA chat agent, persona registry, SSE streaming API, containerized LocalAI VLM default provider, tier-aware model routing (`SubstrateRouter`), and system diagnostic tools (`Doctor CLI`).
5. **Subsystem 5: Desktop Host (Tauri 2) & Dashboard UI** — Cross-platform Rust host shell, async sidecar process launcher (`cherenkov-launcher`), hardware probe, 7-step onboarding wizard, native spec file watcher, and a 5-Workspace / 9-Screen React 19 + TypeScript 5.8 web dashboard with zero-cost IPC bridging.

---

## 1. Architecture

CHERENKOV-QA adopts a strictly enforced **Hexagonal Architecture (Ports & Adapters)** as defined in **ADR-004** and refined in **ADR-011** (Auto-Memory) and **ADR-012** (Hooks). The architectural philosophy prioritizes pure business domain isolation, explicit protocol-based interfaces, dependency inversion, zero vendor lock-in, and clear boundaries between execution tiers.

```
                   ┌─────────────────────────────────────────────────────────┐
                   │                     API & CLI Layer                     │
                   │    (cherenkov/cli/, cherenkov/chat/api/, Tauri UI)      │
                   └────────────────────────────┬────────────────────────────┘
                                                │
                                                ▼
                   ┌─────────────────────────────────────────────────────────┐
                   │                    Use Cases Layer                      │
                   │  (collect.py, promote.py, decompose.py, aggregate.py)  │
                   └────────────────────────────┬────────────────────────────┘
                                                │
                                                ▼
                   ┌─────────────────────────────────────────────────────────┐
                   │                      Ports Layer                        │
                   │    (MemoryRepository, HookExecutor, VLMProvider)        │
                   └────────────────────────────┬────────────────────────────┘
                                                │
                                                ▼
                   ┌─────────────────────────────────────────────────────────┐
                   │                     Domain Layer                        │
                   │   (MemoryEntry, HookEvent, ConductorTask, Persona)      │
                   └─────────────────────────────────────────────────────────┘
                                                ▲
                                                │
                   ┌────────────────────────────┴────────────────────────────┐
                   │                    Adapters Layer                       │
                   │ (SQLite, MemSearch, Redis, Subprocess, Docker, LocalAI) │
                   └─────────────────────────────────────────────────────────┘
```

### 1.1 Hexagonal Layering & ADR-004 Compliance

Per ADR-004, every sub-domain within the codebase adheres to a rigid 5-directory internal layout:
```
cherenkov/{module}/
├── domain/          # Pure business logic, Pydantic v2 schemas, dataclasses, zero I/O
├── ports/           # Protocol / ABC interfaces defining "what" operations are available
├── adapters/        # Concrete I/O drivers (SQLite, Redis, Docker, SSH, Subprocess)
├── use_cases/       # Application orchestration combining domain logic and ports
└── api/             # HTTP endpoints (FastAPI), CLI subcommands, or IPC command handlers
```

#### Code Layout & Subsystem Compliance Mapping:
- **`cherenkov/memory/`**: 
  - `domain/models.py`: Defines `MemoryEntry`, `MemoryQuery`, `MemoryPattern`, `PromotionRule`, `EntryKind`. Pure domain classes with zero external framework imports.
  - `ports/repository.py`: Defines `MemoryRepository(Protocol)` interface.
  - `adapters/sqlite_memory.py`: Implements SQLite FTS5 persistence.
  - `adapters/memsearch_memory.py`: Implements proxy adapter for Milvus vector search.
  - `use_cases/collect.py` & `use_cases/promote.py`: Encapsulates pattern extraction and threshold promotion workflows.
- **`cherenkov/hooks/`**:
  - `domain/models.py`: `HookEvent`, `HookStatus`, `HookContext`, `HookResult`, `HookConfig`, `FailMode`.
  - `ports/executor.py`: `HookExecutor(Protocol)`.
  - `adapters/subprocess_executor.py`: Implements process execution with shell escaping (`shlex.quote`).
  - `registry.py`: TOML loader and event dispatcher.
- **`cherenkov/agents/conductor/`**:
  - `domain/models.py`: `ConductorTask`, `SubAgentTask`, `SubAgentResult`, `ConductorResult`, `MergeStrategy`.
  - `ports/conductor.py`: `AgentConductor(Protocol)`.
  - `adapters/mcp_conductor.py`: Implements parallel sub-task dispatching across MCP mesh.
  - `use_cases/decompose.py` & `use_cases/aggregate.py`: Encapsulates splitting strategies (`split_by_item`, `split_by_role`) and merge logic.

### 1.2 Inward Dependency Flow & Invariants

1. **Dependency Inversion Principle**: Outer layers (Adapters, API, CLI) depend on inner abstractions (Ports, Domain). Inner layers never import from outer layers.
2. **Contract Invariant (Pydantic v2 Gateways)**: All stage boundaries pass strictly typed, immutable Pydantic models defined in `cherenkov/core/contracts.py` (`IngestOutput`, `PlanOutput`, `GenerateOutput`, `ReviewOutput`).
3. **Anti-Lock-In & Invariant D7**: Ejected test suites are standalone Playwright TypeScript scripts. `cherenkov eject` strips all CHERENKOV framework imports, ensuring generated tests execute independently in native Node.js environments.
4. **Suggest-Only Healing Policy**: Healing and verification engines generate reports and suggested code diffs without modifying user source code directly without human validation.

---

## 2. System Design & Inter-Subsystem Data Flow

CHERENKOV-QA operates as a tightly integrated event-driven system connecting CLI commands, asynchronous orchestration DAGs, Second Brain memory stores, MCP tool networks, AI tier routers, and desktop/web UI clients.

```
 +──────────────────────────────────────────────────────────────────────────────────────────+
 │                                     User / UI Layer                                      │
 │   Tauri Desktop Host  │  React 19 Web Dashboard  │  CLI (`cherenkov validate --spec ...`)   │
 +───────────────────────────────────┬──────────────────────────────────────────────────────+
                                     │ (IPC / HTTP / SSE / Direct CLI)
                                     ▼
 +──────────────────────────────────────────────────────────────────────────────────────────+
 │                                  Core Orchestration DAG                                  │
 │ IngestStage ──► PlanStage ──► StageExecutor (Retry/CircuitBreaker) ──► GenerateStage     │
 +─────────┬─────────────────────────────────┬──────────────────────────────────┬───────────+
           │                                 │                                  │
           │ (Read/Write Memory)             │ (Execute Hooks)                  │ (Tool Calls)
           ▼                                 ▼                                  ▼
 ┌───────────────────┐             ┌───────────────────┐              ┌───────────────────┐
 │   Second Brain    │             │  Hooks Infrastructure│           │    MCP Server     │
 │ MemoryRepository  │             │   HookRegistry    │              │  JSON-RPC Stdio   │
 │ SQLite FTS5 / RAG │             │ SubprocessExecutor│              │  Sentinel Tools   │
 └─────────┬─────────┘             └───────────────────┘              └─────────┬─────────┘
           │                                                                    │
           │                                                                    │ (Sub-Agent Dispatch)
           ▼                                                                    ▼
 ┌───────────────────┐                                                ┌───────────────────┐
 │  Knowledge Mesh   │                                                │ Multi-Agent       │
 │ GraphRAG Engine   │                                                │ Conductor         │
 └───────────────────┘                                                └─────────┬─────────┘
                                                                                │
                                                                                │ (Reasoning Requests)
                                                                                ▼
                                                                      ┌───────────────────┐
                                                                      │ SubstrateRouter   │
                                                                      │ Tier 1/2/3 Models │
                                                                      │ LocalAI / Ollama  │
                                                                      └───────────────────┘
```

### 2.1 Complete Execution Pipelines

#### 1. Synthetic Test Generation & Verification Pipeline:
1. **Invocation**: User executes `cherenkov validate --spec openapi.yaml`.
2. **CLI Initialization**: `cherenkov/cli/core.py` rewrites arguments and lazily loads subcommands. `LayeredConfig` (`cherenkov/core/config_loader.py`) resolves configuration across defaults, `cherenkov.toml`, environment variables, and flags.
3. **Ingest Stage**: `IngestStage` parses OpenAPI/GraphQL/gRPC definitions into normalized `EndpointSlice` models.
4. **Plan Stage**: `PlanStage` synthesizes test intent DAGs.
5. **Hook Execution (`PRE_GENERATE`)**: `HookRegistry` dispatches `PRE_GENERATE` events to `SubprocessHookExecutor`.
6. **Parallel Generation**: `OrchestrationEngine` (`cherenkov/core/orchestrator.py`) spawns worker threads. Each worker invokes `StageExecutor` (`cherenkov/core/stage_executor.py`), passing requests through `SubstrateRouter` (`cherenkov/substrate/router.py`) to generate Playwright TypeScript tests.
7. **Circuit Breaking & Retries**: If generation fails schema validation, `StageExecutor` executes exponential backoff retries (up to 3 attempts). If errors persist, `CircuitBreaker` records failure and returns fallback factory outputs.
8. **Review Stage**: 6-gate static and dynamic analysis verifies contract adherence.
9. **Hook Execution (`POST_VALIDATE`)**: Outputs SARIF, JUnit, and HTML reports, and executes `POST_VALIDATE` hooks.
10. **Memory Logging**: Session findings are collected into `SQLiteMemoryRepository` via `collect_from_findings()`.

#### 2. Multi-Agent Conductor Pipeline:
1. **Task Submission**: `ConductorTask` is submitted to `MCPConductor` (`cherenkov/agents/conductor/adapters/mcp_conductor.py`).
2. **Decomposition**: `use_cases/decompose.py` splits the objective into parallel `SubAgentTask` payloads.
3. **MCP Mesh Dispatch**: `MCPConductor` executes sub-tasks in parallel using thread pools, routing calls through `mesh_router.py` to registered sub-agents over JSON-RPC stdio.
4. **Aggregation**: `use_cases/aggregate.py` collects `SubAgentResult` payloads and merges outputs using `UNION`, `CONSENSUS`, or `WEIGHTED` strategies.

### 2.2 Lifecycle & State Synchronization

- **Database State Alignment**: Conversation state, memory logs, and knowledge items operate with Write-Ahead Logging (`PRAGMA journal_mode = WAL`) and 30-second busy timeouts to ensure multi-threaded read/write synchronization.
- **Engine Process Lifecycle**: Tauri 2 host spawns `cherenkov-launcher` as an async sidecar. Standard output NDJSON streams (`LauncherEvent::Port`) trigger TCP liveness polling (`/healthz`). Upon readiness, Tauri emits `engine-healthy` to the frontend, dynamically updating UI liveness indicators.

---

## 3. Comprehensive Design Patterns Catalog

| Pattern | Codebase Location | Concrete Class / Function | Architectural Purpose & Rationale |
|:---|:---|:---|:---|
| **Dependency Injection** | `cherenkov/hooks/registry.py`, `cherenkov/adapters/docker_runner.py`, `cherenkov/core/orchestrator.py` | Abstract port interfaces (`RemoteRunnerPort`, `EventBus`, `HookExecutor`) injected into constructors. | Decouples use case business logic from concrete infrastructure drivers (Docker, SSH, Subprocess). |
| **Strategy Pattern** | `cherenkov/adapters/docker_runner.py` vs `ssh_runner.py`; `cherenkov/ports/vlm_provider.py`; `cherenkov/execution/emitters/*` | `RemoteRunnerPort`, `LocalAIVLMProvider`, `OllamaProvider`, SARIF/JUnit/HTML Emitters. | Enables zero-code-change switching between execution environments, VLM backends, and report formats. |
| **Command Pattern** | `cherenkov/cli/core.py`, `cherenkov/cli/commands/*.py`, `cherenkov/hooks/domain/models.py` | Click command handlers (`validate_cmd`, `audit_cmd`), `HookConfig.run`, `JsonRpcRequest`. | Encapsulates executable operations, parameters, timeouts, and arguments as serializable command objects. |
| **Registry Pattern** | `cherenkov/cli/core.py` (`_register_commands`), `cherenkov/hooks/registry.py` (`HookRegistry`), `cherenkov/mcp/mesh_router.py` (`MCPRegistry`), `cherenkov/chat/persona.py` (`PersonaRegistry`) | `HookRegistry`, `MCPRegistry`, `PersonaRegistry`, `TOOL_REGISTRY`. | Provides centralized lookup, registration, and discovery of subcommands, lifecycle hooks, MCP agents, personas, and tools. |
| **Adapter Pattern** | `cherenkov/sources/graphql/adapter.py`, `cherenkov/sources/grpc/adapter.py`, `cherenkov/adapters/postman_importer.py` | GraphQL, gRPC, and Postman source adapters. | Normalizes heterogeneous external schemas into standard internal `EndpointSlice` domain models. |
| **Observer Pattern** | `cherenkov/core/events.py`, `cherenkov/ports/event_bus.py`, `cherenkov/knowledge/bridges/*` | `CHERENKOVEvent` pub-sub event bus, `AgentMemoryRAGBridge`, `FeedbackRAGBridge`, `HITLReflectorBridge`. | Decouples pipeline execution from external notifications, RAG indexing, and UI events. |
| **Circuit Breaker** | `cherenkov/core/stage_executor.py`, `cherenkov/core/d2_controller.py`, `cherenkov/agents/pilot.py` | `CircuitBreaker`, `D2FeedbackController`, `PilotAgent`. | Binds failure counts and prevents cascade crashes during scenario generation and dry-run execution. |
| **Proxy / Facade Pattern** | `cherenkov/memory/adapters/memsearch_memory.py`, `cherenkov/knowledge/graph_rag.py`, `cherenkov/web/ui/src/lib/tauri.ts` | `MemSearchMemoryRepository`, `GraphRAG`, `invokeDesktop<T>()`. | Wraps complex underlying storage engines or platform APIs behind simplified, unified interfaces. |
| **Chain of Responsibility / Middleware** | `cherenkov/mcp/handlers.py`, `cherenkov/mcp/policy.py`, `cherenkov/mcp/auth.py`, `cherenkov/chat/guard.py` | `MCPAuthMiddleware` -> `PolicyEngine` -> `SafetyGuard` -> Tool Handler. | Sequences authentication, authorization policy checks, and safety rules before tool execution. |
| **Repository Pattern** | `cherenkov/memory/ports/repository.py`, `cherenkov/knowledge/ports/repository.py` | `MemoryRepository`, `KnowledgeMeshRepository`. | Completely abstracts underlying data persistence away from domain logic models. |
| **SSE Streamer Pattern** | `cherenkov/chat/api/routes.py`, `cherenkov/web/ui/src/lib/api.ts` | `stream_chat()`, `StreamingResponse(event_stream())`, `streamChatMessage()`. | Delivers token-by-token AI completions over Server-Sent Events to eliminate UI wait latency. |

---

## 4. Code Quality & Engineering Standards

### 4.1 Thread Safety & Lock Hygiene

CHERENKOV-QA relies heavily on concurrent execution across worker threads, web server requests, and desktop sidecars. Shared stateful components enforce explicit thread synchronization:

- **Per-Thread Event Logging**: `cherenkov/core/errors.py` utilizes `threading.local()` (`_tl.events_file`) to isolate log file paths across concurrent execution threads, preventing log cross-contamination during multi-threaded test runs.
- **Mutex Lock Primitives**: `threading.Lock` guards shared state across critical execution components:
  - `CircuitBreaker._lock` in `cherenkov/core/stage_executor.py`: Protects error counter increments and tripped state checks.
  - `RunBudget._lock` in `cherenkov/core/budget.py`: Synchronizes token cost allocation and balance updates.
  - `D2FeedbackController`: Synchronizes replan iteration counts.
  - `StatsStore`: Protects SQLite metrics updates.
- **SQLite Thread Alignment**: `SQLiteKnowledgeRepository` (`cherenkov/knowledge/adapters/sqlite_repository.py`) and `SQLiteChatMemory` (`cherenkov/chat/adapters/sqlite_memory.py`) store connection objects in `threading.local()` (`self._local.con`). Combined with `PRAGMA journal_mode = WAL` and 30.0s busy timeouts, this enables concurrent thread reads and serial writes without database locking conflicts.

### 4.2 Async Concurrency & Boundary Discipline

- **FastAPI Async Delegates**: Web routes (`cherenkov/chat/api/routes.py`) run inside an `asyncio` event loop. Synchronous memory and LLM calls are explicitly offloaded to worker threads using `await asyncio.to_thread(...)`, keeping the HTTP loop responsive.
- **Desktop Sidecar IPC**: Rust host (`desktop/src-tauri/src/main.rs`) leverages Tokio's async runtime for process spawning, stdout line reading, and HTTP health-checking, preventing UI thread blocking.

### 4.3 Typed Exception Hierarchy & Error Propagation

The core engine enforces a strict typed exception policy rooted at `CherenkovError` in `cherenkov/core/errors.py`. Generic bare `raise Exception` is prohibited.

```
CherenkovError (base)
 ├── ProviderJSONError
 │    └── OllamaJSONError
 ├── ContractError
 ├── RefDepthError
 ├── SpecTooThinError
 ├── EgressError
 ├── AllProvidersFailedError
 ├── CertificationError
 ├── ConfigError (config_loader.py)
 └── BudgetExceededError (budget.py)
```

CLI exit status codes are standard via `ExitCode(IntEnum)`:
```python
class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    VALIDATION_ERROR = 2
    CONFIG_ERROR = 3
    NETWORK_ERROR = 4
```

### 4.4 Input Validation, Security Guards & Shell Escaping

- **JSON-RPC & MCP Boundaries**: MCP handlers in `cherenkov/mcp/handlers.py` parse raw incoming dicts into validated Pydantic models before execution (`VerifySuiteInput`, `CheckSuiteInput`, `HitlApproveInput`).
- **Path Containment Verification**: `_resolve_within_cwd()` (`cherenkov/mcp/handlers.py`, lines 98–112) verifies that target paths resolve strictly within the working directory, preventing directory traversal.
- **Process Shell Injection Safeguards**: `SubprocessHookExecutor` (`cherenkov/hooks/adapters/subprocess_executor.py`, lines 34–37) passes all context template variables through `shlex.quote()` before formatting shell commands.
- **Marketplace Sandbox Regex**: `SandboxValidator` (`cherenkov/mcp/marketplace/sandbox.py`) enforces strict regex matching (`^pip install [a-zA-Z0-9]...`) to block arbitrary shell commands in third-party tool manifests.

---

## 5. Deep-Dive Subsystem Analysis

### 5.1 Subsystem 1: Core CLI, Engine & Clean Architecture

Subsystem 1 houses the execution core, CLI pipeline, configuration manager, and Clean Architecture port definitions.

#### A. Command Registration Pipeline (`cherenkov/cli/core.py`)
To ensure rapid CLI response times, subcommands are lazily imported and registered:

```python
# File: cherenkov/cli/core.py (Lines 77-82)
def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("-") and "--spec" in sys.argv[1:]:
        sys.argv.insert(1, "validate")
    _register_commands()
    cli()
```
`_register_commands()` imports submodules (`validate`, `verify`, `audit`, `synthetic`) dynamically at invocation time, avoiding initial import overhead for heavy libraries (Playwright, PyTorch, FastAPI).

#### B. Layered Configuration & Provenance (`cherenkov/core/config_loader.py`)
Configuration settings are resolved across 5 layers with provenance tracking:
1. **Built-in Defaults**: Defined in `BUILTIN_DEFAULTS` (`profile="laptop"`, egress="internal").
2. **Profile Overrides**: Target profile selection (`laptop`, `ci`, `enterprise-vpc`, `frontier-cloud`).
3. **Project Configuration (`cherenkov.toml`)**: Walked up from CWD.
4. **Environment Variables (`CHERENKOV_*`)**.
5. **Explicit CLI Overrides**.

Provenance tracking snippet (`cherenkov/core/config_loader.py`):
```python
def _set(self, key: str, value: Any, source: str):
    if key not in self._store:
        self._store[key] = []
    self._store[key].append((source, value))

def get_with_provenance(self, key: str) -> list[tuple[str, Any]]:
    return self._store.get(key, [])
```

#### C. DAG Execution & Circuit Breakers (`cherenkov/core/stage_executor.py`)
`StageExecutor` manages stage execution, retry backoff with jitter, and circuit breaking:

```python
# File: cherenkov/core/stage_executor.py (Lines 25-38)
class CircuitBreaker:
    def __init__(self, threshold: int = 2):
        self.threshold = threshold
        self.error_count = 0
        self.tripped = False
        self._lock = threading.Lock()

    def record_failure(self):
        with self._lock:
            self.error_count += 1
            if self.error_count >= self.threshold:
                self.tripped = True
```
When stage failures occur, exponential backoff with jitter (`wait = (2**attempts) * 0.5 + random.uniform(0, 0.5)`) executes up to 3 retries before tripping the breaker and returning fallback outputs.

---

## 5.2 Subsystem 2: Second Brain, Memory Layer, SQLite FTS5 & GraphRAG

Subsystem 2 provides zero-dependency keyword and semantic retrieval, multi-source knowledge mesh capabilities, and SDD session management.

#### A. SQLite FTS5 Memory Engine (`cherenkov/memory/adapters/sqlite_memory.py`)
Stores raw memory logs in `memory_entries` and shadow-indexes content into an external content FTS5 table `memory_fts` via automated SQLite triggers:

```sql
-- File: cherenkov/memory/adapters/sqlite_memory.py (Lines 30-61)
CREATE TABLE IF NOT EXISTS memory_entries (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL,
    task_type     TEXT NOT NULL,
    kind          TEXT NOT NULL,
    content       TEXT NOT NULL,
    tags          TEXT NOT NULL DEFAULT '[]',
    recurrence    INTEGER NOT NULL DEFAULT 0,
    is_promoted   INTEGER NOT NULL DEFAULT 0,
    promoted_at   TEXT,
    created_at    TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
USING fts5(
    id UNINDEXED,
    content,
    task_type,
    kind,
    content=memory_entries,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS memory_entries_ai
AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, id, content, task_type, kind)
    VALUES (new.rowid, new.id, new.content, new.task_type, new.kind);
END;
```

#### B. GraphRAG Query Execution (`cherenkov/knowledge/graph_rag.py`)
`GraphRAG` fans out search queries across heterogeneous knowledge sources (`verdicts`, `idioms`, `incidents`, `hitl`, `feedback`, `agent_memory`), normalizes limits, and ranks by confidence:

```python
# File: cherenkov/knowledge/graph_rag.py (Lines 15-32)
def query(self, query: str, sources: list[str] | None = None, limit: int = 10) -> list[KnowledgeQueryResult]:
    if sources is None:
        sources = ["verdicts", "idioms", "incidents", "hitl", "feedback", "agent_memory"]
    per_source = max(1, limit // len(sources))
    results = []
    for source in sources:
        q = KnowledgeQuery(query=query, source=source, limit=per_source)
        result = self.repository.query(q)
        if result.data:
            results.append(result)
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results[:limit]
```

#### C. Pattern Collection & Promotion (`cherenkov/memory/use_cases/collect.py` & `promote.py`)
- `collect_from_findings()` parses session findings, extracts `PITFALL` and `DECISION` entries, normalizes text by removing session IDs, timestamps, and file paths, hashes normalized text to a 16-character SHA-256 fingerprint, and upserts patterns.
- `run_promotion()` evaluates `PromotionRule(min_session_count=3)`. Eligible patterns have `is_auto_loaded` set to `1` and are prepended to context snippets in all future `agent_sync before` calls.

---

## 5.3 Subsystem 3: MCP Server, Marketplace, Push Events & Hooks Infrastructure

Subsystem 3 implements the Model Context Protocol (MCP) server, tool registry, security policy interceptors, marketplace installer, and pipeline hook engine.

#### A. JSON-RPC 2.0 Stdio Protocol Dispatcher (`cherenkov/mcp/protocol.py`)
Built cleanly without external SDK dependencies, `dispatch_one` processes newline-delimited JSON-RPC messages:

```python
# File: cherenkov/mcp/protocol.py (Lines 59-75)
def dispatch_one(raw: str, table: DispatchTable) -> JsonRpcResponse | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _make_error(None, PARSE_ERROR, f"Parse error: {exc}")

    req_id = data.get("id")
    try:
        req = JsonRpcRequest.model_validate(data)
    except Exception as exc:
        return _make_error(req_id, INVALID_REQUEST, f"Invalid request: {exc}")

    is_notification = "id" not in data
    handler = table.get(req.method)
    if handler is None:
        if is_notification:
            return None
        return _make_error(req.id, METHOD_NOT_FOUND, f"Method not found: {req.method!r}")
```

#### B. Marketplace Sandbox Installer (`cherenkov/mcp/marketplace/sandbox.py`)
Enforces strict regex constraints on package installation commands to block shell injection attacks:

```python
# File: cherenkov/mcp/marketplace/sandbox.py (Lines 12-28)
_ALLOWED_INSTALL_RE = re.compile(
    r"^pip install [a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?(\[[\w,]+\])?(==[\w.*]+)?$"
)

class SandboxValidator:
    def validate_tool_manifest(self, manifest: dict[str, Any]) -> bool:
        required_keys = {"id", "name", "install_command"}
        if not required_keys.issubset(manifest):
            return False
        cmd = manifest.get("install_command", "")
        return bool(_ALLOWED_INSTALL_RE.match(cmd))
```

#### C. Hook Infrastructure (`cherenkov/hooks/adapters/subprocess_executor.py`)
`SubprocessHookExecutor` executes lifecycle hooks configured in `cherenkov.toml` across 10 pipeline events (`PRE_GENERATE`, `POST_GENERATE`, `PRE_REVIEW`, `POST_REVIEW`, `PRE_VALIDATE`, `POST_VALIDATE`, `PRE_EJECT`, `POST_EJECT`, `PRE_COMMIT`, `POST_COMMIT`). Template variables are safely escaped with `shlex.quote()`:

```python
# File: cherenkov/hooks/adapters/subprocess_executor.py (Lines 34-40)
template_vars = context.as_template_vars()
safe_vars = {k: shlex.quote(v) if v else "''" for k, v in template_vars.items()}
rendered_cmd = config.run.format(**safe_vars)
```

---

## 5.4 Subsystem 4: Multi-Agent Conductor, Chat Agent & VLM / LocalAI Tier Routing

Subsystem 4 handles parallel multi-agent task execution over MCP, interactive QA chat assistance, SSE streaming, VLM visual analysis, and tier-aware model routing.

#### A. Multi-Agent Conductor (`cherenkov/agents/conductor/adapters/mcp_conductor.py`)
`MCPConductor` splits tasks into sub-tasks and executes them in parallel across MCP mesh targets:

```python
# File: cherenkov/agents/conductor/adapters/mcp_conductor.py (Lines 47-56)
def execute(self, task: ConductorTask) -> ConductorResult:
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(task.sub_tasks) or 1) as executor:
        future_to_task = {
            executor.submit(self._run_sub_task, sub_task, task.global_timeout_seconds): sub_task
            for sub_task in task.sub_tasks
        }
        for future in concurrent.futures.as_completed(future_to_task):
            ...
```

#### B. Containerized LocalAI VLM Default Provider (`cherenkov/substrate/providers/localai.py`)
Implements `LocalAIVLMProvider` targeting OpenAI-compatible local endpoints (`/v1/chat/completions`). Performs base64 encoding on PNG/JPEG images and formats multimodal request payloads:

```python
# File: cherenkov/substrate/providers/localai.py (Lines 42-58)
def describe_image(self, image_path: str, prompt: str = "") -> str:
    b64_img = self._encode_image(image_path)
    payload = {
        "model": self.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "Describe this image in detail."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
                ],
            }
        ],
    }
```
Auto-resolution in `cherenkov/substrate/provider.py:298-310` detects hardware via `DeviceInfo()`. If local VLM tier is supported and Docker is running, `localai` is selected as default.

#### C. Tier-Aware Model Router (`cherenkov/substrate/router.py`)
`SubstrateRouter` routes requests based on capability tier:
- **`small` (Tier 1)**: Rapid reasoning / code generation (`qwen2.5-coder:7b`).
- **`deep` (Tier 2)**: Edge-case / architectural reasoning (`deepseek-r1:8b` / Cloud).
- **`vision` (Tier 3)**: Multimodal visual analysis (`LocalAIVLMProvider` / `qwen2.5-vl:7b` / GPT-4o).

Enforces E12 Gold-Set certification gates (`CERTIFICATION_ENABLED=True`), egress policy boundaries (`none`, `internal`, `github`, `external`), and token run budget caps before executing LLM calls.

---

## 5.5 Subsystem 5: Desktop Host (Tauri 2) & Dashboard UI

Subsystem 5 provides the desktop wrapper application and React 19 web dashboard.

#### A. Tauri 2 Sidecar Spawning & NDJSON Event Stream (`desktop/src-tauri/src/main.rs`)
The Rust core spawns `cherenkov-launcher` with `CHERENKOV_NO_BROWSER=1` and listens for NDJSON stdout event streams:

```rust
// File: desktop/src-tauri/src/main.rs (Lines 30-41 & 134-147)
#[derive(Debug, Deserialize)]
#[serde(tag = "event", content = "data", rename_all = "snake_case")]
enum LauncherEvent {
    Ready { version: String },
    Port { port: u16 },
    Shutdown { signal: serde_json::Value },
    Progress { step: String, pct: u8, detail: Option<String> },
    DemoMode { reason: String },
}
```
When `LauncherEvent::Port { port }` is received, Tokio polls `http://127.0.0.1:<port>/healthz`. Upon 200 OK status, `engine-healthy` is emitted to the webview and the webview re-navigates if bound to a non-standard port.

#### B. Dynamic Dual-Mode IPC Bridge (`cherenkov/web/ui/src/lib/tauri.ts`)
The web UI uses a zero-cost dynamic proxy bridge to detect Tauri IPC availability without hard runtime dependencies:

```typescript
// File: cherenkov/web/ui/src/lib/tauri.ts (Lines 34-51)
function tauri(): TauriGlobal | null {
  return (window as unknown as { __TAURI__?: TauriGlobal }).__TAURI__ ?? null;
}

export function isDesktop(): boolean {
  return tauri() !== null;
}

export async function invokeDesktop<T>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T | null> {
  const t = tauri();
  if (!t) return null;
  try {
    return await t.core.invoke<T>(cmd, args);
  } catch (err) {
    console.warn(`[desktop] invoke ${cmd} failed:`, err);
    return null;
  }
}
```
This enables the exact same React bundle (`dist/`) to run inside web browsers (served by FastAPI) or inside cross-platform Tauri WebKit/WebView2 windows.

#### C. Web Dashboard Layout & 9 Screen Catalog
The dashboard features a 5-Workspace layout (`Dashboard`, `Authoring`, `Triage`, `Intelligence`, `Settings`) integrating 9 specialized functional screens:
1. `OverviewScreen` (Release readiness, coverage heatmaps, verdict history).
2. `AuthoringWorkspace` (OpenAPI spec ingestion, intent prompt studio, pipeline monitor).
3. `TriageWorkspace` (HITL approval queue, spec vs implementation diff viewer, divergence table).
4. `IntelligenceWorkspace` (GraphRAG Second Brain explorer, SDD memory cockpit, SSE chat copilot).
5. `SettingsWorkspace` / `DeviceManager` (Hardware device inspector, project selector, eject suite panel).
6. `DeviceManagerScreen.tsx` (Standalone `/api/v1/doctor` system health inspector).
7. `KnowledgeExplorerScreen.tsx` (Standalone knowledge mesh query engine).
8. `MobilePilotScreen.tsx` (ADB/Maestro automated mobile device test runner).
9. `SddDashboardScreen.tsx` (SDD session token accounting and pattern promotion cockpit).

---

## 6. Architectural Strengths & Technical Debt Analysis

### 6.1 Key Architectural Strengths

1. **Strict Clean Architecture (ADR-004, ADR-011, ADR-012)**: Pure domain isolation across all modules ensures zero external framework lock-in and high unit-testability.
2. **Anti-Lock-In & Invariant D7**: Ejected Playwright TypeScript tests run natively in Node.js environments without CHERENKOV CLI dependencies.
3. **Resilient Local-First VLM Tiering**: Auto-resolves local containerized `LocalAI` or `Ollama` backends, preserving data privacy while maintaining cloud AI fallback routing.
4. **Layered Configuration Provenance**: 5-layer resolution model (`LayeredConfig`) allows effortless override from environment or TOML while preserving complete origin traceability for diagnostics (`cherenkov doctor`).
5. **Zero-Cost UI Desktop Portability**: `lib/tauri.ts` bridge allows running the React 19 UI seamlessly in browser or desktop modes.

### 6.2 Detailed Technical Debt Inventory & Remediation Plans

| # | Subsystem & File Location | Issue / Technical Debt Description | Risk / Severity | Actionable Remediation Plan |
|:---|:---|:---|:---:|:---|
| 1 | `scripts/memory_sync.py:20` vs `cherenkov/knowledge/adapters/sqlite_repository.py:22` | **Database Path & Schema Fragmentation**: `memory_sync.py` opens a direct SQLite connection to `agent_memory/knowledge.db` with a raw FTS table, bypassing `SQLiteKnowledgeRepository` (`data/knowledge.db`) and `SQLiteMemoryRepository` (`agent_memory/cherenkov_memory.db`). | **HIGH** | Refactor `scripts/memory_sync.py` to use `SQLiteKnowledgeRepository` or `SQLiteMemoryRepository` via standard port interfaces instead of maintaining an uncoordinated 3rd database file. |
| 2 | `cherenkov/hooks/adapters/subprocess_executor.py:82-91` | **Subprocess Timeout Zombie Hazard**: `subprocess.run(shell=True, timeout=...)` catches `TimeoutExpired` but only kills the top parent shell process, leaving child subprocesses running as orphans. | **HIGH** | Spawn processes with process group creation (`start_new_session=True` / `CREATE_NEW_PROCESS_GROUP`) and send `SIGKILL` to the entire process group in timeout handlers. |
| 3 | `cherenkov/substrate/provider.py:264`, `cherenkov/substrate/providers/localai.py` | **VLM Protocol Inheritance Type Debt**: `LocalAIVLMProvider` duck-types `VLMProvider` without explicit protocol inheritance (`# TODO(#type-debt)` comment). | **MEDIUM** | Have `LocalAIVLMProvider` explicitly inherit from `VLMProvider` protocol in `cherenkov/ports/vlm_provider.py`. |
| 4 | `cherenkov/memory/adapters/sqlite_memory.py:154`, `sqlite_repository.py:151` | **FTS5 Double-Quote Injection Bug**: Queries format search terms as `"term"`. If user query contains raw double quotes, SQLite raises `fts5: syntax error`. | **MEDIUM** | Escape internal double-quote characters in search terms (`term.replace('"', '""')`) before wrapping in FTS quotes. |
| 5 | `cherenkov/cli/commands/validate.py` (318 lines) | **CLI Command Monolith**: `validate.py` mixes parameter definitions, spec validation, planning, manifest recording, emitter formatting, and exit code handling in one function. | **MEDIUM** | Extract CLI command orchestration logic into a dedicated application use case (`use_cases/validate_suite.py`). |
| 6 | `cherenkov/mcp/mesh_router.py:177` & `cherenkov/mcp/handlers.py:85` | **Unprotected Shared Global Singletons**: Global singletons `_registry` and `_policy` mutate internal dicts without thread locks. | **MEDIUM** | Add `threading.RLock()` to guard dictionary updates in `register_server`, `unregister_server`, and `reload`. |
| 7 | `cherenkov/agents/conductor/adapters/mcp_conductor.py:47` | **Sync Concurrency Bottleneck**: `MCPConductor` relies on blocking `ThreadPoolExecutor` instead of native async I/O. | **LOW-MEDIUM** | Refactor `MCPConductor` to leverage native `asyncio.gather` for non-blocking sub-task execution. |
| 8 | `cherenkov/chat/agent.py:98-103` | **Pseudo-Streaming User Latency**: `chat_stream()` awaits the complete LLM text completion string before splitting words and yielding SSE tokens. | **LOW** | Wire `chat_stream()` directly to the streaming socket generator of underlying Ollama/OpenAI API clients. |

---

## 7. Conclusion & Future Architectural Roadmap

### 7.1 Final Conclusion

CHERENKOV-QA represents an exceptionally well-engineered, resilient, and extensible platform for AI-native API testing and continuous validation. By enforcing **Hexagonal Architecture (ADR-004)**, **Invariant D7 (Suggest-Only / Anti-Lock-In)**, explicit Pydantic v2 stage contracts, circuit breaker retry ladders, zero-dependency MCP stdio transport, and containerized local VLM execution, the system achieves enterprise-grade security and reliability.

Addressing the technical debt items cataloged in Section 6—specifically unifying database path fragmentation in `memory_sync.py`, fixing subprocess process group termination on timeout, and escaping FTS5 search queries—will solidify the codebase for large-scale enterprise production deployments.

### 7.2 Consolidated 8-Phase Master Architecture & Roadmap Alignment

As documented in `docs/PHASE_PLAN.md` and `docs/PRODUCT_STRATEGY_ROADMAP.md`, CHERENKOV-QA aligns across an 8-Phase Core Development Plan and a 25-Integration Strategy:

```
[Phase -1 & 0a/0b] ──► [Phase 1: Second Brain] ──► [Phase 2: VLM & LocalAI] ──► [Phase 3: Desktop Tauri 2]
     (Foundations)         (Knowledge Mesh & SDD)     (Tier Router & Doctor)        (Rust Shell & Host)
                                                                                            │
                                                                                            ▼
[Phase 8: K8s & Gate] ◄── [Phase 7: Dashboard UI] ◄── [Phase 5-6: Mobile Pilot] ◄── [Phase 4: Chat Agent]
(k3d/CRD/Security)         (React 19 Workspaces)       (ADB / Maestro Devices)    (Conductor & SSE Stream)
                                     │
                                     ▼
                  [Phase CC-1 ──► CC-6: Claude Code Enhancements]
               (FTS5 Auto-Memory, Hooks, Conductor Mesh, Teleport, CLI)
                                     │
                                     ▼
                   [Phases 9-16: Enterprise Market Expansion]
               (25 Integrations: VS Code, GitHub Actions, Slack, Jira)
```

#### Extended Milestone Roadmap:
- **Phases CC-1 to CC-6 (Completed)**: SQLite FTS5 Auto-Memory, 10-Event HookRegistry, Multi-Agent Conductor, MCP Marketplace Sandbox, APScheduler Routines, Remote Teleport, CLI Composability.
- **Phase 9 (Semantic Memory & MemSearch)**: Completed. Full integration of Milvus shadow indexing over repository markdown files.
- **Phase 10 (CI/CD Native Expansion)**: Completed. Jenkins Shared Library (`ci/jenkins/vars/cherenkovValidate.groovy`) and GitHub Actions native workflows.
- **Phases 11–16 (Enterprise & Market Launch)**: 25 IDE/CI/Communication integrations (VS Code Extension, Slack/Teams interactive bots, Jira/Xray sync, GraphQL/gRPC live probes), multi-tenant RBAC governance, enterprise VPC deployment templates, and automated compliance certification reporting (EU AI Act, ISO 42001, OWASP LLM Top 10).

---
*End of Master Comprehensive Technical & Architecture Review — CHERENKOV-QA.*
