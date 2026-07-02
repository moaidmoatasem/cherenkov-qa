---
name: verify
description: "Run cherenkov verify against a live server to confirm generated tests pass and report spec-vs-server divergences."
scope: Verification
invariants: [D7, Suggest-only]
related_contracts: [Track A]
---

# Verify Skill

## Purpose
Run `cherenkov verify` against a target server to execute the generated test suite and surface spec-vs-server conformance divergences. The command is read-only — it never edits test code (D7 invariant).

## When to Use
- You have generated tests and want to validate them against the real server
- You need a verdict (pass/fail) on spec conformance before HITL review
- You want CI-ready conformance output in JSON or JUnit format

## Workflow

### Basic run

```bash
# Against local server
cherenkov verify --target http://localhost:8000

# Against staging, JSON output
cherenkov verify --target https://staging.api.example.com --output json

# Fail-fast on first divergence
cherenkov verify --target http://localhost:8000 --fail-fast

# Filter to a single tag
cherenkov verify --target http://localhost:8000 --tag smoke
```

### What it does

1. Loads generated `.spec.ts` files from `stub/generated_tests/`
2. Starts a Playwright runner against `--target`
3. Executes each scenario; collects actual status codes, response shapes
4. Compares actuals against OpenAPI spec expectations
5. Produces a `ValidationReport` with per-scenario verdicts

### Verdicts

| Verdict | Meaning |
|---------|---------|
| `pass` | Actual matches spec — no divergence |
| `divergence` | Actual differs from spec expectation |
| `flaky` | Inconsistent across retries |
| `error` | Test could not execute (network, auth, etc.) |

### Output formats

```bash
cherenkov verify --output text    # human-readable (default)
cherenkov verify --output json    # machine-readable .cherenkov/report.json
cherenkov verify --output junit   # JUnit XML for CI systems
```

### CI integration

```yaml
# .github/workflows/verify.yml (fragment)
- name: Verify API conformance
  run: cherenkov verify --target ${{ env.API_URL }} --output junit
- uses: actions/upload-artifact@v4
  with:
    name: cherenkov-report
    path: test-junit.xml
```

## D7 Invariant
`verify` is read-only. It never writes to `.spec.ts` files. Divergence findings are written to `.cherenkov/report.json` (report only). Auto-fix suggestions appear in the report but are never applied automatically.

## References
- `cherenkov/cli/commands/verify.py` — command implementation
- `cherenkov/execution/runner.py` — Playwright runner
- `cherenkov/core/contracts.py` — ValidationReport, Verdict types
- `tests/unit/test_verify_command.py` — 8 unit tests
