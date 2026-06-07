---
scope: Visual Regression
invariants: [D7]
related_contracts: [Track B/C]
---

# Visual Regression Skill

## Purpose
Run visual-regression checks against rendered web pages. Captures baseline screenshots, compares subsequent runs pixel-by-pixel, and reports diffs. Reuses Track A's Playwright runner.

## When to Use
- You have a web UI that renders differently across deployments
- You want to catch unintended visual changes in CI
- You need pixel-level diff reporting integrated with your API conformance testing

## Workflow

### Implementation (`cherenkov/execution/visual_diff.py`)

1. **Initialize baseline**: first run captures full-page screenshots as baselines
2. **Compare**: subsequent runs capture new screenshots and compare pixel-by-pixel
3. **Gate evaluation**: each visual slice (URL) is evaluated against configurable diff thresholds
4. **Report**: produces `VisualReport` with per-slice diff pixel counts, pass/fail gates, and baseline/actual paths

### Configuration

```bash
# Baseline URL with default dir (stub/visual_baselines)
./bin/cherenkov visual --target http://localhost:3000/checkout

# Custom baseline directory
./bin/cherenkov visual --target http://localhost:3000 --baseline-dir my_baselines
```

### Contracts
- `VisualSlice` — defines a URL to snapshot
- `VisualGate` — pass/fail with diff pixel threshold
- `VisualReport` — aggregated results

### Data Flow
```
URL → Playwright screenshot → pixel compare → diff report
                                                 ↓
                                          gates + verdicts
```

## References
- `cherenkov/execution/visual_diff.py` — visual diff implementation (in track-b-c-deferred)
- `cherenkov/stages/visual/` — live visual stage module
- `cherenkov/core/contracts.py` — VisualSlice, VisualReport types
- Track A's `PlaywrightRunner` — reused for snapshot captures
- `smoke_test_visual.py` — visual regression smoke test
