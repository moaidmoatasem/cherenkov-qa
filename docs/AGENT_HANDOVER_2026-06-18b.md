# Agent Handover — 2026-06-18 (session 2, Claude Sonnet 4.6)

> Paste as first message. HEAD = `685f85ef` (or later — check `git log --oneline -3`).
> All tests green. CLI migration complete. api.py split deferred (high churn).

---

## 1. Quick orientation

```powershell
Set-Location "\\wsl.localhost\ubuntu-24.04\home\moaid\cherenkov-qa"
git pull origin main
git checkout -- .                           # clears CRLF stub noise
git log --oneline -5
Select-String -Path "cherenkov\core\settings.py" -Pattern "_settings_lock"  # must match
python3 -m pytest tests/ -q --tb=short 2>&1 | Select-Object -Last 5
```

---

## 2. What was done this session

| Commit | Change |
|---|---|
| `0dc87d9e` | FTS5 retroactive rebuild on existing DBs |
| `0bbb0d00` | CLI step 1: diff/report/eject/self-test/completion/init/doctor → Click |
| `ecb4469d` | CLI step 2: visual/perf/hitl (6 subcommands)/review/mcp → Click |
| `685f85ef` | CLI step 3: dashboard/map/daemon/explore/author/tokens/governance/certify/profile → Click |

**All 23 commands are now in Click.** Files: `cherenkov/cli/commands/simple.py`, `advanced.py`, `epoch.py`. `core.py` dispatches via `_CLICK_COMMANDS` list; `legacy_main()` is fallback only.

---

## 3. Recurring hazard — settings lock

`cherenkov/core/settings.py` thread-safe singleton is stripped by the concurrent linter agent every few sessions. The lock **was intact at end of this session**. Check it at the start of every session:

```powershell
Select-String -Path "cherenkov\core\settings.py" -Pattern "_settings_lock"
```

If absent, reapply at the bottom of `settings.py`:
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

Also check `verify_api_key` in `cherenkov/web/api.py` still uses `hmac.compare_digest` (not `==`). The concurrent agent has reverted this to `==` at least once.

---

## 4. Remaining work (priority order)

### P1 — `api.py` route splitting

`cherenkov/web/api.py` is 1297 lines, 38 routes. **Defer until the concurrent agent slows down** — the file is high-churn and a split now will produce immediate merge conflicts.

**When ready, the split plan:**

Shared state to extract to `cherenkov/web/deps.py`:
- `verify_api_key` (auth dependency)
- `_validate_scenario_id`, `_validate_output_path`, `_validate_spec_url` (validators)
- `ConnectionManager`, `manager`, `ws_event_callback` (WebSocket)
- `get_queue()` (HitlQueue singleton)
- All Pydantic request models

Route groups → individual files:
| File | Routes |
|---|---|
| `routes/system.py` | `/healthz`, `/api/v1/health`, `/api/v1/doctor`, `/api/v1/tokens/*`, `/api/v1/settings`, `/api/v1/projects` |
| `routes/pipeline.py` | `/api/v1/ingest`, `/api/v1/run`, `/api/v1/tests`, `/api/v1/validate`, `/api/v1/eject` |
| `routes/review.py` | `/api/v1/review/*` (queue/approve/reject/edit/classify) |
| `routes/analysis.py` | `/api/v1/divergences`, `/api/v1/overview`, `/api/v1/truth-map`, `/api/v1/explore`, `/api/v1/governance` |
| `routes/visual.py` | `/api/v1/visual/*`, `/api/v1/failures`, `/api/v1/memory`, `/api/v1/signals` |
| `routes/observability.py` | `/api/v1/metrics/*`, `/api/v1/mobile/*` |
| `routes/conformance.py` | `/api/conformance/*`, `/`, `/assets/` |

Pattern: each file creates `router = APIRouter(prefix="/api/v1")`, routes use `Depends(verify_api_key)` imported from `deps.py`. In `api.py`, replace inline routes with `app.include_router(...)`.

### P2 — AI provider registry pattern

`cherenkov/ai/router.py` uses `if/elif` chains for provider dispatch. Replace with:
```python
_REGISTRY: dict[str, type[InferenceClient]] = {
    "ollama": OllamaClient,
    "openai": OpenAIClient,
    ...
}
```

### P3 — `legacy_cli.py` cleanup

After E2E CLI smoke-test (`cherenkov diff --help`, `cherenkov hitl list`, etc.), delete the 1029-line `legacy_cli.py` in a single commit. Keeps `legacy_main()` import in `core.py` as a guard — update that too.

### P4 — `verify_api_key` timing-safe comparison

The concurrent agent sometimes reverts `hmac.compare_digest` to plain `==`. Check and reapply if needed:
```python
import hmac
if x_api_key and hmac.compare_digest(x_api_key, configured_key):
    return
```

---

## 5. CRLF noise (permanent false alarm)

After any operation that touches the working tree on Windows, stub files show as modified. Always safe to clear:
```powershell
git checkout -- .
```

---

*Written by Claude Sonnet 4.6 — 2026-06-18. HEAD at time of writing: `685f85ef`.*
