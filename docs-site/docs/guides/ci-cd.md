---
title: CI/CD Integration
description: Integrate CHERENKOV-QA into GitHub Actions, GitLab CI, CircleCI — fail-on-drift, JUnit XML, SARIF output.
---

# CI/CD Integration

CHERENKOV is designed to run as a CI gate. When spec drift is detected, it exits with code `1` — failing the pipeline and preventing a broken API from shipping.

---

## GitHub Actions

### Basic Conformance Check

```yaml
# .github/workflows/api-conformance.yml
name: API Conformance

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install CHERENKOV
        run: pip install cherenkov-qa

      - name: Start API server
        run: |
          # Start your API server here
          docker compose up -d api
          sleep 5  # wait for startup

      - name: Run conformance check
        run: |
          cherenkov validate \
            --spec api/openapi.yaml \
            --target http://localhost:8000 \
            --fail-on-drift \
            --output ./reports

      - name: Upload JUnit results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: conformance-report
          path: reports/

      - name: Upload SARIF to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: reports/test-sarif.json
```

### With Prism Mock (No Real Server Needed)

```yaml
      - name: Start Prism mock server
        run: npx @stoplight/prism-cli mock api/openapi.yaml --port 4010 &

      - name: Run conformance check
        run: |
          cherenkov validate \
            --spec api/openapi.yaml \
            --target http://localhost:4010 \
            --fail-on-drift
```

---

## GitLab CI

```yaml
# .gitlab-ci.yml
api-conformance:
  stage: test
  image: python:3.12
  before_script:
    - pip install cherenkov-qa
  script:
    - cherenkov validate
        --spec api/openapi.yaml
        --target $API_BASE_URL
        --fail-on-drift
        --output reports/
  artifacts:
    reports:
      junit: reports/test-junit.xml
    paths:
      - reports/
    when: always
```

---

## CircleCI

```yaml
# .circleci/config.yml
version: 2.1
jobs:
  api-conformance:
    docker:
      - image: cimg/python:3.12
    steps:
      - checkout
      - run:
          name: Install CHERENKOV
          command: pip install cherenkov-qa
      - run:
          name: Run conformance
          command: |
            cherenkov validate \
              --spec api/openapi.yaml \
              --target $API_BASE_URL \
              --fail-on-drift
      - store_test_results:
          path: reports/
```

---

## Pre-commit Hook

Catch spec drift before a push:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: cherenkov-drift
        name: CHERENKOV spec drift check
        entry: cherenkov validate --spec api/openapi.yaml --target http://localhost:8000 --fail-on-drift
        language: python
        pass_filenames: false
        stages: [pre-push]
```

---

## Exit Codes

| Code | Meaning | CI Effect |
|------|---------|-----------|
| `0` | All tests pass, no drift | Pipeline passes |
| `1` | Drift detected | Pipeline fails |
| `2` | Config/spec parse error | Pipeline fails |

---

## Output Formats

| Flag | Format | Use Case |
|------|--------|---------|
| `--output DIR` | JUnit XML + SARIF in `DIR/` | CI test results + security tab |
| `--json` | JSON to stdout | Machine parsing, custom reporters |
| `--quiet` | Errors only to stdout | Clean CI logs |

---

## Spec Drift Workflow

```
PR opens
  │
  ▼
cherenkov validate (CI gate)
  │
  ├── ✅ exit 0 → PR passes → merge allowed
  │
  └── ❌ exit 1 → PR blocked → CHERENKOV comments on PR:
        "Endpoint GET /pets/{petId}: Expected 200, got 404.
         Spec says field 'name' is required but response omits it."
```

This turns spec drift into a PR review comment, not just a CI failure.
