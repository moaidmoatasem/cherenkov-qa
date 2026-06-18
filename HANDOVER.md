# CHERENKOV -- Session Handover

**Date:** 2026-06-18
**HEAD:** `6ef541fb` on `main` -- synced with `origin/main`
**Tests:** all unit tests passing (clean exit)
**Branch:** `main` -- no open fix branches, tree clean (generated-test CRLF noise is cosmetic)

---

## What landed this session

All security/reliability hardening is on `origin/main`. Key commits (newest first):

| SHA | What |
|---|---|
| `6ef541fb` | Merge origin/main (CLI Click port) |
| `0bbb0d00` | feat(cli): diff/report/eject/self-test/completion/init/doctor ported to Click |
| `323f0805` | feat(g0): "Catch the AI cheating" integrity demo (EPIC #535 / E0.2) |
| `837e19c4` | fix(api): auth on /knowledge/query + `_validate_spec_url` made async (DNS-rebinding) |
| `d5fda086` | merge: QA-18 fix + security hardening + HITL ignore |

Security fixes confirmed on `origin/main`:
- `settings.py` -- 4 configurable timeout env-vars
- `ollama_client.py` -- None-guard before `raise last_err`
- `playwright_invoke.py` -- subprocess timeouts; shlex.quote WSL cmd parts
- `prism_mock.py` -- Docker start/stop timeouts; FileNotFoundError explicit
- `mcp/handlers.py` -- URL scheme check in `_tool_registry_publish`
- `api.py` -- eject auth; SSRF blocklist (is_reserved + GCP metadata); settings protection
- `review.py` -- TSC timeout from settings; two silent-swallow exceptions now log
- `.gitignore` -- secrets section; `requirements.txt` -- dep upper bounds

---

## Remaining work (ordered by impact)

### 1. Gate G0 -- EPIC #535 (ACTIVE BLOCKER)
Gate G0 must pass before any Track B/C features ship. Demo is committed at `demos/catch-the-ai-cheating/`. Next: run the gate evaluation and record the result.
- Spec: `docs/ROADMAP_AQE.md`, `docs/NORTH_STAR.md`
- Issues: #535 (G0), #536-538 (subsequent gates)

### 2. Tauri updater signing key (requires terminal with Tauri toolchain)
`desktop/src-tauri/tauri.conf.json` has `"pubkey": ""` -- auto-update silently fails.
```bash
cargo tauri signer generate -w ~/.tauri/cherenkov.key
# Copy the public key output into tauri.conf.json plugins.updater.pubkey
```
Blocked on Tauri CLI being available in the agent environment.

### 3. FTS5 retroactive migration -- already handled
`_ensure_fts_populated()` in `sqlite_repository.py` line 81 handles this as a safe no-op on every startup. No action needed.

### 4. CSP -- already correct
`middleware/security.py` has `script-src 'self'` (no unsafe-inline/unsafe-eval). Tauri `csp: null` is intentional for localhost-first dev. No action needed.

---

## Environment hazards for next agent

- **Shared working tree**: `~/cherenkov-qa` is one git checkout shared by multiple concurrent sessions. Always run `git branch` before committing; commit each file immediately after editing, not in batches.
- **CRLF noise**: `stub/generated_tests/*.spec.ts` and `npm-package/` files show as modified constantly due to Windows/WSL line-ending mismatch. Cosmetic only -- do not commit unless there are real content changes.
- **GitHub CLI**: `gh auth login` not configured in this agent environment -- PR creation must be done from a terminal where the user is already authenticated.
