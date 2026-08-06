---
title: GitHub Actions Integration
description: Use the CHERENKOV-QA GitHub Actions workflow template for automated API conformance in CI.
---

# GitHub Actions Integration

CHERENKOV-QA provides a reusable GitHub Actions workflow template in the repository's `.github/workflows/` directory. This is **not** a published GitHub Marketplace action -- copy the workflow into your own repository to use it.

!!! warning "Not a Marketplace action"
    The `cherenkov-qa/action@v1` reference below is a template available in the CHERENKOV-QA repo's `.github/workflows/` directory. Copy it into your project's `.github/workflows/` and adjust paths as needed. A published Marketplace action is planned for a future release.

---

## Quick Setup

```yaml
# .github/workflows/api-conformance.yml
name: API Conformance

on: [push, pull_request]

jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run CHERENKOV conformance
        uses: cherenkov-qa/action@v1
        with:
          spec: api/openapi.yaml
          target: http://localhost:8000
          fail-on-drift: true
```

---

## Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `spec` | Yes | — | Path to OpenAPI spec |
| `target` | Yes | — | Base URL of server under test |
| `fail-on-drift` | No | `true` | Exit 1 on spec violation |
| `output` | No | `./reports` | Report output directory |
| `python-version` | No | `3.12` | Python version |

---

## Action Outputs

| Output | Description |
|--------|-------------|
| `drift-count` | Number of divergences found |
| `pass-rate` | Fraction of conformant endpoints |
| `report-path` | Path to the JUnit XML report |
| `sarif-path` | Path to the SARIF file |

---

## Full Workflow with SARIF Security Tab

```yaml
      - name: Run CHERENKOV conformance
        uses: cherenkov-qa/action@v1
        id: conformance
        with:
          spec: api/openapi.yaml
          target: http://localhost:8000
          fail-on-drift: true
          output: ./reports

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: conformance-report
          path: reports/

      - name: Upload SARIF to Security tab
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: ${{ steps.conformance.outputs.sarif-path }}

      - name: Comment on PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `**CHERENKOV Conformance:** ${{ steps.conformance.outputs.drift-count }} drift(s) found. Pass rate: ${{ steps.conformance.outputs.pass-rate }}`
            })
```

---

## Next Steps

- [CI/CD Integration](../guides/ci-cd.md) — GitLab CI, CircleCI, pre-commit, and the full pipeline flow
- [Check Suite (Integrity Audit)](../guides/check-suite.md) — add a test-integrity gate to your PR checks
- [Certificates & Compliance](../guides/certificates.md) — attach a signed verdict to every green build
- [Configuration](../getting-started/configuration.md) — environment variables for CI runners
