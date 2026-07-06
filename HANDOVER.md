# CHERENKOV -- Session Handover

**Date:** 2026-07-05
**HEAD:** see `git log`
**Tests:** 788+ unit/integration tests (0 failures); **UI E2E: 260 headed (qa/ suite), 0 failed** (smoke 39 + journeys 24 + functional 97 + api-contract 23 + nonfunctional 76 + settings-journey 1); pet-store eject suite 37/37
**Branch:** `main`

---

## 📹 Onboarding & KT Package (NEW — 2026-07-06)

A complete onboarding and Knowledge Transfer package was produced for documentation and stakeholder pitching. All content uses **real test data and real caught bugs**.

**Package root:** `docs/onboarding/ (in-repo)`

| Artifact | Description |
|----------|-------------|
| `sessions/session_a_zero_to_hero.md` | 10-min developer demo: install → generate → validate (4 real Petstore bugs) |
| `sessions/session_b_live_case.md` | 15-min QA Lead demo: Stripe/Prism mock, `--repair` loop, HITL queue, `eject` |
| `sessions/session_c_pitch_companion.md` | 5-min exec pitch: 5-QA gate (4/5 yes), verbatim quotes, business case |
| `run_demo.sh` | One-command green→red conformance detection harness with Docker health checks |
| `casts/cast_session_a.sh` | asciinema-ready terminal cast for Session A |
| `casts/cast_session_b.sh` | asciinema-ready terminal cast for Session B |
| `PITCH_DECK.md` | 10-slide markdown pitch deck with talking points, visual cues, timestamps |
| `PITCH_DECK.html` | Interactive HTML presentation (dark theme, glassmorphism, keyboard nav) |
| `FAQ_OBJECTIONS.md` | 25+ Q&A across Technical, Trust/Compliance, and Business categories |
| `VIDEO_RECORDING_GUIDE.md` | 9-chapter guide: Loom/OBS/asciinema setup, audio, publishing |
| `RECORDING_ASSETS/README.md` | Asset directory: naming conventions, recording instructions, manifest template |

**Docs integration:** `docs/INDEX.md` updated with `📹 Onboarding & KT Sessions` section.

**Next human action:** Record the actual Loom/asciinema sessions using the guide and scripts above, then fill in `RECORDING_ASSETS/MANIFEST.md` with published URLs.


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

## Phase 3 status (Rung 3 — Protocol / Authority / Certificate)

All Rung 3 items are DONE (merged 2026-06-27):

| Item | Status | Where | PR |
|---|---|---|---|
| E3.1 — Certificate format + signing | **DONE** | `cherenkov/core/certificate.py`; 18 unit tests | #572 |
| E3.2 — `cherenkov certify` CLI | **DONE** | `cherenkov/cli/commands/certify.py`; 9 CLI tests | #572 |
| E3.3 — CI gate + badge | **DONE** | `.github/workflows/certify-gate.yml`; `workflow_dispatch` only (demo probes live Petstore) | #572 |
| E3.4 — Open cert spec | **DONE** | `docs/specs/CHERENKOV_CERTIFICATE.md` promoted to STABLE v1.0 | #575 |
| E3.5 — Compliance mapping | **DONE** | `docs/compliance/CERT_COMPLIANCE_MAPPING.md`; `compliance_profile()` function; 8 tests | #575 |

**Rung 3: 5/5. Complete.**

---

## Spec coverage-gap report (2026-06-27)

| Item | Status | Where |
|---|---|---|
| `cherenkov/divergence/coverage.py` | **DONE** | `compute_coverage(spec, reports) → CoverageReport`; 12 unit tests |
| `cherenkov verify --coverage-report` | **DONE** | Prints per-endpoint table, gap list, coverage %; warns if no `--spec` |
| `cherenkov certify --coverage-report` | **DONE** | Same output, combined with certificate print |
| Tests | **DONE** | `tests/unit/test_coverage.py`; 18 tests total |

---


## What landed this session (2026-07-05)

| SHA | What |
|---|---|
| (pending) | fix(substrate): real latency tracking — OllamaProvider/OpenAIProvider/GitHubModelsProvider always reported `latency_ms=0`; wrapped client call with `time.monotonic()` bookends |
| (pending) | fix(docker): Dockerfile base image `python:3.14-slim` → `python:3.12-slim` to match CI |

## What landed previous session (2026-07-04)

| SHA | What |
|---|---|
| `e94dab6` | fix(emitters): spec-patch and PR-comment emitters used stale DivergenceReport schema; PR #658 |
| `8eaedb8` | refactor: replace legacy typing generics with built-in equivalents (Python 3.9+); PR #659 |
| `0d2aeaa` | refactor: use `time.monotonic()` for all duration measurements; fix `raise e` → bare `raise`; PR #657 |
| `cd521a3` | fix(generate): correct indentation so spec enrichment runs for openapi source type; PR #650 |
| `fde73f6` | fix: replace silent except-pass blocks with diagnostic logging (scan #4); PR #652 |
| `e926be6` | feat(#628): spec coverage-gap report via `cherenkov validate --coverage-report`; PR #651 |
| `ee9fd91` | fix(events): MCP bridge event schema; fix(generate): restore dead LLM path; PR #654 |
| `004030e` | fix(test): expect RuntimeError from production simulation guard; PR #653 |
| `f1e4f09` | test(generate): add golden snapshot test with prompt-drift guard; PR #648 |
| `4de9ce1` | feat: add SessionStart hook for Claude Code on the web; PR #649 |
| `c262402` | refactor: assert→if/raise, encoding= on open(), lazy logger %s (scan #3); PR #647 |
| `8d1d2d3` | refactor: replace assert guards with if/raise and add encoding= to open() calls; PR #646 |
| `0df49a8` | refactor: logging hygiene, encoding, silent-except, mutable default arg; PR #645 |
| `d42d94c` | feat(validate): --demo mode for no-Ollama first run; PR #639 |
| `49665fd` | refactor: move deferred imports to module level, narrow bare exception; PR #644 |
| `a616a90` | test: mutation test proving divergence detector has real teeth; PR #641 |

## What landed previous session (2026-07-01)

| SHA | What |
|---|---|
| `8d1b9ad` | fix(e2e): harden headed test suite for Xvfb environment — raised global timeout 30→90s; moved sidebar perf `start` to after bootstrap; added `fonts.googleapis.com` to network-failure exclusion; 260/260 headed pass; PR #634 |
| `ed85e2d` | fix(ci): correct Rust toolchain action name in tauri-build.yml — `dtolnay/rust-action` → `dtolnay/rust-toolchain`; PR #634 |

## What landed previous session (2026-06-27)

| SHA | What |
|---|---|
| `9e49d48` | feat(generate): wire RepairLoop into generate CLI command (11 tests) — `cherenkov generate` now routes through RepairLoop by default (--repair/--no-repair flag, --max-attempts 1-10); PR #574 |
| `ef616f9` | fix(test): scope LoggerConfig.suppress_stderr to autouse fixture — module-level assignment was poisoning test_errors_logging.py (5 tests) across the full suite; PR #576 |

## What landed previous session (2026-06-25)

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

> Reprioritized 2026-07-05 per `docs/reviews/STRATEGY_REVIEW_2026-07-05.md` (full strategic + technical review).

0. **R1 — Spec-derived probe planner (P0).** `run_proof()` iterates hardcoded Petstore `PROOF_RUN_PROBES` regardless of the `--spec` passed (`cherenkov/divergence/proof_run.py:318`); both `verify` paths route through it (`cli/commands/verify.py:189`, `verdict/engine.py:162`). Offline `verify` against an arbitrary API currently probes Petstore paths. Fix: synthesize offline hypotheses from the loaded spec (enum violation, required-field omission, documented error codes, response schema/headers). Blocks E0.3 — practitioners pointing verify at their own APIs will hit this.
1. ~~R0 — Truth alignment~~ **DONE** (2026-07-05) — README repositioned to the integrity wedge (`c6e0cec`) and false claims fixed (PyPI badge/`pip install cherenkov-qa` removed — package is NOT on PyPI; quickstart `check-suite --demo` replaced with real commands — that flag never existed); root artifact clutter removed and `.gitignore`-guarded (`soc2_report.json`, `pr.json`, `audit.json`, `issues.txt`, `test-junit.xml`, `test-sarif.json`; `mut_spec.json` and `qwen.json` KEPT — referenced by `tests/test_mutation_validate.py:16` and MCP integration scripts). **Deferred: `cherenkov.py` removal** — it is load-bearing: `.github/workflows/ci.yml:612-626` runs it directly, `Dockerfile.mcp` COPYs it as entrypoint, `bin/cherenkov-npm.js:42` prefers it, `scripts/setup_oi.sh` + `scripts/qwen-code-integration.sh` + `package.json` reference it, and CI gates `scripts/ci_docs_check.py` + `scripts/check_cli_docs.py` load it directly. Commit `0f16fed` deleted it prematurely (docs-parity gate crashed with FileNotFoundError, CI smoke steps and Docker MCP build broken) — **restored** in PR #675; retiring it properly is a migration project (repoint all of the above to the `cherenkov` package CLI first). `0f16fed` also deleted two non-artifacts, both now restored: `mut_spec.json` (fixture for `tests/test_mutation_validate.py:16` — its absence made the Test-coverage CI job fail on every PR) and `qwen.json` (Qwen Code MCP config, see `docs/QWEN_CODE_ALIGNMENT.md`). Follow-up bug worth an issue: `OrchestrationEngine.run_pipeline()` returns *success* when the input spec file is missing — a truth tool should hard-fail on missing input.

   **SURFACE FREEZE (in effect until R3/E0.3 passes):** no new work on `desktop/`, `vscode/`, `cherenkov-backstage-plugin/`, `operator/`, `landing-page/`. Bug fixes only.
2. **E0.3 -- Human validation gate** -- recruit ≥3 QA practitioners to complete quickstart unaided. Cannot be automated. Land R1 first. Recommended pool: Egypt's ESTB/ISTQB CT-GenAI community (see `docs/reviews/STRATEGY_REVIEW_2026-07-05.md` §8.4).
2. ~~Full pipeline integration test~~ **DONE** -- `tests/integration/test_pipeline_e2e.py` 15/15 green.
3. ~~Spec coverage-gap report~~ **DONE** -- `cherenkov/divergence/coverage.py`; `--coverage-report` flag on `verify` + `certify`; 18 tests.
4. ~~`cherenkov report --output report.json` (+ `--diff`)~~ **DONE** -- `cherenkov/cli/commands/report.py`; supports `-o` JSON output, `-d` diff against baseline, `--run`/`--list` RunStore mode; 53 unit tests green; PR #641.
5. ~~Mutation test for the validation engine~~ **DONE** -- `tests/unit/test_mutation_validation.py`; 9 tests prove `WitnessAgent` + `run_proof` detect divergences on mutant server and find zero on conformant server; PR #641.
6. **R2 — Distribution: PyPI publish** -- `twine upload dist/*` once PyPI credentials are available; `dist/cherenkov-1.0.0.whl` is already built. Also: publish MCP server to registries; publish the "Catch the AI cheating" demo write-up.
7. **Tauri updater signing key** -- `desktop/src-tauri/tauri.conf.json` `pubkey` is empty; needs `cargo tauri signer generate` (`cargo install tauri-cli` first).

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

---

## Onboarding & KT Package

**Built:** 2026-07-06 | **Location:** `docs/onboarding/ (in-repo)`

A complete knowledge-transfer and onboarding package was produced for practitioners, engineering leaders, and demo presenters. All assets are self-contained and link back to the canonical `docs/` SSOT.

### Files Produced

| File | Purpose |
|------|---------|
| `run_demo.sh` | Live conformance demo harness — 3-phase: green run, regression injection (REGRESSION_MODE=true), Prism/Stripe validation. Docker health checks, ANSI colour output, cleanup trap. |
| `casts/cast_session_a.sh` | Recordable bash script for Session A (Zero to Hero): init → spec download → generate → validate → regression → report. Drives `asciinema rec`. |
| `casts/cast_session_b.sh` | Recordable bash script for Session B (HITL + Eject): --repair, HITL queue approve/reject, daemon, certify, eject, standalone pytest run. |
| `FAQ_OBJECTIONS.md` | 25-question FAQ across Technical (9), Trust/Compliance (8), and Business (8) categories. Honest answers including current limitations. |
| `RECORDING_ASSETS/README.md` | Directory guide for `.cast`, `.mp4`, `.gif`, and thumbnail assets — naming conventions, recording instructions, asset status tracker. |

### docs/ Updates

| File | Change |
|------|--------|
| `docs/INDEX.md` | Added `📹 Onboarding & KT Sessions` section after top callouts, linking to all 7 onboarding assets. |
| `HANDOVER.md` | Added this section (Onboarding & KT Package). |

### Integration with existing docs

The onboarding package deliberately does **not** duplicate spec content from `docs/`. Instead it links back:
- Session scripts reference `docs/GETTING_STARTED.md` and `docs/CLI_DEMO.md`
- FAQ answers cite specific files (e.g., `cherenkov/truth/sources/graphql.py`, `hitl_audit.jsonl`, `docs/specs/CHERENKOV_CERTIFICATE.md`)
- The demo harness uses the real `./bin/cherenkov` binary from the live tree

### Next steps for this package

1. Record `.cast` files using `asciinema rec` with the cast scripts
2. Screen-record `.mp4` files and produce `.gif` highlights
3. Create thumbnail PNG assets per specs in `RECORDING_ASSETS/README.md`
4. Link recorded assets from `sessions/session_a_zero_to_hero.md` etc.
5. Run the E0.3 gate: 3 practitioners complete Session A unaided

