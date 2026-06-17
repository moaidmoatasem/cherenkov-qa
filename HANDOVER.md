# CHERENKOV — Session Handover

**Date:** 2026-06-18
**HEAD:** `d5fda086`
**Branch:** `main` — fully pushed to `origin/main`
**Tests:** 691 unit tests, 0 failures

---

## What was done this session

Merged `fix/playwright-qa-18-failures` into `main`. All security hardening + runtime fixes are now on `main` at `d5fda086`.

### Fixes committed

| File | Fix |
|------|-----|
| `cherenkov/knowledge/adapters/sqlite_repository.py` | makedirs guard in `_connect()` — prevents OperationalError on fresh checkout with no `data/` dir |
| `cherenkov/knowledge/adapters/sqlite_repository.py` | FTS5 JOIN on `rowid` not `UNINDEXED item_id` — fixes full-table-scan in `search()` |
| `cherenkov/knowledge/api/routes.py` | `dataclasses.asdict()` on `KnowledgeItem` objects — fixes JSON serialization of query results |
| `cherenkov/chat/agent.py` | `chat_stream` wraps `_call_llm` with `await asyncio.to_thread(...)` — stops blocking the event loop |
| `cherenkov/web/middleware/security.py` | Rate limiter: evict idle IPs from `_requests` dict — prevents unbounded memory growth |
| `cherenkov/web/middleware/security.py` | Remove `/metrics` `/truth-map` `/failures` from public `_CACHEABLE_PATHS` |
| `cherenkov/hitl/store.py` | Add public `HitlQueue.ignore()` method |
| `cherenkov/web/api.py` | `classify` endpoint uses `queue.ignore()` instead of private `queue._resolve()` |
| `cherenkov/web/api.py` | `_validate_spec_url`: `socket.getaddrinfo` DNS-rebinding SSRF fix |

---

## Remaining known issues (ordered by impact)

### High

1. **Desktop/Tauri config** (`desktop/src-tauri/tauri.conf.json`)
   - `bundle.externalBin` missing `"cherenkov-launcher"` — app panics on launch
   - `plugins.updater.pubkey` is empty — auto-update non-functional
   - `capabilities/main.json` missing `"fs:default"` and `"http:default"`
   - Needs: signing key generation (terminal op) + config edits

2. **CSP `unsafe-inline`/`unsafe-eval`** (`cherenkov/web/middleware/security.py:73-74`)
   - React dashboard requires them today; fix needs Vite nonce-based CSP build config

### Medium (each is < 10 lines)

3. **`/api/v1/knowledge/query` has no auth guard**
   - File: `cherenkov/knowledge/api/routes.py`
   - Fix: add `_auth=Depends(verify_api_key)` to `get_knowledge()` signature
   - Import `verify_api_key` from `cherenkov.web.sdd_auth` or define alongside existing auth helpers

4. **`_validate_spec_url` blocks the async event loop**
   - File: `cherenkov/web/api.py` — `_validate_spec_url` calls `_socket.getaddrinfo` synchronously
   - Fix: make an async wrapper or call it via `await asyncio.to_thread(_socket.getaddrinfo, host, None)` at the call site

5. **FTS5 rowid triggers not retroactive on existing DBs**
   - Existing deployed DBs need: `INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')`
   - Add to `_init_db()` as a safe idempotent migration or document in `docs/MIGRATIONS.md`

6. **`chat/agent.py` sync `chat()` method** — still calls `_call_llm` blocking; low risk today (only called from sync handlers)

---

## Environment state

- **main HEAD:** `d5fda086` pushed to `origin/main`
- **`fix/playwright-qa-18-failures`:** merged; remote still exists — delete: `git push origin --delete fix/playwright-qa-18-failures`
- **Stash:** 19 stash entries on old branches — safe to ignore
- **Scratch file:** `/home/moaid/fix_ssrf.py` — delete: `rm ~/fix_ssrf.py`

---

## Next agent: priority order

1. `python3 -m pytest tests/unit/ -q` — confirm 691 pass, 0 fail
2. Add auth guard to `/api/v1/knowledge/query` (issue 3 above) — commit + push
3. Make `_validate_spec_url` non-blocking (issue 4 above) — commit + push
4. `git push origin --delete fix/playwright-qa-18-failures` — clean up stale remote branch
5. `rm ~/fix_ssrf.py` — clean up scratch file from home dir
