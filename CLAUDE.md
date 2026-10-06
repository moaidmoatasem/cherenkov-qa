# CLAUDE.md — Cherenkov-QA session norms

## Token discipline (read this first, every turn)

- **Grep before Read.** Never open a file without knowing the target line range.
  - Know the path? → `Grep pattern file` or `Read offset+limit`
  - Don't know the path? → `Glob` or one `Explore` agent (not N inline Greps)
- **Never read these directories** speculatively — they are large, rarely need editing:
  - `agent_memory/` — synced machine state, not source of truth for humans
  - `stub/generated_tests/` — generated artefacts, read only when a specific test is named
  - `docs/` — background context; read only if the task explicitly references a doc
  - `node_modules/`, `.git/` — never
- **Subagent discipline.** Only spawn subagents for genuinely parallel, isolated work.
  Pass file:line refs in the prompt; never ask an agent to "find then fix" in one shot.
- **End of turn.** One sentence: what changed + what's next. No trailing summaries.

## Project identity

- **Repo:** `cherenkov-qa` — the integrity gate for AI-written tests: before an agent's change to a test suite is merged, prove the tests still catch bugs (Core / Assist / Labs; see `docs/ROADMAP.md`)
- **Stack:** Python (FastAPI + Click CLI), React/TypeScript (Vite), Playwright for E2E
- **Key entry points:**
  - `cherenkov/` — core Python package
  - `cherenkov/web/` — FastAPI backend + React UI
  - `cherenkov/cli/` — CLI commands
  - `stub/generated_tests/` — demo & golden test fixtures (generated, do not edit manually)
- **Active branch convention:** `qa/*` branches; `main` is the merge target

## Session loop (one item per session)

1. **Wake:** read only the "Current state" block of `HANDOVER.md` and the open `oversight` issue.
2. **Claim:** take the top unblocked item in `docs/ROADMAP.md` "Now"; check no open PR/branch references it; assign it and label it `in-progress`.
3. **Work:** that one item. Don't start a second.
4. **Stop:** add a dated `HANDOVER.md` entry, tick the ROADMAP, open/update the draft PR.

Never re-audit plan files by hand — `scripts/oversight_check.py` does that weekly.

## Status anchor

Always verify current status from `HANDOVER.md`, not from memory or ROADMAP files.
Memory files are hints — they may be stale. Git state is truth.

## What NOT to do

- Do not read `docs/_archive/ROADMAP_RECONCILIATION.md` as truth (it contained fabricated gate results)
- Do not commit without checking that no parallel agent is mid-edit (volatile shared tree)
- Do not use `git add -A` — stage specific files only
