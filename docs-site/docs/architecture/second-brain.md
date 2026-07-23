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

The knowledge mesh is queryable over its REST API:

```bash
curl -H "X-API-Key: $CHERENKOV_API_KEY" \
  "http://localhost:8000/api/v1/knowledge/query?q=Which+endpoints+drift+most+often&limit=10"
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

- Every `cherenkov validate` run logs findings to a local memory store
- Patterns that appear 3+ times are auto-promoted to "known idioms"
- Idioms are recalled at generation time to avoid repeating past mistakes
- Query promoted idioms through the same `/api/v1/knowledge/query` endpoint above
