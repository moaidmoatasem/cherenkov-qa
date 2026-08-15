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

---

## 10. Version-Diff Evolution Flow (1.2 → 1.3 → 1.4)

```mermaid
flowchart TD
  subgraph V12["Version 1.2.0 (Baseline Foundation)"]
    direction TB
    A1["5-Hub Dashboard Architecture<br/>(Overview, Author, Triage, Coverage, Knowledge)"]
    A2["Live Backend Wiring<br/>(GET /api/v1/divergences, Chat session persistence)"]
    A3["Initial Extensions Base<br/>(VS Code Beta, GraphQL/gRPC/AsyncAPI support)"]
    A4["Test Management Hub<br/>(Health trend charts & generated test records)"]
  end

  subgraph V13["Version 1.3.0 (Enterprise & Agentic Expansion)"]
    direction TB
    B1["Spec Guardian CLI<br/>(cherenkov guardian start — background drift daemon)"]
    B2["Enterprise Security Wiring<br/>(SAML 2.0 SSO, RBAC roles, SOC2 compliance reports)"]
    B3["MCP Tool Federation<br/>(check-suite, verify, generate tools & registry manifest)"]
    B4["FTS5 Engine Optimization<br/>(SQLite shadow-table rowid indexing for Second Brain)"]
  end

  subgraph V14["Version 1.4.0 (Continuous Conformance & Governance)"]
    direction TB
    C1["Coverage Map API<br/>(GET /api/v1/coverage/map — per-endpoint coverage matrix)"]
    C2["Conformance Trend & Regressions<br/>(Automated verdict downgrade & divergence spike detector)"]
    C3["GitHub PR Coverage Bot<br/>(format_coverage_comment diff bot on PR events)"]
    C4["Consolidated Documentation 1.4<br/>(Unified Material for MkDocs hierarchy & versioning)"]
  end

  V12 ==>|"Added Background Daemons, Enterprise SAML, MCP"| V13
  V13 ==>|"Added Coverage Analytics, Regression Engine, CI Bots"| V14

  classDef v12 fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
  classDef v13 fill:#1e293b,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc;
  classDef v14 fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc;

  class A1,A2,A3,A4 v12;
  class B1,B2,B3,B4 v13;
  class C1,C2,C3,C4 v14;
```

---

## 11. 1.4 Consolidated Documentation Site Map

```mermaid
flowchart TB
  Root(["CHERENKOV-QA 1.4 Documentation Hub"])

  subgraph Hub1["1. Getting Started & Tutorials"]
    H1_1["Home & Overview<br/>(index.md)"]
    H1_2["Quickstart<br/>(quickstart.md)"]
    H1_3["Installation & Setup<br/>(installation.md)"]
    H1_4["Configuration & Cost Tiers<br/>(configuration.md / cost-tiers.md)"]
  end

  subgraph Hub2["2. QA & Conformance Workflows"]
    H2_1["API Conformance Testing<br/>(api-conformance.md)"]
    H2_2["Check Suite Integrity Audit<br/>(check-suite.md)"]
    H2_3["Spec Guardian Daemon<br/>(continuous-monitoring.md)"]
    H2_4["HITL Review & Certification<br/>(hitl.md / certificates.md)"]
    H2_5["Dashboard & Docker<br/>(dashboard.md / docker.md)"]
  end

  subgraph Hub3["3. Architecture & Second Brain"]
    H3_1["Clean Architecture & System Design<br/>(clean-architecture.md / system-design.md)"]
    H3_2["Second Brain & Knowledge Mesh<br/>(second-brain.md / ai-pipeline.md)"]
    H3_3["Platform Operating Model<br/>(platform-operating-model.md)"]
    H3_4["User Journeys<br/>(user-journeys.md)"]
    H3_5["Role Guides<br/>(developer, qa-engineer, devops, team-lead)"]
  end

  subgraph Hub4["4. Ecosystem & Integrations"]
    H4_1["CI/CD Native Pipelines<br/>(ci-cd.md / github-actions.md)"]
    H4_2["MCP Protocol & Registry<br/>(mcp.md / langchain.md)"]
    H4_3["IDE Extensions<br/>(vscode.md)"]
    H4_4["Notifications<br/>(notifications.md)"]
  end

  subgraph Hub5["5. Reference & Release Hub"]
    H5_1["CLI Reference & Completions<br/>(cli/reference.md / cli/completions.md)"]
    H5_2["Error Handling & FAQ<br/>(troubleshooting/faq.md / common-issues.md)"]
    H5_3["Release History & Changelog<br/>(releases/v1.4.0.md / changelog.md)"]
  end

  Root --> Hub1
  Root --> Hub2
  Root --> Hub3
  Root --> Hub4
  Root --> Hub5

  classDef rootNode fill:#0f172a,stroke:#6366f1,stroke-width:3px,color:#ffffff;
  classDef hub fill:#1e1b4b,stroke:#818cf8,stroke-width:1.5px,color:#e0e7ff;
  class Root rootNode;
  class H1_1,H1_2,H1_3,H1_4,H2_1,H2_2,H2_3,H2_4,H2_5,H3_1,H3_2,H3_3,H3_4,H3_5,H4_1,H4_2,H4_3,H4_4,H5_1,H5_2,H5_3 hub;
```

