---
name: perf-baseline
description: "Track API endpoint latency with k6 and flag regressions against a statistical SQLite baseline."
scope: Performance
invariants: [Anti-lock-in]
related_contracts: [Track B/C]
---

# Perf Baseline Skill

## Purpose
Run performance baseline checks against API endpoints using k6. Records latency metrics in a local SQLite store and flags regressions.

## When to Use
- You need to track API endpoint latency over time
- You want to catch performance regressions before they reach production
- You have k6 available (graceful degradation when absent)

## Workflow

### Implementation (`track-b-c-deferred/cherenkov/execution/k6_runner.py`)

1. **Load generation**: runs k6 with configurable virtual users (VUs) and duration
2. **Metrics recording**: stores per-run latency stats in `.cherenkov/perf_metrics.db`
3. **Baseline comparison**: after ≥3 runs, computes mean/stddev and flags outliers
4. **Graceful degradation**: if k6 is not installed, runs a simulated baseline tick (HITL verdict)

### Configuration

```bash
# Default load profile
./bin/cherenkov perf --target http://localhost:8000 --endpoint /health --method GET

# Custom load profile
./bin/cherenkov perf --target http://localhost:8000 --endpoint /users --method POST --vus 10 --duration 10
```

### Contracts
- `PerfSlice` — defines target URL, endpoint, HTTP method, VUs, duration
- `PerfReport` — aggregated results with per-gate metrics
- `PerfGate` — latency, threshold, anomaly detection

### Data Flow
```
target/endpoint → k6 load test → SQLite recording → baseline comparison → report
                                                                              ↓
                                                                       anomaly flag
```

## References
- `track-b-c-deferred/cherenkov/execution/k6_runner.py` — k6 integration
- `track-b-c-deferred/cherenkov/execution/perf_analyzer.py` — statistical analysis
- `cherenkov/core/contracts.py` — PerfSlice, PerfReport types
- `smoke_test_perf.py`, `smoke_test_perf_anomaly.py`, `smoke_test_perf_intelligence.py` — perf smoke tests
