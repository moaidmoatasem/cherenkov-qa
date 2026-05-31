# CHERENKOV — Technical Development Plan
**Authority:** v3.1 + delta · **For:** AI coding agents + Moaid
**How to use:** each phase has TASKS (what to build) and DONE (acceptance criteria
an agent can verify). Do not advance a phase until every DONE box is checkable.

---

## Phase 0 — Week 0 Validation (GATE)

See `week0/WEEK0_PLAYBOOK.md`. Nothing in Phases 1+ may be built until the
Week 0 gate passes. This is The One Absolute Rule.

---

## Phase 1 — Week 1 — Generator Hardening

**TASKS**
- Take the Appendix A prompt (in handbook) and the 3 Week-0 specs.
- Iterate the prompt until output is reliably: pure `openapi-fetch` calls,
  specific-status assertions, body-shape assertions, no thrown errors (Delta D8).
- Record the failing patterns you fix (feeds the handbook's "prompt gotchas").

**DONE**
- [ ] On the 3 specs, ≥ 80% of generated tests compile first try.
- [ ] 0 tests use `fetch`/`axios`/raw `request` (Delta D1/D8 enforced).
- [ ] System prompt is a single static constant (prefix-cache safe, Delta).
- [ ] The tuned prompt is committed to `prompts/generator_system.txt`.

---

## Phase 2 — Weeks 2-3 — Core Infrastructure

**TASKS**
- `core/contracts.py`: versioned Pydantic models for every stage boundary
  (`IngestOutput`, `MutationMenu`, `PlanOutput`, `GenerateOutput`, `ReviewOutput`),
  each with `data / status / errors / metadata(schema_version)`.
- `core/logging.py`: structured logging (JSON lines), one logger per stage.
- `core/errors.py`: typed exceptions; never bare `except`.
- `ai/ollama_client.py`: wrapper with `format="json"`, **static** system prompt,
  idle-timeout keep-alive, `<think>` stripper.
- `ai/strip_think.py`: brutal regex `re.sub(r'<think\b[^>]*>.*?</think>','',t,flags=DOTALL)`;
  malformed → treat as hallucination, don't rescue.
- SQLite default; `--engine postgres` switch via `DATABASE_URL`.

**DONE**
- [ ] Every contract round-trips through `.model_validate_json()` in a unit test.
- [ ] `schema_version` bump detection has a test (old version → explicit error).
- [ ] Ollama client returns valid JSON or raises a typed error after the retry ladder.
- [ ] `<think>` stripper handles: clean close, no close, nested — all tested.
- [ ] SQLite DB created on first run with zero config.

---

## Phase 3 — Weeks 4-5 — Pipeline Skeleton

**TASKS**
- `core/orchestrator.py`: run INGEST→PLAN→GENERATE→REVIEW with **stub** stages
  (return canned contract objects) end-to-end.
- Enforce contracts at every boundary; on invalid JSON: `format=json` → validate →
  max 2 reprompts → fallback to happy-path-only plan + logged error (never halt).
- Dry-run→planner feedback channel (wire it now, even if REVIEW is stubbed).
- Circuit breaker (Delta D2): drop a `case_type` after 2 dry-run fails; max 3
  re-plans per endpoint total.
- `cli/progress.py`: live per-stage progress (spinner + elapsed + current item).

**DONE**
- [ ] `cherenkov generate api --spec petstore.yaml` runs the full stubbed DAG
      and prints a clean progress view, no crashes.
- [ ] Feeding a deliberately malformed stage output triggers the retry ladder,
      then the fallback, and logs it — pipeline still completes.
- [ ] Circuit breaker proven with a unit test (3rd re-plan is refused).

---

## Phase 4 — Weeks 6-7 — INGEST (real)

**TASKS**
- `stages/ingest.py`:
  - parse OpenAPI (JSON/YAML); resolve `$ref` with a **depth limit** (guard
    circular refs); emit a self-contained per-endpoint schema slice.
  - generate types via `openapi-typescript`; emit the 2-line `openapi-fetch`
    client setup (Delta D1) — no hand-rolled client class.
  - build the **deterministic mutation menu** (Delta D5 best-effort sample):
    omit one required field · violate one string-length · violate one number bound.
    Empty menu (GET/no constraints) → happy_path + auth only (Delta D4).
  - `json-schema-faker` for missing payloads (respects maxLength/enum/pattern).
  - 3-band richness: >0.7 full · 0.5-0.7 happy+defined-errors+faker · <0.5 warn/skip.

**DONE**
- [ ] Stripe/GitHub spec slices each fit the model context (proven on box).
- [ ] `openapi-typescript` survives the **messy** spec (Delta V2) or limitation documented.
- [ ] Mutation menu for `POST /users{email,password}` yields the expected sampled ids.
- [ ] A GET endpoint yields a non-error menu (happy_path/auth only).
- [ ] `json-schema-faker` output passes Prism validation on a `format:email` field.

---

## Phase 5 — Weeks 8-9 — PLAN + GENERATE (real)

**TASKS**
- `stages/plan.py` (deepseek-r1:8b): emit scenarios `{case_type, priority,
  mutation_id}` — SELECT from the menu, never invent mutation prose. Validate
  every scenario against the slice; drop invented endpoints/params.
- `stages/generate.py` (qwen2.5-coder:7b): one scenario at a time, byte-identical
  static system prompt (prefix cache), input = scenario + stub + explicit mutation
  instruction. Output `{test_code, imports, scenario_id}` via `format=json`.

**DONE**
- [ ] Planner output always validates against the contract or falls back cleanly.
- [ ] Generated tests import the `openapi-fetch` client and use `client.GET/POST(...)`.
- [ ] Every generated test asserts a specific status AND a body shape.
- [ ] Prefix-cache speedup measured (Delta V1) or speed claim dropped honestly.

---

## Phase 6 — Weeks 10-11 — EXECUTE + PRISM

**TASKS**
- `execution/prism_mock.py`: spin `@stoplight/prism` in **dynamic mode** in Docker
  from the spec.
- `execution/playwright_invoke.py`: run `npx playwright test` (pure). Read
  `test-results.json` + stdout for pass/fail. No custom fixture (Delta D3).
- `execution/trace_reader.py`: for FAILED tests only, re-run with `--trace on`
  and parse the trace for status+body. Fixture-log fallback only if trace proves
  unworkable (decided in Week 0 Day 3).

**DONE**
- [ ] Happy-path test passes against Prism; mutation test gets the spec's 4xx.
- [ ] Pass/fail read from native Playwright artifacts (no wrapper dependency).
- [ ] Failed-test trace yields HTTP status + response body programmatically.

---

## Phase 7 — Weeks 12-13 — REVIEW Gates

**TASKS**
- `stages/review.py`, gates cheap-first:
  1 syntax (TS parse) · 2 structure (imports stub, asserts status+shape) ·
  3 AST-validate (ts-morph: uses client, no inline fetch/URL) · 4 novelty
  (nomic-embed-text) · 5 dry-run (Prism; failure → planner feedback) ·
  6 quality (LLM, last).
- Verdicts: >0.9 auto-approve · 0.7-0.9 HITL · <0.7 regenerate (max 2 → HITL).
- HITL queue persisted to SQLite.

**DONE**
- [ ] A test with an inline `fetch` is caught by Gate 3 (AST) with a clear message.
- [ ] A near-duplicate is caught by Gate 4.
- [ ] Dry-run failure routes back to planner and selects a different mutation_id.
- [ ] Verdict thresholds enforced; regenerate caps at 2 then routes to HITL.

---

## Phase 8 — Weeks 14-15 — HEALING (2 types, suggest-only)

**TASKS**
- `healing/diagnose.py`: classify failure BEFORE repair (auth-expiry, contract-drift;
  others → log + human).
- `healing/auth_expiry.py`: detect 401-on-previously-passing; suggest token-refresh
  setup step (creds from env/config). Suggest-only.
- `healing/contract_drift.py`: diff current response vs **last passing snapshot**
  at `.cherenkov/snapshots/{test_name}.json` (Delta D6). Field removed → red
  (likely regression); field added → human review. Suggest-only, loud warning.

**DONE**
- [ ] Snapshot store writes/reads shape-only JSON; first-run skips with a note.
- [ ] Test-content hash detects a modified test → stale snapshot flagged, not auto-diffed.
- [ ] No heal ever auto-commits; every suggestion needs human approval.

---

## Phase 9 — Week 16 — VALIDATE Command

**TASKS**
- `validate/real_server.py`: `cherenkov validate --target <url> --auth-config a.json`
  runs the suite against a real server. SEPARATE from `generate` (never mixed).
- `validate/value_tightening.py`: produce a **report** (Delta D7) — passed/failed +
  actual-vs-expected diff + suggested value assertions. No AST auto-rewrite.

**DONE**
- [ ] `generate` never touches a real server; `validate` never touches Prism.
- [ ] Report suggests `expect(response.name).toBe(sent.name)`-style additions.
- [ ] Tightening is documented as a human step; no test code is auto-modified.

---

## Phase 10 — Week 17 — EJECT + Harden

**TASKS**
- `eject/exporter.py`: copy `tests/` + `clients/`, emit `playwright.config.ts` +
  `package.json`, strip any CHERENKOV metadata.
- Full-pipeline integration tests across all 3 Week-0 specs.

**DONE**
- [ ] Ejected suite runs with `npx playwright test` and zero CHERENKOV deps.
- [ ] Integration test: spec → generate → eject → green run, all in CI.

---

## Phase 11 — Weeks 18-19 — Dashboard (defer-first)

**TASKS**
- WebSocket event backbone; React blue-glow UI per the UI spec (separate doc).
- Mock-data prototype acceptable; real wiring only after core is proven.

**DONE**
- [ ] Live token/context/stage events render; CLI remains the source of truth.

---

## Phase 12 — Weeks 20-22 — Polish, Docs, Ship

**TASKS**
- asciinema demo (a test catching an injected bug); 5-minute get-started; CLI ref.
- Ship to the 5 QA partners; collect the keep/don't-keep signal.

**DONE**
- [ ] A new user goes spec → green ejected test in < 5 minutes following docs.
- [ ] 3+ of 5 partners say they'd keep the tests.
