# CHERENKOV — Session Handover 2026-06-18 (Consolidated)

> **Audience:** Incoming parallel agents. Read this FIRST, then AGENTS.md, then STATUS.md.
> **SSOT:** docs/ (v3.1 + delta is FABRICATED — there is no such version). If cited, stop and re-read docs/.

---

## 1. Current State (git HEAD `7d2d79d0` on `origin/main`)

| Metric | Value |
|--------|-------|
| Branch | `main` (feature branch `claude/qa-automation-ai-strategy-g0a06l` has uncommitted changes — see §6) |
| Tests | 861 passing, 4 skipped (confirmed across 3 runs) |
| Lint | 2 fixable errors (F541 f-string-missing-placeholders) |
| Working tree | 3 modified: `mcp/handlers.py`, `web/api.py`, deleted baseline snapshot |

### What landed this session (across all Claude threads)

1. **18 Playwright QA test failures fixed** (259/259 green)
2. **DNS-rebinding SSRF fix** in `web/api.py` — hostname resolved to IP, private ranges rejected
3. **HITL `ignore()` method** added to `hitl/store.py`; `web/api.py` classify endpoint uses it
4. **asyncio correctness** — `chat/agent.py` offloads `respond()` blocking call to `asyncio.to_thread`
5. **Knowledge API serialization** — KnowledgeItem dataclass → plain dict before JSON
6. **Rate-limiter memory leak** — stale IP eviction from `RateLimitMiddleware._requests`
7. **Ruff F823** — duplicate local import in `review.py` removed
8. **CSP tightening** — removed `unsafe-eval` + `unsafe-inline` from `script-src`
9. **FTS5 retroactive rebuild** — existing DBs get shadow table populated on init
10. **CLI migration to Click** — all 23 commands ported (3-step incremental merge)
11. **Gate G0 E0.2** — TypeScript/Playwright integrity checker + Python demo (`demos/catch-the-ai-cheating/run_demo.py`)
12. **Gate G0 E0.4** — differentiation statement added to `NORTH_STAR.md` §8
13. **CI gate-g0 job** — added to `.github/workflows/cherenkov-ci.yml`
14. **QA AI Intelligence Report** — `docs/QA_AI_INTELLIGENCE_REPORT_2026.md`
15. **QA Automation AI Strategy** — `docs/QA_AUTOMATION_AI_STRATEGY.md`
16. **MeaningfulAssertionGate** — `cherenkov/review/gates/meaningful_assertion.py`
17. **verify_suite MCP tool** — `cherenkov/mcp/handlers.py` (verify_suite + verify_system)
18. **Tauri desktop config** — `externalBin`, `shell:allow-spawn/kill`, `fs:default`, `http:default`

---

## 2. Gate G0 Status (EPIC #535 — ACTIVE)

| Gate | Evidence | Status |
|------|----------|--------|
| **E0.1** — Real divergences on ≥2/3 third-party APIs | `stub/generated_tests/` (Petstore); needs live run against external API | **Needs live execution** |
| **E0.2** — Catch a real agent-cheat, reproducible | `demos/catch-the-ai-cheating/run_demo.py` + TypeScript checker | **DONE** |
| **E0.3** — ≥3 practitioners complete quickstart | Needs real user testing | **NEEDS PEOPLE** |
| **E0.4** — Honest differentiation sentence vs Schemathesis | `NORTH_STAR.md` §8 | **DONE** |

**G0 is blocked on E0.1 (code execution) and E0.3 (user research).**

---

## 3. Open GitHub Issues

| # | Title | Priority |
|---|-------|----------|
| **#535** | EPIC: Phase 0 — Gate G0 (prove the wow + catch an agent-cheat) [ACTIVE] | P0 |
| **#536** | EPIC: Rung 1 — the Tool people love | P1 (post-G0) |
| **#537** | EPIC: Rung 2 — Platform (Reality Engine + MCP) | P2 (post-Rung 1) |
| **#538** | EPIC: Rung 3 — Protocol/Authority (Certificate) | P3 (post-Rung 2) |

---

## 4. Uncommitted Changes (feature branch)

The branch `claude/qa-automation-ai-strategy-g0a06l` has 3 modified files:
- `cherenkov/mcp/handlers.py` (+22 lines) — verify_suite/verify_system MCP tools (E2.1)
- `cherenkov/web/api.py` (+88/-28 lines) — DNS-rebinding SSRF fix + knowledge auth guard
- Deleted `baseline-ui-linux.png` — visual regression baseline update

These should be committed and PR'd to main.

---

## 5. Known Technical Debt (P1-P4 Queue)

| Priority | Item | Detail |
|----------|------|--------|
| **P1** | `api.py` route splitting | 1297 lines, 38 routes — split into 5-6 modules (plan documented in AGENT_HANDOVER_2026-06-18b) |
| **P2** | AI provider registry | OpenAI/Anthropic/LM Studio providers need a registry pattern instead of if/elif chains |
| **P3** | `legacy_cli.py` cleanup | Post-Click-migration, the legacy wrapper should be removed after E2E smoke |
| **P4** | Silent exception swallows | 31 files catch `Exception` and pass; needs systematic audit |
| **P5** | Ruff F541 | 2 f-string with missing placeholders — trivial `--fix` |

---

## 6. Recurring Operational Hazards

1. **Concurrent agents** — multiple Claude/Cursor agents working the same tree cause `.git/index.lock` and revert races. Mitigation: `git add` + `git commit` immediately after each edit. Check `git diff --stat HEAD` before assuming prior changes persist.
2. **Settings lock race** — concurrent agents keep removing `_settings_lock` from `settings.py`. If ruff E402 appears, re-add `import threading as _threading` at line 2 and the lock in `get_settings()`.
3. **`verify_api_key` reverted to `==`** — concurrent agents flip this back to unsafe comparison. Re-apply `hmac.compare_digest` each session.
4. **`gh` auth expires mid-session** — re-auth with `gh auth login -h github.com`.
5. **CRLF warnings** — phantom `git status -M` on Windows. Check `git diff --stat HEAD` for real changes.

---

## 7. Blocking Dependencies

| Blocker | Phase | How to unblock |
|---------|-------|----------------|
| `libwebkit2gtk-4.1-dev` + `pkg-config` | Phase 3 (Desktop) | `sudo apt install -y libwebkit2gtk-4.1-dev pkg-config` in WSL |
| Physical ADB device / Android emulator | Phase 5-6 (Mobile) | `sudo apt install -y android-tools-adb` + physical device |
| Tauri signing key | Phase 3 (Desktop builds) | `cargo tauri signer generate -w ~/.tauri/cherenkov.key` |

---

## 8. Alignment with Docs (SSOT)

All work MUST align with:

| Document | Role | Key Point |
|----------|------|-----------|
| `AGENTS.md` | Operating rules | D7 invariant, anti-lock-in, suggest-only, spec-derived |
| `docs/STATUS.md` | Canonical state | All phases -1→8 complete or env-ready |
| `docs/HANDOVER.md` | What's real | Anti-drift rules, track status, next steps |
| `docs/PHASE_PLAN.md` | Consolidated plan | ~105 issues (#277-#391), all tracked |
| `docs/EXECUTION_PLAN.md` | Premortem + gate discipline | G0 blocks everything; Schemathesis differentiation |
| `docs/NORTH_STAR.md` | 10-year vision | Trust layer for agentic era |
| `docs/ROADMAP_AQE.md` | Gated future-work | G0 → Rung 1 → Rung 2 → Rung 3 |

**DEPRECATED (do NOT cite):**
- `docs/INTEGRATION_HANDOVER_REPORT.md` — FABRICATED
- `docs/ROADMAP_RECONCILIATION.md` — disputed
- `docs/DEFERRED_VISION_ARCHIVE.md` — archived
- `docs/vision/README.md` — warns "DO NOT CITE AS CURRENT"