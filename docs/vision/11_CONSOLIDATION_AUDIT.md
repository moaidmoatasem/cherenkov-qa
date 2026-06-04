# CHERENKOV — Consolidation Audit (honest state of the codebase)

**Date:** 2026-06-04 · **Against:** `main` @ green (426 tests, gate `pass`)
**Why:** a single evidence-based pass over everything built, so the headline
("E0–E13 shipped") is backed by what's actually in the tree — and the gaps are
named, not buried. Per `AGENTS.md`: raw evidence, never claims.

---

## 1. What's actually here (measured, not asserted)

~14,700 LOC of source across 21 packages; 59 test/smoke files; **426 tests pass**, Validation Gate `pass`.

| Package | LOC | Reality check |
|---|---|---|
| `stages/` | 2603 | ✅ INGEST→PLAN→GENERATE→REVIEW + perf/visual/vision sub-stages |
| `core/` | 1935 | ✅ contracts, config, orchestrator, substrate-facing seams |
| `divergence/` | 1381 | ✅ Skeptic/Witness/self-play/proof_run — **the bet, proven on live Petstore** |
| `ai/` | 940 | ✅ Ollama + OpenAI clients, retry ladder, cache |
| `coverage/` | 914 | ✅ E11 coverage loop + assertion gate |
| `reflector/` | 898 | ✅ verdict memory, fingerprint suppression, introspect |
| `truth/` | 800 | ✅ sources + emitters |
| `copilot/` | 705 | 🟡 explorer/intent/mentor — NL-intent has a coverage gap (#158) |
| `healing/` | 681 | ✅ suggest-only (D7 honored) |
| `substrate/` | 616 | ✅ router + tiers incl. real `VLMProvider` (Ollama/OpenAI) |
| `execution/` | 580 | ✅ playwright invoke / trace / validate / eject |
| `hitl/` | 442 | ✅ atomic queue + `hitl/v1` envelope, race-proven |
| `oracle/` | 372 | ✅ oracles |
| `validate/` | 344 | ✅ Validation Gate + evidence collector (`validate/v1`) |
| `openclaw/` | 319 | ✅ Tier-1 adapter (notify+trigger); Tier-2/3 ahead (#149–#151) |
| `federation/` | 280 | 🟡 protocol + cross_check present; real 2-node sync ahead (#152) |
| `sdet/` | 271 | ✅ coverage SDET |
| `governance/` | 240 | ✅ KPI panel |
| `dashboard/` | 223 | 🟡 present; FE redesign tracked separately |
| `continuity/` | 117 | ✅ daemon + PR diff (not yet dogfooded — #154) |

**Verdict:** this is a real, substantial codebase — not a Potemkin tree. The E0–E13 milestones map to actual, tested modules.

---

## 2. Gaps found (with evidence) → tickets

| Finding | Evidence | Ticket |
|---|---|---|
| **Perf LLM metrics are simulated** — TTFT/ITL/cost are `hash()`-derived, not measured. C3/#118 was hollow. | `stages/perf/perf_stage.py:271-278` ("return simulated values to demonstrate the concept") | **#157** (P1) |
| **Copilot drops unsupported NL-intent actions into `// TODO`** in generated artifacts (silent coverage loss). | `copilot/intent.py:212` | **#158** (P2) |
| **Stale `develop` branch** (0 ahead / 57 behind) + 59 root test files. | `git rev-list`, repo root | **#159** (hygiene) |

These are **true-up** items: the feature was claimed done, the substance needs finishing or honest down-scoping. None block the green base.

---

## 3. Things that are genuinely done (so we stop re-litigating them)

- **The bet:** 5 reproduced divergences on live Swagger Petstore v3 — `docs/proof_run/PROOF_RUN.md`.
- **The gate:** passed 4/5 with real QA people — HANDOVER §5, `QA_DEMO_KIT.md`. (Make the evidence machine-auditable: #153.)
- **HITL concurrency:** atomic SQL gatekeeper, race-proven 10/10 + 5/5.
- **E9 vision:** concrete `VLMProvider` with Ollama/OpenAI backends — not a stub.
- **Branch sprawl:** already pruned 30+ → 2 (#130 closed).

---

## 4. Issue-tracker consolidation (state of record)

- **#134** (delivery EPIC) — **delivered**; E0–E13 + gate done. Annotated, points to Horizon 2.
- **#147** (Horizon 2 EPIC) — live plan: #148–#155.
- **True-up from this audit:** #157, #158, #159.
- **Cross-cutting still open:** #131 (X2 branch-protection — do before fan-out), #132 (X3 CI runners), #133 (X4 MCP, now unblocked).
- **Closed/cleaned:** #130 (branches pruned), #133 label (gate passed).

---

## 5. Recommended next moves (in order)

1. **#131 (X2 branch-protection)** — lock the green base before agents fan out.
2. **#157 (perf metrics true-up)** — kill the one real fabrication.
3. **#153 (gate evidence)** — make our own headline auditable.
4. **#148 / #149** — start Horizon 2's value bets (prove-in-the-wild, chat HITL).
5. **#159** — tidy `develop` + root tests when convenient.

> Standing reminder from the delivery plan: revoke any GitHub PATs pasted in plaintext earlier — assume still live.
