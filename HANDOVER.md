# Agent Handover — CHERENKOV QA
**Date:** 2026-06-18 | **Session:** security/reliability hardening + QA-18 fix

---

## Current State

| Item | Value |
|---|---|
| Active branch | `fix/playwright-qa-18-failures` |
| Remote | pushed to `origin/fix/playwright-qa-18-failures` |
| Commits ahead of `origin/main` | 4 |
| Unit tests | all passing (clean exit) |
| `tsc --noEmit` | clean |

---

## What Was Done This Session

### Security hardening (all committed to `origin/main` via earlier commits)
| File | Fix |
|---|---|
| `cherenkov/core/settings.py` | Added 4 configurable timeout fields: `PLAYWRIGHT_TIMEOUT_SECONDS` (120), `TSC_TIMEOUT_SECONDS` (60), `PRISM_DOCKER_START_TIMEOUT_SECONDS` (30), `PRISM_DOCKER_STOP_TIMEOUT_SECONDS` (15) |
| `cherenkov/ai/ollama_client.py` | Guard `raise last_err` when `last_err is None` (prevented TypeError on `max_retries=0`) |
| `cherenkov/execution/playwright_invoke.py` | Subprocess timeouts on native + WSL paths; `shlex.quote` each WSL cmd part (shell-injection fix) |
| `cherenkov/execution/prism_mock.py` | Docker start/stop timeouts; `FileNotFoundError` handled explicitly; bare `except Exception: pass` replaced |
| `cherenkov/mcp/handlers.py` | URL scheme check in `_tool_registry_publish` (SSRF hardening) |
| `cherenkov/web/api.py` | Auth on `eject_test_suite` (was missing); SSRF blocklist adds `is_reserved` + `metadata.google.internal`; `update_settings` guards `security.auth_secret` and `security.egress_policy` from being overwritten |
| `cherenkov/stages/review.py` | TSC gate timeout reads from settings; two silent `except Exception: pass` blocks now log warnings |
| `.gitignore` | Secrets section (`.env`, `.env.*`) |
| `requirements.txt` | Upper-bound pins on all deps |

### QA Playwright suite (4 commits on `fix/playwright-qa-18-failures`)
- `bb2421ff` — resolved 18 Playwright test failures (259/259 passing)
- `3db84d3d` — review.py TSC timeout + exception logging
- `3142ec13` — three runtime correctness fixes (chat, knowledge, rate-limiter)
- `e420903e` — HitlQueue.ignore() method

---

## Immediate Next Step (One Action)

**Create a PR and merge `fix/playwright-qa-18-failures` → `main`.**

```bash
# The PR body is pre-written at .pr-body.md in the repo root
# gh CLI needs auth — run this from a terminal where you're logged in:
gh pr create \
  --base main \
  --head fix/playwright-qa-18-failures \
  --title "fix(qa): resolve 18 Playwright test failures + reliability hardening" \
  --body-file .pr-body.md

# Then merge:
gh pr merge --squash --delete-branch
```

Or open the PR manually at:  
`https://github.com/moaidmoatasem/cherenkov-qa/compare/main...fix/playwright-qa-18-failures`

---

## Recurring Hazard: Shared Working Tree

The WSL path `~/cherenkov-qa` is a single git worktree shared across multiple concurrent agent sessions. This causes:
- Files edited by one session to be silently overwritten by another within seconds
- Branch checkouts happening under you mid-session
- Commits appearing on a different branch than expected

**Mitigation for future agents:** commit each fix file immediately after editing — do not batch edits before committing. Verify `git branch` before every commit.

---

## What Remains (Backlog for Next Session)

1. **Gate G0 validation** — EPIC #535 is the active gate; no new Track B/C features ship until it passes. See `docs/ROADMAP_AQE.md`.
2. **`cherenkov/web/api.py` — `_validate_spec_url` DNS rebinding** — current check resolves the IP at validation time, but DNS rebinding can defeat this. A fix would re-resolve at request time or use `curl --resolve`. Low priority but worth tracking.
3. **HITL backend** — the OpenClaw chat spec assumes a HITL backend that doesn't exist yet. Build terminal HITL first (see `memory/openclaw-integration-review.md`).
4. **npm-package** — `npm-package/bin/cherenkov.js` and `package.json` have uncommitted changes (line-ending noise from concurrent session). Check before publishing.
5. **Generated test files** — `stub/generated_tests/*.spec.ts` show as modified (CRLF churn from background process). Either configure `core.autocrlf` in git or add a `.gitattributes` rule to normalize.
