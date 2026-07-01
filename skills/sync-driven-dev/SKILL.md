---
name: sync-driven-dev
description: "Session sync protocol for tracking token costs, loading pre-computed context, and persisting decisions across agent sessions."
---

# Skill: Sync Driven Development (SDD)

**Stack:** Python 3.10+, JSON filesystem store
**Pattern:** Before/During/After session sync protocol
**Invariant:** Session must be open before work, closed after work
**Token policy:** Track every meaningful token cost, compact aggressively

## When To Load This Skill

Load this skill when:
- Starting ANY agent session on CHERENKOV (it's the default workflow)
- You need to understand what context has been loaded and what's left
- You want to query past experience for a given task type
- Token budget is approaching limits and compaction is needed

## Workflow

### 1. Before Session (REQUIRED)

```bash
python scripts/agent_sync.py before --task <task_type>
```

This:
- Creates a new session with unique ID
- Loads pre-computed context snippets for your task type
- Resets token tracker for this session
- Carries forward previous session history (last 10)
- Prints loaded context so you don't need to re-read docs

**Task types map to context** in `agent_memory/sync/context.json`:
- `*` → always loaded (project identity, anti-drift rails)
- `k8s`, `phase8` → Phase 8 specific context
- `generate`, `validate`, `healing` → design invariants
- `new_module`, `refactor` → clean architecture pattern
- `demo`, `qa` → canonical bug context

If your task doesn't match any specific type, use `general`.

**Token budget:** Default 50k/session. Override with `--budget <n>` for heavy tasks.

### 2. During Session (AS YOU WORK)

#### Log findings in real-time:

```bash
python scripts/agent_sync.py log --type finding "Found duplicate validation in CRD reconciler"
python scripts/agent_sync.py log --type decision "Using Go validator over JSON Schema for CRD types"
python scripts/agent_sync.py log --type pitfall "Go struct tags need json: omitempty for optional fields"
python scripts/agent_sync.py log --type context "K8s CRD v1 requires structural schema in OpenAPI v3.0"
```

**When to log:**
- You make a decision between alternatives → log type=`decision`
- You discover something unexpected → log type=`finding`
- You hit a gotcha or pitfall → log type=`pitfall`
- You find important context not in context.json → log type=`context`

#### Track token-heavy operations:

```bash
python scripts/agent_sync.py token --action read --count 3200 --item "docs/PHASE_PLAN.md"
python scripts/agent_sync.py token --action prompt --count 1500 --item "CRD generation prompt"
python scripts/agent_sync.py token --action generate --count 8500 --item "Go validator code"
python scripts/agent_sync.py token --action search --count 400 --item "grep for CRD refs"
python scripts/agent_sync.py token  # show running total
```

**Token budget triggers:**
- `<60%` → normal operation
- `60-80%` → ⚡ warning — optimize context usage
- `80-95%` → ⚠️ run compaction (`agent_sync compact`)
- `>95%` → ⛔ emergency — close session, start new one

### 3. After Session (REQUIRED)

```bash
python scripts/agent_sync.py after --summary "Built CRD validator in Go, 3 tests passing, 2 decisions logged"
```

This:
- Closes the session (no more logging allowed)
- Extracts decisions from findings → experience records
- Updates token budget with actual usage
- Updates pattern index for future queries
- Prepares state for next session

**Never skip the `after` command.** It's what makes SDD work — without it, the next session starts blank.

### 4. Query Past Experience

```bash
python scripts/agent_sync.py experience query "k8s" --outcome success
python scripts/agent_sync.py experience query "auth" --sort date
python scripts/agent_sync.py experience query "token" --sort cost
```

Use this at the start of a session (after `before`) to see what past agents learned about your task type.

### 5. Status & Compaction

```bash
python scripts/agent_sync.py status              # human-readable
python scripts/agent_sync.py status --json       # machine-readable
python scripts/agent_sync.py compact             # auto-compact (3+ sessions)
python scripts/agent_sync.py compact --force     # force compaction now
```

## Design Rationale (Why Not...)

| Alternative | Rejected Because |
|-------------|-----------------|
| SQLite/Redis | External dep; violates zero-infra principle for sync |
| Markdown only | Not queryable; JSON enables `experience query --sort cost` |
| Auto-sync daemon | Over-engineered for current scale; CLI is enough |
| Cloud sync | Belongs in Phase 8+; filesystem keeps it L0-compatible |

## Token Optimization Tips

1. **Use context.json snippets** instead of re-reading source docs — each snippet is pre-computed at 20-150 tokens vs 500-8000 tokens for full docs
2. **Log heavy reads** — if you read a file >200 lines, log it (`agent_sync token --action read --count X --item path`)
3. **Compact after 3 sessions** — keeps context fresh and prunes stale snippets
4. **Prefer `--json` status** for programmatic use in CI/CD pipelines
5. **Use task-type mapping** — add new mappings to `context.json` for tasks you do frequently

## References

- [Methodology doc](../docs/engineering/SYNC_DRIVEN_DEV.md)
- [Sync runtime files](../agent_memory/sync/MANIFEST.md)
- [Sync tool](../scripts/agent_sync.py)
