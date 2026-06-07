---
scope: Track C Re-integration
invariants: [D7]
---

# RAG Index Query Skill

## Purpose
Query historical test runs, failures, and specifications stored in the SQLite RAG Index.

## Tools
Exposed to MCP via `query_rag_index`.

## Usage for Agents
Invoke `query_rag_index` with a natural language `query` through MCP. Use it to find historical context on test failures or API changes.
