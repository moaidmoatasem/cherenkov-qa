# CHERENKOV — Parallel Agent Execution Plan

> **Read FIRST:** `docs/HANDOVER_SESSION_2026-06-18.md` (just written), then `AGENTS.md`, then `docs/STATUS.md`.
> **Gate discipline:** No work beyond G0 until E0.1 and E0.3 pass. See `docs/EXECUTION_PLAN.md` §3.

---

## Active EPICs (GitHub Issues #535-#538)

| EPIC | Title | Status | Blocks |
|------|-------|--------|--------|
| #535 | Gate G0 (prove the wow) | **ACTIVE** | Blocks #536, #537, #538 |
| #536 | Rung 1 (the Tool) | PENDING | Blocked by #535 |
| #537 | Rung 2 (Platform) | PENDING | Blocked by #536 |
| #538 | Rung 3 (Protocol/Authority) | PENDING | Blocked by #537 |

---

## Parallel Agent Work Plan

### Agent 1: GATE G0 — E0.1 Real Divergence Proof (HIGHEST PRIORITY)

**Goal:** Run CHERENKOV against ≥3 third-party APIs, capture ≥2 genuine spec↔implementation divergences with reproducible evidence.

**Steps:**
1. Commit the uncommitted changes on feature branch (`mcp/handlers.py`, `web/api.py`) and create PR to main
2. Download OpenAPI specs for 3 target APIs:
   - **RealWorld/Conduit API** (multiple independent implementations — spec drift guaranteed)
   - **Gitea** (mature, Docker-runnable, spec maintained alongside Go handlers)
   - **Gotify** or **Swagger Petstore** (Docker-runnable, positive control)
3. Run `cherenkov validate --spec <spec> --target <url>` against each
4. For each divergence found, create evidence file in `docs/evidence/` with:
   - The claim (spec says X)
   - The reality (server returns Y)
   - curl reproduction command
   - Screenshot/asciinema
5. Run Schemathesis on same targets, document what CHERENKOV found that Schemathesis didn't
6. Update `docs/evidence/` with head-to-head comparison
7. Update EPIC #535 with E0.1 evidence

**Auto-skip if:** No network access, no Docker, or Ollama unavailable. In that case, use the Petstore stub evidence already in `stub/` and document limitation.

**Docs to read:** `docs/EXECUTION_PLAN.md` §3, `docs/ROADMAP_AQE.md` E0.1, `docs/proof_run/PROOF_RUN.md`

---

### Agent 2: TECHNICAL DEBT — api.py Route Split (P1)

**Goal:** Split `cherenkov/web/api.py` (1297 lines, 38 routes) into 5-6 focused modules.

**Plan (documented in `docs/AGENT_HANDOVER_2026-06-18b.md`):**
1. Create `cherenkov/web/routes/` directory
2. Extract routes by domain:
   - `knowledge_routes.py` — `/api/v1/knowledge/*`
   - `hitl_routes.py` — `/api/v1/hitl/*`
   - `chat_routes.py` — `/api/v1/chat/*`
   - `validate_routes.py` — `/api/v1/validate/*`, `/api/v1/eject/*`
   - `run_routes.py` — `/api/v1/run/*`
   - `settings_routes.py` — `/api/v1/settings/*`
   - `health_routes.py` — `/healthz`, `/metrics`
3. Keep `api.py` as the FastAPI app factory that includes all routers
4. Move `verify_api_key`, `_validate_spec_url`, `_validate_output_path` to a shared `security.py` module
5. Run `python -m pytest tests/ -q --tb=short` after each extraction
6. Run `python -m ruff check cherenkov/ --fix` after all extractions
7. Commit on a feature branch, open PR

**DO NOT:** Change any route behavior, add features, or modify the security middleware during the split.

**Docs to read:** `docs/AGENT_HANDOVER_2026-06-18b.md` (has detailed split plan), `docs/ARCHITECTURE_MAP.md`

---

### Agent 3: TECHNICAL DEBT — Ruff Fix + Silent Exception Audit (P5 + P4)

**Goal:** Fix the 2 ruff F541 errors, then audit the 31 files that catch `Exception` and pass silently.

**Steps:**
1. `python3 -m ruff check cherenkov/ --fix` — fixes F541 automatically
2. Audit all files with `except Exception: pass` or `except Exception as e: logging.debug(e)`:
   - `grep -rn "except Exception" cherenkov/` to find all 31+ instances
   - For each, determine if the swallow is intentional (expected network timeout where retry is higher) or a bug (silently ignoring a real error)
   - Add `# noqa: E722` with a comment explaining WHY the swallow is safe for intentional ones
   - For bugs, add proper error handling (log at WARNING level, or re-raise)
3. Run tests after each batch of fixes
4. Commit on feature branch

**Docs to read:** `docs/engineering/BEST_PRACTICES.md`, `docs/ERROR_HANDLING.md`

---

### Agent 4: SECURITY REVIEW — SSRF Follow-up

**Goal:** Apply the 3 security fixes identified in the code review across all Claude sessions.

**The 3 issues from the security review:**
1. **CRITICAL:** `api.py` `_validate_spec_url` has a DNS rebinding TOCTOU — hostname resolved at validation time but `requests.get` does a second DNS lookup. Fix: pass the resolved IP directly to requests via a custom transport adapter or use the resolved IP in the URL with Host header override.
2. **CRITICAL:** `_validate_output_path` uses `startswith()` which allows path traversal for sibling directories with common prefixes. Fix: `resolved.startswith(allowed_base + os.sep) or resolved == allowed_base`.
3. **HIGH:** `mcp/handlers.py` `_tool_registry_publish` doesn't validate that the URL host isn't a private IP — the same SSRF blocklist from `_validate_spec_url` should be applied here.

**Note:** Some of these were attempted in previous sessions but need verification. Check `git log` for existing fix attempts before starting.

**Docs to read:** `docs/SECURITY.md` (wiki), the security review in each agent handover

---

### Agent 5: DOCS CLEANUP — Eliminate Redundancy & Fabrication Warnings

**Goal:** Clean up the docs tree by removing redundancy, archiving deprecated docs, and adding clear SOUPçon warnings where needed.

**Steps:**
1. Archive these DEPRECATED files to `docs/_archive/` (keep them but move out of main flow):
   - `docs/INTEGRATION_HANDOVER_REPORT.md` (FABRICATED banner already present)
   - `docs/ROADMAP_RECONCILIATION.md` (DISPUTED)
   - `docs/ROADMAP_NEXT.md` (SUPERSEDED by PHASE_PLAN.md)
   - `docs/DEFERRED_VISION_ARCHIVE.md` (already archived)
2. Add a clear "SUPERSEDED — see PHASE_PLAN.md" redirect header to each
3. Consolidate overlapping FE dashboard docs:
   - Merge `FE_DASHBOARD_REGRESSION.md` into `FE_DASHBOARD_FULL_REGRESSION_TEST_SUITE.md`
   - Delete `FE_DASHBOARD_PARITY_AUDIT.md` (track-b-c-deferred was already re-integrated and deleted)
4. Remove `QA_AI_LANDSCAPE_2026.md` (v2_UPDATED supersedes it)
5. Remove duplicate handover docs: keep only `HANDOVER.md` + this new consolidated handover
6. Update `INDEX.md` to reflect all changes
7. Commit on a feature branch

**DO NOT:** Delete any handover docs — just add clear headers. Historical audit trails matter.

---

### Agent 6: E0.3 PREP — Quickstart Hardening

**Goal:** Prepare the quickstart for external practitioner validation (E0.3). This is NOT running E0.3 (which needs real people), it's making sure the quickstart works on a clean machine.

**Steps:**
1. On a fresh VM or Docker container (no CHERENKOV installed), follow `docs/GETTING_STARTED.md` exactly
2. Time each step and document where friction occurs
3. Verify `./bin/cherenkov doctor` reports all dependencies
4. Verify `./bin/cherenkov self-test` passes
5. Verify `./bin/cherenkov validate --spec petstore.yaml --target http://localhost:8000` works end-to-end
6. Fix any issues found (missing deps, unclear instructions, broken paths)
7. Create a `QUICKSTART_TEST_REPORT.md` in `docs/evidence/` documenting:
   - Time to first green test
   - Every friction point
   - Every error encountered
   - What was unclear in the docs
8. If possible, create a one-line install script: `curl -fsSL https://cherenkov.dev/install.sh | bash`

**Docs to read:** `docs/GETTING_STARTED.md`, `docs/CLI_DEMO.md`, `docs/TESTING.md`

---

## Execution Order

```
Agent 1 (E0.1)  ████████████████████████████  (CRITICAL PATH — unblocks everything)
Agent 4 (Security) █████████████████         (can run in parallel with Agent 1)
Agent 2 (api.py split) ███████████████████   (can run after Agent 4 is done)
Agent 3 (Ruff + exceptions) ██████████       (can run in parallel with Agent 2)
Agent 5 (Docs cleanup) ██████████             (can run any time, no code changes)
Agent 6 (E0.3 prep) ██████████                (can run after Agent 1 commits uncommitted changes)
```

**Critical path:** Agent 1 (E0.1) → Agent 6 (E0.3 prep) → Real E0.3 (human QA practitioners) → G0 passes → Agents 2-5 can continue in parallel.

---

## Agent Rules (from AGENTS.md)

1. **SSOT is `docs/`.** No "v3.1 + delta" — it doesn't exist.
2. **Show RAW EVIDENCE.** Claims are not evidence. Terminal output, git log, test results.
3. **D7 invariant.** Never auto-edit test code. Healing is suggest-only.
4. **Anti-lock-in.** `eject` must produce standalone Playwright with zero CHERENKOV imports.
5. **Spec-derived.** Expected HTTP status comes from the OpenAPI spec, not hardcoded.
6. **Work on feature branches.** Reference an issue.
7. **Get human review before merging to `main`.**
8. **Concurrent agent hazard.** Always check `git diff --stat HEAD` before assuming changes persist. Stage + commit immediately after each edit.
9. **Ruff must pass.** `python3 -m ruff check cherenkov/` must show 0 errors before push.