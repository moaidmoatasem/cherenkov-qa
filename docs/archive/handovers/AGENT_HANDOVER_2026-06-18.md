# Agent Handover — 2026-06-18 (Claude Sonnet 4.6)

> Single source of truth for current state. Paste as your first message.
> HEAD = `e510cfa3`. Main is clean. All tests green (502+ unit, 259/259 Playwright QA).

---

## 1. Environment

- Repo: `github.com/moaidmoatasem/cherenkov-qa` (private), WSL2 at `~/cherenkov-qa`
- Windows path: `\\wsl.localhost\ubuntu-24.04\home\moaid\cherenkov-qa`
- PowerShell (not Bash) is the reliable shell for git/file ops in this env
- A **concurrent linter agent** commits to main continuously — always `git pull` before working

---

## 2. Fixes confirmed in main (do NOT revert)

All verified, committed, tests green.

| File | What was fixed |
|---|---|
| `cherenkov/core/settings.py` | Thread-safe double-checked locking on `get_settings()` singleton — concurrent agent strips this repeatedly, **check first** |
| `cherenkov/web/api.py` | Missing `Config` import; timing-safe API key via `hmac.compare_digest`; pipeline semaphore cap (4 threads); `_validate_output_path` on `/run`; auth guard on `/api/v1/knowledge`; `_validate_spec_url` made async |
| `cherenkov/stages/generate.py` | Import-time crash on missing prompt file wrapped in try/except |
| `cherenkov/stages/review.py` | False-positive Gate 3 rejection of `throw new Error`; configurable TSC timeout |
| `cherenkov/stages/ingest.py` | Mobile source returns `DEGRADED` not silent `OK` with empty endpoints |
| `cherenkov/knowledge/adapters/sqlite_repository.py` | FTS5 per-term AND-quoting; LIKE fallback; retroactive FTS rebuild on existing DBs |
| `cherenkov/chat/agent.py` | Blocking `_call_llm` offloaded to `asyncio.to_thread` |
| `cherenkov/knowledge/api/routes.py` | Dataclass objects serialized to plain dicts before JSON response |
| `cherenkov/web/middleware/security.py` | Rate-limiter dict evicts idle IPs (memory leak fix) |
| `cherenkov/hitl/store.py` | `HitlQueue.ignore()` method; api.py uses it |
| `cherenkov/web/ui/tests/qa/*.spec.ts` | 259/259 Playwright QA tests passing (was 18 failing) |
| `npm-package/bin/cherenkov.js` | `execSync` shell injection → `spawnSync` with arg array |
| `cherenkov/web/api.py` (SSRF) | DNS-rebinding: hostname resolved to IPs before blocklist check |

### Recurring hazard — settings lock

Run this every session start:
```bash
grep -n "_settings_lock" cherenkov/core/settings.py
```
Must return a match. If absent, reapply from [`cherenkov/core/settings.py`](../cherenkov/core/settings.py) — the pattern is double-checked locking with `threading.Lock()`.

---

## 3. CRLF stub noise (permanent false alarm)

`stub/generated_tests/*.spec.ts` and occasionally other files appear as `M` in `git status` on Windows/WSL because the test generator writes CRLF. Fix:
```powershell
git checkout -- .
```
Safe because `git diff --stat` will show zero content changes (only CRLF warnings).

---

## 4. Remaining open work (priority order)

### P1 — CLI unification (see detailed plan below)

`cherenkov/cli/legacy_cli.py` is 1029 lines of argparse coexisting with a thin Click shim in `core.py`. The shim currently dispatches `validate` and `synthetic` to Click and falls back to `legacy_main()` for everything else.

**Commands to migrate** (12 total, in safe order):
1. `diff` — simple 3-arg command, good warmup
2. `report` — 2 optional args, no external deps
3. `eject` — 1 required arg, calls `EjectorEngine`
4. `self-test` — no args, calls dry-run pipeline
5. `completion` — shell completion generator
6. `init` — 2 optional args, calls setup wizard
7. `doctor` — no args, calls health check
8. `visual` — 2 args, calls VisualRegressionEngine
9. `perf` — 5 args, calls PerfStage
10. `hitl show` — calls `HitlQueue.list_pending()`
11. `hitl approve` — calls `HitlQueue.approve()`
12. `hitl reject` — calls `HitlQueue.reject()`
13. `validate` — **already ported**, in `cherenkov/cli/commands/validate.py`

**Migration pattern for each command:**
```python
# cherenkov/cli/commands/<name>.py
import click
from cherenkov.xxx import SomeEngine

@click.command("diff")
@click.option("--before", required=True, type=click.Path(exists=True))
@click.option("--after", required=True, type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["text","json"]), default="text")
def diff_cmd(before, after, fmt):
    """Compare two OpenAPI specs for breaking changes."""
    ...
```

Then in `core.py` add to `known_commands` list and register the command.

**Safety rule:** keep `legacy_main()` fallback until ALL commands are ported. Only delete `legacy_cli.py` after all 12 are migrated and tested.

### P2 — `api.py` route splitting

`cherenkov/web/api.py` is ~900 lines, 40+ routes. Split target:
- `cherenkov/web/routes/pipeline.py` — `/run`, `/status`, `/ws`
- `cherenkov/web/routes/hitl.py` — `/hitl/*`
- `cherenkov/web/routes/knowledge.py` — `/knowledge`
- `cherenkov/web/routes/spec.py` — `/spec/validate`, `/ingest`
- `cherenkov/web/routes/system.py` — `/health`, `/doctor`, `/settings`

Pattern: each file creates `router = APIRouter(prefix="/api/v1")` and registers routes. In `api.py`, replace inline routes with `app.include_router(pipeline.router)` etc.

### P3 — AI provider registry

`cherenkov/ai/router.py` uses `if/elif` chains for provider dispatch. Replace with:
```python
_REGISTRY: dict[str, type[InferenceClient]] = {
    "ollama": OllamaClient,
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
    ...
}
client = _REGISTRY[provider](config)
```

### P4 — Silent exception swallows (31 files)

Most are in optional/observability paths (acceptable). High-value targets:
- `cherenkov/execution/trace_reader.py` — pipeline trace parsing
- `cherenkov/adversarial/runner.py` — adversarial test execution
- `cherenkov/divergence/explorer.py` — drift detection (3 silent swallows)

---

## 5. Quick orientation commands

```powershell
# Always run first
Set-Location "\\wsl.localhost\ubuntu-24.04\home\moaid\cherenkov-qa"
git pull origin main
git status --short
grep -n "_settings_lock" cherenkov/core/settings.py   # must match

# Tests
python3 -m pytest tests/ -q --tb=short 2>&1 | Select-Object -Last 10

# Any new concurrent-agent commits since this handover
git log e510cfa3..HEAD --oneline
```

---

*Written by Claude Sonnet 4.6 — 2026-06-18. HEAD at time of writing: `e510cfa3`.*
