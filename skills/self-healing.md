---
scope: Self Healing
invariants: [Suggest-only healing, D7]
related_contracts: [Track A]
---

# Self Healing Skill

## Purpose
Diagnose test failures and suggest fixes without ever auto-editing test code. All healing operations produce reports and suggestions only — the D7 invariant is absolute.

## When to Use
- A generated test fails validation against the real server
- You want to understand WHY a test failed (healing diagnosis)
- An auth token has expired and needs refreshing
- The server contract has drifted from the OpenAPI spec

## Workflow

### Diagnose (`cherenkov/healing/diagnose.py`)
1. Parses the Playwright test failure output
2. Classifies the failure: `auth_expiry`, `contract_drift`, `flaky`, `unknown`
3. Routes to the appropriate healer module

### Healers (suggest-only)
| Module | Purpose | Action |
|--------|---------|--------|
| `auth_expiry.py` | Detect expired tokens | Suggests refreshing the auth header |
| `contract_drift.py` | Detect spec-vs-server mismatch | Reports the drift (e.g., "spec says 422, server returned 400") |
| `sandbox_healer.py` | Safe sandbox suggestions | Proposes assertion tightening |

### D7 Invariant Enforcement
All healers:
- Write their findings to the validation report
- Output suggestion strings with `consider ->` prefix
- **Never** modify `.spec.ts` files
- **Never** auto-commit changes
- The `smoke_test_healing.py` smoke test verifies this invariant

## References
- `cherenkov/healing/diagnose.py` — failure classification
- `cherenkov/healing/auth_expiry.py` — auth expiry handler
- `cherenkov/healing/contract_drift.py` — contract drift detector
- `cherenkov/healing/sandbox_healer.py` — sandbox suggestions
- `smoke_test_healing.py` — D7 invariant smoke test
