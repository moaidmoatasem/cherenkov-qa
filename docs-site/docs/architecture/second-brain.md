---
title: Second Brain (Knowledge Mesh)
description: CHERENKOV-QA GraphRAG second brain — verdicts, idioms, incidents, and the knowledge mesh architecture.
---

# Second Brain — Knowledge Mesh

CHERENKOV-QA builds a **GraphRAG knowledge mesh** that grows smarter with every run. Past verdicts, idioms, and incidents are stored and recalled to improve future test generation and drift detection.

---

## What Gets Stored

| Type | What It Is | Used For |
|------|-----------|---------|
| **Verdicts** | Human approve/reject decisions on test results | Suppressing recurring false positives |
| **Idioms** | Patterns learned from past failures | Improving generation prompts |
| **Incidents** | Confirmed spec divergences with evidence | Building divergence history |
| **Session memory** | Per-session findings and decisions (CC-1) | Cross-session continuity |

---

## Storage Architecture

```
KnowledgeRepository Protocol
         │
    ┌────┴────┐
    │         │
    ▼         ▼
SQLite      Redis
(default)  (upgrade path)
FTS5       Vector search
```

Default: **SQLite with FTS5** — zero dependencies, works everywhere.
Upgrade path: **Redis** for full-text + vector similarity search at scale.

Switch via `cherenkov.toml`:

```toml
[knowledge]
backend = "sqlite"          # or "redis"
sqlite_path = ".cherenkov/knowledge.db"

[knowledge.redis]
url = "redis://localhost:6379"
```

---

## Query the Second Brain

```bash
# CLI query
python scripts/agent_sync.py experience query "Which endpoints drift most often?"

# Full-text search
python scripts/agent_sync.py memory search "authentication 401"
```

---

## HITL → Reflector Bridge

Human-in-the-loop decisions flow back into the knowledge mesh automatically:

```
QA Reviewer
    │ approve/reject
    ▼
HITL Queue
    │ HITLDecisionMade event
    ▼
Reflector
    │ ingest_human_verdict()
    ▼
KnowledgeRepository
    │ store(verdict)
    ▼
Future Generation
    (idioms recalled → better prompts)
```

---

## Auto-Memory (CC-1)

CHERENKOV automatically extracts and promotes reusable patterns from sessions:

- Every `cherenkov validate` run logs findings to `agent_memory/cherenkov_memory.db`
- Patterns that appear 3+ times are auto-promoted to "known idioms"
- Idioms are recalled at generation time to avoid repeating past mistakes

```bash
# Check memory status
python scripts/agent_sync.py memory status

# List known patterns
python scripts/agent_sync.py memory list --limit 20

# Full-text search memory
python scripts/agent_sync.py memory search "timeout"

# Force-promote eligible patterns
python scripts/agent_sync.py memory promote --threshold 3
```
