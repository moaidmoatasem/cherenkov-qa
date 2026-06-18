# Agent Handover — CHERENKOV QA
**Date:** 2026-06-18 | **HEAD:** `837e19c4` | **Branch:** `main` = `origin/main`

---

## Current State

| Item | Value |
|---|---|
| HEAD | `837e19c4` (fix(api): auth guard on knowledge endpoint + async DNS validator) |
| `origin/main` | `837e19c4` — identical, fully pushed |
| Python tests | 100% passing (all dots, exit 0, confirmed multiple times today) |
| Lint (`ruff`) | 0 issues across entire `cherenkov/` package |
| Working tree | Clean — no uncommitted changes, no untracked files |
| Remote branches | `fix/playwright-qa-18-failures` deleted (merged via PR #543) |

---

## What Was Done This Session (2026-06-18)

### PR #543 — merged to main
All commits below are on `main`:

| Commit | Change |
|---|---|
| `bb2421ff` | fix(qa): resolve 18 Playwright test failures (selector ordering, a11y nav, timeouts, font-load noise) |
| `3db84d3d` | refactor(review): TSC timeout from settings; log swallowed exceptions |
| `3142ec13` | fix: runtime correctness — chat LLM call via `asyncio.to_thread`; knowledge serialization; rate-limiter memory bound |
| `e420903e` | feat(hitl): `HitlQueue.ignore()` public method |
| `f1027ea9` | fix(security): DNS-rebinding SSRF fix — `socket.getaddrinfo` hostname resolution |
| `934f9fbc` | fix(visual): skip redundant comparison pass after fresh baseline init |
| `837e19c4` | fix(api): auth guard on `/api/v1/knowledge/query`; `_validate_spec_url` made async + wrapped in `asyncio.to_thread` |

---

## Known Remaining Issues (ordered by impact)

### High

1. **Desktop/Tauri config** — app panics on launch
   - `tauri.conf.json` missing `bundle.identifier`
   - `updater` config empty — auto-update non-functional
   - Missing `allowlist` and `build.distDir`
   - Needs: signing key generation + config edits

2. **CSP `unsafe-inline`/`unsafe-eval`** — React dashboard requires them today
   - Fix: Vite nonce-based CSP build config

### Medium (each ≤10 lines)

3. **FTS5 rowid triggers not retroactive on existing DBs**
   - Existing deployed DBs need: `INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')`
   - Add a migration note in `cherenkov/knowledge/sqlite_repository.py` `_connect()` or run as a safe no-op

4. **`SpecGuardian.watch()` sync method blocks if called from async context**
   - Low risk today (CLI only), but worth wrapping in `asyncio.to_thread` if HITL ever calls it

---

## Active EPIC: Gate G0 (#535) — nothing to build until gate passes

Exit checklist (all 4 must be ✅ before any Rung 1 work):
- [ ] **E0.1** — ≥2 genuine divergences caught on ≥3 third-party APIs (reproductions required)
- [ ] **E0.2** — CHERENKOV catches an AI-generated suite weakening/hallucinating an assertion
- [ ] **E0.3** — ≥3 practitioners complete quickstart unaided and rate it useful
- [ ] **E0.4** — one defensible differentiation sentence vs Schemathesis/property-based tools

First buildable artifact: `docs/demos/CATCH_THE_AI_CHEATING.md` (E0.2 evidence).

---

## Next Agent: Priority Order

1. **Run `pytest tests/ --ignore=tests/test_legacy_visual.py -q`** — confirm still green
2. **Gate G0 E0.2 demo** — make `docs/demos/CATCH_THE_AI_CHEATING.md` runnable end-to-end
3. **FTS5 migration note** (item 3 above) — small, self-contained
4. **Tauri config** (item 1 above) — needs signing key, coordinate with user
