# CHERENKOV -- Session Handover

**Date:** 2026-06-25
**HEAD:** see `git log`
**Tests:** 770+ unit/integration tests (0 failures); **UI E2E: 294 headed, 0 failed** (smoke 39 + journeys 24 + functional 97 + dashboard 34 + api-contract 23 + nonfunctional 76 + settings-journey 1); pet-store eject suite 37/37
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
| E2.4 -- Source adapters + validate integration | **DONE** | `cherenkov/truth/sources/grpc.py`, `graphql.py`; planners wired into `cherenkov validate` with ingestion counts, per-scenario feedback, human-readable summary; 31 tests |

## What landed this session (2026-06-25)

| SHA | What |
|---|---|
| `49e2079` | fix(test): async rate-limit tests + Path cleanup (19 tests green) — replaced pytest.mark.asyncio with pytest.mark.anyio; pathlib.Path throughout execution/; sequential workers=1 fallback in ValidationEngine |
| `fix` | fix(api): duplicate FastAPI operation ID `healthz_healthz_get` — renamed trivial healthz in health_routes.py to `healthz_simple` with explicit operation_id |

## What landed previous session (2026-06-21)

| SHA | What |
|---|---|
| `4bf529a` | feat(platform): K8s HA (HPA/PDB/NetworkPolicy), prompt versioning + regression-guard integration, self-dogfood CI (13 tests) |
| `fe738c8` | chore(qa): align session — 347 UI tests green, update HANDOVER |
| `515a49a` | feat(platform): close 5 architectural gaps — PII redaction, supply chain, eval regression, cost budget, E2.4 adapters |
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
| E2.4 validate UX | gRPC/GraphQL planners wired into `cherenkov validate`; ingestion + result summary always printed | `cherenkov/cli/commands/validate.py`; 11 tests |
| Supply chain | SBOM + SLSA + CVE scan + dependency review | `.github/workflows/supply-chain.yml` |
| PII redaction | Pattern-based email/phone/SSN/key/card scrubber | `cherenkov/security/redact.py` (24 tests) |
| Eval regression | Baseline-vs-current metric comparison, CI gate | `cherenkov/evals/regression.py`, `bench/eval-baseline.json` (11 tests) |
| Prompt versioning | SHA-256 fingerprints, regression-guard warns on prompt change vs model drift | `cherenkov/evals/prompt_version.py` (13 tests) |
| Cost budget | Per-run USD cap with pre-check, warn threshold, env override | `cherenkov/core/budget.py` (16 tests) |
| K8s HA | HPA 2-10 replicas, PDB minAvailable=1, NetworkPolicy, production deployment | `k8s/cherenkov-hpa.yaml`, `pdb.yaml`, `network-policy.yaml` |
| Self-dogfood CI | Server starts, fetches own /openapi.json, runs `cherenkov verify` against itself | `.github/workflows/self-dogfood.yml` |
| CI | LLM eval regression workflow (daily + on PR) | `.github/workflows/eval-regression.yml` |

---

## Next code actions (ordered by impact)

1. **E0.3 -- Human validation gate** -- recruit ≥3 QA practitioners to complete quickstart unaided. Cannot be automated.
2. ~~Full pipeline integration test~~ **DONE** -- `tests/integration/test_pipeline_e2e.py` 15/15 green; ingest→plan→generate(mocked LLM)→validate(mocked Playwright)→schema check.
3. **PyPI publish** -- `twine upload dist/*` once PyPI credentials are available; `dist/cherenkov-1.0.0.whl` is already built.
4. **Tauri updater signing key** -- `desktop/src-tauri/tauri.conf.json` `pubkey` is empty; needs `cargo tauri signer generate` (`cargo install tauri-cli` first).

### Also shipped last session (2026-06-21 continued)
| What | Files | Tests |
|---|---|---|
| Per-IP token-bucket rate limiting (stdlib-only) | `cherenkov/web/middleware/rate_limit.py` | 13 |
| Feature flags (env/file/runtime priority) + `/api/v1/flags` endpoint | `cherenkov/core/flags.py` | 16 |
| Cost attribution by `org_id` in `RunBudget.summary()` | `cherenkov/core/budget.py` | 0 new (additive) |
| Structured API error codes (17 codes, 3 handlers) | `cherenkov/web/errors.py` | 11 |

---

## Environment hazards

- **Shared working tree**: `~/cherenkov-qa` shared across concurrent agent sessions. Always check `git branch` before committing.
- **CRLF noise**: `stub/generated_tests/*.spec.ts` and `npm-package/` show as modified constantly -- cosmetic, do not commit.
- **GitHub CLI**: not authenticated in this agent environment -- PRs must be created manually.
- **Note on E1.2 warning in ROADMAP_AQE.md**: the "do NOT merge the stale branch" caveat is outdated -- `cherenkov/sdet/` is already on `main` via #92. E1.2 is done.
