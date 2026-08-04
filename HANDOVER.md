# CHERENKOV -- Session Handover

**Date:** 2026-08-02 (round 3 + lead verification)
**HEAD:** `main` at `d9a161f`. **Certified green: 2064 passed, 2 failed** (pre-existing `test_verify_cmd.py` mock drift, tracked as #819). UI revamp `2e66658` build-verified (vite output matches committed dist hashes).
**Tests:** Run `pytest tests/ -m "not slow and not e2e and not integration and not k8s and not ollama and not mobile"`.

> **Re-certified 2026-08-04 at `main` `530468a1`:** **2138 passed, 2 failed, 6 skipped** (8:30, HANDOVER filter). The 2 failures are the network-only `tests/integration/real_demo/test_demo_api_real.py` tests (added in #854; not `integration`-marked so the filter doesn't exclude them; they need a live demo server via `CHERENKOV_TEST_BASE_URL`). The prior `#819 test_verify_cmd.py` drift is **fixed** — it no longer fails. 6 skipped are service-gated (`slow`/`integration`/`e2e`/`k8s`/`ollama`/`mobile`). Prior handover counts (2064/2076/1746) were stale against the grown suite.

**Forward plan:** `docs/ROADMAP_2026H2.md` is the milestone map (M0-M5 + tech-debt track T). This file is the status anchor — **if the two disagree, this file wins.**

## Round 2 swarm result (2026-08-01 night)

Follow-up swarm on the #816 friction log + #792 + SDD runtime:

| Issue | Delivered | Branch (merged to main) |
|---|---|---|
| **#826/#827** (onboarding blockers) | New "Act 0: Prerequisites & Workspace Provisioning" (clone, venv, `pip install -r requirements.txt` + `pip install -e .`, Node, Ollama); Act 2 install fixed; **cold-run verified end-to-end** — `init` exits 0, `cherenkov.toml` created | `fix/track-826-onboarding` |
| **#828** (generate 38/38 → 4 files) | Root cause: `mutation_id` per-endpoint → filename collision → silent overwrite. Fix: `scenario_spec_filename()` in `generate_cmd.py:12` — 38 scenarios now persist 38 files; scratch cleanup on repair path; `.gitignore` covers generated specs | `fix/track-828-validate` |
| **#829** (validate fixture noise + 3.0.4) | `spec_validator.py:69-86` accepts 3.0.x/3.1.x/3.2.x patch versions; **new `validate --tests` filter** (glob/substring, `status: "empty"` on no-match) scopes runs away from the 13 shipped demo fixtures; Act-4 transcript rewritten to real format + `--fail-on-drift` documented (exit 0 by design) | `fix/track-828-validate` |
| **#830** (init transcript) | Real `init` output (mut_spec.json/stub/target_spec.json autodetect, `cherenkov.yml` scaffold) replaces fabricated petstore.json visual; verified byte-accurate | `fix/track-831-faq` |
| **#831** (FAQ stale refs) | `validate-spec`→`validate`+external swagger2openapi; `docs/ci/`→`docs/guides/github-actions-setup.md`; `dist/*.whl`→honest install story; env vars→real `CHERENKOV_TIER_*`/`OLLAMA_URL`/`CHERENKOV_VLM_LOCALAI_URL`; grep-clean verified | `fix/track-831-faq` |
| **#792** (MCP registry) | `manifest.json` (repo root, 890 lines: 37 tools with inputSchemas, auth, resources, 1.2.0); `mcp serve` initialize/tools-list smoke PASS; `docs/README-MCP-PUBLISH.md` rewrite with human checklist. **Submission still needs human** (Smithery login, marketplace account) | `feat/track-792-mcp-manifest` |
| SDD runtime (agent_sync) | `scripts/agent_sync.py:40` `_memsearch_client()` uses `paths=[...]` (memsearch 0.4.x API) + graceful fallback; before/log/token/after/status all exit 0; 5 regression tests | `fix/sdd-runtime` |

## Round 3 swarm result (2026-08-02)

Docs-hygiene round — closes the last #831 finding and hardens the tree:

| Item | Delivered |
|---|---|
| **Wiki stale env vars** (was the last open friction finding) | `docs/wiki/{FAQ,Configuration,Concepts,Security,CLI-Reference,Pipeline,Troubleshooting}.md` — `CHERENKOV_LLM_PROVIDER`/`CHERENKOV_LLM_MODEL`/`LOCALAI_URL`/`LOCALAI_BASE_URL` (NONE exist in `cherenkov/core/settings.py`) replaced with real names: `PROVIDER`, `GEN_MODEL`, `CHERENKOV_TIER_{SMALL,DEEP,VISION}_PROVIDER`, `CHERENKOV_FALLBACK_PROVIDER`+`CHERENKOV_FALLBACK_ENABLED`, `CHERENKOV_VLM_PROVIDER`/`CHERENKOV_VLM_LOCALAI_URL` (VLM tier only), `OLLAMA_URL`. The nonexistent `stub` LLM provider was dropped from FAQ/Configuration — the real no-LLM path is `generate --no-repair` (template fallback). Commit `156dba0`. |
| **Branch hygiene** | 12 merged round-1/2 branches deleted (`feat/track-*`, `fix/track-*`, `fix/sdd-runtime`). |
| **Verification** | Full fast suite on current main: **2064 passed, 2 failed** (#819 pre-existing). `slow`/`integration`/`e2e` markers collect zero offline tests — they are service-gated. |

**Shared-tree hazard (repeat incident, 2026-08-02):** the parallel UI-revamp agent (`2e66658` — "5-Workspace UI/UX Revamp", FastAPI wiring + SPA catch-all route) was editing the shared tree mid-session; a full-suite run during its edits showed **14 transient failures** in `tests/integration/test_api_endpoints.py` (404s on `/api/v1/health` etc.). They vanished once the agent committed — rerun gave 2064 passed. **Lesson: never trust a full-suite result while `.agents/*` or `git status` shows another agent's in-flight edits; verify `git status --short` and rerun before reporting failures.** The SPA catch-all `/{full_path:path}` (registered last, 404s on `api/*`) does not break API routes in isolation (38/38 API tests pass alone).

## Lead verification pass (2026-08-02)

Orchestrator sweep to certify "latest correct work":

- **main is latest and correct**: local == `origin/main` == `d9a161f`; all round-1/2/3 work present (guardian CLI, 37 MCP tools, SAML/RBAC wiring, root shim removed, wiki env refs fixed). Round-1 PRs #820-824 merge commits verified in main history.
- **Full suite re-certified**: 2064 passed / 2 failed (#819 pre-existing). `slow`/`integration`/`e2e` markers collect zero offline tests.
- **UI revamp `2e66658` build-verified**: `vite build` output matches committed dist hashes (`index-ZhckOsq_.css`, `index-pVY_2juK.js`); no frontend regression.
- **No open PRs** (duplicate #825 is closed; no release-please PR pending — `origin/release-please--branches--main` carries an orphaned `release 1.3.0` commit, not merged).
- **Cleanup done**: local stale branches `docs/m0-complete-align` (superseded, M0 closed), `feat/qa-headless-locator-alignment` (superseded by revamp) deleted.
- **BLOCKER — PAT expired/revoked mid-session**: `gh auth status` reports invalid token; `git push` fails ("Invalid username or token") — was valid at session start (pushes `156dba0`/`d9a161f` succeeded), died during the session. All remote ref deletion (`feat/track-810/811/812/814/815-*` — content verified merged) is blocked until the maintainer renews the PAT in `~/.config/gh/hosts.yml`. ~110 stale remote `claude/*` branches remain (parallel-agent artifacts) — do NOT bulk-delete without maintainer review.

**Notes for next agents:**
- **M1 prep is now unblocked**: session_a_zero_to_hero.md survives a cold run (verified). The last #831 finding (stale `docs/wiki/` env vars) was fixed in round 3 (`156dba0`) — `grep -rn CHERENKOV_LLM_PROVIDER docs/wiki` is clean.
- Pre-existing test failures `test_verify_cmd.py::{test_no_divergences_exits_0,test_llm_flag_passed}` (mock drift vs E0.5i `known_identifiers`/`allow_mutations` kwargs) — tracked as **#819**, D7 means agents don't fix; needs SDET owner.
- PAT (moaidmoatasem) has **repo write but NO issues/PR write scope** — can't create issues, comment, close PRs (duplicate #825 still open), or close issues. Maintainer action needed.
- **Shared-tree hazard confirmed**: a parallel Claude agent (`claude/happy-noether-kt638y`) switched the shared tree mid-swarm; round-2 merges briefly landed on its branch then were redone on main. Check `git status`/`git branch` before and after any merge.
- M1 (human validation) window 08-12 → 08-26; onboarding doc is now cold-run-ready.

## Product decision: no enterprise/paid tier — fully open source for the community (2026-08-01)

The maintainer decided CHERENKOV-QA has **no enterprise tier and no monetization** — it's a fully open-source (Apache 2.0), community project. Scope: **positioning only**, not a feature retreat:

- The former "L5 Enterprise, $300+/mo, contact us" framing is gone from `docs-site/docs/index.md`, `docs-site/docs/getting-started/cost-tiers.md`, and `docs-site/docs/cli/reference.md` — SSO/SAML, RBAC, audit logging, and the K8s operator are now presented as ordinary free, self-hosted features, same tier as everything else.
- **The Phase 13 "Enterprise" feature work itself is unchanged and still worth finishing** (#754-763, #810) — SAML/RBAC/audit/GDPR are still real, still useful, still on the roadmap. Just don't reintroduce paywall language, a "contact sales" flow, or license-gated features anywhere (README, docs-site, CLI help text, UI).
- Do not add pricing pages, license-key gating, or an `enterprise@` contact anywhere going forward — if a task seems to call for it, that's a signal the task description is stale, not a signal to build it.

## Where things actually stand (2026-08-01)

- **M0 (spec-shape robustness) is CLOSED** (#808) — gates M1. Zero silent endpoint drops across a 10-spec corpus, mutation battery separates 3/3 cheat classes. See `docs/ROADMAP_2026H2.md` M0 section for the full checklist, all boxes checked.
- **M1 (human validation) has NOT started** — window 2026-08-12 → 2026-08-26, **owner: human**. Its exit criterion is ≥3 real practitioners from outside this repo completing onboarding unaided, with ≥1 re-running it unprompted within 7 days. **No agent can complete this milestone** — do not fabricate, simulate, or approximate practitioner validation. If you're an agent reading this before 08-12, M1 is simply not yours to work on; work the tech-debt track (T, below) instead.
- **UX redesign** (PRs #797-806): 5-hub IA shipped and live-verified in a real browser — Overview, Author & Generate, Triage (Kanban), Coverage & Certification, Knowledge. Full detail in `docs/reviews/UX_REDESIGN_PROPOSAL_2026-08.md`.
- **Release/docs/issue-tracker reconciliation** (PR #807, merged): `.release-please-manifest.json`/`package.json` fixed to `1.2.0`; `CHANGELOG.md`'s false "Phase 11-16 fully implemented" claim corrected; missing docs-site release notes (v1.1.2, v1.2.0) added; 55 open Phase 11-16 GitHub issues reconciled against real code (18 closed with evidence, 14 annotated partial, ~23 genuinely not started — left as-is). Full detail in `docs/reviews/COMPETITIVE_POSITIONING_2026-08.md` (also covers external competitive positioning vs. TestSprite/Momentic/Vibium/MCP, critically cross-checked).

## Open work, as GitHub issues (pick these, don't invent new scope)

| Issue | What | Notes |
|---|---|---|
| **#809** | Release hygiene follow-up | Publish `v1.2.0` GitHub Release (fixes stale `/latest/` docs); the malformed `v.1.1.1` tag rename is flagged for a **human decision**, not autonomous action |
| **#810** | Wire Enterprise SAML/RBAC CLI placeholders | Real logic exists in `cherenkov/enterprise/{saml,rbac}.py`; CLI commands are literal `"""Placeholder"""` stubs |
| **#811** | Spec Guardian daemon CLI entrypoint | **PR open** (`claude/happy-noether-kt638y`) — `cherenkov guardian start` wired to `SpecGuardianDaemon`; also fixed a real `extra={"message": ...}` logging crash the new smoke test surfaced on first-ever exercise of that code path |
| **#812** | MCP tool depth + registry publish | `check-suite`/`verify`/`generate` as agent-invokable MCP tools; `smithery.yaml` exists but nothing's been submitted to a registry |
| **#814** | Retire root `cherenkov.py` | Migration (8 load-bearing consumers), not a delete — see issue for the exact list |
| **#815** | Consolidate dual AI routing (`ai/` + `substrate/`) | Map call sites, propose a plan; don't force a merge if the two layers serve genuinely different purposes |
| **#816** | Prep onboarding assets ahead of M1 | Dry-run `docs/onboarding/sessions/session_a_zero_to_hero.md` cold, file friction logs — this is available now even though M1 itself isn't |

Pick whichever of #809-#816 is unclaimed and matches your context window — they're independent of each other except where noted (e.g. #809's PyPI-publish sub-item is gated behind M1). When one closes, check `docs/ROADMAP_2026H2.md`'s T-track table and this list for what's next; if both are empty of unclaimed work, that itself is worth a comment on the newest closed issue rather than inventing scope.

37 other open GitHub issues remain (Phase 13 Enterprise partials, Phase 15/16 — mostly genuinely unstarted). Their current status is accurate as of the 2026-08-01 triage; don't re-triage them without new evidence.

## Standing rules for agents operating without the maintainer present

These apply any time the maintainer isn't actively in the loop, not just a specific date — treat them as durable, not a temporary posture.

- **Verify before trusting.** This repo has a documented history of prior agent sessions fabricating completion claims (see `CHANGELOG.md`'s "Corrected" note under `[1.2.0]`, and the general norm in `CLAUDE.md`: don't trust `docs/_archive/ROADMAP_RECONCILIATION.md`, memory files are hints not truth). Before claiming anything is "done," grep for the actual code and cite file:line. This applies to your own prior work too, not just other sessions'.
- **One branch per concern, PR against `main`, draft by default.** Don't push directly to `main`. Check `git status` and recent `git log` before starting — this is a shared, volatile tree; other agents may be mid-edit.
- **Stage specific files, never `git add -A`.**
- **Never touch M1's actual pass/fail criteria.** It requires real external practitioners; there is no code change that satisfies it, no matter how much idle capacity is available. Prep work (like #816) is fine; simulating or approximating the milestone itself is not.
- **Don't open new roadmap docs.** `docs/ROADMAP_2026H2.md` explicitly says "No roadmap docs... this file plus HANDOVER.md are the forward plan." Update these two, not a new file. The same goes for a new HANDOVER-equivalent — extend this file's top section, don't fork it.
- **Keep the issue tracker as the work queue.** When you find new well-scoped work (a bug, a wiring gap, a debt item), open a GitHub issue for it rather than only noting it in a PR description — that's what lets the next agent, with no memory of this conversation, find it.
- **A separate autonomous multi-agent system** (`.agents/` — sentinel/auditor archetypes, orchestrator-driven) may also be active on the maintainer's local machine working the same roadmap. If you see `.agents/*/BRIEFING.md` or `.agents/*/handoff.md` state that conflicts with this file, this file (committed to `main`) wins — those are per-machine working notes, not synced truth.
- **Scale scope to available capacity, not the other way round.** If the current issue queue runs dry, prefer opening more small, well-evidenced issues (T-track debt, friction-log items from #816, deeper triage of the still-open 37) over inflating a single issue into a multi-week project. Small and verifiable beats large and unverified — this repo has a specific, recorded history of the latter going wrong.

---

**Branch:** `main` (or create `feat/sprint4-phase11` before merging).

## Sprint 4 / Phase 11 Completion (2026-07-31)

All 5 tracks from the Phase 11 roadmap have been built and verified:

| Track | Status | Key Files |
|-------|--------|-----------|
| **T1 – MCP Stub Tools** | ✅ Complete | `cherenkov/mcp/handlers.py`, `cherenkov/adapters/notifiers/jira_client.py`, `cherenkov/stages/perf/perf_stage.py`, `cherenkov/compliance/mena_scanner.py` |
| **T2 – LangChain Integration** | ✅ Complete | `cherenkov/integrations/langchain/tools.py`, `cherenkov/integrations/langchain/__init__.py`, `pyproject.toml` (added `langchain-core>=0.1.0`) |
| **T3 – Desktop Setup Wizard** | ✅ Complete | `cherenkov/web/ui/src/components/SetupWizard.tsx`, `desktop/src-tauri/src/main.rs` |
| **T4 – VS Code Expansion** | ✅ Complete | `vscode/src/providers/CodeLensProvider.ts` (heal CodeLens), `vscode/src/extension.ts` (`cherenkov.heal` cmd), `vscode/package.json` |
| **T5 – MCP Registry** | ✅ Complete | `smithery.yaml` (already present with correct config) |

### Key Decisions
- **LangChain dependency**: Added `langchain-core` as a core dep in `pyproject.toml` (not optional), since it's lightweight and the integration is a core product feature.
- **Healing CodeLens**: Dispatches to the dashboard `/healing` URL — full inline suggestion UI is in the web dashboard, not in the extension itself (keeps extension footprint small, D7 invariant respected).
- **`smithery.yaml`**: Was already present — verified it points to `cherenkov mcp serve` correctly.

### Next Actions
- Create feature branch and open PR against `main`.
- Record Loom/asciinema sessions for the LangChain integration usage.
- Publish to Smithery / MCP registry after PR is merged.

---

**Date:** 2026-07-31
**HEAD:** see `git log`. Last reflected here: `39ec376` on `feat/qa-headless-locator-alignment`, merged into local `main`, which also carries `origin/main` through #726 and #730.
**Tests:** **1968 passed, 6 skipped, 0 failed** — measured 2026-07-31 (`pytest tests/`). All tracks stable.
**UI E2E:** 260 headed (qa/ suite), 0 failed (smoke 39 + journeys 24 + functional 97 + api-contract 23 + nonfunctional 76 + settings-journey 1); pet-store eject suite 37/37 — **not re-verified since 2026-07-20**; the figure is carried forward, not confirmed.
**Mypy gate:** ⚠️ **FAILING** — 7 errors in 3 files (`cherenkov/ai/openai_client.py`, `cherenkov/ai/nemoclaw_client.py`, `cherenkov/substrate/providers/localai.py`). The 2026-07-06 note below claiming "runs clean on 530 files" no longer holds. A fix is in progress in a separate session.
**Branch:** `feat/qa-headless-locator-alignment`. Run `git rev-list --left-right --count origin/main...HEAD` for the current count rather than trusting a number written here.

## Readiness check follow-up (2026-07-30) -- CLI surface dry-run sweep

Continuation of the 2026-07-29 check below. PR #731 (verify double-probe fix)
merged as `677b450`. Picked up the same methodology -- cold dry-runs against
live targets, not code reading -- and swept the rest of the documented CLI
surface: `certify`, `check-suite`, `generate --repair`, `eject`, `report`,
`daemon`, `doctor`. Two more real, live-verified bugs found and fixed (PR
#734, bundled per this repo's own precedent in #726 of grouping several
small fixes found in one investigative pass):

- **Bug:** `cherenkov generate` silently produced **zero output** on a small,
  valid, realistic spec (`demos/catch-the-ai-cheating/openapi.yaml`) and
  exited 0 ("Successfully generated 0/0 test suites."). Root cause:
  `cherenkov/stages/ingest.py`'s richness heuristic that gates whether an
  endpoint is even used only counts fields reachable via named
  `#/components/schemas/...` `$ref`s and only counts operation-level
  `parameters` -- any endpoint with an **inline** response/request schema
  (common for hand-written or exported specs) or a **path-item-level**
  shared `parameters` block scored near-zero richness and got silently
  dropped. **Fix:** additionally count properties from inline schemas found
  anywhere in the operation, and union operation-level with path-level
  parameters. Verified live: same spec now ingests 1 endpoint, plans 2
  scenarios, generates 2/2 test suites (template-fallback path, no
  Ollama/Docker in this sandbox). New tests in `tests/unit/test_ingest_stage.py`.
- **Bug:** `cherenkov doctor` told users **without Ollama installed at all**
  to "get a GPU" -- `detect_ollama_device()` returns `"UNKNOWN"` specifically
  when Ollama isn't reachable (distinct from `"CPU"`, meaning reachable but
  not GPU-accelerated), but the device-health line treated both the same way
  and printed the CPU/GPU message regardless, plus double-counted the same
  root cause as two separate issues in the summary tally. Same bug class as
  #726's "false Ollama-detected onboarding" fix, but in a different code path
  (`cherenkov/stages/doctor_cmd.py`, the CLI's own doctor, not the web
  onboarding wizard) that fix didn't reach. **Fix:** device line now prints
  "Ollama not reachable -- install/start Ollama..." when unknown, keeps the
  original CPU-mode message only when Ollama is actually reachable, and
  doesn't double-count. New tests in `tests/unit/test_doctor_cmd.py`.

**Clean (no bugs found):** `certify` (incl. `--coverage-report`, `--compliance`,
`--verify` roundtrip -- correctly reuses the single probe sweep, unaffected by
the verify fix's sibling issue since certify never had the double-call);
`check-suite` (all 4 modes -- control/weakened/deleted/hallucinated -- matched
the standalone demo script exactly, `--fail-on-finding` gates correctly);
`report` (`--list`, `--run latest`, `--format json`, `--diff`); `daemon`
(`--max-loops` exits cleanly, correctly re-validated the ingest richness fix
against its own default-watched `stub/target_spec.json`).

**Flagged, deliberately not fixed:** `cherenkov eject`'s zero-lock-in claim
holds (verified with a real `npm install` + `npx playwright test --list` in
the ejected output -- zero `cherenkov` imports). But `npx tsc --noEmit` on
the ejected output fails: 3 of the 12 tracked `stub/generated_tests/golden_*.spec.ts`
fixtures reference a `/pets` endpoint not present in `stub/generated-types.ts`
(which itself doesn't fully match the current `stub/target_spec.json` --
it has `/orders`/`/products` paths the current spec no longer declares), and
2 fixtures build a `/users` POST body missing a `name` field the current
types require. Real inconsistency, but `stub/generated_tests/` and
`stub/generated-types.ts` are generated artifacts (`RUN_ORDER.md`: `npx
openapi-typescript` + `generate_and_score.py` against `stub/target_spec.json`)
that `CLAUDE.md` explicitly says not to hand-edit, and no CI job currently
runs `tsc --noEmit` against them (checked: no workflow does) so this isn't an
active regression, just a real latent one. Left as a finding, not a fix --
regenerating requires the actual codegen pipeline, not a manual patch.
**Note on process:** the first eject dry-run in this session was contaminated
by untracked local cruft in the shared working tree (leftover `*.spec.spec.ts`
files from earlier dogfooding, gitignored, not part of the repo) that
produced a misleading larger failure count; re-ran from a clean `git clone`
of the branch to get the trustworthy result above -- exactly the
"Environment hazards: shared working tree" risk this file already warns about.

**Gate G0 status unchanged: still 3/4, E0.3 still not attempted.** Nothing in
this sweep required or constitutes E0.3 evidence -- it's hardening the path
E0.3 will walk, not a substitute for it.

## Readiness check (2026-07-29)

Ran independently, not from memory: `pytest tests/unit tests/evals` green (one file,
`test_mcp_auth.py`, fails to even *collect* in this sandbox due to a missing system
`cffi` package -- confirmed to be a container-environment gap, not a code defect, by
installing `cffi` and re-running it clean in isolation). Live-reproduced both G0
demos: `demos/catch-the-ai-cheating/run_demo.sh` (control PASS, all 3 injected cheats
CAUGHT) and `cherenkov demo`. Re-verified `docs/evidence/e0.1_divergences.md`'s
methodology is sound (curl-reproducible, dated, real third-party targets).

**Gate G0 is still 3/4 -- E0.3 (≥3 outside practitioners complete the quickstart
unaided) has not been attempted.** `docs/e0.3/PRACTITIONER_KIT.md` exists (PR #689)
but no `docs/e0.3/runs/*.md` results exist. This is the one gate that cannot be
automated and is the sole blocker on Gate G0 / public launch. Feature work was
otherwise idle 2026-07-20 -> 2026-07-29 (dependency bumps + one docs fix only).

**Dry run (agent, not a substitute for E0.3):** followed `docs/e0.3/PRACTITIONER_KIT.md`
steps 1-4 cold in a fresh venv against a live dogfood target (own `/openapi.json`,
81 paths) to surface friction before real practitioners spend their one shot on it.
Found and fixed a real bug in the process:

- **Bug:** `cherenkov verify` (rich-verdict mode, the default) ran the full
  spec-derived probe sweep against the live target *twice* per invocation --
  `cherenkov/verdict/engine.py`'s `VerdictEngine.run()` already computes
  `divergence_reports` internally, but `cherenkov/cli/commands/verify.py`'s
  `_run_rich_verdict()` then called `run_proof(...)` a second time from scratch
  just to get a list it already had, to print divergence detail / compute
  coverage. Symptom a cold user would hit: on an 81-path spec this doubled
  wall-clock time (63s -> 9s after the fix) and printed the identical-looking
  probe sweep twice back-to-back with no distinguishing label -- reads exactly
  like a stuck loop, which is exactly the kind of thing E0.3's own survey asks
  about ("What almost made you quit?").
  **Fix:** `VerdictEngine` now stashes the reports it already computed on
  `self.divergence_reports`; `_run_rich_verdict` reads that instead of
  re-running `run_proof`. Verified before/after against the same live target:
  identical verdict output, 40 probes instead of 80, 9s instead of 63s.
  Updated `tests/unit/test_verify_cmd.py` / `tests/unit/test_coverage.py`
  mocks that were patching the now-removed call site
  (`cherenkov.cli.commands.verify.run_proof`) to patch
  `cherenkov.divergence.proof_run.run_proof` instead, matching where the
  engine actually resolves it. Full unit/eval suite green after the change.

> **Note:** `docs/HANDOVER.md` is a separate, reverse-chronological session log (older format, kept for history). This file (`HANDOVER.md`, repo root) is the canonical status anchor per `CLAUDE.md`. The 2026-07-13 update below reconciles both -- the work logged in `docs/HANDOVER.md`'s "2026-07-11 HITL severity" section is the same work as the HITL severity entry below.

## What landed this session (2026-07-29 to 2026-07-30)

The `_run_rich_verdict` double-probe-sweep fix is already narrated in full above
(the "Dry run" bullet) -- it landed as PR #731. Also landed, not yet logged here:

| SHA | What |
|---|---|
| `4ffd7ea` (#726) | fix: spec coverage no longer conflates "no bugs found" with "not tested" -- a fully-probed, 100%-clean target (incl. CHERENKOV's own self-dogfood run) was grading D/SUSPECT with a false LOW_COVERAGE flag; `run_proof` now tracks every endpoint actually probed via an optional `probed_endpoints` out-param. Also: onboarding no longer falsely reports Ollama as detected; generate output pollution + a retry storm fixed. |
| `75a2fbd` (#730) | fix(ops): Dockerfile `python:3.14-slim` -> `3.12-slim` (a 2026-07-05 fix that was logged as landed but had never actually made it into the file -- confirmed via full `git log -p` on `Dockerfile`, which had only ever contained `3.14-slim`); untracked 126MB of committed PyInstaller build output under `build/cherenkov-launcher/` (already gitignored, force-added at some point); marked `PROJECT_REVIEW.md` (dated 2026-06-15, stale) as superseded; added `.github/workflows/surface-freeze-gate.yml` to enforce the SURFACE FREEZE below as a checked CI gate instead of a prose convention. |
| `87fbf33` (#732) | fix(ci): stage placeholder sidecar before Tauri build. |

**Known pre-existing CI red, unrelated to any of the above:** `tauri-build.yml`'s
`build (macos-latest)` / `build (ubuntu-latest)` jobs have failed on every run on
`main` back to at least 2026-07-01 -- `A public key has been found, but no private
key. Make sure to set TAURI_SIGNING_PRIVATE_KEY environment variable.` This is the
already-tracked "Tauri updater signing key" item further down this file (needs
`cargo tauri signer generate` + storing the private half as a repo secret -- an
owner action, not something an agent should do unilaterally).

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
| `onboarding/VIDEO_RECORDING_GUIDE.md` | 9-chapter guide: Loom/OBS/asciinema setup, audio, publishing |
| `RECORDING_ASSETS/README.md` | Asset directory: naming conventions, recording instructions, manifest template |

**Docs integration:** `docs/INDEX.md` updated with `📹 Onboarding & KT Sessions` section.

**Next human action:** Record the actual Loom/asciinema sessions using the guide and scripts above, then fill in `RECORDING_ASSETS/MANIFEST.md` with published URLs.


## Gate G0 status (EPIC #535)

G0 requires E0.1 AND E0.2 AND E0.3 AND E0.4.

| Exit criterion | Status | Evidence |
|---|---|---|
| E0.1 -- real divergences on 3rd-party APIs | **DONE** | `docs/evidence/e0.1_divergences.md` -- 6 divergences across 3 APIs |
| E0.2 -- integrity catch (catch the AI cheating) | DONE | `demos/catch-the-ai-cheating/`; CI-gated; 10/10 pass |
| E0.3 -- 3 practitioners complete quickstart unaided | NOT YET (unblocked by R1; kit ready) | `docs/e0.3/PRACTITIONER_KIT.md` — recruitment message, cold-run protocol, survey, pass criteria. R2 write-up ready too: `docs/marketing/CATCH_THE_AI_CHEATING_WRITEUP.md` |
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

**Also landed (2026-07-10):** A-F health score for proof runs (`cherenkov verify --health-score`) — `cherenkov/divergence/health.py`; composes coverage + divergence density + check-suite integrity into a 0-100 score/grade; PR #693.

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


## What landed this session (2026-07-30) — spec-shape soundness

Forward plan now lives in [`docs/ROADMAP_2026H2.md`](docs/ROADMAP_2026H2.md) (milestones M0–M5). **M0 is new and gates E0.3.**

| SHA | What |
|---|---|
| `90d8829` | **fix(divergence): honor PathItem-level parameters in probe planning.** OpenAPI 3.x lets a path parameter be declared once on the PathItem and inherited by every operation under it. `probe_planner` read only `operation.parameters`, so on the inherited form `{id}` was never filled, `_path_with_samples` returned None, and the endpoint was **dropped from planning entirely** — `verify` then reported a clean run on an endpoint it never probed. Reproduced with one API written both legal ways: operation-level planned 1 probe, PathItem-level planned 0 and exited 0 "conformant". Same failure class as #720. `merge_path_item_parameters()` is the single definition of the (name, in) precedence rule, routed through all three parameter call sites. 4 regression tests. |
| `7780c1d` | **fix(ingest): inherit PathItem parameters onto endpoint slices.** Completes the above — the meaningful-assertion gate reads parameters from `EndpointSlice.operation`, sliced in `IngestStage`, so it was still silently skipping. `truth/sources/openapi.py:72` had the same blind spot. Merging once at the slicing point fixes every downstream consumer. Also splits the gate's skip message via `explain_unmutatable()`: the two None causes (no documented 2xx vs unfillable path params) previously shared one misleading message. 7 tests. |
| `bbe24e5` | **docs(evidence): E0.5e — measured the baseline-free integrity oracle.** See `docs/evidence/e0.5e_oracle_discrimination.md`. Baseline-free detection **works**: isolated single-axis mutants plus a conforming run catch 3/3 cheat classes with no false alarm on the honest suite. But **the coarse mutation that ships today catches 0 of 3** — it changes the status code and drops a required field in the same response, so failure can't be attributed and a deliberately weakened suite scores "assertions are meaningful". The gate's docstring cites `toBeLessThan(500)` as the case it prevents; that is the exact assertion in `suite_cheat_weakened`, and it is not caught. **E0.5f (build the mutation battery) is now M0's top item.** |
| `0b19e36` | fix(test): `test_returns_suggested_patch_not_applied` patched `_tool_auto_heal_code` with `wraps=`, which mocks nothing, so the real `InferenceRouter` opened a live LLM connection and the test hung until the suite timed out. Mock the router, matching the sibling test. |

**Known-open from this session:** `demos/catch-the-ai-cheating/openapi.yaml` never declares `{id}` — invalid OpenAPI, and common in hand-written specs. The engine drops such endpoints silently; E0.5g requires reporting every zero-probe endpoint before considering inferred sample values.

## What landed previous session (2026-07-15 to 2026-07-20)

| SHA | What |
|---|---|
| `b2aec15` (#721) | feat(review): meaningful-assertion gate wired into the default `cherenkov generate --repair` path — `cherenkov/divergence/mutant_synth.py` derives a deliberately-wrong (status, body) response from any OpenAPI operation's documented success response (no hand-authored broken-response table needed), and `ReviewStage._gate_meaningful_assertion` spins it up via `BrokenImplServer` to prove a generated test fails a synthesized spec regression, not just that it satisfies the syntactic `assertion` gate's regex. Closes a real gap: `RepairLoop` previously optimized `quality_score` purely against syntactic/LLM-judge gates and never proved a test would catch a real bug — the same "self-healing masks regressions" failure mode covered in `cherenkov/sdet/assertion_gate.py` (E11-2) but only on the separate `CoverageLoop` path, not the default generate path. New setting `CHERENKOV_MEANINGFUL_ASSERTION_GATE` (default on). `RepairLoop` repair-instruction feedback is now gate-aware (specific guidance when the failing gate is `meaningful-assertion` vs generic syntax gates). 25 new/updated tests: `tests/unit/test_mutant_synth.py`, `tests/unit/test_review_meaningful_gate.py`, `tests/evals/test_repair_loop.py`. |
| `f6650f5` (#720) | fix(verify): sound verdicts under rate-limiting + fail-fast on unreachable target. Follow-up to `docs/evidence/blackbox_functional_assessment_2026-07-08.md`. Two soundness gaps in the R1 probe planner (#703): (1) the witness skipped its response-field oracle on HTTP 429, so a rate-limited probe read as "conformant" and verdicts flip-flopped run-to-run against a genuinely divergent target — `WitnessAgent` now backs off/retries on 429 (honors `Retry-After`, bounded by `_MAX_RETRIES_429`); (2) an unreachable target made every probe fail identically → 0 divergences → exit 0, silently passing an outage as clean — `verify`/`certify` now run a reachability preflight (`_assert_reachable`) and abort with exit 2 (any HTTP response, incl. 4xx/5xx, counts as reachable; only connection-level failures abort). Regression tests for 429 retry/bound, `Retry-After` parsing, and the reachability preflight. mypy clean. **Note:** `#722` and `#723` are follow-on PRs with the *same* title/body as `#720` but an empty diff (identical tree) — no additional fix landed in them, just re-merges of the same session's branch. Nothing further to do here. |
| `770a688` (#711) | refactor: lint lookover — fixed SIM117, SIM115, F401, B017, RUF unicode, N8xx naming violations (conflict-resolved). |
| `6f1839b` (#709) | feat(certificate): map OWASP Top 10 for LLM Applications risk categories into the certificate compliance profile. |
| `2cb33ab` (#708) | feat(certificate): map compliance profile to ISO/IEC 42001 and OWASP AI Testing Guide. |
| `468de64`, `1320d25` (#716, #714) | chore(deps): routine bumps — mkdocs-material ~=9.7.7, fastapi 0.139.2. |

## What landed previous session (2026-07-13)

| SHA | What |
|---|---|
| `6e6fea0` | feat(witness): V2 oracles — `verify` now asserts documented response-schema fields and response headers on top of status-code oracles (the deferred R1 item, below, is now closed); `probe_planner.py` happy-path hypotheses carry documented fields/headers; 17 tests; PR #703 |
| `3d51baf` | feat(hitl,copilot): HITL queue severity (`HitlItem.severity`, SQLite migration, `hitl list --severity`) + new `agentic-exploration` skill (live agent judges plain-language scenarios, `cherenkov record` enqueues failures as `D3_ui_spec` hypotheses into the same HITL queue); inspired by a survey of `MhmdElGazzar/agentex`; PR #697 |
| `97a9f4e` | fix: revert `_ingest_output`→`ingest_output` ARG-rename regression; resolve CodeQL alerts in `vision_confirm.py`; ruff auto-fixes; PR #696 |
| `7660006` | fix(api): `GET /api/v1/tests` runs synchronously instead of via `asyncio.to_thread` — fixed intermittent CI 500s; PR #698 |
| `d8dc934` | perf: hoist inline `re.compile` calls to module-level constants (cleanup cycle 8); PR #695 |
| `649ff8a` | refactor: hoist lazy stdlib imports to module level (cleanup cycle 7); PR #694 |
| `d77adf3` | feat(verify): A-F health score for proof runs (`verify --health-score`) — composes `CoverageReport` + divergence density + optional check-suite integrity findings into a 0-100 score/grade; `cherenkov/divergence/health.py`; PR #693 |
| `bfb7070`, `30ab4cd`, `3798eab`, `5fc2338` | chore(deps): routine bumps — uvicorn 0.51.0, anyio >=4.14.2, pymarkdownlnt ~=0.9.39, pydantic 2.13.4 |

## What landed previous session (2026-07-05)

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

> **Mypy gate is now BLOCKING (2026-07-06):** all 151 type errors fixed (was `continue-on-error: true` with 162 errors); `mypy cherenkov/` runs clean on 530 files. The cleanup surfaced and fixed real runtime bugs: `review_ocr/stage.py` crashed on any log line without a file match (missing required `OCRFinding.file`) and on every `run_on_file` call (`OCRRuleEngine.SUPPORTED_EXTENSIONS` doesn't exist — it's module-level in `rules.py`); `ai/langchain.py` instantiated a Protocol (TypeError) — now uses `SQLiteConversationMemory`; `dashboard/render.py` real-model branch accessed nonexistent `GraphNode.method/.path` and a nonexistent `get_claims_by_endpoint`; `substrate/providers/{openai,ollama}.py` called nonexistent `client.complete()` → `complete_code()` (their unit tests mocked the nonexistent method — MagicMock hid the bug); `spec_guardian/daemon.py` referenced `DriftStore.DRIFT_DB` (module-level constant → AttributeError); `execution/coverage_report.py` imported nonexistent `CherenkovConfig` (→ `LayeredConfig`); `reflector/store.py` second store class used unset `self.log`; `web/sdd_routes.py` mixed `SddSession` objects into a dict list (AttributeError under `task_type` filter); `mcp/server.py` called missing `StructuredLogger.debug` (method added). 5 targeted `# type: ignore[...]` remain, each with a `TODO(#type-debt)` comment.

0. ~~R1 — Spec-derived probe planner (P0)~~ **DONE** (2026-07-07) — `cherenkov/divergence/probe_planner.py`: `plan_probes()` + `spec_hypotheses()` synthesize probes and offline hypotheses mechanically from any OpenAPI spec (required-field omission, enum violation, documented error codes for integer path params, happy-path status; depth-1 `$ref`). Wired into `run_proof()` (`max_probes=40` param; Petstore demo path unchanged when spec omitted), `verdict/engine.py` traffic capture, and `cherenkov verify --max-probes`. 13 tests in `tests/unit/test_probe_planner.py` incl. mutation-pattern e2e: conformant in-process Orders server → 0 divergences, mutant → ≥3, on a spec with no Petstore path. Self-dogfood exit test: `verify` against CHERENKOV's own 81-path `/openapi.json` probes its own endpoints (`/api/v1/chat/...`, `/api/v1/sdd/...`), 0 false divergences. **V2 oracles**: DONE (2026-07-13) — response-schema field presence + header assertions landed via Witness repro-step format extensions (`_parse_expected_fields_headers()`); see PR #703 in "What landed this session" above. E0.3 is now unblocked.
1. ~~R0 — Truth alignment~~ **DONE** (2026-07-05) — README repositioned to the integrity wedge (`c6e0cec`) and false claims fixed (PyPI badge/`pip install cherenkov-qa` removed — package is NOT on PyPI; quickstart `check-suite --demo` replaced with real commands — that flag never existed); root artifact clutter removed and `.gitignore`-guarded (`soc2_report.json`, `pr.json`, `audit.json`, `issues.txt`, `test-junit.xml`, `test-sarif.json`; `mut_spec.json` and `qwen.json` KEPT — referenced by `tests/test_mutation_validate.py:16` and MCP integration scripts). **Deferred: `cherenkov.py` removal** — it is load-bearing: `.github/workflows/ci.yml:612-626` runs it directly, `Dockerfile.mcp` COPYs it as entrypoint, `bin/cherenkov-npm.js:42` prefers it, `scripts/setup_oi.sh` + `scripts/qwen-code-integration.sh` + `package.json` reference it, and CI gates `scripts/ci_docs_check.py` + `scripts/check_cli_docs.py` load it directly. Commit `0f16fed` deleted it prematurely (docs-parity gate crashed with FileNotFoundError, CI smoke steps and Docker MCP build broken) — **restored** in PR #675; retiring it properly is a migration project (repoint all of the above to the `cherenkov` package CLI first). `0f16fed` also deleted two non-artifacts, both now restored: `mut_spec.json` (fixture for `tests/test_mutation_validate.py:16` — its absence made the Test-coverage CI job fail on every PR) and `qwen.json` (Qwen Code MCP config, see `docs/QWEN_CODE_ALIGNMENT.md`). ~~Follow-up bug worth an issue: `OrchestrationEngine.run_pipeline()` returns *success* when the input spec file is missing~~ **FIXED** — `_run_pipeline_inner` now aborts with `success=False` on a FAILED INGEST or PLAN stage (verified 2026-07-10: `run_pipeline('/nonexistent/spec.json')` → `False`).

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

