# Implementation Plan: Mobile Testing Context for CHERENKOV

**Status:** Draft v0.1 · **Date:** 2026-06-08
**Author:** Autonomous planning agent (response to `docs/vision/MOBILE_AUTOMATION_RESEARCH.md`)
**SSOT anchors:** [`docs/HANDOVER.md`](../HANDOVER.md) · [`docs/SCOPE_LEDGER.md`](../SCOPE_LEDGER.md) · [`docs/ROADMAP_NEXT.md`](../ROADMAP_NEXT.md) · [`docs/vision/00_VISION.md`](../vision/00_VISION.md) · [`docs/vision/01_ARCHITECTURE.md`](../vision/01_ARCHITECTURE.md) · [`docs/vision/06_AUTONOMOUS_QA_FABRIC.md`](../vision/06_AUTONOMOUS_QA_FABRIC.md)

> **Anti-drift reminder (HANDOVER §2).** No "v3.1 + delta", no fabricated
> tests, no "100% complete" claims. Every implementation step exits on
> **raw evidence** — terminal output, git status, recorded test runs.

---

## [Overview]

**Single sentence:** Add a first-class mobile testing capability to CHERENKOV
by widening the four open seams (Sources, Models, Artifacts, Oracles) so that
the existing Reality Engine can ingest mobile UIs/traffic, reason about them
with a vision-language model, drive a mobile runtime via the new Pilot agent,
and emit standalone mobile tests (Maestro / Appium) — without ever forking
Track A or violating the four design invariants (D7, anti-lock-in,
suggest-only, spec-derived).

**Why this matters, in the project's own words.** The Reality Engine's
deliverable is *truth*; the deliverable is *evidence that sources of truth
agree*. Today the Sources seam accepts OpenAPI, code, traffic, and DB schema
(see `01_ARCHITECTURE.md` §5). The mobile research (LLMs + RAG + agents
redefining mobile QA) makes it obvious that **the most-deployed software in
the world runs on a phone, and a Reality Engine that can't see the phone is
incomplete**. Adding mobile is therefore not a new product — it is a
required widening of one of the four open seams, exactly as the
`06_AUTONOMOUS_QA_FABRIC.md` table already anticipates ("UI: DOM +
**screenshots/video**" and "**Vision-Language tier: UI-TARS / Qwen3-VL**"
are listed as new Source and Model families).

**Strategic placement (the choice the plan defends).** The plan uses
**build-over (parallel)**, not a new track. It widens the existing seams
while Wave 2/3/4 (honesty debt, UI-only loop, one-click install) continues.
The reasons are explicit in the Autonomous QA Fabric doc: "scale-up, not
stack-on — every capability grows an existing module." This is the only
choice that (a) preserves the Substrate Router as the single keystone for
intelligence, (b) reuses the existing Truth Model + Reflector + Diverge nce
Loop, and (c) keeps the four design invariants untouched. A new track
would re-introduce the very problem the 2026-06-05 reconcile/horizon work
just resolved.

**Honest scope boundaries.** This plan covers: (1) the **mobile Source
Adapter** (L1) — ingests iOS/Android UI dumps, accessibility trees, and
mobile traffic captures; (2) a **Vision-Language-Model provider** in the
Substrate (L0) — the keystone for everything visual; (3) the **Pilot
agent** (L2, extends Witness) — observes a screen, reasons about the next
action, executes it on a real device/emulator; (4) **mobile-aware planning
and generation stages** (L3) — produce ejectable Maestro YAML and
Appium-style TS; (5) **MCP-native exposure** — CHERENKOV is *both* an MCP
server (expose `mobile_inspect`, `mobile_act`, `mobile_capture_view`)
*and* an MCP client (drives Maestro / Appium servers); (6) a
**semantic visual oracle** that replaces brittle pixel diff with
VLM-judged pass/fail, gated by the existing anti-reward-hacking
self-play so it never rubber-stamps; (7) a **mobile-aware Reflector** that
distinguishes `bug | flaky | env | intended` for mobile failures (auth
expiry, OS permission modal, app backgrounded, etc.). The plan does **not**
ship: physical robotics (Mobot-class), a competitor-to-Kobiton device farm,
or any auto-PR of mobile findings. Those are noted as out-of-scope and
gated on demand signal, consistent with `HANDOVER §6.3`.

**Kill-criteria for the whole mobile capability (matches the
"≥5 reproduced divergences" rigor from E3).** Mobile is "shipped" only
when, on a real Android emulator (or a real device via MCP), CHERENKOV:
(a) ingests an APK/IPA + a mobile traffic capture and reproduces a
D3_ui_spec-style divergence that the spec alone missed; (b) ejects a
standalone Maestro YAML that runs green outside CHERENKOV; (c) the
Reflector/loop shows that a previously-rejected mobile finding no
longer re-surfaces (the E7-style behavioral test); (d) the validation
gate's 5-QA panel (Wave 5) has at least one reviewer who runs the
mobile golden path on a phone and gives attributable "yes" evidence.

---

## [Types]

All types extend (never replace) the existing `cherenkov/core/contracts.py`
contracts. Every new model is Pydantic, versioned via `SCHEMA_VERSION`,
and emits onto the existing `StageMeta`/`Status`/`Verdict` enums so the
REVIEW / HITL / Reflector loops Just Work.

### Source-side types (L1 — Truth Model)

```python
# cherenkov/sources/mobile/contracts.py

class MobilePlatform(str, Enum):
    ANDROID = "android"
    IOS = "ios"

class MobileUIElement(BaseModel):
    """One node from a UIAutomator dump or iOS XCUITest accessibility tree."""
    id: str                       # CHERENKOV-assigned (not the OS id)
    role: str                     # "button" | "textfield" | "label" | "cell" | ...
    label: str | None             # accessibility label (may be missing in Flutter)
    text: str | None              # visible text
    bounds: tuple[int, int, int, int]  # x, y, x+w, y+h in screen px
    clickable: bool = False
    focusable: bool = False
    platform_id: str | None       # OS resource-id (Android) / identifier (iOS)
    schema_version: int = SCHEMA_VERSION

class MobileScreenState(BaseModel):
    """One captured screen at a moment in time — the Pilot's observation."""
    platform: MobilePlatform
    package_or_bundle: str        # "com.example.app" / "com.example.app"
    activity_or_scene: str | None # "MainActivity" / "LoginViewController"
    screenshot_path: str          # local file path, evidence artefact
    ui_dump: list[MobileUIElement]
    captured_at: int              # unix ts
    orientation: str = "portrait" # "portrait" | "landscape"
    schema_version: int = SCHEMA_VERSION

class MobileTrafficEntry(BaseModel):
    """A single captured request/response from a mobile proxy or device log."""
    method: str
    url: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: str | None = None
    response_status: int
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: str | None = None
    latency_ms: int = 0
    captured_at: int
    schema_version: int = SCHEMA_VERSION

class MobileAppContext(BaseModel):
    """Per-app RAG chunk: app version, build variant, locale, build flavour, etc.
    Stored alongside the source-claim so the Reflector and Pilot can reason
    about 'works on free build, fails on enterprise build'-style issues."""
    app_id: str
    app_version: str
    build_variant: str = "release"   # "debug" | "release" | "staging" | ...
    locale: str = "en-US"
    os_version: str | None = None
    device_model: str | None = None
    schema_version: int = SCHEMA_VERSION
```

### Substrate-side types (L0 — Provider)

```python
# cherenkov/substrate/vlm_provider.py (extends substrate/provider.py)

class VLMTier(str, Enum):
    """Capability tier for vision-language models. Used by Substrate Router
    to route the Pilot's reasoning to the right model."""
    SMALL_VLM = "small_vlm"      # 3-4B param, e.g. Qwen2.5-VL-3B, MiniCPM-V
    MID_VLM   = "mid_vlm"        # 7-8B, e.g. Qwen2.5-VL-7B, LLaVA-1.6-13B
    FRONTIER_VLM = "frontier_vlm" # 70B+ or hosted, e.g. GPT-4o, Claude-3.5-Sonnet

class VLMRequest(BaseModel):
    """Reasoning Request extension for vision tasks. Honors existing
    ReasoningRequest contract (sensitivity, max_cost, max_latency) and
    adds a screen image + structured output schema."""
    task: str                     # e.g. "identify the primary CTA on this screen"
    image_path: str               # mandatory for VLM
    ui_dump: list[MobileUIElement] = Field(default_factory=list)  # hint
    prompt: str                   # free-form prompt with intent
    output_schema: dict | None    # Pydantic model JSON schema
    capability_tier: VLMTier = VLMTier.SMALL_VLM
    max_cost: float = 0.0
    max_latency: int = 0
    sensitivity: str = "standard"
    schema_version: int = SCHEMA_VERSION

class VLMResult(BaseModel):
    content: dict | str           # parsed per output_schema, or raw text
    provider: str
    model: str
    cost_usd: float = 0.0
    latency_ms: int = 0
    cached: bool = False
    schema_version: int = SCHEMA_VERSION
```

### Agent-side types (L2 — Pilot)

```python
# cherenkov/agents/pilot.py

class PilotActionKind(str, Enum):
    TAP = "tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    TYPE_TEXT = "type_text"
    PRESS_BACK = "press_back"
    PRESS_HOME = "press_home"
    OPEN_DEEP_LINK = "open_deep_link"
    ROTATE = "rotate"
    SCROLL = "scroll"
    WAIT = "wait"
    ASSERT_PRESENT = "assert_present"
    ASSERT_TEXT = "assert_text"
    ASSERT_ABSENT = "assert_absent"
    DONE = "done"                 # terminal — intent satisfied (or impossible)

class PilotAction(BaseModel):
    """One atomic action the Pilot will execute on the device."""
    kind: PilotActionKind
    target: str = ""              # role+label description ("the green confirm button")
    value: str = ""               # text to type, expected assertion text, deep-link URL
    confidence: float = 0.0       # 0.0–1.0 VLM self-reported confidence
    rationale: str = ""           # VLM explanation (kept for Reflector, never used in test)
    schema_version: int = SCHEMA_VERSION

class PilotObservation(BaseModel):
    """One cycle: state in, action out, plus the resulting state.
    This is the unit the Reflector ingests and the UI replays."""
    id: str
    intent: str                   # the original plain-language intent
    state_before: MobileScreenState
    action: PilotAction
    state_after: MobileScreenState | None = None
    error: str | None = None
    duration_ms: int = 0
    schema_version: int = SCHEMA_VERSION

class PilotTrace(BaseModel):
    """Full execution of a plain-language intent — list of observations."""
    intent: str
    started_at: int
    finished_at: int = 0
    observations: list[PilotObservation] = Field(default_factory=list)
    final_state: MobileScreenState | None = None
    outcome: Literal["success", "failed", "blocked", "timeout"] = "success"
    schema_version: int = SCHEMA_VERSION
```

### Stage-side types (L3 — Plan / Generate)

```python
# cherenkov/stages/mobile_*.py (mirror existing ui_* types)

class MobileScenario(BaseModel):
    """A planned mobile journey, parallel to the existing UIScenario."""
    id: str
    name: str
    intent: str                   # plain-language source
    platform: MobilePlatform
    target_package: str           # "com.example.app"
    steps: list[PilotAction] = Field(default_factory=list)
    expected_outcomes: list[str] = Field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

class MobileSlice(BaseModel):
    """A single mobile test target — a screen + intent + baseline."""
    name: str
    intent: str
    target_package: str
    baseline_screenshot: str | None = None  # semantic oracle baseline (not pixel)
    context: MobileAppContext = Field(default_factory=MobileAppContext)
    schema_version: int = SCHEMA_VERSION

class MobileGateResult(BaseModel):
    gate: str                     # "semantic_visual" | "intent_satisfied" | "pilot_trace_complete"
    passed: bool
    detail: str = ""
    schema_version: int = SCHEMA_VERSION

class MobileReport(BaseModel):
    """PilotStage output. Mirrors VisualReport shape; HITL on failure."""
    scenario_id: str
    gates: list[MobileGateResult]
    verdict: Verdict              # reused from contracts.py
    status: Status                # reused
    trace: PilotTrace | None = None
    errors: list[StageError] = Field(default_factory=list)
    metadata: StageMeta
    schema_version: int = SCHEMA_VERSION
```

### Oracle-side types (semantic visual oracle)

```python
# cherenkov/oracle/visual_oracle.py (existing file — extend, do not replace)

class VisualOracleKind(str, Enum):
    PIXEL_DIFF = "pixel_diff"              # existing
    SEMANTIC_VLM = "semantic_vlm"          # NEW — VLM-judged
    HYBRID = "hybrid"                       # NEW — both, VLM wins on disagreement

class SemanticVisualVerdict(BaseModel):
    """A VLM-judged pass/fail. NEVER sole oracle — always combined with
    the existing adversarial self-play (E3-3) to kill 'true==true' rewards."""
    question: str                  # "Does this screen show a successful checkout?"
    vlm_response: str
    confidence: float
    pixel_diff_summary: dict | None = None
    final_passed: bool
    rationale: str = ""
    schema_version: int = SCHEMA_VERSION
```

### Skill & MCP envelope types

```python
# cherenkov/skills/mobile.md is markdown only (no code). The MCP handlers
# in cherenkov/mcp/handlers.py gain new MCPTool definitions using only
# existing MCP contract types (MCPContent, MCPToolCallResult, etc.) — no
# new envelope needed.
```

---

## [Files]

All paths are relative to repo root unless absolute. New files are
**additive**; existing files are **edited in place, never replaced**.

### New files (additive)

| Path | Purpose | LOC est. |
|---|---|---|
| `cherenkov/sources/__init__.py` | Package marker (sources seam) | 5 |
| `cherenkov/sources/contracts.py` | `MobileUIElement`, `MobileScreenState`, `MobileTrafficEntry`, `MobileAppContext` (defined above) | 90 |
| `cherenkov/sources/adapter.py` | `SourceAdapter` SPI: `def name(self)`, `def can_ingest(self, path)`, `def ingest(self, path) -> IngestOutput` | 60 |
| `cherenkov/sources/mobile/android_dump.py` | Parser for `uiautomator dump` XML output → `MobileScreenState` | 110 |
| `cherenkov/sources/mobile/ios_dump.py` | Parser for iOS XCUITest `accessibilityDescription` JSON → `MobileScreenState` | 110 |
| `cherenkov/sources/mobile/har_to_traffic.py` | Extract `MobileTrafficEntry[]` from a HAR captured on a phone | 70 |
| `cherenkov/sources/mobile/adapter.py` | `MobileSourceAdapter` (implements SPI) — orchestrates parsers + writes claims to the Truth Model | 150 |
| `cherenkov/substrate/vlm_provider.py` | `VLMProvider` ABC + `OllamaVLMProvider` (Qwen2.5-VL via Ollama) + `OpenAIVLMProvider` (GPT-4o) | 220 |
| `cherenkov/substrate/vlm_router.py` | Tier-aware VLM router; reuses `substrate/router.py` SPI; adds `egress` + VLM-specific cost/latency budgets | 180 |
| `cherenkov/agents/__init__.py` | Package marker | 5 |
| `cherenkov/agents/pilot.py` | `Pilot` agent — observe → reason → act loop; uses VLM + RAG; produces `PilotTrace` | 280 |
| `cherenkov/agents/explorer_mobile.py` | Mobile flavour of the existing `divergence/explorer.py` — crawls an app, surfaces anomalies, feeds the Skeptic | 200 |
| `cherenkov/stages/mobile_plan.py` | `MobilePlanStage` — pure-deterministic (no LLM) mapping of `MobileSlice` → `MobileScenario` set; same role as existing `stages/plan.py` | 120 |
| `cherenkov/stages/mobile_generate.py` | `MobileGenerateStage` — emits **Maestro YAML** (default) and optional Appium TS, by analogy to `stages/ui_generate.py`. Uses the Substrate Router via the new VLM provider for hints only. | 240 |
| `cherenkov/stages/mobile_review.py` | `MobileReviewStage` — runs the ejected Maestro YAML in a sandbox and feeds `MobileReport` into the existing REVIEW pipeline; tsc-only for the Appium variant | 110 |
| `cherenkov/stages/mobile_cmd.py` | CLI surface: `cherenkov mobile init`, `cherenkov mobile run --intent "..."`, `cherenkov mobile eject --output <dir>` | 100 |
| `cherenkov/oracle/visual_oracle_vlm.py` | `SemanticVisualOracle` — VLM-backed pass/fail, *never* sole oracle; pairs with the existing pixel-diff oracle in `oracle/visual_oracle.py` | 180 |
| `cherenkov/execution/maestro_runner.py` | `MaestroRunner` — wraps the `maestro` CLI (or a Maestro MCP server) for action execution; anti-lock-in: writes plain YAML, runs outside CHERENKOV | 160 |
| `cherenkov/execution/appium_runner.py` | `AppiumRunner` — alternative runtime, used when an app cannot be re-authored as Maestro YAML (e.g. third-party apps with locked-down flows) | 200 |
| `cherenkov/reflector/mobile_extensions.py` | `MobileFailureClassifier` — extends `healing/diagnose.py` to classify mobile failures (OS modal, auth expiry, network blip, app backgrounded) | 150 |
| `cherenkov/rag/mobile_index.py` | `MobileAppRAGIndex` — per-app RAG over release notes, deeplinks, screen maps, prior Pilot traces (nomic-embed-text, mirrors `rag/schema_index.py`) | 180 |
| `cherenkov/web/mobile_routes.py` | FastAPI routes: `GET /api/v1/mobile/sessions`, `POST /api/v1/mobile/run`, `GET /api/v1/mobile/trace/<id>` — wired into the existing `cherenkov/web/api.py` | 90 |
| `cherenkov/web/ui/src/screens/Mobile/MobileView.tsx` | New dashboard screen — list Pilot traces, replay, classify into bug/flaky/env/intended | 250 |
| `cherenkov/web/ui/src/components/MobileScreenViewer.tsx` | Screenshot+UI-dump side-by-side viewer for manual review (HITL Tier-1) | 160 |
| `cherenkov/web/ui/src/hooks/useMobileSession.ts` | React Query hook for the new endpoints | 70 |
| `docs/skills/mobile.md` | Skill doc — autonomous agents read this before running a mobile session (mirrors `skills/visual-regression.md` style) | 80 |
| `docs/plans/2026-06-08-mobile-evidence.md` | Evidence ledger (run logs, screenshots, gate results) — required raw evidence for the Wave-5 mobile kill-criteria | 30 |
| `tests/unit/test_mobile_source_adapter.py` | Unit tests for Android/iOS dump parsers + HAR→traffic mapping | 220 |
| `tests/unit/test_vlm_provider.py` | VLM provider contract tests; mock Ollama + OpenAI; honour `egress` dial | 150 |
| `tests/unit/test_pilot_agent.py` | Pilot loop with a stubbed device transport; cycle count, terminal action, no-shared-context verifier | 180 |
| `tests/unit/test_mobile_rag_index.py` | Mobile RAG round-trip: ingest, retrieve, cache invalidation | 130 |
| `tests/unit/test_semantic_visual_oracle.py` | Oracle passes correct mock, fails broken impl (D3 anti-reward-hacking) | 120 |
| `tests/smoke/smoke_test_mobile.py` | End-to-end: ingest APK, run Pilot in a stubbed emulator, eject a Maestro YAML, run it standalone in a clean temp dir | 280 |
| `eject_fixtures/mobile/maestro_guest_checkout.yaml` | The first ejected Maestro YAML — proves anti-lock-in by running zero-CHERENKOV | 50 |
| `eject_fixtures/mobile/README.md` | "How to run these outside CHERENKOV" — `maestro test eject_fixtures/mobile/maestro_guest_checkout.yaml` | 25 |
| `cherenkov-policy.mobile.example.json` | Example policy granting `mobile_run`, `mobile_capture_view` etc. for the new MCP tools; defaults to "blocked" until enabled | 60 |

### Existing files to edit (additive, never breaking)

| Path | Specific change |
|---|---|
| `cherenkov/core/contracts.py` | **No** change to existing enums. (Optional, deferred) Re-export the new `Mobile*` types in the same file for discoverability — but only if it doesn't bloat the file past 700 lines; otherwise leave them in `sources/mobile/contracts.py`. |
| `cherenkov/core/orchestrator.py` | Add `run_mobile_stage(slices, run_id)` and `run_pilot(intent, package, run_id)` methods. Wire `MobilePlanStage` and `MobileGenerateStage` into the DAG **only** when the spec is an APK/IPA path or `--intent` is passed. Track A path is unchanged. |
| `cherenkov/stages/ingest.py` | Extend `run()` to dispatch to `MobileSourceAdapter` when the spec path ends in `.apk`, `.ipa`, or `.maestro/`; otherwise the existing JSON/YAML path is preserved. The branch is one `if` — no existing tests touched. |
| `cherenkov/substrate/router.py` | Extend the policy allowlist to include `VLM` capability tier. **Reuse** the existing capability-tier→provider routing; do not duplicate. |
| `cherenkov/substrate/provider.py` | Add a `VLMProvider` to the provider registry by name (`vlm`). No behaviour change for non-VLM callers. |
| `cherenkov/divergence/skeptic.py` | Add a `mobile_hypothesizer` strategy that consumes `MobileAppContext` + `MobileTrafficEntry[]` and emits D1/D3/D4 hypotheses in the existing `DivergenceHypothesis` shape. The Skeptic is unchanged for API-only flows. |
| `cherenkov/divergence/explorer.py` | Add a `mobile_explorer` mode that wraps `agents/explorer_mobile.py`. Honours the existing `risk_digest` API. |
| `cherenkov/divergence/witness.py` | Add a `pilot_reproduce(hypothesis) -> ReproductionResult` method that delegates to `agents/pilot.py` instead of `cherenkov/execution/validate.py`. |
| `cherenkov/divergence/self_play.py` | Extend the adversarial self-play to also run ejected mobile tests against the correct mock + a deliberately broken one. (Required for the kill-criteria: D3 anti-reward-hacking.) |
| `cherenkov/healing/diagnose.py` | Hook `MobileFailureClassifier` to the existing `FailureClass` enum via a `MOBILE_*` prefix. Existing `AUTH_EXPIRY` / `CONTRACT_DRIFT` unchanged. |
| `cherenkov/oracle/visual_oracle.py` | Add `SemanticVisualOracle` as a sibling — **not** a replacement. The existing `pixel_diff` oracle is the default; `hybrid` is opt-in via `cherenkov.toml`. |
| `cherenkov/ai/rag_index.py` | Add a `mobile_add_trace(trace)` method; do not change the schema. |
| `cherenkov/mcp/handlers.py` | Add 4 MCP tools: `mobile_list_sessions`, `mobile_run`, `mobile_capture_view`, `mobile_approve_trace`. Each delegates to `agents/pilot.py` and the existing `HitlQueue`; no new envelope. **All new tools gated by the existing `cherenkov-policy.json` allowlist**, defaulting to **blocked** until explicitly enabled — the trust model for MCP peers is "untrusted" (see `cherenkov/mcp/handlers.py` docstring). |
| `cherenkov/mcp/policy.py` | Add `mobile_*` to the policy schema; example provided in `cherenkov-policy.mobile.example.json`. |
| `cherenkov/hitl/store.py` | Add `classification` support for `mobile_bug | mobile_flaky | mobile_env` alongside existing `bug | flaky | env | intended`. No migration — additive. |
| `cherenkov/web/api.py` | Mount the new routes from `cherenkov/web/mobile_routes.py`. Add `/api/v1/mobile/*` to the OpenAPI metadata. |
| `cherenkov/web/ui/src/App.tsx` | Register the new `MobileView` screen in the router and the sidebar nav. |
| `cherenkov/web/ui/src/api.ts` | Add the 3 mobile endpoints to the typed client. |
| `cherenkov/stages/doctor_cmd.py` | Extend `check_*` to also probe `adb` (Android) and `xcrun simctl` (iOS) presence. Fail-soft — only emit warnings, never block the doctor. |
| `cherenkov/core/feedback_store.py` | Reuse as-is — mobile findings flow through the same FeedbackStore. |
| `cherenkov/reflector/reflector.py` | Feed `PilotTrace` outcomes into the verdict memory using the existing `VerdictRecord` shape. Add a `mobile_outcome` reason field. No new module. |
| `cherenkov.py` | Add the `mobile` subcommand (init, run, eject, trace-list). No changes to existing commands. |
| `cherenkov/execution/eject.py` | Extend the ejector to recognise the `mobile/maestro_*.yaml` eject pattern. Verify the ejected dir contains zero `cherenkov` imports — same rule the API ejector already enforces. |
| `docs/HANDOVER.md` | Update the Track A inventory list and SCOPE_LEDGER §B to note the new mobile seam (one bullet under "WIDENED Sources/Models/Artifacts/Oracles"). Do not change the validation-gate status. |
| `docs/SCOPE_LEDGER.md` | Add the mobile work to §B "Built-ahead, now LIVE" table — same row pattern as the existing `ai/openai_client.py` and `stages/visual/`. |
| `docs/ROADMAP_NEXT.md` | Add a new row to Wave 6 "Earned expansion" with the mobile capability ticket IDs and a one-line note that they are gated on demand signal from the 5-QA panel. |
| `docs/vision/06_AUTONOMOUS_QA_FABRIC.md` | Update the §2.1 table: change "Vision perception" scale-up target from "add VLM provider" to "add VLM provider + Pilot agent + mobile source adapter" with the now-built real modules referenced. |
| `docs/vision/02_ROADMAP.md` | Add E14 (Mobile Conformance) to the Gantt at the end, gated on Wave 5. |
| `AGENTS.md` | Add a one-line reference to `docs/skills/mobile.md` in the autonomous-fabric section. |
| `pyproject.toml` | Add optional mobile-extras: `appium-python-client>=3.0`, `pure-python-adb>=0.3`, `Pillow>=10.0`. All gated behind `pip install cherenkov-qa[mobile]`. The default install does **not** require mobile. |
| `cherenkov-policy.json` | Add the `mobile_*` tool entries to the **blocked** default list, with a comment instructing operators to enable them deliberately. |
| `Makefile` | Add `make mobile-smoke` target that runs `tests/smoke/smoke_test_mobile.py` against a local Android emulator (skipped automatically if `adb devices` is empty). |
| `.dockerignore` | No change. |
| `docs/HANDOVER.md` (cross-ref) | Add a one-paragraph "Mobile capability" section at the bottom of §3, with a pointer to this plan. |

### Files NOT touched (explicit non-changes)

- `cherenkov/core/contracts.py` enums (`Status`, `Verdict`, `TriageCategory`).
- `cherenkov/healing/diagnose.py` `FailureClass` enum (only extended via
  subclassing in `MobileFailureClassifier`).
- `cherenkov/core/orchestrator.py` Track A path (`run_pipeline`).
- `cherenkov/stages/generate.py` and `cherenkov/stages/review.py`
  (the API-conformance generators are untouched — mobile is a sibling,
  not a fork).
- `cherenkov/stages/ui_generate.py` and `cherenkov/stages/ui_plan.py`
  (the *web* UI generators are kept; the *mobile* generators are new
  files with different names to avoid the "two systems for the same
  thing" failure mode).

### Configuration / metadata

- `cherenkov.toml.example` — add a `[mobile]` section with `platform`,
  `target_package`, `eject_format` (maestro|appium|both), and a
  `vlm_tier` selector (`small_vlm` is the default for laptop profile).
- `cherenkov-policy.mobile.example.json` — see Files table.

---

## [Functions]

### New functions (with exact signature, file path, purpose)

```python
# cherenkov/sources/adapter.py
def register_adapter(adapter: SourceAdapter) -> None: ...
def get_adapter_for(path: str) -> SourceAdapter | None: ...

# cherenkov/sources/mobile/adapter.py
class MobileSourceAdapter:
    def name(self) -> str: ...                       # "mobile"
    def can_ingest(self, path: str) -> bool: ...     # *.apk | *.ipa | *.maestro/ | *.har
    def ingest(self, path: str, run_id: str) -> IngestOutput: ...

# cherenkov/sources/mobile/android_dump.py
def parse_uiautomator_dump(xml_path: str, screenshot_path: str) -> MobileScreenState: ...
def stream_uiautomator_dump_via_adb(device_id: str, dest_dir: str) -> Iterator[MobileScreenState]: ...

# cherenkov/sources/mobile/ios_dump.py
def parse_xcuitest_dump(json_path: str, screenshot_path: str) -> MobileScreenState: ...
def stream_via_simctl(device_id: str, dest_dir: str) -> Iterator[MobileScreenState]: ...

# cherenkov/sources/mobile/har_to_traffic.py
def har_to_mobile_traffic(har_path: str, app_id: str | None = None) -> list[MobileTrafficEntry]: ...

# cherenkov/substrate/vlm_provider.py
class VLMProvider(ABC):
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def complete(self, req: VLMRequest) -> VLMResult: ...

class OllamaVLMProvider(VLMProvider):
    def __init__(self, model: str = "qwen2.5-vl:7b", base_url: str | None = None): ...
    def complete(self, req: VLMRequest) -> VLMResult: ...

class OpenAIVLMProvider(VLMProvider):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None): ...
    def complete(self, req: VLMRequest) -> VLMResult: ...

# cherenkov/substrate/vlm_router.py
def route_vlm(req: VLMRequest, policy: dict | None = None) -> VLMProvider: ...
def get_vlm_for_tier(tier: VLMTier) -> VLMProvider: ...

# cherenkov/agents/pilot.py
class Pilot:
    def __init__(self, runner: MaestroRunner | AppiumRunner, vlm: VLMProvider, rag: MobileAppRAGIndex): ...
    def run(self, intent: str, target_package: str, run_id: str) -> PilotTrace: ...
    def _observe(self) -> MobileScreenState: ...
    def _reason(self, state: MobileScreenState, intent: str) -> PilotAction: ...
    def _act(self, action: PilotAction) -> MobileScreenState: ...
    def _assert(self, expected: str, state: MobileScreenState) -> bool: ...
    def _should_stop(self, intent: str, history: list[PilotObservation]) -> PilotAction: ...
    def _recover(self, error: str, state: MobileScreenState) -> PilotAction: ...   # anti-reward-hack: explicit recovery, no silent replan

# cherenkov/agents/explorer_mobile.py
class MobileExplorer:
    def __init__(self, runner: MaestroRunner | AppiumRunner, vlm: VLMProvider): ...
    def crawl(self, target_package: str, run_id: str, max_screens: int = 30) -> list[ExplorerFinding]: ...
    def to_hypotheses(self, findings: list[ExplorerFinding]) -> list[DivergenceHypothesis]: ...

# cherenkov/stages/mobile_plan.py
class MobilePlanStage:
    def __init__(self, run_id: str | None = None): ...
    def run(self, slices: list[MobileSlice]) -> PlanOutput: ...   # DETERMINISTIC — no LLM

# cherenkov/stages/mobile_generate.py
class MobileGenerateStage:
    def __init__(self, run_id: str | None = None, eject_format: str = "maestro"): ...
    def run(self, scenario: MobileScenario) -> GenerateOutput: ...   # emits YAML or Appium TS
    def _render_maestro(self, scenario: MobileScenario) -> str: ... # anti-lock-in: pure YAML, no CHERENKOV refs

# cherenkov/stages/mobile_review.py
class MobileReviewStage:
    def __init__(self, run_id: str | None = None, sandbox: str = "maestro_cli"): ...
    def run(self, scenario: MobileScenario, code: str) -> ReviewOutput: ...   # reuses Verdict

# cherenkov/oracle/visual_oracle_vlm.py
class SemanticVisualOracle:
    def __init__(self, vlm: VLMProvider, base_oracle: VisualOracle): ...
    def evaluate(self, baseline: str, actual: str, question: str) -> SemanticVisualVerdict: ...

# cherenkov/execution/maestro_runner.py
class MaestroRunner:
    def __init__(self, binary_path: str = "maestro", workspace: str | None = None): ...
    def install_app(self, apk_path: str, device_id: str) -> None: ...
    def launch(self, package: str, device_id: str) -> MobileScreenState: ...
    def execute(self, flow_path: str, device_id: str) -> dict: ...   # returns {"passed": bool, "trace": ...}
    def capture_screen(self, device_id: str, dest_dir: str) -> MobileScreenState: ...

# cherenkov/execution/appium_runner.py
class AppiumRunner:
    def __init__(self, server_url: str = "http://127.0.0.1:4723", capabilities: dict | None = None): ...
    def install_app(self, apk_path: str) -> None: ...
    def launch(self, package: str) -> MobileScreenState: ...
    def execute(self, scenario: MobileScenario) -> PilotTrace: ...
    def capture_screen(self, dest_dir: str) -> MobileScreenState: ...

# cherenkov/reflector/mobile_extensions.py
class MobileFailureClassifier:
    def __init__(self, base: FailureClassifier): ...   # wraps healing/diagnose.py
    def classify(self, error: str, state: MobileScreenState) -> FailureClass: ...
    def is_modal_overlay(self, state: MobileScreenState) -> bool: ...
    def is_app_backgrounded(self, state: MobileScreenState) -> bool: ...

# cherenkov/rag/mobile_index.py
class MobileAppRAGIndex:
    def __init__(self, app_id: str, cache_dir: str = ".cherenkov/mobile_rag_cache"): ...
    def add_release_notes(self, text: str, version: str) -> None: ...
    def add_screen_map(self, screens: list[MobileScreenState]) -> None: ...
    def add_prior_trace(self, trace: PilotTrace) -> None: ...
    def retrieve(self, query: str, top_k: int = 5) -> list[Chunk]: ...
    def clear(self) -> None: ...

# cherenkov/web/mobile_routes.py
async def list_sessions() -> list[dict]: ...            # GET /api/v1/mobile/sessions
async def run_mobile(payload: dict) -> dict: ...        # POST /api/v1/mobile/run
async def get_trace(trace_id: str) -> dict: ...          # GET /api/v1/mobile/trace/{id}
async def approve_trace(payload: dict) -> dict: ...     # POST /api/v1/mobile/trace/{id}/approve
```

### Modified functions (existing; exact name, path, required changes)

| Function (signature) | Path | Required change |
|---|---|---|
| `OrchestrationEngine.run_pipeline(spec_path)` | `cherenkov/core/orchestrator.py` | **No change.** New `run_mobile_stage` is a sibling method; Track A path is untouched. |
| `OrchestrationEngine.run_visual_stage(slices)` | `cherenkov/core/orchestrator.py` | Add a `run_mobile_stage(slices, run_id)` sibling (200 LOC). No changes to `run_visual_stage` or `run_perf_stage`. |
| `IngestStage.run(spec_path)` | `cherenkov/stages/ingest.py` | Add one `if` branch: if `spec_path.endswith((".apk", ".ipa", ".maestro", ".har"))`, delegate to `MobileSourceAdapter.ingest()`; otherwise the existing JSON/YAML path is preserved. 5 LOC change. |
| `SubstrateRouter.route(req)` | `cherenkov/substrate/router.py` | Extend the `Provider` registry with `VLMProvider`. No changes for non-VLM callers. |
| `Skeptic.hypothesize(claims)` | `cherenkov/divergence/skeptic.py` | Add an optional `mobile_hypothesizer` strategy; the existing API-only path is unchanged. |
| `Witness.reproduce(hypothesis)` | `cherenkov/divergence/witness.py` | Add a `pilot_reproduce` method that uses `Pilot` for mobile hypotheses; existing HTTP-replay path is unchanged. |
| `AdversarialSelfPlay.run(test, oracle)` | `cherenkov/divergence/self_play.py` | Extend to also run the ejected mobile flow against a correct + a deliberately broken screen. |
| `HealingDiagnose.classify(error)` | `cherenkov/healing/diagnose.py` | Wrap, don't modify — `MobileFailureClassifier` adds new classes; existing `FailureClass` is unchanged. |
| `HitlQueue.classify(item_id, classification)` | `cherenkov/hitl/store.py` | Extend the `classification` field allowed values with `mobile_bug | mobile_flaky | mobile_env` (additive). |
| `cherenkov.mcp.handlers.handle_tool_call` | `cherenkov/mcp/handlers.py` | Add 4 new tool cases. The existing trust model ("MCP peers are untrusted") and `PolicyEngine.is_tool_allowed` gate are **not** relaxed. |
| `EjectorEngine.eject_suite(output_path)` | `cherenkov/execution/eject.py` | Detect `mobile/` subdirs in the source tests; emit a separate `mobile_eject_format` flag in the output; the **zero `cherenkov` imports** invariant becomes "the mobile eject dir has zero `cherenkov` imports, period" — verified by the existing grep step. |
| `cherenkov.py` (top-level CLI) | `cherenkov.py` | Add `mobile` subcommand (init, run, eject, trace-list). No changes to any existing subcommand. |
| `get_parser()` | `cherenkov.py` | Add the mobile subparsers. |
| `RAGIndex.add_incident(...)` | `cherenkov/ai/rag_index.py` | **No change.** Add a sibling `mobile_add_trace(trace)` that calls the existing `add_incident` per failure observation. |
| `Reflector.record(verdict)` | `cherenkov/reflector/reflector.py` | Add a `mobile_outcome` field to the verdict's `detail` string. No schema change. |
| `cherenkov.stages.doctor_cmd.check_*` | `cherenkov/stages/doctor_cmd.py` | Add 2 new checks: `check_adb`, `check_xcrun_simctl`. Fail-soft. |

### Removed functions

None. The plan is purely additive; no existing function is deleted, renamed, or has its signature changed in a breaking way. The only signature-adjacent change is `IngestStage.run` gaining an `if` branch (the input type is the same `str`; the return type is the same `IngestOutput`).

---

## [Classes]

### New classes

| Class | File | Key methods | Inheritance / collaborators |
|---|---|---|---|
| `SourceAdapter` (ABC) | `cherenkov/sources/adapter.py` | `name()`, `can_ingest(path)`, `ingest(path, run_id) -> IngestOutput` | Collaborates with `truth/index.py` to write claims |
| `MobileSourceAdapter` | `cherenkov/sources/mobile/adapter.py` | `name()` → "mobile", `can_ingest(path)`, `ingest(path, run_id)` | Inherits `SourceAdapter`. Uses `parse_uiautomator_dump`, `parse_xcuitest_dump`, `har_to_mobile_traffic` |
| `VLMProvider` (ABC) | `cherenkov/substrate/vlm_provider.py` | `name()`, `complete(req) -> VLMResult` | Honors `egress` dial via `Config.EGRESS` |
| `OllamaVLMProvider` | `cherenkov/substrate/vlm_provider.py` | `complete(req)` | Inherits `VLMProvider`. Calls Ollama `/api/chat` with image input |
| `OpenAIVLMProvider` | `cherenkov/substrate/vlm_provider.py` | `complete(req)` | Inherits `VLMProvider`. Calls `chat.completions.create` with image_url |
| `Pilot` | `cherenkov/agents/pilot.py` | `run`, `_observe`, `_reason`, `_act`, `_assert`, `_recover` | Inherits nothing. Collaborates with `MaestroRunner`/`AppiumRunner`, `VLMProvider`, `MobileAppRAGIndex`, `HitlQueue` |
| `MobileExplorer` | `cherenkov/agents/explorer_mobile.py` | `crawl`, `to_hypotheses` | Wraps `divergence/explorer.py` patterns |
| `MobilePlanStage` | `cherenkov/stages/mobile_plan.py` | `run(slices) -> PlanOutput` | Mirrors `stages/plan.py` — DETERMINISTIC, no LLM |
| `MobileGenerateStage` | `cherenkov/stages/mobile_generate.py` | `run(scenario) -> GenerateOutput`, `_render_maestro(scenario)` | Mirrors `stages/generate.py` |
| `MobileReviewStage` | `cherenkov/stages/mobile_review.py` | `run(scenario, code) -> ReviewOutput` | Mirrors `stages/review.py` |
| `SemanticVisualOracle` | `cherenkov/oracle/visual_oracle_vlm.py` | `evaluate(baseline, actual, question)` | Composes `VLMProvider` + existing `VisualOracle` |
| `MaestroRunner` | `cherenkov/execution/maestro_runner.py` | `install_app`, `launch`, `execute`, `capture_screen` | Wraps the `maestro` CLI; alternatively talks to a Maestro MCP server |
| `AppiumRunner` | `cherenkov/execution/appium_runner.py` | `install_app`, `launch`, `execute`, `capture_screen` | WebDriver protocol; fallback for locked-down flows |
| `MobileFailureClassifier` | `cherenkov/reflector/mobile_extensions.py` | `classify(error, state)`, `is_modal_overlay`, `is_app_backgrounded` | Wraps `healing/diagnose.py` |
| `MobileAppRAGIndex` | `cherenkov/rag/mobile_index.py` | `add_release_notes`, `add_screen_map`, `add_prior_trace`, `retrieve` | Mirrors `rag/schema_index.py` |
| `MobileSession` (UI state) | `cherenkov/web/ui/src/screens/Mobile/types.ts` | (TypeScript interface only) | Used by `MobileView.tsx` |
| `MobileTrace` (UI state) | `cherenkov/web/ui/src/components/MobileScreenViewer/types.ts` | (TypeScript interface only) | Used by `MobileScreenViewer.tsx` |

### Modified classes (existing)

| Class | Path | Specific modification |
|---|---|---|
| `OrchestrationEngine` | `cherenkov/core/orchestrator.py` | Add `run_mobile_stage(slices, run_id)`, `run_pilot(intent, package, run_id)`, `run_mobile_review(scenario, code)`. The `run_pipeline` Track A method is **unchanged**. |
| `IngestStage` | `cherenkov/stages/ingest.py` | Add `if is_mobile_spec(path): return self._mobile_dispatch(path, run_id)` branch at the top of `run()`. |
| `SubstrateRouter` | `cherenkov/substrate/router.py` | Add `vlm` to the provider registry; extend the tier→provider table with `VLM` rows. |
| `Skeptic` | `cherenkov/divergence/skeptic.py` | Add `mobile_hypothesizer` strategy; the existing `hypothesize(claims)` is unchanged. |
| `Witness` | `cherenkov/divergence/witness.py` | Add `pilot_reproduce(hypothesis) -> ReproductionResult`; the existing `reproduce` is unchanged. |
| `AdversarialSelfPlay` | `cherenkov/divergence/self_play.py` | Add an `assertion_gate` overload that takes a `PilotTrace` and a `MobileScenario`; existing `assertion_gate(test, oracle)` is unchanged. |
| `HealingDiagnose` | `cherenkov/healing/diagnose.py` | **No schema change.** `MobileFailureClassifier` extends by composition (not inheritance). |
| `HitlQueue` | `cherenkov/hitl/store.py` | Add 3 new `classification` enum values (`mobile_bug`, `mobile_flaky`, `mobile_env`); existing values unchanged. |
| `EjectorEngine` | `cherenkov/execution/eject.py` | Detect mobile tests via the new `cherenkov/stages/mobile_*` markers; emit a separate `mobile/` subdir; enforce the **zero `cherenkov` imports** rule. |
| `MobileView` (new) | `cherenkov/web/ui/src/screens/Mobile/MobileView.tsx` | New component; registered in `App.tsx`. |
| `App` (React) | `cherenkov/web/ui/src/App.tsx` | Register `/mobile` route; add sidebar item. |
| `RAGIndex` | `cherenkov/ai/rag_index.py` | Add `mobile_add_trace(trace)`; no schema change. |
| `Reflector` | `cherenkov/reflector/reflector.py` | Add `mobile_outcome` to the verdict `detail` field; no schema change. |
| `PolicyEngine` | `cherenkov/mcp/policy.py` | Add `mobile_*` tool entries; example provided. |
| `Config` | `cherenkov/core/config.py` | Add `MOBILE_EJECT_FORMAT` (default "maestro") and `VLM_TIER` (default "small_vlm"). |

### Removed classes

None. The plan is purely additive.

---

## [Dependencies]

All new dependencies are **optional** — installed only when the user opts in
via `pip install cherenkov-qa[mobile]`. The default `pip install cherenkov-qa`
does not require them, and the default `cherenkov` CLI commands work without
them. This honours the project's anti-lock-in principle: you don't have to
adopt mobile to use CHERENKOV.

### New Python packages (`pyproject.toml` → `[project.optional-dependencies]`)

| Package | Version | Purpose | Notes |
|---|---|---|---|
| `appium-python-client` | `>=3.0` | WebDriver-protocol client to Appium server (iOS + Android) | Optional; only loaded if `AppiumRunner` is constructed |
| `pure-python-adb` | `>=0.3` | ADB interaction without the `adb` binary (used when `adb` is not on PATH) | Optional |
| `Pillow` | `>=10.0` | Screenshot diff + crop helpers for the semantic oracle | Already implicitly required by some tests |
| `pydantic` | `>=2.5` | (no change) | Already a hard dep |

### New system / CLI tools (NOT pip packages — must be present on the host)

| Tool | Version | Purpose | Optional? | When required |
|---|---|---|---|---|
| `maestro` CLI | `>=1.30` | Ejectable mobile flow runtime; 2MB binary footprint, MCP-native | No | Required for `cherenkov mobile eject` and Pilot's execution path on Android |
| `adb` (Android Debug Bridge) | `>=34.0` | Android device control; used by `MaestroRunner` for install/launch/capture | No | Required only when running mobile on Android |
| `xcrun simctl` (macOS only) | bundled with Xcode | iOS simulator control | No | Required only when running mobile on iOS |
| `aapt` (Android Asset Packaging Tool) | bundled with `adb` | Extract app package + version from APK | No | Required only when ingesting `.apk` specs |
| A vision-language model in Ollama | `qwen2.5-vl:7b` (default), `minicpm-v:8b`, `llava:13b` | `OllamaVLMProvider` — primary substrate for mobile | No | Required for any mobile session; pulled via `ollama pull qwen2.5-vl:7b` |
| (Optional) frontier VLM API key | n/a | `OpenAIVLMProvider` for `frontier_vlm` tier | Yes | Only if `egress: any` and `vlm_tier: frontier_vlm` |

### Python version

- **Minimum Python:** `>=3.10` (no change from current CHERENKOV requirement;
  the `tuple[int, int, int, int]` type in `MobileUIElement.bounds` requires
  the new generic syntax from 3.9+, satisfied by 3.10).
- **Tested on:** Python 3.12.3 (WSL Ubuntu, matches existing `docs/PLAYBOOK.md`).

### No changes to existing dependencies

This plan adds **zero** new hard dependencies. The default `pip install
cherenkov-qa` continues to install only what it installs today. Mobile
extras live behind a feature flag, so CI does not break for users who do
not adopt mobile.

### Configuration knobs (no new tool)

Two new `Config` entries, both with safe defaults:

```python
# cherenkov/core/config.py — append, do not edit existing entries
MOBILE_EJECT_FORMAT: str = "maestro"   # "maestro" | "appium" | "both"
VLM_TIER: str = "small_vlm"            # "small_vlm" | "mid_vlm" | "frontier_vlm"
```

### NPM / JS dependencies (frontend)

None new. The new `MobileView.tsx` and `MobileScreenViewer.tsx` use the
same `react-query`, `tailwindcss`, and `lucide-react` already in
`cherenkov/web/ui/package.json`.

---

## [Testing]

The plan is a **plan**, so this section specifies the testing strategy and
the evidence the implementation must produce — not the test code itself.
Per `HANDOVER §2`, **every implementation step exits on raw evidence**;
this section is the contract for what that evidence looks like.

### Unit tests (pytest, must pass before any merge)

| Test file | What it covers | Required evidence |
|---|---|---|
| `tests/unit/test_mobile_source_adapter.py` | Android/iOS dump parsers; HAR → `MobileTrafficEntry`; `can_ingest` dispatch | `pytest -q tests/unit/test_mobile_source_adapter.py` → all green; a sample `uiautomator dump.xml` and a sample HAR in `tests/fixtures/mobile/` |
| `tests/unit/test_vlm_provider.py` | `VLMProvider` contract; `OllamaVLMProvider` round-trips a stubbed Ollama; `OpenAIVLMProvider` honours the `egress` dial; mock images are tiny PNGs to keep CI fast | `pytest -q tests/unit/test_vlm_provider.py`; screenshot of `egress=none` rejecting an OpenAI call |
| `tests/unit/test_pilot_agent.py` | Pilot loop with a stubbed `MaestroRunner`; cycle count capped; `_recover` is invoked (not silent replan); terminal `DONE`; `PilotTrace` JSON serialisable | `pytest -q tests/unit/test_pilot_agent.py`; the trace JSON for a 3-step intent |
| `tests/unit/test_mobile_rag_index.py` | `MobileAppRAGIndex` round-trip; cache invalidation on app version bump; mock embedding model (no Ollama) | `pytest -q tests/unit/test_mobile_rag_index.py` |
| `tests/unit/test_semantic_visual_oracle.py` | **Anti-reward-hacking:** the `SemanticVisualOracle` + the existing `AdversarialSelfPlay` pass a correct mock, fail a deliberately broken screen. **This is the kill-criteria test for E9-mobile** | `pytest -q tests/unit/test_semantic_visual_oracle.py` |
| `tests/unit/test_ejector_mobile.py` | `EjectorEngine` strips every `cherenkov` import from the ejected `mobile/` dir; `maestro test ejected.yaml` runs in a clean temp dir without CHERENKOV installed | `pytest -q tests/unit/test_ejector_mobile.py`; the ejected YAML + the grep result `0` |
| `tests/unit/test_mobile_failure_classifier.py` | `MobileFailureClassifier` produces `MOBILE_OS_MODAL`, `MOBILE_NETWORK_BLIP`, `MOBILE_APP_BACKGROUNDED` etc. for known screenshots | `pytest -q tests/unit/test_mobile_failure_classifier.py` |
| `tests/unit/test_mcp_mobile_tools.py` | The 4 new MCP tools (`mobile_list_sessions`, `mobile_run`, `mobile_capture_view`, `mobile_approve_trace`) are **blocked by default**; `policy_reload` after editing `cherenkov-policy.json` allows them; untrusted peer cannot bypass the policy | `pytest -q tests/unit/test_mcp_mobile_tools.py`; the `policy_list` output showing blocked and allowed states |

### Smoke test (E2E, must pass on a host with `adb` + an Android emulator)

`tests/smoke/smoke_test_mobile.py` (~280 LOC) is the **end-to-end proof**
that all the kill-criteria are reachable. It must, in order:

1. Ingest a bundled `.apk` (`stub/sample_apps/petstore.apk` — added by this
   plan, ~50 KB) and a `.har` capture of a real device session.
2. Run the `MobilePlanStage` and `MobileGenerateStage` to produce a
   `MaestroScenario`.
3. Use `MaestroRunner` to install the APK, launch it, and execute the
   generated YAML in a fresh Android emulator.
4. Capture the resulting `PilotTrace`.
5. **Run the ejected Maestro YAML in a clean tempdir with `maestro` on the
   PATH but CHERENKOV not installed** — proves the anti-lock-in invariant.
6. Save the screenshots, the trace JSON, and the verdict record to
   `.cherenkov/evidence/2026-06-XX-mobile-smoke/`.
7. Exit non-zero if any of the above fails.

Required evidence (raw): the captured screenshots, the trace JSON, the
`maestro test --debug` log, and the `git status` showing the new files
created. The smoke is auto-skipped if `adb devices` returns empty (no
emulator), exactly like the existing `make` pattern for GPU-dependent
smokes.

### E2E dashboard test (Playwright, must pass before any frontend merge)

`cherenkov/web/ui/tests/mobile_e2e.spec.ts` (~120 LOC):

1. Boot the dashboard, navigate to `/mobile`.
2. Confirm the seeded `PilotTrace` shows up.
3. Open the `MobileScreenViewer`; confirm screenshot + UI dump render.
4. Click "Classify as mobile_bug" → confirm the HITL queue reflects it.

### Mutation test (anti-reward-hacking gate)

`tests/unit/test_self_play_mobile.py` (~100 LOC) — the same shape as
the existing `test_self_play.py`:

- Take a correct mock app screen.
- Inject a Pilot trace that "passes" by asserting nothing.
- Confirm the `AdversarialSelfPlay` rejects it (failed the broken impl).

### Performance / load test (optional, only if k6-mobile is integrated)

Not in scope. If a k6-mobile executor is later added, it will live behind
the same `stages/perf/` family.

### Honest no-go zone (what we will NOT test in this plan)

- Physical real-device testing (Mobot class) — out of scope.
- A "compete-with-Kobiton" device-farm scenario — out of scope.
- Auto-PR of mobile findings — out of scope (D7 says no auto-edit anyway).

### Evidence ledger

`docs/plans/2026-06-08-mobile-evidence.md` will record (per the
`docs/process/VALIDATION_EVIDENCE_LEDGER.md` pattern):

- A run log for each Pilot session (intent, screenshots, trace, verdict).
- A row per smoke-test execution (date, pass/fail, evidence path).
- The first 3 mobile divergences reproduced against a real app.

This file is the **raw evidence** the Wave-5 5-QA panel will be asked to
verify; it MUST exist before the validation gate can be passed for the
mobile capability.

---

## [Implementation Order]

Numbered steps for the lowest-risk, highest-evidence path. Each step has
a **kill-criterion** — the raw evidence that proves the step works —
matching the `06_AUTONOMOUS_QA_FABRIC.md §5` discipline.

> **Prerequisite:** the Wave 2 honesty-debt tickets (#222, #223, #224,
> #239) MUST land first. No new seam widens until the existing dashboard
> tells the truth. This is non-negotiable.

### Step 1 — Land the Source Adapter SPI and the mobile parsers (no LLM)

**Why first:** zero new intelligence, just data plumbing. Proves the
ingest path without any flakiness from the VLM or the Pilot.

- Create `cherenkov/sources/adapter.py` (SPI) and
  `cherenkov/sources/mobile/{contracts,android_dump,ios_dump,har_to_traffic,adapter}.py`.
- Add the `if is_mobile_spec(path): ...` branch in `cherenkov/stages/ingest.py`.
- Bundle `stub/sample_apps/petstore.apk` and `stub/sample_apps/petstore.har`
  (~100 KB total).
- **Kill-criterion:** `pytest tests/unit/test_mobile_source_adapter.py` green;
  `python3 cherenkov.py ingest --file stub/sample_apps/petstore.apk` prints
  ≥1 mobile endpoint and ≥1 traffic entry; `git status` shows the new files
  and no modifications to `cherenkov/stages/ingest.py` other than the new
  branch.

### Step 2 — Add the VLM provider to the Substrate

**Why second:** the Pilot depends on it; nothing else does. Lets us
calibrate VLM cost/latency in isolation.

- Create `cherenkov/substrate/vlm_provider.py` (ABC + Ollama + OpenAI).
- Add `vlm` to the provider registry in `cherenkov/substrate/provider.py`.
- Add `VLM_TIER` and `MOBILE_EJECT_FORMAT` to `cherenkov/core/config.py`.
- Add a CLI subcommand `cherenkov doctor --vlm` (fail-soft).
- **Kill-criterion:** `pytest tests/unit/test_vlm_provider.py` green; on a
  host with Ollama + `qwen2.5-vl:7b`, a sample `VLMRequest` returns a
  structured `VLMResult` in <10s on a 1280×720 PNG; with `EGRESS=none` the
  OpenAI provider raises `PermissionError` and the Ollama provider still
  works (raw stderr captured).

### Step 3 — Build the Pilot loop (with a stubbed device transport)

**Why third:** now we can reason about actions on a screen without owning
a real device. The stubbed transport is the `InMemoryRunner` test double
that returns canned `MobileScreenState` per action.

- Create `cherenkov/agents/pilot.py`.
- Create `cherenkov/execution/maestro_runner.py` (just the interface + the
  `InMemoryRunner` test double; the real `MaestroRunner` lands in Step 5).
- **Kill-criterion:** `pytest tests/unit/test_pilot_agent.py` green; a
  3-step intent on the stubbed transport produces a `PilotTrace` whose
  observations match the canned states, with a terminal `DONE`; a recovery
  scenario exercises `_recover` and not a silent replan.

### Step 4 — Land the mobile RAG index

**Why fourth:** the Pilot reads it; better to land it before the Pilot
goes near a real device.

- Create `cherenkov/rag/mobile_index.py` (mirrors `rag/schema_index.py`).
- Add `mobile_add_trace(trace)` to `cherenkov/ai/rag_index.py` (calls
  `add_incident` per failure observation).
- **Kill-criterion:** `pytest tests/unit/test_mobile_rag_index.py` green;
  a 1 KB release-notes blob + a 3-screen `MobileScreenState` list are
  ingested, retrieved, and the cache is invalidated on app version bump.

### Step 5 — Land the Maestro / Appium runners and the e2e smoke

**Why fifth:** this is the first time we touch a real device. Everything
up to here is local-Python-only.

- Add the real `MaestroRunner` implementation (replace the stub from Step 3).
- Add the `AppiumRunner` as the fallback.
- Create `cherenkov/stages/mobile_{plan,generate,review,cmd}.py`.
- Create `cherenkov/execution/eject.py` mobile branch.
- **Kill-criterion:** `make mobile-smoke` exits 0 on a host with `adb`
  and an Android emulator; the ejected `maestro_guest_checkout.yaml`
  runs green in a clean tempdir (`maestro test ...`); the smoke writes
  screenshots, trace JSON, and `git status` to
  `.cherenkov/evidence/2026-06-XX-mobile-smoke/`.

### Step 6 — Land the semantic visual oracle (with the anti-reward-hacking gate)

**Why sixth:** now that we can produce traces, we can judge them. The
semantic oracle is the most failure-prone of the new pieces, so it lands
last among the *core* work.

- Create `cherenkov/oracle/visual_oracle_vlm.py` (`SemanticVisualOracle`).
- Extend `cherenkov/divergence/self_play.py` to add the mobile gate.
- Add `VisualOracleKind` to `cherenkov/oracle/visual_oracle.py`.
- **Kill-criterion:** `pytest tests/unit/test_semantic_visual_oracle.py`
  green; the oracle passes the correct mock and fails the deliberately
  broken screen (the E3-style "no `true==true`" discipline); a
  VLM-judged pass is rejected when the pixel diff says fail (consistency
  check).

### Step 7 — Wire MCP (server + client)

**Why seventh:** the rest of the capability is local; MCP makes it
remote-controllable. CHERENKOV becomes an MCP server that exposes mobile
tools to any agent (Claude, Copilot) and an MCP client that drives the
Maestro MCP server.

- Add the 4 tools to `cherenkov/mcp/handlers.py`.
- Add `mobile_*` entries to `cherenkov/mcp/policy.py` and
  `cherenkov-policy.json` (default **blocked**).
- Add a `cherenkov mcp connect maestro` client (talks to a Maestro MCP
  server if one is reachable).
- **Kill-criterion:** `pytest tests/unit/test_mcp_mobile_tools.py` green;
  with default policy, `mobile_run` returns
  `Tool 'mobile_run' blocked by policy for server 'cherenkov' in profile 'full-dev'.`;
  after enabling, the same call returns a `PilotTrace` id.

### Step 8 — Land the dashboard UI

**Why last:** the dashboard is the validation vehicle (per
`ROADMAP_NEXT.md §1`); it must reflect the truth the previous steps
have produced, not lie about it (the Wave 2 lesson).

- Add `cherenkov/web/mobile_routes.py` and mount in `cherenkov/web/api.py`.
- Add `MobileView.tsx`, `MobileScreenViewer.tsx`, `useMobileSession.ts`.
- Register the route in `App.tsx` and the sidebar.
- **Kill-criterion:** `npx playwright test tests/mobile_e2e.spec.ts` green;
  the dashboard's `/mobile` screen lists traces, supports classification,
  and shows screenshots side-by-side with the UI dump; a real QA
  reviewer can hit it on a phone and classify a finding without a
  terminal.

### Step 9 — Update the docs (HANDOVER, SCOPE_LEDGER, ROADMAP_NEXT, vision)

**Why last:** the docs are the SSOT. They MUST reflect the new state
truthfully, including any honest gaps (no "100% complete" claims — see
the §1 anti-drift reminder).

- Update `docs/HANDOVER.md` §3 (one bullet on the mobile capability) and
  SCOPE_LEDGER §B.
- Update `docs/ROADMAP_NEXT.md` Wave 6 with the new tickets.
- Update `docs/vision/06_AUTONOMOUS_QA_FABRIC.md` §2.1 with the
  now-built real modules.
- Add E14 (Mobile Conformance) to `docs/vision/02_ROADMAP.md`.
- **Kill-criterion:** `git diff --stat` on the docs files shows only
  additive edits; `make docs-check` (existing CI step) still passes;
  the new mobile evidence ledger is linked from
  `docs/process/VALIDATION_EVIDENCE_LEDGER.md`.

### Step 10 — Gate the work behind the 5-QA validation gate

**Why last:** per `HANDOVER §5` and `ROADMAP_NEXT.md` Wave 5, the
validation gate is the milestone that turns "built" into "shipped." No
mobile work counts as "shipped" until ≥1 of the 5 QA reviewers runs the
mobile golden path on a phone and gives attributable "yes" evidence
in the validation evidence ledger.

- Add the mobile golden path to `docs/QA_DEMO_KIT.md` and the
  `cherenkov review --demo` flow.
- Recruit at least 1 reviewer from the QA outreach list who owns a
  phone and is willing to run the Pilot live.
- **Kill-criterion:** the evidence ledger row for the mobile reviewer
  has a name, a date, a run id, and a `yes|maybe|no` verdict.

---

## Cross-cutting risks & guardrails

These are **predicated on** `06_AUTONOMOUS_QA_FABRIC.md §6` "Premortem"
failure modes. The plan mitigates each, and the implementation must
not erode any of them.

| Failure mode | Plan-level mitigation |
|---|---|
| **Scope sprawl drowns the core** | The mobile work is gated by the 5-QA gate (Step 10). Each step has a kill-criterion that exits on raw evidence; if a step can't hit its criterion, it is **cut, not extended**. |
| **Reflector becomes a data swamp** | Step 4 + Step 6 add per-app RAG *and* feed the existing `Reflector` with `PilotTrace` outcomes; the kill-criterion is the *behavioral* one (rejected finding stops re-surfacing), not "memory exists." |
| **VLM costs break local-first** | Default tier is `small_vlm` (Qwen2.5-VL-7B on Ollama); `frontier_vlm` is opt-in; `EGRESS` dial blocks it by default; cost & latency are reported via the existing `ai/accounting.py` ledger. |
| **Reward-hacking built anyway** | The semantic oracle is **never** the sole oracle; it pairs with the existing `AdversarialSelfPlay` (E3-3). The mutation test in `tests/unit/test_self_play_mobile.py` is the gate. |
| **Manual-QA pillar stays a slogan** | Step 8 ships the dashboard UI; the kill-criterion is "a real QA reviewer can hit `/mobile` on a phone and classify a finding without a terminal." |
| **MCP connectors become a maintenance tax** | The 4 new MCP tools are **blocked by default**; the operator must explicitly enable them in `cherenkov-policy.json`. No external server is contacted unless policy allows. |
| **We compete head-on and lose** | The plan serves a divergence (D3 ui↔spec on mobile), not a standalone feature; mobile is *a* Truth Model source, not a competitor to Kobiton/Mabl. |
| **The model-agnostic substrate ages badly** | `VLMProvider` is a versioned Pydantic contract; the new `VisualOracleKind` is added to the existing model-certification gate in `cherenkov/substrate/certification.py`. |

---

## Plan summary (the one-paragraph version)

Add mobile to CHERENKOV by widening the four open seams (Sources,
Models, Artifacts, Oracles) so the existing Reality Engine can ingest
mobile UIs and traffic (a new `SourceAdapter` SPI with Android/iOS/HAR
parsers), reason about them via a new VLM provider in the Substrate
(Qwen2.5-VL by default, GPT-4o opt-in via `egress`), drive a real device
through a new Pilot agent (extends Witness with vision), emit standalone
Maestro YAML and Appium TS (ejectable, zero-CHERENKOV), and judge
results through a semantic visual oracle that never decides alone — it's
gated by the existing adversarial self-play. Everything is additive: the
Track A path is untouched, the four design invariants are preserved, and
all new dependencies are optional behind `pip install cherenkov-qa[mobile]`.
The plan lands in 10 evidence-gated steps, starting with no-LLM data
plumbing (the source adapter) and ending at the 5-QA validation gate.

---

## Open questions for the human reviewer

These are the points where the plan deliberately asks for human input
before coding begins. None blocks the plan's structure; each is a
calibration knob.

1. **Primary mobile platform first — Android emulator, iOS simulator,
   or real device via MCP?** The plan defaults to Android emulator
   (cheapest to land in CI) with iOS as Step-5b. If you'd rather start
   on real devices (Kobiton MCP), Step 5 changes shape but the rest
   is the same.

2. **Maestro-first or Appium-first as the ejectable format?** The plan
   defaults to Maestro (lighter, MCP-native, anti-lock-in friendly)
   with Appium as the fallback for third-party apps. The opposite is
   also defensible if your audience is already Appium-fluent.

3. **Should `cherenkov mobile eject` be a top-level subcommand, or
   nested under `cherenkov eject --format=maestro`?** The plan picks
   the top-level subcommand (clearer UX, more CLI surface). Nested is
   a one-line change if you prefer it.

4. **Is the `frontier_vlm` tier a real need for the 5-QA gate, or can
   we land mobile with `small_vlm` + a documented "use frontier only
   for hard cases" knob?** The plan defaults to the latter to keep
   local-first honest.

5. **Do you want a one-page "Mobile golden path" addendum to
   `docs/QA_DEMO_KIT.md` as part of Step 8, or as a separate doc?**
   The plan adds a one-page addendum inline.

---

*This plan is anchored to the SSOT. If anything here contradicts a doc
in `docs/`, the docs win, and this plan is updated. If anything here
fabricates a status, delete it. Raw evidence at every step; no claims
without a terminal log.*

---

**End of plan.**


