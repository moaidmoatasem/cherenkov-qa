# ADR-012: Hook Execution Model

**Status:** Accepted
**Date:** 2026-06-28
**Deciders:** Owner (via Claude Code-Inspired Enhancement Plan approval)
**Related:** ADR-004 (Clean Architecture), ADR-005 (Event-Driven)

---

## Context

CHERENKOV's pipeline stages (ingest → plan → generate → review → validate →
eject) are executed sequentially with no extension points. Teams using CHERENKOV
in CI/CD workflows frequently need to run actions alongside pipeline steps:

- Auto-format generated tests after `generate`
- Post a Slack alert after `validate` when divergences are found
- Open a GitHub PR after `eject` succeeds
- Run a linter before `commit`

Currently these integrations require wrapping the `cherenkov` CLI in shell
scripts — fragile, undocumented, and invisible to CHERENKOV itself.

Claude Code's hooks model — shell commands that fire before/after key actions,
configured in `CLAUDE.md` — is the inspiration.

## Decision

### Hook Events

Ten named hook events, one before and one after each major pipeline operation:

| Event | Fires when |
|---|---|
| `pre_generate` | Before the GENERATE stage starts |
| `post_generate` | After GENERATE completes (pass or fail) |
| `pre_review` | Before the 6-gate REVIEW |
| `post_review` | After REVIEW, verdict available as `{verdict}` |
| `pre_validate` | Before `cherenkov validate` against live server |
| `post_validate` | After validate, report at `{report_path}` |
| `pre_eject` | Before `cherenkov eject` |
| `post_eject` | After eject, output at `{output_dir}` |
| `pre_commit` | Before git commit (if CHERENKOV manages commits) |
| `post_commit` | After git commit |

### Configuration: `cherenkov.toml [hooks.*]`

Each hook is a TOML table under `[hooks.<event>]`:

```toml
[hooks.post_validate]
run = "python scripts/notify_slack.py {report_path}"
timeout = 30        # seconds; default: 30
fail_mode = "warn"  # "warn" (default) or "abort"
env = { SLACK_CHANNEL = "#qa-alerts" }

[hooks.post_eject]
run = "gh pr create --title 'chore: tests for {endpoint}' --body {report_path}"
fail_mode = "warn"
```

**Template variables** (injected by CHERENKOV at fire time):

| Variable | Value |
|---|---|
| `{report_path}` | Absolute path to the most recent report JSON |
| `{output_dir}` | Eject output directory |
| `{verdict}` | Review verdict: `auto_approve` / `hitl` / `regenerate` |
| `{endpoint}` | Current endpoint being processed |
| `{spec_path}` | Path to the OpenAPI spec file |

### Execution Model

- **Subprocess**: `subprocess.run(shell=True, timeout=<timeout>)` — maximum
  flexibility, any language, any tool.
- **Timeout**: enforced; exceeded → logged as warning, hook marked TIMEOUT.
- **`fail_mode = "warn"`** (default): hook failure is logged; pipeline continues.
- **`fail_mode = "abort"`**: hook failure raises `HookAbortError`; pipeline stops
  with exit code 3 (`ERROR`).
- **Environment**: CHERENKOV env vars + user-defined `env` table are injected.
- **Async hooks**: hooks run synchronously in the calling thread. Long-running
  hooks should use `fail_mode = "warn"` and background themselves internally.

### Module Layout (Clean Architecture, ADR-004)

```
cherenkov/hooks/
├── domain/models.py               # HookEvent, HookConfig, HookResult, FailMode
├── ports/executor.py              # HookExecutor Protocol
├── adapters/subprocess_executor.py # Default: shell subprocess with timeout
├── registry.py                    # HookRegistry: load from config_loader
└── api/routes.py                  # /api/v1/hooks/list|run|log
```

## Alternatives Considered

**Async Python functions**: rejected — couples hook code to CHERENKOV internals;
shell commands are universal and language-agnostic.

**Webhook (HTTP POST to URL)**: rejected — over-engineered for local hooks;
webhook notifiers already exist in `cherenkov/adapters/notifiers/webhook.py`
for the network notification use case.

**Pre-commit framework integration**: rejected — pre-commit hooks fire on git
events, not on CHERENKOV pipeline events; the two are orthogonal.

## Consequences

- `cherenkov/hooks/` follows ADR-004 Clean Architecture.
- `[hooks.*]` keys are added to the schema validated in `config_loader.py`.
- Unknown hook event names in `cherenkov.toml` produce an explicit validation error.
- Default `fail_mode = "warn"` ensures existing pipelines are not disrupted.
- D7 invariant unaffected: hooks cannot edit test code (they are shell commands,
  not CHERENKOV pipeline stages; the D7 rule applies to pipeline stages).
- `.githooks/pre-push` (existing shell hook) is unaffected.
