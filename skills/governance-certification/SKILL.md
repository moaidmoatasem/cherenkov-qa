---
name: governance-certification
description: "Surface QA KPIs and certify model capability tiers against a gold set using RAG-Triad metrics."
scope: Governance
invariants: [D7]
related_contracts: [Track B/C]
---

# Governance & Certification Skill

## Purpose
Surface quality KPIs and certify model capability tiers against a gold set using RAG-Triad metrics.

## When to Use
- You want to track escape rate, false positive rate, coverage, and maintenance metrics
- You need to certify that a model tier meets quality thresholds
- You are running the E12 Governance KPI panel

## Workflow

### Governance (`cherenkov/governance/`)

```bash
# Show KPI panel
./bin/cherenkov governance

# Machine-readable JSON
./bin/cherenkov governance --json

# Trend a single metric
./bin/cherenkov governance --trend escape_rate
```

KPIs tracked:
- `health_score` — overall pipeline health
- `escape_rate` — bugs that passed review
- `coverage` — spec coverage percentage
- `maintenance` — test maintenance burden

### Certification (`cherenkov/stages/certify_cmd.py`)

```bash
# Certify default (small) tier
./bin/cherenkov certify

# Certify deep tier with RAG-Triad detail
./bin/cherenkov certify --tier deep --rag-report
```

Valid tiers: `small`, `deep`, `vision`.

Uses RAG-Triad metrics: Faithfulness, Answer Relevance, Context Relevance.

## References
- `cherenkov/governance/` — KPI panel implementation
- `cherenkov/stages/certify_cmd.py` — certification command
- `smoke_test_governance.py` — governance smoke test
- `smoke_test_certification.py` — certification smoke test
