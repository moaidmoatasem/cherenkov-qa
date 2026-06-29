---
title: System Architecture Diagrams
description: 17 Mermaid diagrams covering CHERENKOV-QA's system context, AI pipeline, divergence loop, and more.
---

# System Architecture Diagrams

All CHERENKOV architectural flows rendered as interactive diagrams.

---

## 1. System Context

```mermaid
flowchart TB
  Dev([Developer / QA]); Agent([Autonomous Agent]); CI([CI/CD])
  subgraph CK[CHERENKOV-QA Extended]
    Core[Core Pipeline - Track A]
    KB[Second Brain - Phase 1]
    VLM[VLM + LocalAI - Phase 2]
    DH[Desktop Host - Phase 3]
    Chat[Chat Agents - Phase 4]
    Mob[Mobile Testing - Phase 5-6]
    Dash[Dashboard - Phase 7]
    K8s[K8s + Cloud - Phase 8]
  end
  subgraph Src[Sources]
    S1[OpenAPI]; S2[Traffic/OTel]; S3[DB schema]; S4[Code/UI]
    S5[APK/HAR/HIL Mobile]
  end
  subgraph Mod[Models via Substrate Router]
    M1[Local Ollama/vLLM]; M2[Cloud OpenAI/Anthropic]
    M3[LocalAI VLM]
  end
  subgraph Out[Artifacts]
    O1[Playwright]; O2[Spec patch]; O3[PR comment/report]
    O4[Maestro YAML Mobile]; O5[Appium Python Mobile]
  end
  Dev-->CK; Agent-->CK; CI-->CK
  Src-->CK; CK<-->Mod; CK-->Out; Out-->CI
  KB -.-> Chat
  VLM -.-> Mob
  DH -.-> CK
  Dash -.-> KB
```

---

## 2. Track A Pipeline — Spec In, Tests Out

```mermaid
sequenceDiagram
  participant U as User
  participant IN as INGEST
  participant PL as PLAN (deepseek)
  participant GE as GENERATE (qwen)
  participant RV as REVIEW (6 gates)
  participant FS as tests/
  U->>IN: OpenAPI spec
  IN->>IN: parse + depth-1 slice, openapi-fetch stub, mutation menu
  IN->>PL: endpoint slices + menu
  PL->>PL: select mutation_id (never invents), strip think
  PL->>GE: chosen scenario
  GE->>GE: write test w/ openapi-fetch (static prompt → prefix cache)
  GE->>RV: candidate test
  RV->>RV: syntax→structure→AST→assertions→tsc --noEmit→Prism dry-run
  alt verdict auto_approve (>0.9)
    RV->>FS: write test
  else dry-run fail
    RV-->>PL: D2 loop back (circuit-break at 2 fails/case)
  else hitl (0.7-0.9)
    RV->>U: human review
  end
```

---

## Divergence Loop — The Core Capability

```mermaid
sequenceDiagram
  participant TM as Truth Model
  participant K as Skeptic
  participant Sub as Substrate Router
  participant W as Witness
  participant T as Target System
  participant Sc as Scribe
  TM->>K: two claims about endpoint X (spec vs traffic)
  K->>Sub: ReasoningRequest{tier} "where do these diverge?"
  Sub-->>K: hypothesis (D1-D5) + predicted evidence
  K->>W: divergence hypothesis
  W->>T: fire minimal real request
  T-->>W: real response
  W->>W: diff real vs claim
  alt reproduced
    W->>Sc: confirmed + evidence
    Sc-->>TM: update + emit artifact
  else not reproduced
    W-->>K: reject (tautology/noise)
  end
```

---

## 4. Clean Architecture Module Structure

```mermaid
flowchart TB
  subgraph Domain["domain/"]
    M["models.py — Pydantic models, enums"]
  end
  subgraph Ports["ports/"]
    P1["repository.py — Protocol interfaces"]
    P2["event_bus.py"]
  end
  subgraph Adapters["adapters/"]
    A1["sqlite_{module}.py — Default adapter"]
    A2["redis_{module}.py — Upgrade adapter"]
  end
  subgraph UseCases["use_cases/"]
    UC["{action}.py — Orchestration"]
  end
  subgraph API["api/"]
    API1["routes.py — FastAPI routes"]
  end
  Domain --> Ports
  Ports --> Adapters
  Adapters --> UseCases
  UseCases --> API
  note["Dependency rule: arrows point inward. Outer layers depend on inner layers."]
```

---

## 5. Second Brain Architecture

```mermaid
flowchart TB
  subgraph KB[KnowledgeRepository Protocol]
    Q[query]
    S[store]
    SR[search]
    G[get_by_id]
  end
  subgraph Stores[Separate Stores]
    V[verdicts.db]
    H[hitl.db]
    F[feedback.json]
    AM[agent_memory/]
    I[incidents/]
    ID[idioms/]
  end
  subgraph Adapters[Adapters]
    SQL[SQLiteKnowledgeRepository]
    RED[RedisKnowledgeRepository]
  end
  subgraph Bridges[Event Bridges]
    HB[HITL → Reflector]
    FB[Feedback → RAG]
    AB[agent_memory → RAG]
  end
  KB --> Adapters
  Adapters --> Stores
  Bridges --> KB
  CLI["cherenkov knowledge query"] --> KB
  APIRoute["/api/v1/knowledge/query"] --> KB
  ChatAgent[Chat Agent] --> KB
```

---

## 6. Chat Agent Flow

```mermaid
sequenceDiagram
  participant U as User
  participant UI as ChatPanel (React)
  participant API as /api/v1/chat/sessions/{id}/stream
  participant Agent as QAChatAgent
  participant Mem as ConversationMemory
  participant KB as KnowledgeRepository
  participant LLM as SubstrateRouter (LLM)
  U->>UI: "Why was this test rejected?"
  UI->>API: GET /stream?message=...
  API->>Agent: chat(session_id, message)
  Agent->>Mem: get_messages(session_id)
  Mem-->>Agent: conversation history
  Agent->>KB: query("idioms", limit=5)
  KB-->>Agent: top idioms
  Agent->>LLM: chat(messages + system_prompt)
  LLM-->>Agent: tool_call: explain_divergence
  Agent->>KB: explain_divergence(endpoint, method)
  KB-->>Agent: divergence explanation
  Agent->>LLM: chat(messages + tool_result)
  LLM-->>Agent: final response (streaming)
  Agent-->>API: yield tokens
  API-->>UI: SSE tokens
  UI-->>U: display streaming response
```

---

## 7. Desktop Host IPC

```mermaid
sequenceDiagram
  participant UI as Tauri 2 UI (React)
  participant Rust as Tauri 2 (Rust)
  participant IPC as NDJSON IPC
  participant CLI as CHERENKOV CLI (PyInstaller)
  UI->>Rust: invoke("start_sidecar")
  Rust->>CLI: spawn child process
  CLI-->>Rust: stdout {event: "ready"}
  Rust-->>UI: emit("sidecar_ready")
  UI->>Rust: invoke("run", {spec_path: "..."})
  Rust->>IPC: stdin {command: "run", args: {...}}
  IPC->>CLI: forward command
  CLI-->>IPC: stdout {event: "progress", data: {...}}
  IPC-->>Rust: forward event
  Rust-->>UI: emit("progress", {...})
```

---

## 8. Release Flow

```mermaid
flowchart LR
  MS[Milestone complete] --> CH[Update CHANGELOG.md]
  CH --> TG[git tag vX.Y]
  TG --> Rel[GitHub Release - notes from CHANGELOG]
  Rel --> Pre{validation gate tested?}
  Pre -->|no| PR[mark pre-release]
  Pre -->|yes| GA[mark latest]
```

---

## 9. Validation Gate Flow

```mermaid
sequenceDiagram
  participant CI as CI / PR check
  participant VG as validate/gate.py
  participant TR as Test Runner (Playwright)
  participant DB as verdicts.db
  participant HITL as HITL Queue
  participant QA as QA Reviewer
  CI->>VG: cherenkov validate --target url
  VG->>TR: spawn Playwright suite
  TR-->>VG: JUnit XML + trace files
  VG->>DB: persist VerdictRecord per test
  loop per failing/uncertain test
    VG->>HITL: enqueue HITLItem (confidence 0.7-0.9)
    QA->>HITL: cherenkov hitl list / approve / reject
    HITL-->>DB: update verdict
  end
  VG->>VG: tally pass_rate = approved / total
  alt pass_rate >= 0.8
    VG-->>CI: exit 0 — gate PASSED
  else pass_rate < 0.8
    VG-->>CI: exit 1 — gate FAILED
  end
```
