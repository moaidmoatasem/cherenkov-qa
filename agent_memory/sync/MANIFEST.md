# Agent Sync Runtime — MANIFEST

This directory is the **runtime state** of the SDD (Sync Driven Development) protocol. Every agent session reads from and writes to these files. The sync IS the source of truth for session continuity.

## Files

| File | Purpose | Mutates |
|------|---------|---------|
| `session.json` | Active/last session state (task, start/end, summary, findings count) | Every `before`/`after` |
| `tokens.json` | Persistent token budget tracker (by type, by session, running total) | Every `token` call |
| `context.json` | Pre-computed context snippets (by task pattern, auto-refreshed) | Every `compact` |
| `experience.json` | Structured experience records (decisions, outcomes, patterns) | Every `after` |
| `findings/` | Per-session fine-grained finding logs | Every `log` call |

## Lifecycle

```
agent_sync before  →  creates session.json, loads context
agent_sync log     →  appends to findings/sess_{id}.json
agent_sync token   →  updates tokens.json
agent_sync after   →  compacts findings, updates experience, closes session
agent_sync status  →  reads current state (read-only)
agent_sync compact →  force context compaction (prune + promote)
```

## Invariants

1. `session.json` MUST exist and have `session.status = "open"` before any work
2. `tokens.json` MUST exist and be non-negative (budget enforcement)
3. Experience records are append-only — never deleted, only archived
4. Findings are per-session — each session gets its own findings file
5. Context is auto-refreshed — stale context is pruned, high-value context is promoted

## Why This Exists

Without sync, every agent session starts from zero. With sync, each session picks up where the last left off — compounding knowledge, saving tokens, and avoiding repeated mistakes.
