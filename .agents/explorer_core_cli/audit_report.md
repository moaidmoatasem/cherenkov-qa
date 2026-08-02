# Subsystem 1 Deep-Dive Audit Report: Core CLI, Engine, Clean Architecture, Ports & Adapters, and System Engine

**Target Subsystem:** Core CLI, Engine, Clean Architecture, Ports & Adapters, and System Engine  
**Auditor:** Explorer 1  
**Project Root:** `Z:\home\moaid\cherenkov-qa`  
**Working Directory:** `Z:\home\moaid\cherenkov-qa\.agents\explorer_core_cli`  
**Date:** 2026-08-02  

---

## Executive Summary

This deep-dive architectural and code audit assesses **Subsystem 1** of **CHERENKOV-QA**, encompassing the Core CLI pipeline, Execution Engine, Stage Executor, Configuration resolution system, Domain Model contracts, Ports & Adapters (ADR-004 compliance), and cross-cutting System Engine capabilities.

The audit confirms that CHERENKOV-QA possesses a highly resilient, battle-tested execution foundation built around clean boundaries, explicit Pydantic v2 contracts, fallback retry ladders, and zero vendor lock-in (Anti-lock-in / D7 invariant). The newer sub-domains (`cherenkov/memory/`, `cherenkov/hooks/`, `cherenkov/chat/`, `cherenkov/agents/conductor/`) strictly implement the 5-layer Ports & Adapters pattern mandated by **ADR-004**. Legacy execution components (such as `cherenkov/core/orchestrator.py` and `cherenkov/execution/validate.py`) maintain strong fault-tolerance via circuit breakers and structured logging, though they reflect historical evolution where CLI handlers occasionally orchestrate complex multi-stage workflows directly.

---

## 1. Architecture & Clean Architecture (ADR-004 Compliance)

### 1.1 Adherence to Ports & Adapters Specification (ADR-004)
ADR-004 establishes Hexagonal / Ports & Adapters Architecture across all CHERENKOV-QA modules:
```
cherenkov/{module}/
├── domain/          # Pure business logic, Pydantic models, no I/O
├── ports/           # Protocol / ABC interfaces ("what", not "how")
├── adapters/        # Concrete I/O implementations (SQLite, Redis, Docker, SSH)
├── use_cases/       # Orchestration of domain + ports
└── api/             # Thin FastAPI routes / CLI commands
```

#### Verification of Module Boundaries:
1. **`cherenkov/memory/`**:
   - `domain/models.py`: Defines `MemoryEntry`, `MemoryQuery`, `PatternCandidate`. Pure domain data, zero external dependencies.
   - `ports/repository.py`: Defines `MemoryRepository(Protocol)` interface (`store`, `search`, `promote`).
   - `adapters/sqlite_memory.py` & `adapters/memsearch_memory.py`: Implements SQLite FTS5 storage and MemSearch vector integration.
   - `use_cases/collect.py` & `use_cases/promote.py`: Encapsulates business actions.
2. **`cherenkov/hooks/`**:
   - `domain/models.py`: `HookEvent`, `HookAction`, `HookResult`.
   - `ports/executor.py`: `HookExecutor(Protocol)`.
   - `adapters/subprocess_executor.py`: Implements process-level hook execution.
   - `registry.py`: Manages event-driven hook dispatching configured via `cherenkov.toml`.
3. **`cherenkov/ports/` & `cherenkov/adapters/` (Core Level)**:
   - Interface protocols in `cherenkov/ports/`: `DeviceRegistry`, `EventBus`, `KnowledgeRepository`, `NotifierPort`, `RemoteRunnerPort` (`abc.ABC`), `VLMProvider`.
   - Concrete implementations in `cherenkov/adapters/`: `DockerRunner`, `SSHRunner`, `QwenCodeEventBus`, `notifiers/*` (Slack, Teams, Linear, PagerDuty, OpsGenie).

### 1.2 Dependency Rule Analysis
```
domain/  <───  ports/  <───  adapters/  <───  use_cases/  <───  cli / api / core
 (Pure)       (Protocol)     (Concrete)       (Application)      (Entrypoints)
```
- **Inward Dependency Flow**: Modules in `cherenkov/memory` and `cherenkov/hooks` strictly obey dependency inversion. Ports depend on domain models; adapters import ports and domain models; use cases inject ports; CLI/API endpoints wire adapters to use cases.
- **Contract Enforcement**: Stage boundaries in `cherenkov/core/contracts.py` act as typed gateways between execution stages. Data passed between stages (`IngestOutput`, `PlanOutput`, `GenerateOutput`, `ReviewOutput`) must conform to Pydantic v2 schemas.

---

## 2. System Design & Core Engine Architecture

### 2.1 CLI Invocation Pipeline
The CLI entry pipeline follows a lazy registration design to optimize startup performance:

```
[CLI Invocation]
       │
       ▼
cherenkov/__main__.py: main()
       │
       ▼
cherenkov/cli/core.py: main()
 ├── 1. Rewrite bare flags (e.g. `--spec foo.yaml` → `validate --spec foo.yaml`)
 ├── 2. _register_commands(): Lazily imports subcommands (validate, verify, audit, etc.)
 └── 3. cli(): Executes Click command hierarchy
```

#### Command Registration snippet (`cherenkov/cli/core.py`):
```python
def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("-") and "--spec" in sys.argv[1:]:
        sys.argv.insert(1, "validate")
    _register_commands()
    cli()
```
*Key Detail*: Lazy imports in `_register_commands()` prevent loading heavy dependencies (e.g., Playwright, PyTorch/VLM, FastAPI, SQLite engines) until a specific command is executed.

### 2.2 Layered Configuration Resolution & Provenance Model
Configuration resolution is managed by `LayeredConfig` in `cherenkov/core/config_loader.py` and backed by structured defaults in `cherenkov/core/config.py`.

#### Precedence Hierarchy (Lowest → Highest):
1. **Built-in Defaults**: Defined in `BUILTIN_DEFAULTS` (`profile="laptop"`, egress="internal", small/deep tiers using `ollama`/`qwen2.5-coder:7b`).
2. **Profile Overrides**: Selected profile (`laptop`, `ci`, `enterprise-vpc`, `frontier-cloud`) overrides default values.
3. **Project File (`cherenkov.toml`)**: Walked up from CWD; validated against `KNOWN_KEYS`.
4. **Environment Variables (`CHERENKOV_*`)**: Environment variable overrides.
5. **CLI Overrides**: Explicit CLI flags passed at invocation time.

#### Provenance Tracking (`cherenkov/core/config_loader.py`):
Every setting records its origin (`source`) so `cherenkov doctor` can report exactly which layer configured a value:
```python
def _set(self, key: str, value: Any, source: str):
    if key not in self._store:
        self._store[key] = []
    self._store[key].append((source, value))

def get_with_provenance(self, key: str) -> list[tuple[str, Any]]:
    return self._store.get(key, [])
```

### 2.3 Execution Engine & Workflow Orchestration

The system execution flow operates through two main orchestration engines:
1. `OrchestrationEngine` (`cherenkov/core/orchestrator.py`): DAG Orchestration for synthetic test generation and verification.
2. `ValidationEngine` (`cherenkov/execution/validate.py`): Execution of generated Playwright suites against live targets.

#### DAG Workflow Lifecycle (`OrchestrationEngine`):
```
[IngestStage] ──► [PlanStage] ──► [ThreadPoolExecutor: Scenario Workers]
                                    ├── Scenario 1: GenerateStage ──► ReviewStage
                                    ├── Scenario 2: GenerateStage ──► ReviewStage
                                    └── Scenario N: ...
                                              │
                                              ▼ (D2 Feedback Loop if dry-run fails)
                                  [Post Evals & Adversarial Scans]
                                              │
                                              ▼
                                  [Stats & Metrics Persisted]
```

#### Stage Execution & Circuit Breaker (`cherenkov/core/stage_executor.py`):
Stage execution is wrapped by `StageExecutor`, which implements a exponential backoff retry ladder and records failures to a `CircuitBreaker`.

```python
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

If a stage fails schema validation or raises an exception:
- Up to 3 retry attempts are made with exponential backoff + jitter: `wait = (2**attempts) * 0.5 + random.uniform(0, 0.5)`.
- If max attempts are exhausted, `CircuitBreaker.record_failure()` is called and a fallback factory payload is returned.
- If total error count hits `threshold`, the breaker trips and aborts downstream DAG execution.

---

## 3. Comprehensive Design Patterns Catalog

| Pattern | Implementation File(s) | Concrete Mechanism & Usage |
|:---|:---|:---|
| **Dependency Injection** | `cherenkov/hooks/registry.py`, `cherenkov/adapters/docker_runner.py`, `cherenkov/core/orchestrator.py` | Abstract port interfaces (`RemoteRunnerPort`, `EventBus`, `HookExecutor`) are injected into use cases and engines via constructors. |
| **Strategy Pattern** | `cherenkov/adapters/docker_runner.py` vs `ssh_runner.py`; `cherenkov/ports/vlm_provider.py`; `cherenkov/execution/emitters/*` | `RemoteRunnerPort` provides selectable strategy implementations for containerized vs. SSH remote execution. Emitters provide SARIF, JUnit, HTML, Allure export strategies. |
| **Command Pattern** | `cherenkov/cli/core.py`, `cherenkov/cli/commands/*.py` | Encapsulates CLI operations into discrete Click command handlers (`validate_cmd`, `audit_cmd`, `verify_cmd`, `synthetic_cmd`). |
| **Registry Pattern** | `cherenkov/cli/core.py` (`_register_commands`), `cherenkov/hooks/registry.py` (`HookRegistry`), `cherenkov/adapters/notifiers/registry.py` | Centralized lookup registries for CLI subcommands, lifecycle hooks, and notification targets. |
| **Adapter Pattern** | `cherenkov/sources/graphql/adapter.py`, `cherenkov/sources/grpc/adapter.py`, `cherenkov/adapters/postman_importer.py` | Adapts heterogeneous external specs (GraphQL SDL, gRPC Protos, Postman Collections, OpenAPI) into normalized internal `EndpointSlice` models. |
| **Observer Pattern** | `cherenkov/core/events.py`, `cherenkov/ports/event_bus.py`, `cherenkov/adapters/qwen_code_event_bus.py` | `CHERENKOVEvent` publisher/subscriber mechanism decoupling core pipeline execution from UI notifications, metrics logging, and external integrations. |
| **Circuit Breaker** | `cherenkov/core/stage_executor.py` (`CircuitBreaker`), `cherenkov/core/d2_controller.py` (`D2FeedbackController`) | Stateful thread-safe circuit breaking preventing cascade failures during scenario generation and dry-run execution. |
| **Factory Pattern** | `cherenkov/core/certificate.py` (`issue_certificate`), `cherenkov/core/stage_executor.py` (`fallback_factory`) | Encapsulates object creation for verification certificates and contract fallback outputs. |

---

## 4. Code Quality, Thread Safety & Error Handling Analysis

### 4.1 Typed Exception Hierarchy
CHERENKOV-QA enforces a strict typed exception policy rooted at `CherenkovError` in `cherenkov/core/errors.py`. Bare `raise Exception` is prohibited in core pipeline code.

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

CLI exit status code mapping is cleanly encapsulated via `ExitCode(IntEnum)`:
```python
class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    VALIDATION_ERROR = 2
    CONFIG_ERROR = 3
    NETWORK_ERROR = 4
```

### 4.2 Thread Safety & Concurrency Safeguards
- **Per-Thread Event Logging**: `cherenkov/core/errors.py` uses `threading.local` (`_tl.events_file`) to ensure concurrent pipeline runs in multi-threaded environments (or unit test runners) do not cross-contaminate log event files.
- **Thread Lock Guards**: `threading.Lock` is explicitly utilized across shared stateful components:
  - `CircuitBreaker._lock` in `cherenkov/core/stage_executor.py`
  - `RunBudget._lock` in `cherenkov/core/budget.py`
  - `_budget_lock` in global budget allocator
  - `D2FeedbackController` replan metrics
  - `StatsStore` SQLite persistence

### 4.3 Error Propagation & Boundary Protection
Stage boundary protection is strictly enforced by `StageExecutor.execute()`. When a stage function finishes, the executor verifies that the return object is an instance of `_PIPELINE_OUTPUT_TYPES` (`IngestOutput`, `PlanOutput`, `GenerateOutput`, `ReviewOutput`). If invalid, a `ContractError` is raised immediately, preventing unvalidated raw dicts or None values from corrupting downstream stages.

```python
if not isinstance(result, _PIPELINE_OUTPUT_TYPES):
    raise ContractError(f"Stage {stage_name} returned unvalidated raw types.")
```

---

## 5. Architectural Strengths, Technical Debt & Actionable Improvements

### 5.1 Key Architectural Strengths
1. **Strict Clean Architecture (ADR-004)**: All newly introduced modules (`memory`, `hooks`, `chat`, `agents/conductor`) cleanly isolate domain logic from external frameworks, databases, and I/O.
2. **Resilient DAG Execution**: The combination of `StageExecutor` retry ladders, exponential backoff with jitter, fallback factories, and `CircuitBreaker` bounds prevents catastrophic crashes during long test generation runs.
3. **Layered Config with Full Provenance**: The 5-layer resolution model (`LayeredConfig`) allows effortless configuration override from environment or TOML, while preserving complete traceability for debugging (`cherenkov doctor`).
4. **Verifiable Trust Certification**: `VerificationCertificate` (`cherenkov/core/certificate.py`) provides SHA-256 fingerprinting and HMAC signing mapped directly to regulatory frameworks (EU AI Act Art. 9/12/13, SOC 2 CC4.1/CC6.7/CC7.2, ISO 25010/42001, OWASP LLM Top 10).
5. **Anti-Lock-In (D7 Invariant)**: Ejected tests are standalone Playwright TypeScript files that execute independently without requiring the CHERENKOV framework or CLI.

### 5.2 Technical Debt & Areas for Improvement

| Area | Observation / Debt | Risk Level | Recommended Refactoring / Improvement |
|:---|:---|:---:|:---|
| **CLI Command Monoliths** | `cherenkov/cli/commands/validate.py` (318 lines) mixes Click parameter definition with spec preflight validation, GraphQL/gRPC planning, manifest recording, emitter formatting, and exit code handling. | **Medium** | Extract CLI command orchestration logic into a dedicated `use_cases/validate_suite.py` application layer file, keeping CLI handlers thin. |
| **Sync / Async Boundary Split** | `OrchestrationEngine` relies on synchronous `ThreadPoolExecutor` and blocking `time.sleep()`, whereas newer adapters (`DockerRunner`, `SSHRunner`) utilize `asyncio`. | **Low-Medium** | Migrate `OrchestrationEngine` to leverage native `asyncio` event loops with `asyncio.gather` for parallel scenario execution. |
| **Dual Degradation Abstractions** | `cherenkov/core/error_handling.py` provides `GracefulDegradation` and `HealthStatus` (boolean health check dicts), while `StageExecutor` uses exception-based `CircuitBreaker`. | **Low** | Consolidate `GracefulDegradation` with `CircuitBreaker` under a unified system health & resilience port. |
| **Legacy Directory Structures** | Sub-directories like `cherenkov/execution/` and `cherenkov/stages/` contain mixed concerns dating before ADR-004 adoption. | **Low** | Gradually wrap legacy stage executors behind Clean Architecture `use_cases/` without breaking external API contracts. |

---

## Conclusion

Subsystem 1 (Core CLI, Engine, Clean Architecture, Ports & Adapters, and System Engine) exhibits robust software engineering, high type safety, clear fault-tolerance mechanisms, and comprehensive adherence to project design invariants. The codebase provides a solid, extensible platform for AI-native API testing and continuous validation.
