# CHERENKOV — Diagrams (Mermaid, render on GitHub)

System, sequence, flow, and lifecycle diagrams. Companion to [`docs/vision/01_ARCHITECTURE.md`](../vision/01_ARCHITECTURE.md) and [`docs/process/GITHUB_PM.md`](../process/GITHUB_PM.md).

---

## 1. System context

```mermaid
flowchart TB
  Dev([Developer / QA]); Agent([Autonomous Agent]); CI([CI/CD])
  subgraph CK[CHERENKOV]
    Core[Reasoning Harness + Truth Model]
  end
  subgraph Src[Sources]
    S1[OpenAPI]; S2[Traffic/OTel]; S3[DB schema]; S4[Code/UI]
  end
  subgraph Mod[Models via Substrate Router]
    M1[Local Ollama/vLLM]; M2[Cloud OpenAI/Anthropic]
  end
  subgraph Out[Artifacts]
    O1[Playwright]; O2[Spec patch]; O3[PR comment/report]
  end
  Dev-->CK; Agent-->CK; CI-->CK
  Src-->CK; CK<-->Mod; CK-->Out; Out-->CI
```

## 2. Track A pipeline (sequence) — spec in, tests out

```mermaid
sequenceDiagram
  participant U as User
  participant IN as INGEST
  participant PL as PLAN (deterministic)
  participant GE as GENERATE (qwen)
  participant RV as REVIEW (6 gates)
  participant FS as tests/
  U->>IN: OpenAPI spec
  IN->>IN: parse + depth-1 slice, openapi-fetch stub, mutation menu
  IN->>PL: endpoint slices + menu
  PL->>PL: select mutation_id (never invents), strip <think>
  PL->>GE: chosen scenario
  GE->>GE: write test w/ openapi-fetch (static prompt → prefix cache)
  GE->>RV: candidate test
  RV->>RV: syntax→structure→AST→assertions→tsc --noEmit→Prism dry-run
  alt verdict auto_approve (>0.9)
    RV->>FS: write test
  else dry-run fail
    RV-->>PL: D2 loop back (circuit-break at 2 fails/case)
  else hitl (0.7–0.9)
    RV->>U: human review
  end
```

## 3. Divergence loop (sequence) — THE BET

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
  Sub-->>K: hypothesis (D1–D5) + predicted evidence
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

## 4. Reflector learning loop (sequence) — Epoch 7 (proposed)

```mermaid
sequenceDiagram
  participant W as Witness/Healing
  participant H as Human (Verdict)
  participant R as Reflector
  participant DB as verdicts.db
  participant K as Skeptic
  participant Sc as Scribe
  W->>R: ReproductionResult / FailureClass
  H->>R: accept | reject | refine (+reason)
  R->>DB: persist VerdictRecord / Idiom
  R->>K: reweight hypothesis ranking (rejected stop recurring)
  R->>Sc: idiom updates (what to emit / check)
  Note over R,DB: Exit = behavioral: rejected findings don't return; hit-rate ↑
```

## 5. FE user journey (flowchart) — manual-QA first

```mermaid
flowchart TD
  A[Land on Overview<br/>release readiness] --> B{What now?}
  B -->|See risk| C[Divergences ★<br/>severity-sorted findings]
  B -->|Explore build| D[Explore ★<br/>second pair of eyes]
  B -->|Author test| E[Author by Intent ★<br/>plain English]
  D --> C
  C --> F[Open finding<br/>claim A vs B + evidence]
  F -->|Close with test| G[Pilot executes live<br/>vision-confirmed]
  E --> G
  G --> H[Review Queue<br/>approve / reject + reason]
  H -->|teaches| I[(Reflector memory)]
  H -->|approve| J[Eject standalone Playwright<br/>zero lock-in]
  I -.idioms.-> E
```

## 6. Application lifecycle — issue/ticket state machine

```mermaid
stateDiagram-v2
  [*] --> Ready: acceptance written, labels set (DoR)
  Ready --> InProgress: branch feat/<issue>-slug
  InProgress --> InReview: PR opened (+ raw evidence)
  InReview --> InProgress: changes requested
  InReview --> Done: checks green + approved + squash-merge
  InProgress --> Blocked: dependency / gate
  Blocked --> Ready: unblocked
  Done --> [*]
```

## 7. Git / PR flow

```mermaid
flowchart LR
  M[(main protected)] -->|branch| B[feat/123-slug]
  B --> C[commits: Conventional + #123]
  C --> P[PR: template + evidence + Closes #123]
  P --> CK{CI checks<br/>Docs · Healing · CLI · CodeQL}
  CK -->|fail| C
  CK -->|pass| RV{1+ approval<br/>threads resolved}
  RV -->|changes| C
  RV -->|approve| SQ[squash-merge] --> M
  SQ --> CL[issue auto-closed<br/>milestone burns down]
```

## 8. Release flow

```mermaid
flowchart LR
  MS[Milestone complete] --> CH[Update CHANGELOG.md]
  CH --> TG[git tag vX.Y]
  TG --> Rel[GitHub Release<br/>notes from CHANGELOG]
  Rel --> Pre{validation gate tested?}
  Pre -->|no| PR[mark pre-release]
  Pre -->|yes| GA[mark latest]
```

---

## 9. Second Brain Architecture (Phase 1)

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

  CLI[cherenkov explore] --> KB
  API[/api/v1/knowledge/query] --> KB
  Chat[Chat Agent] --> KB
```

## 10. Event Bus Flow (Phase 0b)

```mermaid
sequenceDiagram
  participant HITL as HITL Queue
  participant EB as EventBus
  participant R as Reflector
  participant KB as KnowledgeRepository

  HITL->>EB: emit(HITLDecisionMade)
  EB->>R: subscribe("HITLDecisionMade")
  R->>R: ingest_human_verdict()
  R->>KB: store(verdict)

  Note over EB: Fallback chain:<br/>asyncio.Queue → Redis Streams
```

## 11. Clean Architecture Module (Phase 0b)

```mermaid
flowchart TB
  subgraph Domain[domain/]
    M[models.py<br/>Pydantic models, enums]
  end

  subgraph Ports[ports/]
    P1[repository.py<br/>Protocol interfaces]
    P2[event_bus.py]
  end

  subgraph Adapters[adapters/]
    A1[sqlite_{module}.py<br/>Default adapter]
    A2[redis_{module}.py<br/>Upgrade adapter]
  end

  subgraph UseCases[use_cases/]
    UC[{action}.py<br/>Orchestration]
  end

  subgraph API[api/]
    API1[routes.py<br/>FastAPI routes]
  end

  Domain --> Ports
  Ports --> Adapters
  Adapters --> UseCases
  UseCases --> API

  Note over Domain,API: Dependency rule:<br/>Arrows point inward<br/>Outer layers depend on inner layers
```

## 12. Desktop Host IPC (Phase 3)

```mermaid
sequenceDiagram
  participant UI as Tauri 2 UI (React)
  participant Rust as Tauri 2 (Rust)
  participant IPC as NDJSON IPC
  participant CLI as CHERENKOV CLI (PyInstaller)

  UI->>Rust: invoke("start_sidecar")
  Rust->>CLI: spawn child process
  CLI-->>Rust: stdout: {"event":"ready"}
  Rust-->>UI: emit("sidecar_ready")

  UI->>Rust: invoke("run", {spec_path: "..."})
  Rust->>IPC: stdin: {"command":"run","args":{...}}
  IPC->>CLI: forward command
  CLI-->>IPC: stdout: {"event":"progress","data":{...}}
  IPC-->>Rust: forward event
  Rust-->>UI: emit("progress", {...})

  Note over IPC: Commands: run, stop, status, config_set, config_get<br/>Events: progress, result, error, health_change
```

## 13. Chat Agent Flow (Phase 4)

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
  API-->>UI: SSE: {"event":"token","data":{"token":"..."}}
  UI-->>U: display streaming response
```

## 14. Mobile Testing Tiers (Phase 5-6)

```mermaid
flowchart TB
  subgraph Tier1[Tier 1: Browser Emulation]
    B1[Chromium]
    B2[Firefox]
    B3[WebKit]
  end

  subgraph Tier2[Tier 2: Android Emulator]
    A1[Android Studio AVD]
    A2[Genymotion]
  end

  subgraph Tier3[Tier 3: iOS Simulator]
    I1[Xcode Simulator]
  end

  subgraph Tier4[Tier 4: Physical Device]
    P1[Android (ADB)]
    P2[iOS (libimobiledevice)]
  end

  subgraph Execution[Execution]
    M[Maestro YAML]
    AP[Appium Python]
  end

  Tier1 --> Execution
  Tier2 --> Execution
  Tier3 --> Execution
  Tier4 --> Execution

  Note over Tier1,Tier4: Device selection based on DeviceClass:<br/>GPU_WORKSTATION → Tier 2<br/>CPU_HIGH_END → Tier 3<br/>CPU_STANDARD → Tier 1
```

## 15. Updated System Context (Consolidated Plan)

```mermaid
flowchart TB
  Dev([Developer / QA]); Agent([Autonomous Agent]); CI([CI/CD])

  subgraph CK[CHERENKOV-QA Extended]
    Core[Core Pipeline<br/>Track A]
    KB[Second Brain<br/>Phase 1]
    VLM[VLM + LocalAI<br/>Phase 2]
    DH[Desktop Host<br/>Phase 3]
    Chat[Chat Agents<br/>Phase 4]
    Mob[Mobile Testing<br/>Phase 5-6]
    Dash[Dashboard<br/>Phase 7]
    K8s[K8s + Cloud<br/>Phase 8]
  end

  subgraph Src[Sources]
    S1[OpenAPI]; S2[Traffic/OTel]; S3[DB schema]; S4[Code/UI]
    S5[APK/HAR/HIL<br/>Mobile]
  end

  subgraph Mod[Models via Substrate Router]
    M1[Local Ollama/vLLM]; M2[Cloud OpenAI/Anthropic]
    M3[LocalAI<br/>VLM]
  end

  subgraph Out[Artifacts]
    O1[Playwright]; O2[Spec patch]; O3[PR comment/report]
    O4[Maestro YAML<br/>Mobile]
    O5[Appium Python<br/>Mobile]
  end

  Dev-->CK; Agent-->CK; CI-->CK
  Src-->CK; CK<-->Mod; CK-->Out; Out-->CI

  KB -.-> Chat
  VLM -.-> Mob
  DH -.-> CK
  Dash -.-> KB
```

---

## 16. Validation Gate flow (5-QA runbook)

```mermaid
sequenceDiagram
  participant CI as CI / PR check
  participant VG as validate/gate.py
  participant TR as Test Runner (Playwright)
  participant DB as verdicts.db
  participant HITL as HITL Queue
  participant QA as QA Reviewer

  CI->>VG: cherenkov validate --target <url>
  VG->>TR: spawn Playwright suite (stub/generated_tests/)
  TR-->>VG: JUnit XML + trace files
  VG->>DB: persist VerdictRecord per test
  loop per failing/uncertain test
    VG->>HITL: enqueue HITLItem (confidence 0.7-0.9)
    QA->>HITL: cherenkov hitl list / approve / reject
    HITL-->>DB: update verdict (approved | rejected)
  end
  VG->>VG: tally: pass_rate = approved / total
  alt pass_rate >= gate_threshold (default 0.8)
    VG-->>CI: exit 0 — gate PASSED
  else pass_rate < gate_threshold
    VG-->>CI: exit 1 — gate FAILED (report.json written)
  end
  Note over VG,DB: Evidence written to .cherenkov/evidence/<run_id>/
```

## 17. Certificate issuance flow (Spec Guardian / Phase 14)

```mermaid
sequenceDiagram
  participant Dev as Developer / CI
  participant CK as CHERENKOV Engine
  participant VG as Validation Gate
  participant SG as Spec Guardian
  participant CA as Certificate Authority (local key)
  participant Reg as Certificate Registry

  Dev->>CK: cherenkov certify --llm deep
  CK->>VG: run full validation suite
  VG-->>CK: ValidationReport (pass_rate, evidence_dir)
  CK->>SG: evaluate_claims(spec, report)
  SG-->>CK: ClaimSet{verified, unverified, disputed}
  CK->>CA: sign(ClaimSet + run_id + timestamp)
  CA-->>CK: CherenkovCertificate{sig, fingerprint, expiry}
  CK->>Reg: store(certificate)
  CK-->>Dev: certificate.json + fingerprint
  Note over CA,Reg: Certificate is portable — forward to auditors,<br/>CI gates, or marketplaces via fingerprint URL
```

---

## 18. Version-Diff Evolution Flow (1.2 → 1.3 → 1.4)

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

## 19. 1.4 Consolidated Documentation Site Map

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
