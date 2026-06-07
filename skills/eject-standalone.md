---
scope: Eject
invariants: [Anti-lock-in]
related_contracts: [Track A]
---

# Eject Standalone Skill

## Purpose
Strip all CHERENKOV metadata and hooks from generated tests, producing a standalone vanilla Playwright suite with zero tool dependency.

## When to Use
- You want to keep generated tests in your own repository
- You need a CI-ready test suite that runs without CHERENKOV
- You are done evaluating the tool and want to adopt the tests

## Workflow

### Implementation (`cherenkov/execution/eject.py`)

1. Copies all generated `.spec.ts` files to the output directory
2. Strips CHERENKOV-specific trace interception metadata from imports
3. Emits a clean `client.ts` with pure `openapi-fetch` typing (no monkey-patching)
4. Generates standard `playwright.config.ts` and `package.json`
5. Verifies the ejected suite compiles with `tsc --noEmit`

### Verification

```bash
./bin/cherenkov eject --output ejected_suite
cd ejected_suite && npm install && npx playwright test
```

The ejected folder should:
- Contain zero references to "cherenkov" in imports or config
- Run `npx playwright test` green
- Be copyable to any machine without the CHERENKOV repo

## Anti-Lock-In Proof

The `smoke_test_eject.py` test verifies the eject invariant:
```
Verifies: eject produces standalone Playwright — verified: npm install && npx playwright test
runs green with ZERO "cherenkov" on the path.
```

## References
- `cherenkov/execution/eject.py` — eject implementation
- `smoke_test_eject.py` — automated invariant verification
- `docs/GETTING_STARTED.md` — user-facing eject docs
