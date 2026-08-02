# Subsystem 4 Deep-Dive Audit Report: Multi-Agent Conductor, Chat Agent, Persona Registry, SSE Streaming, VLM & LocalAI Tier Routing

**Audit Directory:** `Z:\home\moaid\cherenkov-qa\.agents\explorer_conductor_vlm`  
**Auditor:** Explorer 4  
**Date:** 2026-08-02  
**Target Scope:** Subsystem 4 (`cherenkov/agents/`, `cherenkov/agents/conductor/`, `cherenkov/chat/`, `cherenkov/substrate/`, `cherenkov/vlm/`, `cherenkov/cli/`, `cherenkov/stages/doctor_cmd.py`)

---

## Executive Summary

This report delivers a file-level architectural audit of **Subsystem 4** in CHERENKOV-QA, covering the Multi-Agent Conductor (Phase CC-2 / ADR-013), Tool-Calling Chat Agent (Phase 4), Persona Registry, SSE Streaming infrastructure, Vision-Language Model (VLM) backends (Phase 2), LocalAI integration, AI Tier Routing (`SubstrateRouter`), and system diagnostic tools (`Doctor CLI`).

Overall, Subsystem 4 demonstrates clean separation of concerns through Ports & Adapters (Clean Architecture), robust thread-safety for SQLite conversation state, structured multi-agent decomposition, and tier-aware model routing with fallback mechanisms. Key technical debt items include duck-typing without protocol inheritance in VLM providers, pseudo-streaming token generation in the chat agent, thread-pool-based parallel execution in the Conductor, and unfulfilled placeholder logic in weighted aggregation.

---

## 1. Agent & Conductor Architecture

### 1.1 Multi-Agent Fan-Out/Fan-In on MCP Mesh

The Multi-Agent Conductor (`cherenkov/agents/conductor/`) orchestrates parallel sub-agents over Model Context Protocol (MCP) servers to execute complex tasks such as multi-perspective code reviews, multi-dimensional API spec auditing, and parallel test suite generation.

#### Component Breakdown:
* **Port (`cherenkov/agents/conductor/ports/conductor.py`)**:
  Defines `AgentConductor` as a typing `Protocol`:
  ```python
  class AgentConductor(Protocol):
      def execute(self, task: ConductorTask) -> ConductorResult:
          ...
  ```
* **Domain Models (`cherenkov/agents/conductor/domain/models.py`)**:
  * `MergeStrategy`: Enum (`UNION`, `CONSENSUS`, `WEIGHTED`).
  * `SubAgentTask`: Individual sub-task containing `instruction`, `context`, `budget` (default 5,000 tokens), and unique `task_id` (UUID4).
  * `SubAgentResult`: Result payload from sub-agent execution containing `task_id`, `agent_id`, `status` (`"success"`, `"failed"`, `"timeout"`, `"budget_exceeded"`), `output`, `tokens_used`, and `error_message`.
  * `ConductorTask`: High-level specification with `objective`, `payload`, `sub_tasks`, `merge_strategy`, and `global_timeout_seconds` (default 300s).
  * `ConductorResult`: Aggregated final output with overall `status` (`"success"`, `"partial"`, `"failed"`), `aggregated_output`, `sub_results`, and `total_tokens_used`.

* **Adapter (`cherenkov/agents/conductor/adapters/mcp_conductor.py`)**:
  `MCPConductor` implements `AgentConductor` by dispatching sub-tasks over the MCP mesh router (`self.registry.forward_tool_call(self.target_tool_name, arguments)`):
  ```python
  class MCPConductor:
      def __init__(self, target_tool_name: str = "run_sub_agent_task"):
          self.target_tool_name = target_tool_name
          self.registry = get_registry()

      def execute(self, task: ConductorTask) -> ConductorResult:
          with concurrent.futures.ThreadPoolExecutor(max_workers=len(task.sub_tasks) or 1) as executor:
              future_to_task = {
                  executor.submit(self._run_sub_task, sub_task, task.global_timeout_seconds): sub_task
                  for sub_task in task.sub_tasks
              }
              for future in concurrent.futures.as_completed(future_to_task):
                  ...
  ```

* **Decomposition & Aggregation Use Cases**:
  * `cherenkov/agents/conductor/use_cases/decompose.py`:
    * `split_by_item`: Formats a prompt template for each item in a target list (e.g. endpoints) with context cloning.
    * `split_by_role`: Assigns base task instructions to specialized agent roles (e.g., Security, Performance, Style).
  * `cherenkov/agents/conductor/use_cases/aggregate.py`:
    * `aggregate_results(results, strategy)`: Performs `UNION` (lists concatenated, dicts merged, or values collected), `CONSENSUS` (returns most common result using `collections.Counter`), or `WEIGHTED` (currently defaults to union as placeholder).

* **Pre-packaged Conductor Team Templates**:
  * `cherenkov/agents/conductor/templates/audit_team.py`: Creates audit teams across 3 roles: Security Architect, API Designer, Documentation Specialist.
  * `cherenkov/agents/conductor/templates/generate_team.py`: Creates parallel test generation tasks across target endpoint paths.
  * `cherenkov/agents/conductor/templates/review_team.py`: Creates multi-perspective code review tasks across Security Auditor, Performance Expert, and Style Consistency Checker.

* **Autonomous Pilot Agent (`cherenkov/agents/pilot.py`)**:
  Implements `PilotAgent` with an execution loop, recovery mechanism (`_recover`), and circuit breakers enforcing `max_observations` (default 20) and `timeout_seconds` (default 300s).

---

### 1.2 Tool-Calling Chat Agent

The Chat Agent (`cherenkov/chat/agent.py`) handles multi-turn conversational interactions for QA assistance, querying test verdicts, explaining divergences, and generating test scenarios.

#### Execution Loop:
1. **Message Reception**: `chat()` or `chat_stream()` receives user prompt, creates/retrieves session in memory, and persists user message.
2. **Context Preparation (`_prepare_llm_context`)**: Fetches conversation history, looks up session persona, loads system prompt via `PersonaRegistry.compose_prompt()`, and attaches runtime context (e.g., recent idioms from `cherenkov.reflector.reflector`).
3. **Substrate Routing (`_call_llm`)**:
   Passes structured message list to `SubstrateRouter` via `ReasoningRequest(task=json.dumps(messages), capability_tier="small")`.
   If router is missing, falls back to `_fallback_llm()` returning mock responses for keywords like `verdict`, `idiom`, or `divergence`.
4. **Tool Execution & Guard (`cherenkov/chat/tools.py`)**:
   Tools are registered in `TOOL_REGISTRY`:
   * `query_verdicts`: Fetches recent verdicts from reflector.
   * `query_idioms`: Fetches recent test idioms from reflector.
   * `explain_divergence`: Uses `GraphRAG` (`cherenkov/knowledge/graph_rag.py`) to explain visual/spec divergence.
   * `run_test`: Plans test scenarios for a given endpoint via `IngestStage` and `PlanStage`.
   All tools are decorated with `@_guard.wrap_tool` from `cherenkov/chat/guard.py` for audit logging and security policy evaluation (`check_tool_call`).

---

### 1.3 Persona Registry

Located in `cherenkov/chat/persona.py`, the Persona Registry provides domain-specific agent personalities and context injection.

* **`Persona` Dataclass**:
  ```python
  @dataclass
  class Persona:
      persona_id: str
      name: str
      description: str
      system_prompt: str
      tools: list[str] = field(default_factory=list)
      model: str = "qwen2.5-coder:7b"
      temperature: float = 0.1
  ```
* **Default Persona**: `qa_assistant` ("Answers questions about API test results, divergences, and idioms" with tools `["query_verdicts", "query_idioms", "explain_divergence", "run_test"]`).
* **Prompt Composition (`PersonaRegistry.compose_prompt`)**:
  Dynamically appends runtime context dictionaries into system prompt string:
  ```python
  if "project_context" in context:
      prompt += f"\n\nProject context:\n{context['project_context']}"
  if "idioms" in context:
      prompt += f"\n\nKnown idioms:\n" + "\n".join(f"- {i}" for i in context["idioms"][:10])
  if "recent_divergences" in context:
      prompt += f"\n\nRecent divergences:\n" + "\n".join(f"- {d}" for d in context["recent_divergences"][:5])
  ```

---

### 1.4 SSE Streaming Infrastructure

Located in `cherenkov/chat/api/routes.py`, the web API exposes Server-Sent Events (SSE) streaming for real-time text delivery.

* **Endpoint**: `POST /api/v1/chat/sessions/{session_id}/stream`
* **Route Implementation**:
  ```python
  @router.post("/api/v1/chat/sessions/{session_id}/stream")
  async def stream_chat(session_id: str, body: ChatMessageRequest, agent: QAChatAgent = Depends(get_agent)):
      ...
      async def event_stream():
          async for token in agent.chat_stream(session_id, body.content):
              yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
          yield f"event: complete\ndata: {json.dumps({})}\n\n"

      return StreamingResponse(event_stream(), media_type="text/event-stream")
  ```
* **Agent Generator (`QAChatAgent.chat_stream`)**:
  Runs LLM completion via `asyncio.to_thread(self._call_llm, llm_messages)`, splits completion into word tokens, and yields each token while persisting the complete response to memory.

---

## 2. VLM & AI Tier Routing Architecture

### 2.1 LocalAI as Default VLM Backend

LocalAI serves as the local, containerized default Vision-Language Model backend in CHERENKOV-QA.

* **Provider (`cherenkov/substrate/providers/localai.py`)**:
  Implements `LocalAIVLMProvider` targeting OpenAI-compatible endpoints (`/v1/chat/completions`).
  * `describe_image(image_path, prompt)`: Encodes image to base64 and formats multimodal request payload with `image_url` data URI (`data:image/png;base64,...`).
  * `compare_images(baseline_path, actual_path)`: Sends dual images to VLM to identify visual changes and request JSON (`description`, `kind`, `confidence`). Includes JSON parse fallback on unexpected raw text responses.
  * `health()`: Checks endpoint availability via `GET /readyz` with 5s timeout.
* **Auto-Resolution (`cherenkov/substrate/provider.py:298-310`)**:
  `_resolve_vlm_provider()` checks device hardware capabilities using `cherenkov.core.devices.DeviceInfo`. If local VLM tier is supported and Docker is present (`info.has_docker`), `localai` is auto-selected as default VLM provider; otherwise it falls back to `ollama`.

---

### 2.2 MiniGPT & Vision-Language Models

* **`cherenkov/substrate/vlm_provider.py`**:
  Defines core `VLMProvider` class that accepts `InferenceClient` (e.g. `OllamaInferenceClient`) using settings model `TIER_VISION_MODEL` (`qwen2.5-vl:7b` / `llava`). Encodes images via `_encode_image()` and invokes `complete_vision()`.
* **`cherenkov/ports/vlm_provider.py`**:
  Clean Architecture Protocol defining `VLMProvider`:
  ```python
  class VLMProvider(Protocol):
      def describe_image(self, image_path: str, prompt: str = "") -> str: ...
      def compare_images(self, baseline_path: str, actual_path: str) -> dict[str, Any]: ...
      def health(self) -> bool: ...
  ```
* **Visual Oracle (`cherenkov/oracle/visual_oracle_vlm.py`)**:
  Integrates VLM vision capability into testing stages to perform automated visual regression testing and UI anomaly classification.

---

### 2.3 Tier-Aware Model Routing (`SubstrateRouter`)

`SubstrateRouter` (`cherenkov/substrate/router.py`) handles model selection, egress control, budget enforcement, certification, and fallback routing.

```
+-----------------------------------------------------------------------------------+
|                                ReasoningRequest                                   |
|                        (capability_tier: small|deep|vision)                        |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        SubstrateRouter.route(request)                             |
+-----------------------------------------------------------------------------------+
    |                      |                         |                         |
    v                      v                         v                         v
1. Resolution         2. Certification          3. Egress Policy         4. Budget Check
provider_for_tier()   E12 Gold-Set Gate         _enforce_egress()        budget.pre_check()
    |                      |                         |                         |
    +----------------------+-------------------------+-------------------------+
                                          |
                                          v
                         +---------------------------------+
                         | Retry Wrapper (with_retry)      |
                         | Primary: provider.generate()    |
                         +---------------------------------+
                                          |
                        [Failure?] -------+------- [Success?]
                            |                           |
                            v                           v
                +-----------------------+     +-------------------+
                | Fallback Provider     |     | Charge Budget     |
                | FALLBACK_PROVIDER     |     | Return Result     |
                +-----------------------+     +-------------------+
```

#### Capability Tiers:
1. **`small` (Tier 1)**: Rapid reasoning and code generation (e.g., `qwen2.5-coder:7b` via Ollama/GitHub Models).
2. **`deep` (Tier 2)**: Complex architectural and edge-case reasoning (e.g., `deepseek-r1:8b` / OpenAI / Anthropic).
3. **`vision` (Tier 3)**: Multimodal visual analysis (e.g., `LocalAIVLMProvider`, Ollama `qwen2.5-vl:7b`, OpenAI GPT-4o vision).

#### Enterprise Routing Controls:
* **E12 Certification Gate**: When `CERTIFICATION_ENABLED=True`, verifies that the target model passes gold-set verification before executing production requests.
* **Egress Policy Enforcement (`_enforce_egress`)**: Enforces network policy (`none`, `internal`, `github`, `external`), blocking cloud providers when operating under strict offline/internal mandates.
* **Run Budget Accounting**: Pre-checks cost cap before execution and charges actual cost upon completion (`budget.charge()`).

---

### 2.4 Doctor CLI Diagnostic Checks

System diagnostic checks are provided by two complementary modules:

1. **Substrate Doctor (`cherenkov/substrate/doctor.py`)**:
   Provides CLI command `cherenkov doctor` targeting hardware and AI backends:
   * `_detect_device()`: Inspects CPU count, RAM, OS, GPU presence, and Docker daemon state via `DeviceInfo()`.
   * `_detect_ollama_vlm()`: Queries `http://localhost:11434/api/tags` for installed vision models (e.g. models containing `vl` or `vision`).
   * `_detect_localai_vlm()`: Queries `LocalAI` status endpoint (`VLM_LOCALAI_URL/readyz`).
   * `recommendations`: Recommends optimal VLM backend (`localai`, `ollama`, or `openai`) based on hardware tier.

2. **Stage Doctor (`cherenkov/stages/doctor_cmd.py`)**:
   Full system health report (`run_doctor()`):
   * Configuration provenance (`load_effective_config()`).
   * Tool binaries on PATH: `ollama`, `node` (including NVM discovery paths), `playwright` (via npx), `docker` (Prism container readiness), `cargo` & `tauri-cli` (Track C Desktop support).
   * Egress policy consistency against selected tier models.
   * Spec file autodetection and demo fixture readiness.

---

## 3. Design Patterns Audit

| Design Pattern | Implementation Location | Concrete Class / Function | Purpose & Rationale |
| :--- | :--- | :--- | :--- |
| **Orchestrated Fan-Out / Fan-In** | `cherenkov/agents/conductor/` | `MCPConductor.execute()`, `aggregate_results()` | Decomposes complex workloads into parallel sub-tasks across MCP agents and merges outputs via strategy. |
| **Strategy Pattern** | `cherenkov/substrate/providers/`, `cherenkov/ports/vlm_provider.py` | `LocalAIVLMProvider`, `OllamaProvider`, `OpenAIProvider`, `GitHubModelsProvider` | Enables zero-code-change switching of underlying AI and VLM providers via configuration or hardware detection. |
| **Registry Pattern** | `cherenkov/chat/persona.py`, `cherenkov/chat/tools.py` | `PersonaRegistry`, `TOOL_REGISTRY` | Centralizes lookup, registration, dynamic prompt composition, and guard wrapping for personas and tools. |
| **Streamer / Pub-Sub** | `cherenkov/chat/api/routes.py` | `stream_chat()`, `StreamingResponse(event_stream())` | Publishes token events over standard SSE HTTP streams to eliminate client waiting latency. |
| **Circuit Breaker** | `cherenkov/agents/pilot.py` | `PilotAgent.run()` | Enforces observation count caps and strict timeout bounds to prevent infinite agent execution loops. |
| **Decorator Pattern** | `cherenkov/substrate/retry.py`, `cherenkov/chat/tools.py` | `@retryable`, `@_guard.wrap_tool` | Injects transparent exponential backoff retries and security guard logging into callables. |

---

## 4. Code Quality, Async Concurrency & Fault Tolerance

### 4.1 Async Concurrency & Threading

* **Conductor Execution (`mcp_conductor.py`)**:
  Conductor uses `concurrent.futures.ThreadPoolExecutor(max_workers=len(task.sub_tasks))` for parallel execution. While functional for thread-blocking MCP clients, it allocates OS threads per sub-task instead of leveraging native `asyncio.gather()`.
* **FastAPI API Async Boundary (`routes.py`)**:
  FastAPI route handlers use `asyncio.to_thread()` to delegate synchronous memory and agent operations (e.g. `await asyncio.to_thread(agent.create_session, body.persona_id)`), preserving event-loop responsiveness under heavy HTTP traffic.

---

### 4.2 Streaming & Backpressure

* **SSE Event Formatting (`routes.py`)**:
  Generator yields standard SSE tokens (`event: token\ndata: {"token": "..."}\n\n`).
* **Backpressure Risk**:
  `QAChatAgent.chat_stream()` in `agent.py` awaits the full LLM completion string from `_call_llm()` before splitting it into words and yielding tokens. This simulates streaming at the API layer but does not achieve true network-level streaming backpressure from the underlying LLM socket.

---

### 4.3 LLM Connection Retries & Fallbacks

* **Exponential Backoff (`cherenkov/substrate/retry.py`)**:
  * Implement `with_retry()` with full-jitter exponential backoff (`_delay()`).
  * Permanent Error Classification (`_PERMANENT_SUBSTRINGS`): Budget exceeded, certification failure, content policy, authorization failure bypass retries to prevent wasted execution cycles.
  * Transient Error Retries (`_TRANSIENT_SUBSTRINGS`): Automatically retries HTTP 429, 502, 503, rate limits, network timeouts, and server errors.
* **Provider Fallback (`SubstrateRouter.route`)**:
  If primary provider generation fails after retries, `SubstrateRouter` attempts execution against `FALLBACK_PROVIDER` (if configured and distinct from primary).
* **Offline Mock Fallback (`QAChatAgent._fallback_llm`)**:
  If AI substrate router is unavailable, `QAChatAgent` gracefully falls back to deterministic mock responses based on prompt keywords (`verdict`, `idiom`, `divergence`).

---

### 4.4 Thread Safety in Agent Execution State

* **SQLite Thread-Local Connections (`cherenkov/chat/adapters/sqlite_memory.py`)**:
  Uses `threading.local()` to maintain per-thread SQLite connections:
  ```python
  def _connect(self) -> sqlite3.Connection:
      con = getattr(self._local, "con", None)
      if con is not None:
          try:
              con.execute("SELECT 1")
              return con
          except Exception:
              ...
      con = sqlite3.connect(self.db_path, timeout=30.0)
      con.execute("PRAGMA journal_mode=WAL")
      con.execute("PRAGMA foreign_keys = ON")
      self._local.con = con
      return con
  ```
  `PRAGMA journal_mode=WAL` (Write-Ahead Logging) and `timeout=30.0` allow concurrent thread reads and serial writes without database locking errors.

---

## 5. Architectural Strengths & Technical Debt

### 5.1 Architectural Strengths
1. **Clean Architecture Adherence**: Modules strictly adhere to Domain, Ports, Adapters, and Use Cases structure per ADR-004.
2. **Robust Multi-Tenant Thread Safety**: SQLite conversation memory handles multi-threaded access seamlessly via thread-local connections and WAL mode.
3. **Hardware-Aware VLM Tiering**: Intelligent fallback and recommendations in Doctor CLI for local vs cloud VLM backends (LocalAI / Ollama / OpenAI).
4. **Enterprise Egress & Budget Controls**: `SubstrateRouter` enforces E12 gold-set certification, network egress boundaries, and cost accounting before dispatching AI calls.

---

### 5.2 Technical Debt & Recommendations

| # | Subsystem / Location | Issue Description | Impact / Severity | Recommended Remediation |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `cherenkov/substrate/provider.py:264`, `cherenkov/substrate/providers/localai.py` | `LocalAIVLMProvider` duck-types `VLMProvider` without explicit protocol inheritance (`# TODO(#type-debt)` comment). | Medium (Type safety violation) | Have `LocalAIVLMProvider` explicitly inherit from `VLMProvider` or implement `cherenkov.ports.vlm_provider.VLMProvider` protocol. |
| 2 | `cherenkov/substrate/providers/vlm.py:25,32` | `VLMProvider` adapter calls nonexistent methods `OldVLM().describe_image` and `compare_images` (`# TODO(#type-debt)` comment). | High (Broken adapter) | Fix `substrate/providers/vlm.py` to forward calls to `LocalAIVLMProvider` or update `substrate/vlm_provider.py` method signatures. |
| 3 | `cherenkov/chat/agent.py:98-103` | Pseudo-streaming: `chat_stream()` awaits full text from LLM before splitting string and yielding tokens. | Low (User latency / UX) | Connect `chat_stream` directly to the streaming socket generator of Ollama/OpenAI clients. |
| 4 | `cherenkov/agents/conductor/adapters/mcp_conductor.py:47` | Conductor uses synchronous `ThreadPoolExecutor` for MCP sub-tasks. | Medium (Concurrency bottleneck) | Migrate `MCPConductor` to native `asyncio` (`asyncio.gather`) using async MCP client transport. |
| 5 | `cherenkov/agents/conductor/use_cases/aggregate.py:55` | `MergeStrategy.WEIGHTED` is unfulfilled placeholder logic falling back to plain union. | Low (Feature incomplete) | Implement LLM-as-judge scoring for weighted result aggregation. |
| 6 | `cherenkov/substrate/doctor.py` vs `cherenkov/stages/doctor_cmd.py` | Code duplication between Substrate doctor CLI checks and Stage doctor health check command. | Low (Maintenance overhead) | Consolidate core detection routines into `cherenkov/core/devices.py` or shared substrate diagnostics module. |

---

## 6. Verification Method

To verify the audit findings and validate the stability of Subsystem 4, execute the following commands in the workspace environment:

1. **Run Unit Test Suite for Subsystem 4**:
   ```bash
   pytest tests/unit/test_agent_conductor.py tests/unit/test_chat.py tests/unit/test_doctor.py tests/unit/test_localai_vlm.py -v
   ```
2. **Execute Doctor CLI Diagnostic Verification**:
   ```bash
   python -m cherenkov.substrate.doctor --json-output
   ```
3. **Verify Conductor Templates & Decomposition**:
   Inspect `cherenkov/agents/conductor/templates/review_team.py`, `audit_team.py`, `generate_team.py`.

---
*Report compiled by Explorer 4 — Read-only Investigation Complete.*
