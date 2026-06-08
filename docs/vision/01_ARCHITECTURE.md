# CHERENKOV — Architecture

Companion to [`00_VISION.md`](00_VISION.md). All diagrams are Mermaid (render natively on GitHub).

---

## 1. System context (C4 level 1)

Who/what CHERENKOV talks to.

```mermaid
flowchart TB
  Dev([Developer / QA])
  Agent([Autonomous Dev Agent])
  CI([CI / CD])

  subgraph CK[CHERENKOV Reality Engine]
    direction TB
    Core[Reasoning Harness]
  end

  subgraph Sources[Sources of Truth]
    Spec[OpenAPI / gRPC / GraphQL]
    Code[Source Code]
    Traffic[Live Traffic / OTel]
    DB[(DB Schema)]
    UI[Frontend Bundle]
  end

  subgraph Models[Intelligence Substrate]
    Local[Local: Ollama / vLLM]
    Cloud[Cloud: OpenAI / Anthropic]
  end

  subgraph Out[Artifacts]
    Tests[Playwright / k6 / pytest]
    Patches[Spec / Code Patches]
    Reports[PR Comments / Reports / Webhooks]
  end

  Dev --> CK
  Agent --> CK
  CI --> CK
  Sources --> CK
  CK <--> Models
  CK --> Out
  Out --> CI
  Out --> Dev
```

---

## 2. The layer map (and where the old plan lives)

Ten layers (original 7 + 3 new from consolidated plan). The original 22-week generator becomes **L1 + L3** — real, needed, but no longer the whole product.

```mermaid
flowchart TB
  L6["L6 · Federation — truth protocol, cross-service contracts, divergence corpus  (far future)"]
  L5["L5 · Experience — zero-config CLI, full config surface, dashboard"]
  L4["L4 · Continuity — daemon, watch, behavioral diff on every PR"]
  L3_5["L3.5 · Mobile Testing — Maestro/Appium, 4-tier devices, semantic visual oracle  (Phase 5-6)"]
  L3["L3 · Artifact Layer — GENERATE / REVIEW / EXECUTE / EJECT  (← original Track A)"]
  L2["L2 · Divergence Engine — Skeptic + Witness  (THE BET)"]
  L1_5["L1.5 · Chat Agents — tool-calling, persona registry, SSE streaming  (Phase 4)"]
  L1["L1 · Truth Model — multi-source INGEST → unified semantic graph  (← extends Track A INGEST)"]
  L0_5["L0.5 · Knowledge Mesh — Second Brain, GraphRAG, event bridges  (Phase 1)"]
  L0["L0 · Substrate — model-agnostic inference router + provider plugins + LocalAI VLM  (Phase 2)"]

  L6 --> L5 --> L4 --> L3_5 --> L3 --> L2 --> L1_5 --> L1 --> L0_5 --> L0
  style L2 fill:#1f6feb,stroke:#fff,color:#fff
  style L0 fill:#238636,stroke:#fff,color:#fff
  style L3 fill:#9e6a03,stroke:#fff,color:#fff
  style L1 fill:#9e6a03,stroke:#fff,color:#fff
  style L0_5 fill:#d4c5f9,stroke:#fff,color:#fff
  style L1_5 fill:#5319e7,stroke:#fff,color:#fff
  style L3_5 fill:#fbca04,stroke:#fff,color:#fff
```

> 🟦 the bet · 🟩 new foundation · 🟧 inherited from the original plan · 🟪 Second Brain (Phase 1) · 🟪 Chat Agents (Phase 4) · 🟨 Mobile Testing (Phase 5-6)

### New Layers (Consolidated Plan)

**L0.5 · Knowledge Mesh (Phase 1):**
- Second Brain: unified query interface over separate stores (verdicts, idioms, incidents, HITL, feedback, agent_memory)
- GraphRAG: multi-domain retrieval with semantic search
- Event bridges: HITL → Reflector, Feedback → RAG, agent_memory → RAG
- Adapters: SQLiteKnowledgeRepository (default), RedisKnowledgeRepository (upgrade)
- See [15_SECOND_BRAIN.md](15_SECOND_BRAIN.md) for full details

**L1.5 · Chat Agents (Phase 4):**
- Tool-calling agent: query_verdicts, query_idioms, explain_divergence, run_test
- Persona registry: system prompt composition with project context, idioms, Truth Model
- Conversation memory: session history, context window management
- SSE streaming: real-time token streaming to ChatPanel React component
- MCP integration: external MCP clients can query knowledge
- See [16_CHAT_AGENT.md](16_CHAT_AGENT.md) for full details

**L3.5 · Mobile Testing (Phase 5-6):**
- Mobile source adapters: APK/HAR/HIL ingestion
- Pilot agent: 3-step intent orchestration with circuit breaker (20 observations, 5 min timeout)
- Mobile stages: plan, generate, review (Maestro YAML)
- Semantic visual oracle: VLM-based screenshot analysis with anti-reward-hacking gate
- Dual eject formats: Maestro YAML + Appium Python (ZERO CHERENKOV imports)
- 4-tier device support: Browser emulation → Android emulator → iOS simulator → Physical device
- See [17_MOBILE_TESTING.md](17_MOBILE_TESTING.md) for full details

---

## 3. The four agents + the metabolism

CHERENKOV is *made of* reasoning, not augmented by it. Four cooperating agents (a fifth optional), none clever alone.

```mermaid
flowchart LR
  subgraph Inputs
    S[Sources of Truth]
  end

  C[Cartographer\nPERCEPTION\nbuilds Truth Model]
  K[Skeptic\nHYPOTHESIS\nfinds candidate divergences]
  W[Witness\nVERIFICATION\nreproduces divergence for real]
  Sc[Scribe\nSYNTHESIS\nemits closing artifact]
  R[Reflector\nLEARNING\nremembers being wrong]

  TM[(Truth Model\nsemantic graph + embeddings)]

  S --> C --> TM
  TM --> K -->|hypothesis| W
  W -->|reproduced?| Sc
  W -->|no repro / noise| K
  Sc --> ART[Artifacts]
  Sc --> R
  ART -->|human/CI verdict| R
  R -->|policy update| K
  R -->|idiom update| Sc

  style K fill:#1f6feb,stroke:#fff,color:#fff
  style W fill:#1f6feb,stroke:#fff,color:#fff
```

| Agent | Role | Intelligence need | Cadence |
|---|---|---|---|
| **Cartographer** | Normalize all sources into the Truth Model | Cheap / small | Continuous (on change) |
| **Skeptic** | Adversarially hypothesize divergences | Deep reasoning | On model update / traffic shift |
| **Witness** | Independently reproduce the divergence | Near-zero (deterministic harness) | Per hypothesis |
| **Scribe** | Choose + write the artifact that closes the loop | Mid / code-tuned | Per confirmed divergence |
| **Reflector** | Learn from rejected/accepted findings | Mid | Per verdict (async) |

---

## 4. The Substrate Router (L0) — the keystone

Treats intelligence as a market: right brain for the right job, decided per call, bounded by org policy.

```mermaid
flowchart TB
  Caller[Agent emits a Reasoning Request\n(task, schema, budget, sensitivity)]
  Router{Substrate Router}

  subgraph Policy
    Egress["egress: none | internal | any"]
    Budget["cost / latency / quality budgets"]
    Tier["capability tier required"]
  end

  subgraph Providers[Provider Plugins]
    P1[Ollama local]
    P2[vLLM self-host]
    P3[OpenAI]
    P4[Anthropic]
    P5[future model]
  end

  Cache[(Prefix / response cache)]

  Caller --> Router
  Policy --> Router
  Router --> Cache
  Router -->|route by tier+policy| P1 & P2 & P3 & P4 & P5
  P1 & P2 & P3 & P4 & P5 -->|validated structured output| Caller
  Router -.->|fallback / spillover on failure| Router
```

**Contract:** agents NEVER name a model. They emit a *Reasoning Request* — `{task, output_schema, capability_tier, max_cost, max_latency, sensitivity}` — and the router picks a provider that satisfies org policy. Swapping models = config, never code. A bank sets `egress: none`; a startup sets `egress: any`; same product.

---

## 5. The Divergence Loop in detail (L2 — the bet)

```mermaid
sequenceDiagram
  participant TM as Truth Model
  participant K as Skeptic
  participant Sub as Substrate
  participant W as Witness
  participant Tgt as Target System
  participant Sc as Scribe

  TM->>K: two claims about endpoint X (spec vs traffic)
  K->>Sub: "where do these diverge?" (Reasoning Request)
  Sub-->>K: hypothesis + predicted evidence
  K->>W: divergence hypothesis
  W->>Tgt: fire minimal real request
  Tgt-->>W: real response
  W->>W: diff real vs claim
  alt reproduced
    W->>Sc: confirmed divergence + evidence
    Sc->>Sub: "what artifact closes this?"
    Sub-->>Sc: test / patch / comment
    Sc-->>TM: update model + emit artifact
  else not reproduced
    W-->>K: rejected (tautology / noise) — try again
  end
```

**Anti-reward-hacking (adversarial self-play option):** the Witness can run the candidate test against BOTH a correct mock (Prism) AND a deliberately-broken implementation. A test that passes both is tautological (`true==true`) and is killed. This directly attacks the existential failure mode of autonomous QA.

---

## 6. The five-way divergence space (what L2 detects)

```mermaid
flowchart LR
  Spec[Spec claims] ---|D1| Code[Code does]
  Code ---|D2| Prod[Prod returns]
  UI[UI sends] ---|D3| Spec
  DB[(DB enforces)] ---|D4| Code
  Spec ---|D5| Prod

  classDef n fill:#161b22,stroke:#8b949e,color:#fff;
  class Spec,Code,Prod,UI,DB n;
```

| Divergence | Example | Why it matters |
|---|---|---|
| **D1 spec↔code** | spec says `format=email`, code accepts anything | spec lies; integrators break |
| **D2 code↔prod** | prod leaks `_internal_debug` 3% of the time | silent PII / contract drift |
| **D3 ui↔spec** | UI sends `"555-1234"`, API wants E.164 | integration drift |
| **D4 db↔code** | DB `UNIQUE(email)`, API never checks | race condition / 500s |
| **D5 spec↔prod** | endpoint in spec no longer exists | dead contract |

---

## 7. Continuity & behavioral diff (L4)

```mermaid
flowchart LR
  PR[Pull Request] --> D[CHERENKOV daemon]
  Base[(Truth Model @ base)] --> D
  D --> Diff[Behavioral Diff]
  Diff -->|"3 endpoints changed shape, 1 intended"| Comment[PR comment + evidence]
  Diff --> Gate{Policy gate}
  Gate -->|block on unintended drift| CI
```

`git diff` shows *code* changes; CHERENKOV shows *behavior* changes. A behavioral diff on every PR — nobody ships this; everyone needs it.

---

## 8. Open-seam plugin interfaces (summary)

```mermaid
flowchart TB
  subgraph Harness[Proprietary Reasoning Harness]
    core[Agents + Truth Model + Divergence Loop]
  end
  SRC[[Source Adapter SPI]] --> core
  core --> ART[[Artifact Emitter SPI]]
  core <--> MOD[[Model Provider SPI]]
  core <--> ORA[[Oracle SPI]]
```

Each SPI is a small, versioned contract (Pydantic models, à la the existing `core/contracts.py`). New capability = new plugin, never a rewrite. See [`03_CONFIGURATION.md`](03_CONFIGURATION.md) for how plugins are selected and configured.
