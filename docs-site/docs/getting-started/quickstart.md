---
title: Quickstart
description: Run your first CHERENKOV-QA conformance test against a real API in under 5 minutes.
---

# Quickstart

Run CHERENKOV against the Petstore API — the canonical OpenAPI example — in under 5 minutes.

---

## Step 1 — Get a Spec

```bash
# Download the Petstore OpenAPI spec
curl -o petstore.yaml https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.yaml
```

Or use your own spec:

```bash
# Point to any OpenAPI 3.x spec
export SPEC=./my-api.yaml
```

---

## Step 2 — Start a Target Server

You need a running server that implements the spec. For the Petstore example:

```bash
# Start the Petstore mock server via Prism
npx @stoplight/prism-cli mock petstore.yaml --port 4010
```

Or use your real server:

```bash
export TARGET=http://localhost:8000
```

---

## Step 3 — Run CHERENKOV

```bash
cherenkov validate \
  --spec petstore.yaml \
  --target http://localhost:4010
```

CHERENKOV will:

1. **Ingest** the spec → parse all endpoints and schemas
2. **Plan** → select test scenarios per endpoint
3. **Generate** → write typed Playwright tests using the local LLM
4. **Review** → 6-gate validation (syntax, AST, TypeScript, Prism dry-run)
5. **Execute** → run tests against your live server
6. **Report** → conformance violations with evidence

---

## Step 4 — Read the Report

```
CHERENKOV Conformance Report
════════════════════════════
Spec:   petstore.yaml
Target: http://localhost:4010
Run:    2026-06-29T00:00:00Z

✅ GET  /pets             200 — Conformant
✅ POST /pets             201 — Conformant
❌ GET  /pets/{petId}     Expected: 200, Got: 404 — DRIFT DETECTED
✅ DELETE /pets/{petId}   204 — Conformant

Summary: 3/4 passed · 1 divergence · Exit code: 1
```

!!! tip "Exit code semantics"
    - `0` — all tests pass, no drift
    - `1` — drift detected (spec violation found)
    - `2` — validation errors (config, spec parse failures)

---

## Step 5 — Explore in the Dashboard

```bash
cherenkov dashboard
```

Opens the React dashboard at `http://localhost:8000`:

- **Overview** — release readiness summary
- **Divergences** — severity-sorted findings with evidence
- **Explore** — second pair of eyes on your API
- **Chat** — ask questions about past verdicts

---

## Step 6 — Eject to Vanilla Playwright (Optional)

When you're ready to own your tests outright:

```bash
cherenkov eject --output ./ejected-tests
```

This removes all CHERENKOV imports and produces pure Playwright tests that run with no dependencies on CHERENKOV:

```bash
cd ejected-tests
npm install
npx playwright test
```

---

## Common Flags

```bash
cherenkov validate \
  --spec petstore.yaml \
  --target http://localhost:4010 \
  --fail-on-drift \        # exit 1 on any drift (for CI)
  --output ./reports \     # write JUnit XML + SARIF to dir
  --json                   # machine-readable JSON output
```

---

## Next Steps

- [Full CLI reference →](../cli/reference.md)
- [Set up CI/CD integration →](../guides/ci-cd.md)
- [Configure local LLM →](../guides/local-llm.md)
- [Deploy K8s operator →](../guides/k8s-operator.md)
