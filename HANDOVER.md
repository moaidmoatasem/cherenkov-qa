# CHERENKOV -- Session Handover

**Date:** 2026-06-21
**HEAD:** see `git log`
**Tests:** 770+ unit tests; G0 10/10; E11 60/60; **UI E2E: 347 passed, 0 failed** (qa suite + a11y + dashboard_e2e + projects_deep); pet-store eject suite 37/37
**Branch:** `main`

---

## Gate G0 status (EPIC #535)

G0 requires E0.1 AND E0.2 AND E0.3 AND E0.4.

| Exit criterion | Status | Evidence |
|---|---|---|
| E0.1 -- real divergences on 3rd-party APIs | **DONE** | `docs/evidence/e0.1_divergences.md` -- 6 divergences across 3 APIs |
| E0.2 -- integrity catch (catch the AI cheating) | DONE | `demos/catch-the-ai-cheating/`; CI-gated; 10/10 pass |
| E0.3 -- 3 practitioners complete quickstart unaided | NOT YET | User-research activity (can't code our way out) |
| E0.4 -- honest differentiation sentence vs Schemathesis | DONE | `docs/NORTH_STAR.md` section 8 |

**Gate G0: 3/4. Only E0.3 (human recruitment) remains.**

---

## AQE Phase 1 status (Rung 1 -- "the Tool people love")

All code-deliverable Phase 1 items are DONE:

| Item | Status | Where |
|---|---|---|
| E1.1 -- `cherenkov verify` UX | **DONE** | `cherenkov/cli/commands/verify.py`; 8 unit tests |
| E1.2 -- meaningful-assertion gate | **DONE** | `cherenkov/sdet/`; 60 tests (E11 landed via #92) |
| E1.3 -- guardrails-can't-be-weakened proof | **DONE** | `demos/catch-the-ai-cheating/`; CI-gated |
| E1.4 -- eject command hardening | **DONE** | `cherenkov/execution/eject.py`; 10 unit tests |
| E1.5 -- install friction to near-zero | **DONE** | `install.sh` (git+pip/pipx one-liner); Dockerfile fixed (3.12, `pip install .`, `cherenkov` entrypoint); `dist/cherenkov-1.0.0.whl` built and verified |

---

## Phase 2 status (Rung 2 -- "the Platform")

| Item | Status | Where |
|---|---|---|
| E2.1 -- `verify_system` MCP tool | **DONE** | `cherenkov/mcp/handlers.py`; 11 unit tests; `cherenkov mcp install` |
| E2.5 -- `cherenkov check-suite` | **DONE** | `cherenkov/cli/commands/check_suite.py`; 13 unit tests |
| E2.2 -- MCP context consumer | **DONE** | `cherenkov/mcp/client.py` (MCPClient); mesh forwarding; `auto_heal_code` dispatch; 19 unit tests |
| E2.3 -- Continuous engine | **DONE** | `cherenkov daemon --url <target>` polls on interval, detects spec file changes, runs `run_proof`, queues divergences to HitlQueue; 12 unit tests |
| E2.4 -- Source adapters (gRPC/GraphQL) | **DONE** | `cherenkov/truth/sources/grpc.py`, `graphql.py`; exported from `__init__`; 20 tests |

## What landed this session (2026-06-21)

| SHA | What |
|---|---|
| `a4f104b` | feat(e2.4): wire gRPC + GraphQL SourceAdapters into truth/sources (20 tests) |
| `0590092` | feat: landing page, docs site, npm packages, GitHub Action |
| `5656ca5` | chore(qa): finalize E2.3 merge — fix UI test suite bugs (347 UI tests green) |
| (in 5656ca5) | fix: duplicate `#workspace-search-input` — sidebar nav search shadowed project filter; renamed to `#nav-search-input` |
| (in 5656ca5) | fix: `#btn-projects-new-run` button — wrong label ("New Project") and wrong handler; now says "New Validation Run" and calls `onNewRun` |
| (in 5656ca5) | feat: `GET /api/v1/visual/scenarios` endpoint — 5 demo VLM scenarios for VisualRegressionScreen |
| (in 5656ca5) | fix: `GET /api/v1/ocr/status` — wrap in try/except so unavailable OCR binary returns 200+error field instead of 500 |

---

## Platform gaps closed (this session)

| Area | Deliverable | Files |
|---|---|---|
| E2.4 truth sources | gRPC + GraphQL SourceAdapter (claim extraction layer) | `cherenkov/truth/sources/grpc.py`, `graphql.py` |
| Supply chain | SBOM + SLSA + CVE scan + dependency review | `.github/workflows/supply-chain.yml` |
| PII redaction | Pattern-based email/phone/SSN/key/card scrubber | `cherenkov/security/redact.py` (24 tests) |
| Eval regression | Baseline-vs-current metric comparison, CI gate | `cherenkov/evals/regression.py`, `bench/eval-baseline.json` (11 tests) |
| Cost budget | Per-run USD cap with pre-check, warn threshold, env override | `cherenkov/core/budget.py` (16 tests) |
| CI | LLM eval regression workflow (daily + on PR) | `.github/workflows/eval-regression.yml` |

---

## Next code actions (ordered by impact)

1. **E0.3 -- Human validation gate** -- recruit ≥3 QA practitioners to complete quickstart unaided. Cannot be automated.
2. **E2.4 -- gRPC/GraphQL planner integration** -- wire `gRPCScenarioPlanner` + `GraphQLScenarioPlanner` into `cherenkov validate` so gRPC/GraphQL specs flow end-to-end.
3. **Budget integration with substrate** -- call `get_run_budget().pre_check()` + `.charge()` in `cherenkov/substrate/` providers so the cap is actually enforced at runtime.
4. **PII integration with observability** -- wrap `cherenkov/observability/llm_tracer.py` trace spans with `redact_dict()` before writing.
5. **PyPI publish** -- `twine upload dist/*` once PyPI credentials are available; `dist/cherenkov-1.0.0.whl` is already built.
6. **Tauri updater signing key** -- `desktop/src-tauri/tauri.conf.json` `pubkey` is empty; needs `cargo tauri signer generate` (`cargo install tauri-cli` first).

---

## Environment hazards

- **Shared working tree**: `~/cherenkov-qa` shared across concurrent agent sessions. Always check `git branch` before committing.
- **CRLF noise**: `stub/generated_tests/*.spec.ts` and `npm-package/` show as modified constantly -- cosmetic, do not commit.
- **GitHub CLI**: not authenticated in this agent environment -- PRs must be created manually.
- **Note on E1.2 warning in ROADMAP_AQE.md**: the "do NOT merge the stale branch" caveat is outdated -- `cherenkov/sdet/` is already on `main` via #92. E1.2 is done.
