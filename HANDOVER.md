# CHERENKOV -- Session Handover

**Date:** 2026-06-18
**HEAD:** 
**Branch:**  -- fully pushed to 
**Tests:** 691 unit tests, 0 failures

---

## What was done this session

Merged  into . All security hardening + runtime fixes are now on .

### Fixes committed

| File | Fix |
|------|-----|
|  | makedirs guard in _connect() -- prevents OperationalError on fresh checkout |
|  | FTS5 JOIN on rowid not UNINDEXED item_id -- fixes full-table-scan in search() |
|  | dataclasses.asdict() on KnowledgeItem objects -- fixes JSON serialization |
|  | chat_stream wraps _call_llm with asyncio.to_thread -- stops blocking event loop |
|  | Rate limiter: evict idle IPs -- prevents unbounded memory growth |
|  | Remove /metrics /truth-map /failures from public _CACHEABLE_PATHS |
|  | Add public HitlQueue.ignore() method |
|  | classify endpoint uses queue.ignore() not queue._resolve() |
|  | _validate_spec_url: socket.getaddrinfo DNS-rebinding SSRF fix |

---

## Remaining known issues (ordered by impact)

### High

1. **Desktop/Tauri config** ()
   -  missing  -- app panics on launch
   -  is empty -- auto-update non-functional
   -  missing  and 
   - Needs: signing key generation (terminal op) + config edits

2. **CSP unsafe-inline/unsafe-eval** ()
   - React dashboard requires them today; fix needs Vite nonce-based CSP build config

### Medium (self-contained code fixes -- each is <10 lines)

3. ** has no auth guard**
   - File: 
   - Fix: add  parameter to 
   - Import:  (or use  from  helpers)

4. ** blocks the async event loop**
   - File: , inside 
   - Fix:  -- but function is sync, so wrap the call at the call site or make a separate async validator

5. **FTS5 rowid triggers not retroactive on existing DBs**
   - Existing deployed DBs need: 
   - Add a migration note in  or run in  as a safe no-op

6. ** sync  method blocks** -- only affects callers that are async; low risk today

---

## Environment state

- **main HEAD:**  pushed to 
- **:** merged; remote branch still exists -- delete: 
- **Stash:** 19 stash entries on old branches -- safe to ignore (all pre-date this work)
- **Scratch file:**  -- delete: 

---

## Next agent: priority order

1. ........................................................................ [ 10%]
........................................................................ [ 20%]
........................................................................ [ 31%]
........................................................................ [ 41%]
........................................................................ [ 52%]
........................................................................ [ 62%]
........................................................................ [ 72%]
........................................................................ [ 83%]
........................................................................ [ 93%]
...........................................                              [100%] -- confirm 691 pass, 0 fail
2. Add auth to  (item 3 above) -- commit + push
3. Make  non-blocking (item 4 above) -- commit + push
4. Delete stale remote branch: 
5. Clean scratch file: 
