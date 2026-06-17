# Agent Handover — 2026-06-17 (Claude Sonnet 4.6, multi-session review)

> Paste this as your first message when resuming. Raw state, no hallucinated claims.

---

## Current repo state (as of 2026-06-17 ~19:50 UTC+3)

- **Branch:** `main`, clean working tree, fully pushed to origin
- **Last commit:** `6c017020` — fix: thread-safe double-checked locking in get_settings() singleton
- **Test suite:** 502+ unit tests, exit 0, verified twice this session

---

## Fixes confirmed in `main` (do NOT revert)

All the following are committed and on origin/main. Each was reverted at least
once by the concurrent linter agent and reapplied:

| File | Fix | Commit (approx) |
|---|---|---|
| `cherenkov/web/api.py` | Added missing `Config` import (NameError on /health + /doctor); timing-safe API key comparison via `hmac.compare_digest`; `_pipeline_semaphore` concurrency cap (4 threads); `_validate_output_path` on `/run` | 7d54fb26 |
| `cherenkov/stages/generate.py` | `_load_system_prompt()` wrapped in try/except so missing file doesn't crash at import | 7d54fb26 |
| `cherenkov/stages/review.py` | Gate 3 regex no longer flags `throw new Error` as a forbidden HTTP keyword (was producing false REGENERATE verdicts) | 7d54fb26 |
| `cherenkov/stages/ingest.py` | Mobile source `.apk/.har/.hil` now returns `Status.DEGRADED` with `MOBILE_SOURCE` error instead of `Status.OK` with empty endpoints | 7d54fb26 |
| `cherenkov/knowledge/adapters/sqlite_repository.py` | FTS5 search: per-term AND-joined quoting instead of whole-phrase wrap — fixes multi-word queries and plugs raw FTS5 syntax injection | acdf10cc |
| `cherenkov/validate/jira_exporter.py` | BOM removed from file header | acdf10cc |
| `npm-package/bin/cherenkov.js` | `execSync(cmd + args)` → `spawnSync(cmd, argsArray)` — closes shell command-injection vector | 172a0e31 |
| `npm-package/package.json` | BOM removed; `files` allowlist added; license corrected to Apache-2.0 | 172a0e31 |
| `cherenkov/core/settings.py` | Thread-safe double-checked locking on `get_settings()` singleton using `threading.Lock` | 6c017020 |

---

## Known recurring hazard: concurrent linter agent

A second agent is actively committing to the same branch. It has:
- Added legitimate improvements (timeout fields in settings, test suites in `cherenkov/web/ui/tests/qa/`)
- **Reverted** the `settings.py` singleton fix at least twice

**Rule:** before any commit, run `git diff cherenkov/core/settings.py` and verify
`_settings_lock` is present. If absent, the concurrent agent stripped it again — reapply
[`cherenkov/core/settings.py:133-142`](../cherenkov/core/settings.py) using the
double-checked locking pattern shown below:

```python
import threading as _threading

_settings_instance: "CherenkovSettings | None" = None
_settings_lock = _threading.Lock()

def get_settings() -> "CherenkovSettings":
    global _settings_instance
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                _settings_instance = CherenkovSettings()
    return _settings_instance
```

---

## What was NOT fixed (out of scope or lower priority)

1. **Dual CLI** — `cherenkov/cli/legacy_cli.py` (argparse) coexists with `cherenkov/cli/core.py`
   (Click). Migration deferred. Tackling it requires testing both paths end-to-end.

2. **SSRF DNS-rebinding gap** — `_validate_spec_url` in `cherenkov/web/api.py` blocks
   private-IP ranges at DNS resolution time, but a malicious server can return a public IP
   initially and redirect to 169.254.x.x at TCP connect. Full fix requires a library like
   `ssrf-protect` or binding the HTTP client to a restricted resolver.

3. **FastAPI route proliferation** — `cherenkov/web/api.py` is ~800 lines, 40+ routes.
   ADR-010 recommends slicing into `web/routes/{pipeline,hitl,knowledge,spec}.py`.
   Mechanical refactor, no logic change.

4. **AI provider registry** — `cherenkov/ai/router.py` uses `if/elif` chains for provider
   dispatch. ADR-010 recommends a `registry: dict[str, type[InferenceClient]]` pattern.

---

## CRLF stub files — persistent false alarm

`stub/generated_tests/*.spec.ts` (20 files) appear as modified in `git status` on Windows/WSL2
because the test generator writes CRLF on Windows. `.gitattributes` (`* text=auto eol=lf`) is
already correct. **Fix when they reappear:** `git checkout -- stub/generated_tests/`

---

## Next priority work (for the next session/agent)

1. **Verify settings.py lock is still present** — concurrent agent keeps stripping it.
   `grep -n "_settings_lock" cherenkov/core/settings.py` should return a hit.

2. **Run the new QA suite** — commit `561e4f07` added 2500+ lines of Playwright tests in
   `cherenkov/web/ui/tests/qa/`. These have NOT been run or validated. Start with:
   ```
   cd cherenkov/web/ui && npx playwright test tests/qa/smoke-regression-exploratory.spec.ts --reporter=line
   ```
   Expect failures until the dev server is running at `http://localhost:5173`.

3. **Fix the empty commit message** — commit `561e4f07` has message `feat:` (no body).
   Amend or document what it actually added (the 5 new QA test files).

4. **CLI unification** — migrate `legacy_cli.py` to Click, delete `legacy_cli.py`,
   verify `cherenkov --help` still works. See ADR-010 in `docs/`.

5. **SSRF DNS-rebinding** — see item 2 in "not fixed" above. Add `ssrf-protect` or
   equivalent and tighten `_validate_spec_url`.

---

## How to orient quickly

```bash
# State
git log --oneline -10
git status --short
grep -n "_settings_lock" cherenkov/core/settings.py   # must return a hit

# Tests
cd /home/moaid/cherenkov-qa
python3 -m pytest tests/ -q --tb=short 2>&1 | tail -20

# Diff against last known-good state
git diff 6c017020 HEAD --stat
```

---

*Written by Claude Sonnet 4.6 — 2026-06-17*
