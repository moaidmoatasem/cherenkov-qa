# CHERENKOV-QA System Design

**Date:** 2026-06-08
**Status:** Active
**Related EPIC:** #277 (Phase -1)

---

## Overview

CHERENKOV-QA is an API conformance testing platform that generates Playwright tests from OpenAPI specs and validates them against real servers. The system follows Clean Architecture (Ports/Adapters) and is designed for extensibility, testability, and anti-lock-in.

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

## Module Structure

### Core Modules

| Module | Purpose | Location |
|--------|---------|----------|
| `core/` | Orchestrator, config, contracts, errors | `cherenkov/core/` |
| `substrate/` | Model providers, routing, certification | `cherenkov/substrate/` |
| `stages/` | Pipeline stages (ingest, plan, generate, review) | `cherenkov/stages/` |
| `execution/` | Test execution, ejection | `cherenkov/execution/` |
| `healing/` | Failure diagnosis, suggestions | `cherenkov/healing/` |

### Extended Modules

| Module | Purpose | Location |
|--------|---------|----------|
| `knowledge/` | Second Brain, GraphRAG, knowledge mesh | `cherenkov/knowledge/` |
| `chat/` | Chat agent, conversation memory, tools | `cherenkov/chat/` |
| `mobile/` | Mobile testing, Maestro/Appium | `cherenkov/sources/mobile/` |
| `divergence/` | Divergence detection, self-play | `cherenkov/divergence/` |
| `reflector/` | Learning from verdicts, idioms | `cherenkov/reflector/` |

---

## Data Flow

```
OpenAPI Spec
    ↓
[Ingest Stage] → Parse spec, extract endpoints
    ↓
[Plan Stage] → Generate test scenarios
    ↓
[Generate Stage] → Generate Playwright tests (LLM)
    ↓
[Review Stage] → 6-gate review (syntax, structure, AST, assertions, tsc, Prism)
    ↓
[Validate Stage] → Run tests against real server
    ↓
[Eject Stage] → Export standalone Playwright tests
```

---

## Data Stores

| Store | Format | Purpose | Location |
|-------|--------|---------|----------|
| `verdicts.db` | SQLite | Test verdicts | `data/verdicts.db` |
| `hitl.db` | SQLite | HITL queue | `data/hitl.db` |
| `feedback.json` | JSON | Human feedback | `data/feedback.json` |
| `knowledge.db` | SQLite | Knowledge mesh | `data/knowledge.db` |
| `chat.db` | SQLite | Chat sessions | `data/chat.db` |
| `agent_memory/` | Markdown | Agent wiki | `agent_memory/` |
| `incidents/` | JSON | Incident reports | `incidents/` |

---

## Contracts

### ReasoningRequest

```python
@dataclass
class ReasoningRequest:
    task: str
    output_schema: dict
    capability_tier: str  # "small", "deep", "vision"
    max_cost: float
    max_latency: float
    sensitivity: str  # "none", "internal", "any"
```

### Verdict

```python
@dataclass
class Verdict:
    verdict: Literal["AUTO_APPROVE", "HITL", "REGENERATE"]
    confidence: float
    reason: str
    test_path: str
```

### KnowledgeResult

```python
@dataclass
class KnowledgeResult:
    data: Any
    source: str  # "verdicts", "idioms", "incidents", "hitl", "feedback", "agent_memory"
    confidence: float
    metadata: dict[str, Any]
```

---

## Seams

| Seam | Version | Defined In | Producer | Consumer |
|------|---------|------------|----------|----------|
| Reasoning | - | `core/contracts.py` | Every stage | `substrate/` router |
| Verdict | - | `core/contracts.py` | `stages/review.py` | Emitters, `hitl/` |
| hitl/v1 | `hitl/v1` | `hitl/contracts.py` | `hitl/store.py` | Dashboard, CLI |
| validate/v1 | `validate/v1` | `validate/contracts.py` | `validate/gate.py` | CI, 5-QA runbook |
| knowledge/v1 | `knowledge/v1` | `knowledge/ports/repository.py` | `knowledge/adapters/` | Chat, Dashboard |
| chat/v1 | `chat/v1` | `chat/ports/memory.py` | `chat/adapters/` | Chat agent |
| mobile/eject/v1 | `mobile/eject/v1` | `execution/mobile_eject_*.py` | Mobile stages | Maestro, Appium |
| vlm/v1 | `vlm/v1` | `substrate/ports/vlm_provider.py` | `substrate/providers/` | Visual oracle |

---

## Design Patterns

### Strategy Pattern

VLM Router selects provider based on DeviceClass → VLMTier:

```python
router = SubstrateRouter(device_class=DeviceClass.GPU_WORKSTATION)
provider = router.get_vlm_provider()  # Returns LocalAIVLMProvider
```

### Repository Pattern

KnowledgeRepository abstracts storage:

```python
repo = SQLiteKnowledgeRepository()  # or RedisKnowledgeRepository
result = repo.query(KnowledgeQuery(query="auth timeout"))
```

### Observer Pattern

Event bus for coordination:

```python
event_bus = AsyncQueueEventBus()
event_bus.subscribe("HITLDecisionMade", handler)
event_bus.emit(HITLDecisionMade(item_id="123", action="approve"))
```

### Circuit Breaker

Pilot agent has max observations and timeout:

```python
pilot = PilotAgent(runner, max_observations=20, timeout_seconds=300)
```

---

## Extension Points

### Adding a New Testing Type

1. **Create Source Adapter**:
```python
class AccessibilitySourceAdapter:
    def ingest(self, url: str) -> AccessibilityReport:
        pass
```

2. **Create Stage**:
```python
class AccessibilityPlanStage:
    def plan(self, report: AccessibilityReport) -> list[dict]:
        pass
```

3. **Create Oracle**:
```python
class AccessibilityOracle:
    def validate(self, test_result: dict) -> dict:
        pass
```

### Adding a New Model Provider

1. **Implement VLMProvider Protocol**:
```python
class CustomVLMProvider:
    def analyze(self, image: bytes, prompt: str) -> VLMResponse:
        pass

    def is_available(self) -> bool:
        pass

    def get_tier(self) -> str:
        return "custom"
```

2. **Register in Router**:
```python
self.custom = CustomVLMProvider()

def get_vlm_provider(self):
    if self.custom.is_available():
        return self.custom
```

---

## Configuration

Layered configuration (defaults → profile → cherenkov.toml → env → CLI):

```toml
# cherenkov.toml
[substrate]
provider = "localai"
egress = "none"

[vlm]
tier = "small"

[redis]
enabled = false

[desktop]
port = 8000
host = "localhost"

[logging]
level = "INFO"
format = "json"
```

---

## Deployment

### Local (Development)

```bash
# Start LocalAI + Redis + CHERENKOV
docker compose -f docker-compose.ai.yml up -d

# Run pipeline
cherenkov validate --spec petstore.yaml --target http://localhost:8000
```

### K8s (k3d)

```bash
# One-time setup: build images + create cluster
make k3d-up

# Run integration tests
make k3d-test

# Tear down
make k3d-down
```

### Production (Full K8s)

```bash
# Deploy CRDs
kubectl apply -f operator/config/crd/bases/

# Deploy operator
kubectl apply -f operator/config/rbac/
kubectl apply -f operator/config/manager/

# Create a ConformanceCheck resource
kubectl apply -f conformancecheck.yaml
```

---

## Kubernetes Operator

CHERENKOV includes a **Kubernetes operator** that manages `ConformanceCheck` custom resources. When a `ConformanceCheck` is created, the operator spawns a validation Job, tracks its progress, and reports results back to the resource status.

### CRD: ConformanceCheck

```yaml
apiVersion: validation.cherenkov.io/v1alpha1
kind: ConformanceCheck
spec:
  targetRef:                    # Required: the K8s resource to validate
    apiVersion: apps/v1
    kind: Deployment
    name: my-api
    namespace: default
    port: 8080
  specRef: "petstore-spec"      # ConfigMap containing the OpenAPI spec
  schedule: "*/30 * * * *"     # Optional: cron schedule for recurring checks
  gates:                        # Optional: specific gates to validate
    - name: "status-codes"
      type: "conformance"
      assert: "all responses match spec"
  llmConcurrency: 2             # Optional: max concurrent LLM tasks (1-16)
  deviceTargets:                # Optional: mobile/web device targets
    - platform: "android"
      osVersion: "14"
      deviceName: "pixel_7"
      browser: "chrome"
      viewportSize:
        width: 1080
        height: 1920
  visualConfig:                 # Optional: visual testing config
    enabled: true
    vlmProvider: "localai"
    threshold: 0.95
    screenshotOnFail: true
    diffMethod: "ssim"
```

### Reconciler Flow

```
ConformanceCheck created (phase="")
        │
        ▼
Phase=Pending ──► Acquire concurrency slot
        │              │
        │              ▼
        │         Create validate Job
        │              │
        ▼              ▼
Phase=Running ──► Watch Job status
        │              │
        ├── Job Complete ──► Phase=Pass ✓
        ├── Job Failed   ──► Phase=Fail ✗
        └── Job Error    ──► Phase=Error ⚠
```

### Operator Architecture

```
┌──────────────────────────────────────────┐
│  Controller Manager (operator/main.go)    │
│  ┌────────────────────────────────────┐   │
│  │ ConformanceCheckReconciler         │   │
│  │  ├─ Get CR → determine phase       │   │
│  │  ├─ TryAcquire scheduler slot      │   │
│  │  ├─ Create/validate Job via Runner │   │
│  │  └─ Update status + emit events    │   │
│  ├────────────────────────────────────┤   │
│  │ Scheduler (concurrency limiter)    │   │
│  │  └─ MAX_CONCURRENT_LLM_TASKS env   │   │
│  ├────────────────────────────────────┤   │
│  │ JobRunner                          │   │
│  │  └─ Creates batch/v1 Job pods      │   │
│  │     └─ Mounts spec ConfigMap       │   │
│  │     └─ Injects env vars            │   │
│  └────────────────────────────────────┘   │
│  Health: /healthz, /readyz                │
│  Metrics: /metrics (:8080)                │
└──────────────────────────────────────────┘
```

### CLI Bridge (`k8s-run`)

A Go CLI tool that creates a `ConformanceCheck` CR and polls for results:

```bash
k8s-run --spec petstore-spec --target prism --port 4010 --timeout 60s
```

### K8s Manifests (`k8s/`)

| File | Purpose |
|------|---------|
| `namespace.yaml` | `cherenkov` namespace |
| `petstore-configmap.yaml` | Inline OpenAPI spec |
| `ollama-pvc.yaml` | 20Gi PVC for models |
| `ollama-service.yaml` | ClusterIP port 11434 |
| `ollama-statefulset.yaml` | GPU-backed Ollama |
| `ollama-init-job.yaml` | Pre-pull models |
| `prism-deployment.yaml` | Mock API server |
| `prism-service.yaml` | ClusterIP port 4010 |
| `cherenkov-deployment.yaml` | Engine daemon |
| `cherenkov-service.yaml` | ClusterIP port 8000 |
| `operator-rbac.yaml` | SA + ClusterRole + binding |
| `operator-deployment.yaml` | Operator pod |
| `crd-conformancecheck.yaml` | CRD definition |
| `k3d-cluster.yaml` | k3d cluster config |
| `kustomization.yaml` | Kustomize overlay |

---

## Security

- **Egress policy**: `none` (no outbound), `internal` (localhost only), `any` (allow cloud)
- **Input validation**: Strip control chars, reject non-UTF8
- **Rate limiting**: 20 req/min, 100 messages/session
- **Token budget**: Max 4000 tokens per chat message
- **No secrets in code**: All secrets via environment variables

---

## Performance Baselines

| Module | Baseline | Notes |
|--------|----------|-------|
| VLM request (LocalAI) | < 10s for 1280×720 PNG | GPU required |
| Knowledge query (SQLite) | < 500ms for 1000-record DB | Full-text search |
| Chat response (short) | < 5s first token | LocalAI or Ollama |
| Dashboard API (`/overview`) | < 200ms p95 | SQLite queries |
| Desktop startup (cold) | < 8s to window visible | Tauri 2 + sidecar |

---

## Testing Strategy

- **Unit tests**: 500+ tests, >80% coverage
- **Contract tests**: 50+ tests, all adapters pass same tests
- **Integration tests**: 50-100 tests, cross-module integration
- **E2E tests**: 5-10 tests, golden paths only
- **Smoke tests**: 10+ tests, CLI commands work

---

## References

- `docs/PHASE_PLAN.md` (Consolidated plan)
- `docs/adr/ADR-004-clean-architecture.md` (Clean Architecture)
- `docs/vision/01_ARCHITECTURE.md` (Existing architecture)
- `docs/vision/09_WIRING_SCHEMA.md` (Existing seams)
