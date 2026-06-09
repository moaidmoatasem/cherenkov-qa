# Architecture

> **Navigation:** [Home](Home.md) · [Pipeline](Pipeline.md) · **Architecture** · [CLI Reference](CLI-Reference.md) · [Configuration](Configuration.md) · [Deployment](Deployment.md) · [Roadmap](Roadmap.md) · [FAQ](FAQ.md) · [Troubleshooting](Troubleshooting.md)

CHERENKOV is built in three layers: a **CLI** on the outside, a **domain** in the middle, and **infrastructure adapters** at the edges. Nothing in the domain layer imports from infrastructure — the Clean Architecture boundary is enforced by ADR-004.

---

## System Overview

```mermaid
graph TB
    subgraph CLI ["🖥️  CLI Layer  (cherenkov.py)"]
        direction LR
        VALIDATE[validate]
        EJECT[eject]
        HEAL[heal]
        CHAT[chat]
        DAEMON[daemon]
        DOCTOR[doctor]
        REVIEW_WEB[review --web]
    end

    subgraph ORCH ["⚙️  Orchestration  (cherenkov/core/)"]
        ORC[Orchestrator]
        STAGES[Pipeline Stages]
        EVENTS[Event Bus]
    end

    subgraph DOMAIN ["📐  Domain  (pure Python — no I/O)"]
        TRUTH[Truth Model\nOpenAPI · Traffic · DB Schema]
        ORACLE[Verdict Oracle\nSpec-derived expected status]
        CONTRACTS[Contracts\nPydantic models]
        KNOWLEDGE[Knowledge Mesh\nGraphRAG · Second Brain]
        DIVERGENCE[Divergence Engine\nSelf-play · Proof runs]
    end

    subgraph ADAPTERS ["🔌  Ports & Adapters"]
        LLM[LLM Router\nOllama · LocalAI · OpenAI]
        PLAYWRIGHT[Playwright\nRunner]
        PRISM[Prism\nMock Server]
        K8S[K8s Operator\nConformanceCheck CRD]
        SNYK[Snyk\nSecurity Bridge]
    end

    subgraph INTERFACES ["🎨  User Interfaces"]
        WEB[React Dashboard\n9 screens · Vite + TypeScript]
        MCP_S[MCP Server\nIDE & agent integration]
        CHAT_I[Chat Agent\nSSE streaming]
    end

    CLI --> ORCH
    ORCH --> DOMAIN
    DOMAIN --> ADAPTERS
    CLI --> INTERFACES
    INTERFACES --> ORCH
```

---

## Directory Map

```
cherenkov-qa/
│
├── cherenkov.py              ← Main CLI (all commands live here)
├── bin/cherenkov             ← Shell wrapper (invokes cherenkov.py)
│
├── cherenkov/                ← Main Python package
│   ├── core/                 ← Orchestrator · contracts · config · errors
│   ├── stages/               ← ingest → plan → generate → review → validate
│   ├── execution/            ← validate · eject · playwright_invoke · trace
│   ├── healing/              ← diagnose · auth_expiry · contract_drift · sandbox
│   ├── divergence/           ← skeptic · witness · self_play · proof_run
│   ├── truth/                ← truth model · index · emitters
│   ├── sources/              ← openapi · traffic · mobile · db_schema
│   ├── knowledge/            ← knowledge_mesh · graph_rag · schema_index
│   ├── ai/                   ← router · ollama_client · accounting · cache
│   ├── agents/               ← pilot · exploration agents
│   ├── chat/                 ← chat agent · tool-calling · conversation memory
│   ├── mcp/                  ← MCP protocol server
│   ├── governance/           ← KPI · certification · audit
│   ├── compliance/           ← MENA · governance scanning
│   ├── continuity/           ← PR diff tracking
│   ├── federation/           ← cross-check · protocol · corpus
│   ├── hitl/                 ← human-in-the-loop queue
│   ├── observability/        ← metrics · structured logging · Logfire
│   ├── security/             ← Snyk bridge
│   ├── oracle/               ← verdict oracle · expected status resolver
│   ├── reflector/            ← learning from verdicts · idiom extraction
│   ├── substrate/            ← provider certification · routing logic
│   ├── ports/                ← adapter port interfaces (Ports/Adapters)
│   └── web/ui/               ← React dashboard (Vite · TypeScript · Tailwind)
│
├── operator/                 ← Go K8s operator (ConformanceCheck CRD)
├── engine/                   ← Engine service (spec loader · validator)
├── stub/                     ← Test fixtures · generated tests · OpenAPI client
├── target/                   ← Sample target API (FastAPI)
├── tests/                    ← Test suite (smoke · unit · integration · e2e)
├── skills/                   ← Autonomous workflow instructions
└── docs/                     ← All documentation
```

---

## Pipeline Stages Detail

```mermaid
flowchart TD
    subgraph INGEST ["Stage 1 — Ingest"]
        I1[Parse OpenAPI 3.x spec]
        I2[Validate schema structure]
        I3[Extract endpoints · schemas · examples]
        I1 --> I2 --> I3
    end

    subgraph PLAN ["Stage 2 — Plan"]
        P1[Enumerate test scenarios]
        P2[Happy path per endpoint]
        P3[Edge cases: auth · validation · error]
        P4[Prioritize by risk]
        P1 --> P2 --> P3 --> P4
    end

    subgraph GENERATE ["Stage 3 — Generate"]
        G1[Build LLM prompt from scenario]
        G2[Local LLM inference\nOllama qwen2.5-coder:7b]
        G3[Parse generated TypeScript]
        G4[Inject openapi-fetch bindings]
        G1 --> G2 --> G3 --> G4
    end

    subgraph REVIEW ["Stage 4 — 6-Gate Review"]
        R1[Gate 1: Syntax check]
        R2[Gate 2: Structure check]
        R3[Gate 3: AST validation]
        R4[Gate 4: Assertion coverage]
        R5[Gate 5: TypeScript compile tsc]
        R6[Gate 6: Prism mock dry-run]
        R1 --> R2 --> R3 --> R4 --> R5 --> R6
    end

    subgraph VALIDATE ["Stage 5 — Validate"]
        V1[Playwright runner against live server]
        V2[Capture request · response · timing]
        V3[Oracle: compare vs spec-derived expected]
        V4[Tightening analysis]
        V1 --> V2 --> V3 --> V4
    end

    INGEST --> PLAN --> GENERATE --> REVIEW --> VALIDATE
```

---

## LLM Routing

CHERENKOV never hardcodes a model name. Agents emit a `ReasoningRequest` with a `capability_tier`; the Substrate Router picks the best available provider.

```mermaid
flowchart LR
    REQ["ReasoningRequest\n{capability_tier: 'code-gen'}"]

    subgraph ROUTER ["Substrate Router  (cherenkov/ai/router.py)"]
        T1[Tier: code-gen]
        T2[Tier: reasoning]
        T3[Tier: vision]
        T4[Tier: embedding]
    end

    subgraph PROVIDERS ["Providers"]
        OL["🏠 Ollama\nqwen2.5-coder:7b\n(default, free)"]
        LA["🐳 LocalAI\nGPU · VLM support"]
        OAI["☁️  OpenAI\nCloud fallback"]
    end

    REQ --> ROUTER
    T1 --> OL
    T2 --> OL
    T3 --> LA
    T4 --> LA
    OL -. "fallback" .-> LA
    LA -. "fallback" .-> OAI

    style OL fill:#dcfce7,stroke:#16a34a
    style LA fill:#dbeafe,stroke:#3b82f6
    style OAI fill:#fef9c3,stroke:#ca8a04
```

**Provider selection priority:**
1. Ollama (local, free, default)
2. LocalAI (local, Docker, VLM support)
3. OpenAI (cloud, paid, fallback only)

---

## Truth Model

The Truth Model is the source of expected behavior. It aggregates evidence from multiple sources to build a ground truth for what the API *should* do.

```mermaid
flowchart LR
    subgraph SOURCES ["Truth Sources"]
        SRC1["📄 OpenAPI Spec\n(primary source)"]
        SRC2["🌐 Traffic Capture\n(observed behavior)"]
        SRC3["🗄️  DB Schema\n(data constraints)"]
        SRC4["📱 Mobile Flows\n(UI paths)"]
    end

    subgraph TRUTH ["Truth Model  (cherenkov/core/truth_model.py)"]
        INDEX[Truth Index]
        ORACLE[Verdict Oracle\nSpec-derived status]
        DRIFT[Drift Detector\nDelta between sources]
    end

    SRC1 --> INDEX
    SRC2 --> INDEX
    SRC3 --> INDEX
    SRC4 --> INDEX
    INDEX --> ORACLE
    INDEX --> DRIFT
```

---

## Healing Architecture

Healing is **always suggest-only**. The D7 invariant is enforced: no automation ever modifies test code.

```mermaid
flowchart TD
    FAIL[Test Failure\nPlaywright result]

    subgraph DIAGNOSIS ["Diagnosis  (cherenkov/healing/)"]
        D1[Classify failure type]
        D2{Type?}
        D3[Auth expiry\nToken/session expired]
        D4[Contract drift\nSpec changed]
        D5[Server error\n5xx / timeout]
        D6[Assertion gap\nTest too loose]
    end

    subgraph OUTPUT ["Output — Suggest Only"]
        S1["📝 Fix suggestion\n(never auto-applied)"]
        S2["📊 Diagnosis report\n.cherenkov/heal/report.json"]
        S3["🔔 HITL notification\n(if queue enabled)"]
    end

    FAIL --> D1 --> D2
    D2 --> D3 --> S1
    D2 --> D4 --> S1
    D2 --> D5 --> S2
    D2 --> D6 --> S1
    S1 --> S2 --> S3
```

---

## K8s Operator

```mermaid
flowchart LR
    subgraph CLUSTER ["Kubernetes Cluster (k3d / production)"]
        CRD["ConformanceCheck CRD\nspec: {target, openapi-url}"]
        CTRL[Go Controller\noperator/controllers/]
        JOB[Kubernetes Job\ncherenkov validate]
        CM[ConfigMap\nResults]
    end

    subgraph CLI ["CLI Bridge"]
        K8SRUN[k8s-run\noperator/cmd/]
    end

    CRD --> CTRL --> JOB --> CM
    K8SRUN --> CRD

    style CRD fill:#dbeafe,stroke:#3b82f6
    style JOB fill:#dcfce7,stroke:#16a34a
```

Apply a `ConformanceCheck` manifest → the operator spins up a job → CHERENKOV runs → results land in a ConfigMap. No `kubectl exec` needed.

---

## Knowledge Mesh (Second Brain)

```mermaid
graph LR
    subgraph INPUTS ["Inputs"]
        CODE[Codebase\nfiles + symbols]
        SPECS[API Specs\nOpenAPI schemas]
        VERDICTS[Test Verdicts\npass/fail history]
        IDIOMS[Code Idioms\nextracted patterns]
    end

    subgraph MESH ["Knowledge Mesh  (cherenkov/knowledge/)"]
        GRAPH[Knowledge Graph\nentities + relationships]
        RAG[GraphRAG\nretrieval-augmented generation]
        IDX[Schema Index\nfast lookup]
    end

    subgraph CONSUMERS ["Consumers"]
        CHAT_C[Chat Agent\nQ&A over codebase]
        GEN_C[Test Generator\ncontext-aware generation]
        HEAL_C[Healer\nhistorical failure patterns]
    end

    CODE --> GRAPH
    SPECS --> IDX
    VERDICTS --> GRAPH
    IDIOMS --> GRAPH
    GRAPH --> RAG
    IDX --> RAG
    RAG --> CHAT_C
    RAG --> GEN_C
    RAG --> HEAL_C
```

---

## Clean Architecture Enforcement

Per [ADR-004](../adr/), domain logic never imports from infrastructure:

```
Domain layer (pure Python, no I/O):
  cherenkov/core/contracts.py     — Pydantic models
  cherenkov/oracle/               — verdict logic
  cherenkov/truth/                — truth model logic
  cherenkov/divergence/           — divergence detection

Infrastructure adapters (I/O allowed):
  cherenkov/ai/ollama_client.py   — Ollama HTTP calls
  cherenkov/execution/playwright_invoke.py — subprocess
  cherenkov/mcp/server.py         — network
  cherenkov/security/snyk_bridge.py — subprocess
```

The `cherenkov/ports/` directory defines the interfaces that adapters implement. Domain code only depends on the port interfaces, never on concrete adapter implementations.

---

## Design Invariants

These rules are **non-negotiable** and tested in CI on every push.

| Invariant | Enforcement |
|-----------|------------|
| **D7 — no auto-edit** | `smoke_test_healing.py` — asserts healing never writes test files |
| **Anti-lock-in** | `smoke_test_eject.py` — ejected tests run without CHERENKOV on PATH |
| **Spec-derived oracle** | `smoke_test_validate.py` — expected status from OpenAPI, never hardcoded |
| **Suggest-only healing** | `ci.yml: Healing Suggest-Only` job — required check on `main` |
| **Model-agnostic** | `test_substrate_providers.py` — no model name in domain code |

---

## Further Reading

- [ADR-001: Seam Widening](../adr/) — why we extend at seams, not cores
- [ADR-004: Clean Architecture](../adr/) — the Ports/Adapters boundary
- [ADR-005: Event-Driven Orchestration](../adr/) — why we use events
- [ADR-006: Knowledge Mesh](../adr/) — why a graph, not just a vector store
- [docs/engineering/SYSTEM_DESIGN.md](../engineering/SYSTEM_DESIGN.md) — full system design doc
