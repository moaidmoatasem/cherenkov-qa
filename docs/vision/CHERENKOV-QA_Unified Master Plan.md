# CHERENKOV-QA: Unified Master Plan

**Consolidating: Desktop + Mobile + Chat Agents + Second Brain + UI Revamp + Infrastructure**

---

## 1. Vision & Invariants

### What CHERENKOV Becomes

From: *CLI-first API conformance testing tool with a dashboard*

To: **AI-native QA platform** that:
- Runs on desktop (Tauri 2) or CLI or K8s
- Tests APIs **and** mobile apps **and** visual UIs
- Has a **second brain** that compounds knowledge across every run
- Has a **chat agent** you can ask "why did this test fail?" and get evidence-linked answers
- Is **free to start** (LocalAI/Docker Compose, zero cloud dependency)
- Is **local-first** (all data stays on your machine by default)
- Is **contribution-ready** (clean architecture, ports/adapters, behavioral contracts)

### Design Invariants (NEVER broken)

| # | Invariant | Meaning |
|---|---|---|
| D7 | Never auto-edit test code | Validate/healing produce reports/suggestions only |
| Anti-lock-in | Tests must run without CHERENKOV | `eject` strips all imports; Maestro YAML runs standalone |
| Suggest-only | Healing never auto-commits | Diagnoser produces text suggestions, never patches |
| Spec-derived | Expected HTTP status from OpenAPI spec | Not hardcoded assumptions |
| Build-over | New capabilities extend existing seams | No parallel `mobile/` module duplicating Substrate/RAG/Truth Model |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Tauri 2 Desktop Host                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │  Setup   │ │  Device  │ │  Chat    │ │  Mobile  │ │ Knowledge│    │
│  │  Wizard  │ │  Manager │ │  Panel   │ │ Dashboard│ │ Explorer │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘    │
│       │             │            │             │             │           │
│  ┌────▼─────────────▼────────────▼─────────────▼─────────────▼────┐    │
│  │            NDJSON Sidecar Protocol / SSE / WebSocket            │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────────┐
│                        FastAPI Backend (:8000)                        │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ /healthz │ │ /api/v1/*│ │/api/v1/  │ │/api/v1/  │ │/api/v1/  │  │
│  │          │ │  (exist) │ │chat/*    │ │mobile/*  │ │knowledge/*│  │
│  └─────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────────┐
│                    OrchestrationEngine (core/orchestrator.py)           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │
│  │ Track A    │ │ Track B/C  │ │ Mobile     │ │ Chat Agent │        │
│  │ Pipeline   │ │ Visual/    │ │ Pillot+   │ │ (Second    │        │
│  │ INGEST→    │ │ Perf/Div   │ │ Maestro   │ │  Brain)    │        │
│  │ PLAN→GEN→ │ │            │ │            │ │            │        │
│  │ REVIEW     │ │            │ │            │ │            │        │
│  └──────┬─────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘        │
└─────────┼─────────────┼──────────────┼──────────────┼────────────────┘
          │             │              │              │
┌─────────▼─────────────▼──────────────▼──────────────▼────────────────┐
│                        Shared Seam Layer                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Sources  │ │ Substrate│ │ Agents   │ │ Stages   │ │ Oracle   │  │
│  │ (Ingest+ │ │ (LLM+   │ │ (Pilot+  │ │ (Plan+   │ │ (Pixel+  │  │
│  │  Mobile) │ │  VLM+   │ │  Explorer│ │  Generate+│ │  Semantic│  │
│  │          │ │  Router) │ │  Chat)   │ │  Review) │ │  VLM)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└──────────────────────────┬────────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────────┐
│                     Second Brain (Knowledge Layer)                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    EventBus (asyncio.Queue / Redis)           │   │
│  │  VerdictRecorded | HITLDecisionMade | DivergenceFound |     │   │
│  │  PilotObservation | ChatMessage                              │   │
│  └──────┬──────────┬──────────┬──────────┬──────────┬──────────┘   │
│         │          │          │          │          │                │
│  ┌──────▼────┐ ┌──▼──────┐ ┌─▼───────┐ ┌▼─────────┐ ┌▼─────────┐ │
│  │TruthModel │ │Verdict  │ │RAGIndex │ │HITL      │ │Feedback   │ │
│  │(SQLite+   │ │Store    │ │(+Redis  │ │Queue     │ │Store      │ │
│  │ persisted)│ │(SQLite) │ │ vector) │ │(SQLite)  │ │(→SQLite)  │ │
│  └───────────┘ └─────────┘ └─────────┘ └──────────┘ └───────────┘ │
└────────────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────────┐
│              Ports & Adapters (Clean Architecture)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Knowledge  │ │Inference │ │ Memory   │ │ Device   │ │ EventBus  │  │
│  │Repo Port  │ │Port      │ │Port      │ │Port      │ │Port       │  │
│  └─────┬─────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘  │
│        │             │            │            │            │             │
│  ┌─────▼─────┐ ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐  │
│  │SQLite     │ │LocalAI   │ │SQLite    │ │Maestro   │ │NDJSON    │  │
│  │Adapter    │ │Adapter   │ │Memory   │ │Device    │ │EventBus  │  │
│  └───────────┘ │Ollama    │ │Adapter  │ │Adapter   │ │Adapter   │  │
│  ┌───────────┐ │Adapter   │ └─────────┘ └─────────┘ └─────────┘  │
│  │Redis      │ │OpenAI    │ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │Adapter    │ │Adapter   │ │Redis    │ │Appium   │ │Redis    │  │
│  │(optional) │ │(opt-in)  │ │Memory  │ │Device   │ │Streams  │  │
│  └───────────┘ └─────────┘ │(optional)│ │Adapter  │ │(optional)│  │
│                             └─────────┘ └─────────┘ └─────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────────┐
│                    Infrastructure (Docker Compose)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ LocalAI  │ │ Redis   │ │ MCP     │ │ Android  │ │ k3s      │  │
│  │ (LLM+   │ │ Stack   │ │ Gateway │ │ Emulator │ │ (K8s     │  │
│  │  VLM)   │ │ (cache+ │ │ (Docker │ │ (opt)   │ │  operator)│  │
│  │          │ │  vector) │ │  AI)    │ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Core Stack (Required)

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Runtime** | Python | 3.10+ | Backend, agents, pipeline |
| **Frontend** | React 19 + Vite 6 + TypeScript 5.8 | Existing | Dashboard |
| **Desktop** | Tauri 2 | New | Desktop host (Windows/macOS/Linux) |
| **Sidecar** | PyInstaller | Existing | Bundle Python + UI into desktop app |
| **Data Stores** | SQLite (WAL mode) | Existing | HITL, Verdicts, RAG, Knowledge |
| **LLM (default)** | LocalAI via Docker | New | OpenAI-compatible API, VLM, embeddings |
| **LLM (fallback)** | Ollama | Existing | For existing users who have it installed |
| **LLM (opt-in)** | OpenAI GPT-4o-mini | Existing | Cloud VLM, requires egress policy |
| **Vector Search** | SQLite brute-force → Redis RediSearch | New (optional) | RAG similarity, defaults to SQLite |
| **Event Bus** | asyncio.Queue → Redis Streams | New (optional) | Cross-module notifications |

### Optional Stack (Enhanced Mode)

| Component | Technology | Purpose | When Needed |
|---|---|---|---|
| **Redis Stack** | `redis/redis-stack-server` | Vector search, pub/sub, session cache, JSON docs | Multi-agent coordination, enhanced second brain |
| **Docker MCP Gateway** | `docker/mcp-gateway` | Unified external agent access, auth, tool discovery | When exposing CHERENKOV to external agents (Claude, Copilot) |
| **Android Emulator** | Android SDK + ADB | Mobile testing on Android | `cherenkov mobile init` optional setup |
| **iOS Simulator** | Xcode + simctl | Mobile testing on iOS | macOS only, optional |
| **Maestro CLI** | `maestro` | Ejectable mobile test runtime | `cherenkov mobile init` optional setup |
| **Appium** | `appium-python-client` | Alternative mobile runtime for locked-down apps | Optional, pip install cherenkov-qa[mobile] |
| **Docker Compose AI** | `docker-compose.ai.yml` | One-command stack: LocalAI + Redis + CHERENKOV | `docker compose -f docker-compose.ai.yml up` |

### Mobile Stack (New, Optional)

| Component | Technology | Purpose |
|---|---|---|
| **Primary eject** | Maestro YAML | Mobile test runtime (anti-lock-in) |
| **Fallback eject** | Appium Python/TS | For locked-down third-party apps |
| **VLM** | Qwen2.5-VL (via LocalAI) | Screen understanding for Pilot agent |
| **Device control** | ADB + Maestro | Android emulator/device control |
| **Device control** | simctl + Maestro | iOS simulator control |

---

## 4. Module Structure

### New Modules

```
cherenkov/
├── ports/                              # INTERFACES (no external deps)
│   ├── __init__.py
│   ├── knowledge.py                    # KnowledgeRepository protocol
│   ├── inference.py                    # InferencePort (extends InferenceClient)
│   ├── inference_streaming.py          # StreamingInferencePort
│   ├── memory.py                       # MemoryPort — conversation sessions
│   ├── device.py                       # DevicePort — Maestro/Appium/Playwright
│   └── event_bus.py                    # EventBus — domain events + pub/sub
│
├── adapters/                           # IMPLEMENTATIONS (depend on external libs)
│   ├── __init__.py
│   ├── sqlite_knowledge.py            # SQLite adapter for KnowledgeRepository
│   ├── redis_knowledge.py             # Redis adapter (optional, enhanced mode)
│   ├── localai_inference.py           # LocalAI adapter for InferencePort
│   ├── sqlite_memory.py               # SQLite adapter for MemoryPort
│   ├── redis_memory.py                # Redis adapter (optional, enhanced mode)
│   ├── maestro_device.py              # Maestro adapter for DevicePort
│   ├── appium_device.py               # Appium adapter for DevicePort
│   └── ndjson_event_bus.py            # NDJSON sidecar adapter for EventBus
│
├── knowledge/                          # SECOND BRAIN
│   ├── __init__.py
│   ├── repository.py                  # Unified KnowledgeRepository implementation
│   ├── graph_rag.py                   # Hybrid vector + graph retrieval
│   ├── bridges.py                     # HITL→Reflector, Feedback→RAG, Memory→RAG
│   └── events.py                      # Domain events (VerdictRecorded, etc.)
│
├── chat/                               # CHAT AGENTS
│   ├── __init__.py
│   ├── memory.py                      # ConversationMemory (SQLite + optional Redis)
│   ├── persona.py                     # PersonaRegistry — compose system prompts
│   ├── agent.py                       # QAChatAgent — observe→reason→act→respond
│   ├── tools.py                       # CHERENKOV-specific tools for agent
│   └── streaming.py                  # SSE/streaming support
│
├── sources/                             # MOBILE SOURCES
│   ├── __init__.py
│   ├── adapter.py                      # SourceAdapter SPI
│   └── mobile/
│       ├── __init__.py
│       ├── contracts.py               # MobileUIElement, MobileScreenState, etc.
│       ├── android_dump.py
│       ├── ios_dump.py
│       ├── har_to_traffic.py
│       └── adapter.py                 # MobileSourceAdapter
│
├── substrate/
│   ├── vlm_provider.py                # NEW: VLMProvider ABC + implementations
│   ├── vlm_router.py                  # NEW: Tier-aware VLM routing
│   ├── provider.py                    # EXTEND: Register VLM + LocalAI tiers
│   ├── router.py                       # Existing SubstrateRouter
│   └── certification.py               # Existing model certification
│
├── agents/                             # AGENTS
│   ├── __init__.py
│   ├── pilot.py                       # Pilot agent (observe→reason→act)
│   └── explorer_mobile.py            # Mobile-aware explorer
│
├── core/
│   ├── devices.py                     # NEW: DeviceClass, VLMTier, DeviceTarget, recommend_vlm_tier()
│   ├── config.py                      # EXTEND: VLM_TIER, MOBILE_EJECT_FORMAT, LOCALAI_*, DESKTOP_*
│   ├── contracts.py                    # EXTEND: MobileSlice, MobileScenario, PilotAction, KnowledgeResult
│   ├── orchestrator.py                # EXTEND: run_mobile_stage(), run_pilot(), process_all_scenarios()
│   ├── truth_model.py                 # EXTEND: Add save()/load() via KnowledgeRepository
│   ├── feedback_store.py             # EXTEND: Bridge to Reflector via EventBus
│   ├── config_loader.py              # EXTEND: desktop profile, LocalAI profile, Redis support
│   └── errors.py                      # Existing (no changes)
│
├── stages/
│   ├── ingest.py                      # EXTEND: Mobile spec dispatch (.apk/.har/.maestro)
│   ├── mobile_plan.py                # NEW: DETERMINISTIC mobile plan stage
│   ├── mobile_generate.py            # NEW: Maestro YAML + Appium TS generation
│   ├── mobile_review.py              # NEW: Mobile review stage
│   ├── mobile_cmd.py                 # NEW: CLI surface for mobile commands
│   └── doctor_cmd.py                 # EXTEND: check_adb, check_xcrun_simctl, check_vlm, check_localai
│
├── execution/
│   ├── maestro_runner.py             # NEW: Maestro CLI wrapper (DevicePort adapter)
│   └── appium_runner.py             # NEW: Appium fallback (DevicePort adapter)
│
├── oracle/
│   ├── visual_oracle.py             # EXTEND: VisualOracleKind enum (pixel_diff/semantic_vlm/hybrid)
│   └── visual_oracle_vlm.py         # NEW: SemanticVisualOracle (gated by self-play)
│
├── reflector/
│   ├── reflector.py                  # EXTEND: Accept events from HITL bridge
│   ├── store.py                       # Existing VerdictStore
│   └── mobile_extensions.py          # NEW: MobileFailureClassifier
│
├── divergence/
│   ├── skeptic.py                     # EXTEND: mobile_hypothesizer strategy
│   ├── explorer.py                    # EXTEND: mobile_explorer mode
│   ├── witness.py                     # EXTEND: pilot_reproduce method
│   └── self_play.py                   # EXTEND: mobile assertion gate
│
├── rag/
│   └── mobile_index.py               # NEW: Per-app RAG (mirrors rag/schema_index.py)
│
├── web/
│   ├── api.py                         # EXTEND: /healthz, /api/v1/chat/*, /api/v1/mobile/*, /api/v1/knowledge/*
│   ├── chat_routes.py                # NEW: Chat API endpoints + SSE streaming
│   ├── mobile_routes.py              # NEW: Mobile API endpoints
│   ├── divergences.py               # Existing
│   └── ui/src/
│       ├── components/
│       │   ├── ChatPanel.tsx          # NEW: Chat UI component
│       │   ├── MobileScreenViewer.tsx  # NEW: Screenshot+UI dump viewer
│       │   ├── SetupScreen.tsx         # REVAMP: 7-step wizard
│       │   ├── ReviewScreen.tsx        # EXTEND: mobile traces, chat button
│       │   ├── HealingScreen.tsx       # EXTEND: structured suggestions
│       │   ├── DivergencesScreen.tsx   # EXTEND: "ask about this" chat
│       │   └── EjectScreen.tsx         # EXTEND: format selector
│       ├── screens/
│       │   ├── Mobile/                 # NEW: Mobile dashboard
│       │   ├── Chat.tsx               # NEW: Full chat screen
│       │   ├── KnowledgeExplorer.tsx   # NEW: Second brain browser
│       │   └── DeviceManager.tsx      # NEW: Device detection & management
│       └── hooks/
│           ├── useChatSession.ts       # NEW: React Query hook for chat
│           └── useMobileSession.ts     # NEW: React Query hook for mobile
│
├── mcp/
│   ├── handlers.py                   # EXTEND: +7 tools (4 mobile + 3 knowledge)
│   ├── policy.py                      # EXTEND: mobile_* + knowledge_* policy entries
│   ├── server.py                      # Existing stdio MCP server
│   └── contracts.py                  # Existing JSON-RPC contracts
│
├── desktop/
│   └── src-tauri/
│       └── src/
│           ├── main.rs               # REWRITE: Full Tauri 2 host with NDJSON
│           ├── hardware.rs            # NEW: GPU/CPU/RAM detection → DeviceClass
│           └── setup/
│               ├── windows.rs         # NEW: Windows setup orchestration
│               ├── macos.rs           # NEW: macOS setup orchestration
│               └── linux.rs           # NEW: Linux setup orchestration
│
├── hitl/
│   ├── store.py                      # EXTEND: +3 mobile classifications, event emission
│   ├── cmd.py                        # Existing HITL CLI
│   └── contracts.py                  # Existing HITL contracts
│
├── ai/
│   ├── interface.py                  # EXTEND: chat() → streaming support
│   ├── rag_index.py                  # EXTEND: multi-domain indexing + mobile traces
│   ├── ollama_client.py              # Existing (keep as fallback)
│   └── openai_client.py             # Existing (opt-in for frontier VLM)
│
└── packaging/
    ├── launcher.py                   # EXTEND: NDJSON events, CHERENKOV_NO_BROWSER, signal handlers
    ├── cherenkov.spec                 # EXTEND: desktop_logging hiddenimport, exclude tests/stub
    └── build.ps1                      # Existing Windows build script
```

### New Files Outside cherenkov/

```
docker-compose.ai.yml                  # NEW: LocalAI + Redis + CHERENKOV stack
cherenkov-policy.mobile.example.json   # NEW: Mobile MCP tools policy
eject_fixtures/mobile/
├── maestro_guest_checkout.yaml        # NEW: First ejected Maestro YAML
└── README.md                          # NEW: "How to run outside CHERENKOV"
tests/
├── unit/
│   ├── test_devices.py               # NEW: DeviceClass, VLMTier, DeviceTarget
│   ├── test_mobile_source_adapter.py  # NEW: Mobile parsers
│   ├── test_vlm_provider.py          # NEW: VLM provider contracts
│   ├── test_pilot_agent.py           # NEW: Pilot loop with stubbed transport
│   ├── test_mobile_rag_index.py      # NEW: Mobile RAG round-trip
│   ├── test_semantic_visual_oracle.py # NEW: Anti-reward-hacking gate
│   ├── test_ejector_mobile.py        # NEW: Maestro YAML zero-import test
│   ├── test_mobile_failure_classifier.py # NEW
│   ├── test_mcp_mobile_tools.py      # NEW: Mobile MCP tools blocked by default
│   ├── test_knowledge_repository.py  # NEW: Knowledge port contracts
│   ├── test_event_bus.py             # NEW: Event publishing and subscription
│   ├── test_chat_agent.py            # NEW: Chat agent tool calling
│   ├── test_conversation_memory.py   # NEW: Session persistence
│   └── test_self_play_mobile.py      # NEW: Mobile anti-reward-hacking
├── contracts/                         # NEW: Behavioral contract tests
│   ├── test_knowledge_repository_contract.py
│   ├── test_memory_repository_contract.py
│   └── test_device_port_contract.py
└── smoke/
    └── smoke_test_mobile.py          # NEW: End-to-end mobile smoke test
```

---

## 5. Revised Flows (Consolidated)

### 5.1 First-Run Flow (NEW: 7-Step Wizard)

```
User launches CHERENKOV desktop app
│
├─ Step 1: Welcome + language preference
├─ Step 2: Hardware Detection
│   ├─ GPU (NVIDIA/AMD/Apple Silicon/None) → DeviceClass → VLMTier
│   ├─ RAM (total + available)
│   ├─ OS (Windows/macOS/Linux)
│   └─ Show: "Your GPU: NVIDIA RTX 4070 → mid_vlm recommended"
├─ Step 3: Engine Selection
│   ├─ Auto-detect LocalAI (Docker) or Ollama
│   ├─ If neither: offer `docker compose -f docker-compose.ai.yml up`
│   ├─ Offer cloud VLM (GPT-4o-mini) as opt-in with egress policy
│   └─ Show: "LocalAI detected with qwen2.5-vl:7b (4.8GB)"
├─ Step 4: VLM & Model Setup
│   ├─ Pull recommended model if not present
│   ├─ Verify model responds to test prompt
│   └─ Show: "Model ready. VLM tier: mid_vlm"
├─ Step 5: Provisions Check
│   ├─ Node.js ≥18, Playwright, Python ≥3.10
│   ├─ ADB (optional, for Android), Xcode simctl (optional, for iOS)
│   ├─ Maestro CLI (optional, for mobile testing)
│   └─ Offer one-click install for missing items
├─ Step 6: Device Targets
│   ├─ Browser emulation (zero setup): iPhone 15, Galaxy S24, iPad Air
│   ├─ Android emulator (ADB + Maestro): Pixel 8, Galaxy S24
│   ├─ iOS simulator (Xcode + Maestro): iPhone 15 Pro, iPad Air (macOS only)
│   ├─ Physical device (ADB/USB): any connected device
│   └─ Show: "Selected: Browser + Android emulator" or "No mobile targets (API-only mode)"
├─ Step 7: Project Bootstrap
│   ├─ Find OpenAPI spec (local files or URL)
│   ├─ Or use demo Petstore spec
│   ├─ Write cherenkov.toml with all detected config
│   ├─ Start LocalAI + Redis (if Docker Compose available)
│   └─ Open dashboard → "Setup complete!"
```

CLI equivalent: `cherenkov onboard` (zero-config first run)

### 5.2 Pipeline Flow (Revised: All Scenarios + Mobile + Events)

```
User starts pipeline (dashboard "New Spec Run" or CLI: cherenkov validate/api)
│
├─ INGEST
│   ├─ .yaml/.json → IngestStage (existing)
│   └─ .apk/.ipa/.har/.maestro → MobileSourceAdapter.ingest()
│
├─ PLAN
│   ├─ IngestOutput → PlanStage (existing, deterministic)
│   └─ MobileIngestOutput → MobilePlanStage (deterministic, no LLM)
│
├─ GENERATE (per scenario, with retry ladder + D2 feedback)
│   ├─ Scenario → GenerateStage (Playwright TS, existing)
│   └─ MobileScenario → MobileGenerateStage (Maestro YAML + optional Appium TS)
│
├─ REVIEW (6 gates + semantic visual oracle)
│   ├─ syntax → structure → AST → assertion → TSC → prism-dryrun
│   ├─ Mobile: + semantic_visual gate (VLM-judged)
│   ├─ VLM confidence < 0.7 → escalate to HITL
│   └─ Output: ReviewOutput or MobileReport with Verdict
│
├─ Decision Gate (per scenario, not just first):
│   ├─ AUTO_APPROVE → Eject
│   ├─ HITL → Queue → Human Review → Approve/Reject → Reflector learns
│   └─ REGENERATE → Loop back (max 3, circuit breaker per endpoint)
│
├─ Domain Events Emitted (NEW):
│   ├─ VerdictRecorded → KnowledgeRepository stores
│   ├─ HITLDecisionMade → Reflector.ingest_human_verdict()
│   └─ DivergenceFound → Skeptic hypothesizes
│
├─ PARALLEL (per DeviceTarget, if configured):
│   ├─ Visual Regression: VisualStage with per-device viewport
│   ├─ Performance: PerfStage with per-device thresholds
│   └─ Mobile Execution: PilotTrace → SemanticOracle → MobileReport
│
└─ EJECT (format determined by Config.EJECT_FORMAT):
    ├─ Playwright TS (existing)
    ├─ Maestro YAML (new, anti-lock-in)
    ├─ Appium TS (new, fallback)
    └─ All: zero CHERENKOV imports verified
```

### 5.3 HITL Review Flow (Revised: Second Brain Bridge)

```
User opens ReviewScreen
│
├─ Sees pending items (API tests + mobile traces + visual diffs)
│
├─ Reviews item:
│   ├─ Approve → HITLDecisionMade event
│   │   ├─ HitlQueue.approve() (atomic)
│   │   ├─ Reflector.ingest_human_verdict(ACCEPT) (NEW)
│   │   ├─ KnowledgeRepository stores context (NEW)
│   │   └─ RAG indexes the decision (NEW)
│   │
│   ├─ Reject → HITLDecisionMade event
│   │   ├─ HitlQueue.reject() (atomic)
│   │   ├─ Reflector.ingest_human_verdict(REJECT) (NEW)
│   │   ├─ Rejected fingerprint recorded (existing)
│   │   └─ RAG indexes the reason (NEW)
│   │
│   ├─ Classify (extended):
│   │   ├─ regression / intended / ignore (existing)
│   │   ├─ mobile_bug / mobile_flaky / mobile_env (NEW)
│   │   └─ Each → Reflector learns (NEW)
│   │
│   ├─ Edit → save modified test code (existing)
│   │
│   └─ Chat about this item (NEW):
│       ├─ ChatPanel opens with item context
│       ├─ QAChatAgent queries KnowledgeRepository
│       ├─ Agent responds with evidence-linked explanation
│       └─ Conversation stored in ConversationMemory
│
└─ Learning Loop Closed (NEW):
    ├─ Every HITL decision feeds Reflector ✓
    ├─ Every verdict feeds KnowledgeRepository ✓
    └─ Future runs benefit from accumulated knowledge ✓
```

### 5.4 Chat Agent Flow (NEW)

```
User opens ChatPanel (sidebar or full ChatScreen)
│
├─ Session starts:
│   ├─ ConversationMemory.create_session()
│   ├─ PersonaRegistry.compose("qa_expert"):
│   │   ├─ Base: "You are CHERENKOV, a QA expert..."
│   │   ├─ + Project context: TruthModel.get_endpoints() summary
│   │   ├─ + Recent idioms: Reflector.get_top_idioms(limit=5)
│   │   └─ + Conversation history: Memory.get_context(session_id)
│   └─ System prompt assembled
│
├─ User sends message: "Why was POST /users rejected?"
│
├─ QAChatAgent processes:
│   ├─ Retrieve context: KnowledgeRepository.query("POST /users rejection")
│   ├─ Compose LLM call (streaming SSE)
│   ├─ Identify intent (question vs. action)
│   └─ Stream response with evidence links
│
├─ User clicks evidence link → navigates to relevant screen
│
└─ Exchange stored in ConversationMemory for future context
```

### 5.5 Mobile Testing Flow (NEW)

```
User: cherenkov mobile run --intent "guest checkout" --target emulator-5554
│
├─ Setup: Device Manager → select target → verify ADB/Maestro → confirm VLM
├─ Ingest: MobileSourceAdapter.ingest(.apk/.har/.maestro) → MobileIngestOutput
├─ Plan: MobilePlanStage.run(slices) → MobilePlanOutput (deterministic, no LLM)
├─ Generate: MobileGenerateStage.run(scenario) → Maestro YAML (or Appium TS)
├─ Review: MobileReviewStage + SemanticVisualOracle → MobileReport + Verdict
├─ Pilot (optional): observe→reason→act→assert→recover loop → PilotTrace
│
├─ Decision:
│   ├─ PASS → Eject Maestro YAML → Verify zero CHERENKOV imports → Save evidence
│   ├─ UNCERTAIN (VLM < 0.7) → HITL queue → user classifies
│   └─ FAIL → MobileFailureClassifier → Verdict feeds Reflector
│
└─ Learning: PilotTrace → KnowledgeRepository, Verdict → Reflector, VLM judgment → RAG
```

### 5.6 Second Brain Query Flow (NEW)

```
Any agent → KnowledgeRepository.query("Why does POST /users return 201?", domains=["verdicts", "idioms", "incidents"], top_k=10)
│
├─ Vector Search: RAGIndex.query_similar() across all domains
├─ Graph Traversal: TruthModel.get_edges() for related claims
├─ Verdict Lookup: VerdictStore.query_recent() for recent verdicts
├─ Idiom Lookup: VerdictStore.get_top_idioms() for confirmed patterns
├─ Hybrid Ranking: vector_similarity*0.4 + graph_proximity*0.3 + recency*0.2 + idiom_overlap*0.1
└─ Return: KnowledgeResult(items, scores, evidence_links)
```

---

## 6. Implementation Phases

### Phase 0: P0 Bug Fixes + Clean Architecture Foundations (Weeks 1-2)

| Step | Kill-Criterion |
|---|---|
| Fix pipeline to process ALL scenarios (not just first) | `run_pipeline()` processes every scenario in `plan.scenarios` |
| Fix `get_stats()` state mutation (separate `decay_idioms()`) | `get_stats()` is read-only, `decay_idioms()` called explicitly |
| Wire mock API endpoints to real data | `/overview`, `/truth-map`, `/failures`, `/metrics` return real KnowledgeRepository data |
| Persist Truth Model to SQLite | `truth_model.save()` and `truth_model.load()` work across restarts |
| Add `KnowledgeResult` standardized envelope | All CLI commands and API endpoints return `KnowledgeResult` JSON |
| Define port interfaces (`ports/*.py`) | All Protocol definitions type-check |
| Add `CHERENKOVEvent` domain events | `VerdictRecorded`, `HITLDecisionMade`, `DivergenceFound` events defined |
| Create `cherenkov/core/devices.py` | `DeviceClass`, `VLMTier`, `DeviceTarget`, `recommend_vlm_tier()` |
| Extend `Config` with new fields | `VLM_TIER`, `MOBILE_EJECT_FORMAT`, `LOCALAI_*`, `DESKTOP_*` |
| Create `docker-compose.ai.yml` | `docker compose -f docker-compose.ai.yml up` starts LocalAI + Redis + CHERENKOV |

### Phase 1: Second Brain (Weeks 3-5)

| Step | Kill-Criterion |
|---|---|
| Create `knowledge/repository.py` (SQLite adapter) | Persist + retrieve claims across restarts |
| Create `knowledge/graph_rag.py` | Vector search + Truth Model traversal returns relevant knowledge |
| Bridge HITL → Reflector | Human approve/reject → `Reflector.ingest_human_verdict()` fires automatically |
| Expand RAG to multi-domain | `query_similar("auth timeout")` returns verdicts AND incidents AND idioms |
| Index `agent_memory/*.md` into RAG | Semantic search over agent memory |
| Index feedback into RAG | Human feedback is searchable |
| Create `knowledge/bridges.py` | All 5 bridges (HITL→Reflector, Feedback→RAG, Memory→RAG, Verdict→RAG, Truth→SQLite) |
| Create `adapters/sqlite_memory.py` (ConversationMemory) | Create session, add messages, retrieve context, persist across restarts |
| Add CLI command: `cherenkov knowledge query` | Returns KnowledgeResult in JSON/text/pretty format |

### Phase 2: Substrate VLM + LocalAI Integration (Weeks 3-4, parallel with Phase 1)

| Step | Kill-Criterion |
|---|---|
| Create `substrate/vlm_provider.py` (ABC + LocalAI + Ollama + OpenAI) | `pytest tests/unit/test_vlm_provider.py` green; egress=none blocks OpenAI |
| Create `substrate/vlm_router.py` (tier-aware routing) | Correct provider selected for each VLM tier |
| Register VLM in `provider.py` | `provider_for_tier("vlm")` returns VLMProvider |
| Test LocalAI Docker integration | `docker compose -f docker-compose.ai.yml up` + VLM request returns result in <10s |
| Add `/healthz` endpoint to `web/api.py` | `GET /healthz` returns `{status, vlm_tier, localai_available, redis_available}` |
| Extend `packaging/launcher.py` | NDJSON events, `CHERENKOV_NO_BROWSER=1`, signal handlers |
| Create `adapters/localai_inference.py` | LocalAI InferenceClient with streaming support |
| Add `cherenkov doctor --vlm` / `--localai` | Shows VLM tier, LocalAI status, model availability |

### Phase 3: Desktop Host + Setup Wizard (Weeks 5-8)

| Step | Kill-Criterion |
|---|---|
| Rewrite `desktop/src-tauri/src/main.rs` | Tauri 2 host with NDJSON parsing, AppState, EngineHandle |
| Create `desktop/src-tauri/src/hardware.rs` | GPU/CPU/RAM detection → DeviceClass → VLMTier recommendation |
| Create `desktop/src-tauri/src/setup/{windows,macos,linux}.rs` | OS-specific prerequisite detection and installation |
| Build 7-step setup wizard in React | Wizard completes, writes config, starts engine |
| Extend `OnboardingWizard.tsx` from 3 steps to 7 | All 7 steps functional with real detection |
| Create `DeviceManagerScreen.tsx` | Shows available targets, SDK status, test connection |
| Update `SettingsScreen.tsx` | VLM tier selector, device target config, Redis config, egress policy |

### Phase 4: Chat Agents (Weeks 5-6, parallel with Phase 3)

| Step | Kill-Criterion |
|---|---|
| Create `chat/persona.py` | PersonaRegistry composes system prompts from project context + idioms + Truth Model |
| Create `chat/agent.py` (QAChatAgent) | Multi-turn conversation with context window management |
| Create `chat/tools.py` | Agent can call `query_verdicts`, `query_idioms`, `explain_divergence`, `run_test` |
| Create `chat/streaming.py` + FastAPI SSE | Tokens stream to desktop app in real time |
| Add MCP knowledge query tools | `query_verdicts`, `query_idioms`, `query_truth_model` exposed via MCP |
| Create `web/chat_routes.py` | 4 endpoints: sessions, messages, stream, history |
| Create `ChatPanel.tsx` component | Chat renders in sidebar, shows streaming tokens |
| Create `ChatScreen.tsx` full-screen view | Chat with knowledge links, navigable to other screens |

### Phase 5: Mobile Testing Core (Weeks 5-10, parallel tail)

| Step | Kill-Criterion |
|---|---|
| Create `sources/mobile/` (contracts, android_dump, ios_dump, har_to_traffic, adapter) | `pytest tests/unit/test_mobile_source_adapter.py` green |
| Extend `stages/ingest.py` with `if is_mobile_spec(path)` | APK/HAR ingestion works |
| Create `agents/pilot.py` with InMemoryRunner stub | `pytest tests/unit/test_pilot_agent.py` green |
| Create `stages/mobile_{plan,generate,review,cmd}.py` | Maestro YAML generation with zero CHERENKOV imports |
| Create `execution/maestro_runner.py` (interface + stub) | Pilot loop works with stub |
| Create `rag/mobile_index.py` | Per-app RAG round-trip works |
| Create `oracle/visual_oracle_vlm.py` (SemanticVisualOracle) | Anti-reward-hacking gate passes |

### Phase 6: Mobile Execution + Semantic Oracle (Weeks 9-11)

| Step | Kill-Criterion |
|---|---|
| Replace InMemoryRunner with real `MaestroRunner` | ADB commands work, screenshots captured |
| Create `execution/appium_runner.py` | Appium fallback for locked-down apps |
| Create `reflector/mobile_extensions.py` | `MOBILE_OS_MODAL`, `MOBILE_NETWORK_BLIP`, `MOBILE_APP_BACKGROUNDED` classifications |
| Extend `divergence/skeptic.py` with `mobile_hypothesizer` | D1/D3/D4 hypotheses for mobile context |
| Extend `divergence/self_play.py` with mobile assertion gate | Correct mock passes, broken one fails |
| Add `make mobile-smoke` target | `make mobile-smoke` exits 0 with Android emulator, skips without |
| Create `eject_fixtures/mobile/maestro_guest_checkout.yaml` | `maestro test` runs green in clean tempdir |

### Phase 7: Dashboard Revamp (Weeks 8-10, parallel with Phase 6)

| Step | Kill-Criterion |
|---|---|
| Wire mock endpoints to real KnowledgeRepository data | `/overview`, `/truth-map`, `/failures`, `/metrics` return real data |
| Add MOCK DATA badges where not ready | 10/17 screens that still use mock data show a badge |
| Wire "Initialize Pilot Run" to `POST /api/v1/run` | Button works end-to-end |
| Add toast notifications for all error/loading states | No silent `catch(console.warn)` |
| Create `MobileScreen.tsx` + `MobileScreenViewer.tsx` | Dashboard `/mobile` shows Pilot traces |
| Create `KnowledgeExplorer.tsx` | Browse idioms, verdicts, incidents, Truth Model, chat history |
| Create `DeviceManagerScreen.tsx` | Shows emulators/devices, SDK status, test connections |
| Extend `ReviewScreen.tsx` with mobile + chat | Mobile trace review, chat button per item |
| Extend `HealingScreen.tsx` with structured suggestions | Diagnosis shows `missing_fields`, `added_fields`, `suggested_fix` |
| Extend `EjectScreen.tsx` with format selector | Playwright/Maestro/Appium/All format choice |
| Extend `DivergencesScreen.tsx` with chat | "Ask about this" button opens ChatPanel |
| Extend `MemoryScreen.tsx` with interactive explorer | Filter by endpoint, drill into pattern, edit decay |

### Phase 8: K8s + Cloud + Validation (Weeks 11-14)

| Step | Kill-Criterion |
|---|---|
| Fix K8s Phase 0 issues (F1-F5) | `make k3d-up && make k3d-test` green |
| Extend ConformanceCheck CRD with DeviceTarget + VisualConfig | `kubectl apply` succeeds |
| Extend operator to pass device env vars to Job spec | Job passes DeviceTarget to runner |
| Add cloud device farm integration (Kobiton/BrowserStack via MCP) | Remote device test runs |
| 5-QA validation gate (desktop + mobile + chat) | Evidence ledger has ≥5 attributable "yes" verdicts |
| Clean architecture docs + contributor guide | New contributor can add an adapter in <30 minutes |
| Open-source readiness (LICENSE, CODE_OF_CONDUCT, CONTRIBUTING.md, SECURITY.md) | Repository meets community standards |

---

## 7. Bug Fixes (Priority Order)

| # | Bug | Fix | Priority | Phase |
|---|---|---|---|---|
| 1 | Pipeline only processes `plan.scenarios[0]` | Loop over all scenarios in `run_pipeline()` | P0 | 0 |
| 2 | `get_stats()` mutates state | Separate `decay_all_idioms()` from `get_stats()` | P0 | 0 |
| 3 | Mock API endpoints return empty data | Wire to real KnowledgeRepository | P0 | 0 |
| 4 | HITL decisions don't feed Reflector | Emit event → `Reflector.ingest_human_verdict()` | P0 | 0 |
| 5 | Healing suggestions are text-only | Add structured `DiagnosisResult` output | P1 | 7 |
| 6 | Cache/accounting stats only to stdout | Persist to `events.jsonl` + KnowledgeRepository | P1 | 0 |
| 7 | Two review servers (port 8080 + 8000) | Deprecate `review_serve.py`, FastAPI only | P1 | 7 |
| 8 | Eject only produces one test file | Eject all scenarios in `stub/generated_tests/` | P1 | 5 |
| 9 | RAG only indexes incidents | Expand to multi-domain | P2 | 1 |
| 10 | Truth Model in-memory only | Add `save()`/`load()` via KnowledgeRepository | P2 | 1 |

---

## 8. CLI Commands (Full Map)

### Existing (Unchanged)

```bash
cherenkov validate          # Track A pipeline
cherenkov init             # Project setup (extended with --vlm, --device, --mobile)
cherenkov doctor            # Health checks (extended with --vlm, --localai, --mobile)
cherenkov review           # Start dashboard
cherenkov hitl list/show/approve/reject/classify/explain
cherenkov eject            # Eject test suite (extended with --format)
cherenkov visual           # Visual regression (extended with --device)
cherenkov perf             # Performance baseline
cherenkov map              # Truth model
cherenkov daemon            # Continuous watch
cherenkov explore           # Live surface crawl
cherenkov author            # Author by intent
cherenkov governance        # KPI panel
cherenkov certify           # Model certification
cherenkov profile           # Autonomy ladder
cherenkov self-test         # Deterministic dry-run
cherenkov report            # Generate report
cherenkov mcp serve         # MCP server
```

### New Commands

```bash
cherenkov mobile init      # Set up mobile testing (detect ADB, install Maestro, pull model)
cherenkov mobile run       # Run Pilot agent on device target
cherenkov mobile eject     # Eject mobile test suite (Maestro/Appium/All)
cherenkov mobile trace-list  # List Pilot traces
cherenkov chat             # Interactive chat with QA agent
cherenkov knowledge query  # Query second brain
cherenkov knowledge idioms # List top idioms for endpoint
cherenkov status           # Single source of truth (doctor + run state + queue + last finding)
cherenkov onboard          # Zero-config first-run (init + doctor + first run with petstore)
```

### Aliases (Shortcuts, Don't Replace Originals)

```bash
cherenkov api              # alias for: validate
cherenkov system           # alias for: init/doctor/daemon
cherenkov system status    # alias for: status
```

### Global Flags (Add to ALL Commands)

```bash
--format json|text|pretty  # Output format (standardized envelope)
--verbose                  # Debug logging
--config PATH             # Config file override
--profile NAME            # Configuration profile (laptop/ci/enterprise/frontier-cloud)
```

---

## 9. API Endpoints (Full Map)

### Existing (Unchanged)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Liveness + Ollama detection |
| POST | `/api/v1/ingest` | Parse OpenAPI spec |
| POST | `/api/v1/run` | Trigger pipeline |
| GET | `/api/v1/tests` | Retrieve generated tests |
| POST | `/api/v1/review/approve` | Approve HITL item |
| POST | `/api/v1/review/reject` | Reject HITL item |
| POST | `/api/v1/review/explain` | AI explanation |
| POST | `/api/v1/review/edit` | Save edited test code |
| GET | `/api/v1/review/queue` | List HITL queue |
| POST | `/api/v1/review/classify` | Classify HITL item |
| POST | `/api/v1/validate` | Run Playwright validation |
| POST | `/api/v1/eject` | Export standalone suite |
| GET | `/api/v1/divergences` | List divergences |
| POST | `/api/v1/divergences/act` | Act on divergence |
| GET | `/api/v1/settings` | Load settings |
| PUT | `/api/v1/settings` | Save settings |
| GET | `/api/v1/doctor` | System health checks |
| GET | `/api/v1/projects` | List projects |
| WS | `/ws/live` | Real-time event stream |

### New Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/healthz` | Sidecar health (distinct from `/health`; includes `vlm_tier`, `device_class`, `redis_available`) |
| POST | `/api/v1/chat/sessions` | Create chat session |
| POST | `/api/v1/chat/{id}/messages` | Send message to chat agent |
| GET | `/api/v1/chat/{id}/stream` | SSE stream for chat responses |
| GET | `/api/v1/chat/{id}/history` | Get conversation history |
| GET | `/api/v1/knowledge/query` | Query second brain (multi-domain) |
| GET | `/api/v1/knowledge/idioms` | Get top idioms for an endpoint |
| GET | `/api/v1/knowledge/verdicts` | Get recent verdicts |
| POST | `/api/v1/mobile/run` | Start mobile test run |
| GET | `/api/v1/mobile/sessions` | List mobile sessions |
| GET | `/api/v1/mobile/trace/{id}` | Get pilot trace |
| POST | `/api/v1/mobile/trace/{id}/approve` | Approve mobile trace |
| GET | `/api/v1/devices` | List available device targets |
| POST | `/api/v1/devices/refresh` | Refresh device detection |

### Revamped Endpoints (Wire to Real Data)

| Method | Path | Change |
|---|---|---|
| GET | `/api/v1/overview` | Wire to KnowledgeRepository (was mocked) |
| GET | `/api/v1/truth-map` | Wire to persisted Truth Model (was mocked) |
| GET | `/api/v1/failures` | Wire to VerdictStore + Diagnoser (was mocked) |
| GET | `/api/v1/metrics` | Wire to KnowledgeRepository (was mocked) |
| GET | `/api/v1/memory` | Add query params for filtering |

---

## 10. Dashboard Screens (Full Map)

### Existing Screens (Keep)

| Screen | Path | Status |
|---|---|---|
| ProjectsScreen | `/` | Keep as-is |
| PipelineScreen | `/pipeline` | Extend: show all scenarios |
| ReviewScreen | `/review` | Extend: mobile traces, chat button |
| HealingScreen | `/healing` | Extend: structured suggestions |
| EjectScreen | `/eject` | Extend: format selector |
| SettingsScreen | `/settings` | Extend: VLM tier, device config, Redis, egress |
| AuthorScreen | `/author` | Extend: device target selector |
| SignalsScreen | `/signals` | Wire to real data |
| GovernanceScreen | `/governance` | Wire to real data |
| MemoryScreen | `/memory` | Extend: interactive idiom explorer |

### Existing Screens (Revamp)

| Screen | Path | Change |
|---|---|---|
| OnboardingWizard | (overlay) | Expand from 3 steps to 7 |
| SetupScreen | `/setup` | Add mobile spec upload, device target selection |
| OverviewScreen | `/overview` | Wire to real KnowledgeRepository data |
| TruthMapScreen | `/truth-map` | Wire to persisted Truth Model |
| DivergencesScreen | `/divergences` | Add mobile divergences, "ask about this" chat |

### New Screens

| Screen | Path | Purpose |
|---|---|---|
| ChatScreen | `/chat` | Full-screen chat with QA agent |
| ChatPanel | (overlay) | Floating chat accessible from any screen |
| MobileScreen | `/mobile` | Pilot trace list, replay, classify |
| MobileScreenViewer | (component) | Screenshot + UI dump side-by-side |
| DeviceManagerScreen | `/devices` | Detect emulators, install SDKs, test connections |
| KnowledgeExplorer | `/knowledge` | Browse second brain: idioms, verdicts, incidents, Truth Model |

---

## 10. Cost Estimate

| Item | Monthly Cost | Notes |
|---|---|---|
| LocalAI (self-hosted) | **$0** | Docker Compose, runs on user's hardware |
| Redis Stack (self-hosted) | **$0** | `redis/redis-stack-server` Docker image |
| Ollama (existing users) | **$0** | Already installed, works as fallback |
| Android emulator | **$0** | Android Studio / command-line tools |
| Maestro CLI | **$0** | Open-source |
| ChromaDB (alternative to Redis) | **$0** | `pip install chromadb` |
| Cloud VLM (opt-in) | $0.01-0.10/call | Only when egress enabled |
| Cloud device farms (opt-in) | $0.10-1.00/test | Only when explicitly configured |
| **Solo developer total** | **$0/month** | Everything free, local-first |

---

## 11. Open Questions

| # | Question | Options | Recommendation |
|---|---|---|---|
| 1 | LocalAI or Ollama as default? | LocalAI (Docker-native, OpenAI-compatible, VLM built-in) vs Ollama (simpler CLI, wider model support) | LocalAI as default in Docker Compose, Ollama as standalone fallback |
| 2 | Redis required or optional? | Required (full second brain) vs Optional (SQLite fallback for solo users) | Optional with graceful degradation |
| 3 | Docker MCP Gateway: internal-only or external-facing? | Internal (CHERENKOV MCP server stays stdio-only) vs External (Docker MCP Gateway for agents like Claude, Copilot) | Start internal, upgrade to Docker MCP Gateway when multi-agent coordination is needed |
| 4 | Airflow/Prefect for pipeline orchestration? | Yes (formal DAG scheduling) vs No (use existing OrchestrationEngine) | No — CHERENKOV is event-driven, not batch-scheduled. asyncio.Queue → Redis Streams is sufficient. |
| 5 | CLI restructuring: rename or alias? | Rename (cleaner but breaks existing scripts) vs Alias (backward compatible) | Alias only — never break existing commands |
| 6 | Chat agent model: which for default? | Local VLM (qwen2.5-vl:3b) vs Local text (qwen2.5-coder:7b) vs Cloud (GPT-4o-mini) | Text for chat (qwen2.5-coder), VLM for visual (qwen2.5-vl), cloud opt-in for frontier |

---

This is the complete unified plan covering all 5 capabilities (desktop, mobile, chat, second brain, clean architecture) plus infrastructure (LocalAI, Redis, Docker Compose, MCP Gateway) plus UI revamp plus bug fixes. Shall I begin implementation, or do you want to adjust any decisions first?