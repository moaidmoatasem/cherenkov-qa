---
scope: HITL Review
invariants: [D7]
related_contracts: [Track A]
---

# HITL Review Skill

## Purpose
Manage the Human-In-The-Loop review queue when the REVIEW stage produces uncertain verdicts (confidence 0.7-0.9). Items can be triaged via CLI or Web UI.

## When to Use
- A REVIEW stage returns `Verdict.HITL` for a generated test
- A human needs to decide: approve (keep), reject (discard), or classify (regression/intended/ignore)
- You want AI explanation of why an item was flagged

## Workflow

### CLI Operations (`cherenkov/hitl/cmd.py`)

```bash
# List pending items
./bin/cherenkov hitl list
./bin/cherenkov hitl list --all
./bin/cherenkov hitl list --status approved --json

# Inspect a specific item
./bin/cherenkov hitl show <item_id>

# Approve (atomic — only one actor wins on race)
./bin/cherenkov hitl approve <item_id> --actor @alice

# Reject with required reason
./bin/cherenkov hitl reject <item_id> --reason "incorrect_spec"

# Classify (Tier-2)
./bin/cherenkov hitl classify <item_id> --classification regression

# AI explanation (Tier-3)
./bin/cherenkov hitl explain <item_id>
```

All subcommands support `--json` for `hitl/v1` envelope output.

### Web UI Operations (`cherenkov/web/api.py`)

```bash
./bin/cherenkov review --web --port 8000 --demo
```

Opens a browser-based review dashboard with:
- Findings queue (approve/reject/classify buttons)
- "Why flagged?" AI explanation panel
- Rejection reason capture
- No build step — ships prebuilt `dist/`

### SQLite Queue (`cherenkov/hitl/store.py`)
- Durable SQLite store at `.cherenkov/hitl.db`
- Atomic status transitions: `pending → approved | rejected`
- Race-condition safe (SQLite write-lock)

### Error Codes
| Code | Meaning |
|------|---------|
| `conflict` | Item already resolved by another actor |
| `not_found` | Item ID not found |
| `forbidden` | Actor not authorized |
| `db_locked` | SQLite busy-timeout exceeded |

## References
- `cherenkov/hitl/cmd.py` — CLI hitl dispatch
- `cherenkov/hitl/store.py` — SQLite queue implementation
- `cherenkov/web/api.py` — FastAPI review endpoints
- `cherenkov/web/ui/` — React/Vite frontend
- `smoke_test_hitl_cli.py`, `smoke_test_hitl_race.py`, `smoke_test_hitl_concurrency.py` — smoke tests
- `docs/GETTING_STARTED.md` — user-facing HITL docs
