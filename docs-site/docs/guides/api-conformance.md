---
title: API Conformance Testing
description: How CHERENKOV-QA performs API conformance testing — from spec ingestion to drift reporting.
---

# API Conformance Testing

CHERENKOV-QA automates the full API conformance loop: spec → tests → execution → drift report.

---

## What Is Conformance Testing?

API conformance testing validates that your live server **matches its OpenAPI specification**. If the spec says `GET /pets` returns a 200 with a list of pets, conformance testing verifies that the real server does exactly that — every field, every status code, every schema constraint.

Most teams skip this because writing these tests is tedious. CHERENKOV eliminates the tedium.

---

## The Conformance Loop

```
OpenAPI Spec (ground truth)
         │
         ▼
CHERENKOV generates typed tests
         │
         ▼
Tests execute against real server
         │
         ▼
Response vs Spec → DRIFT REPORT
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 PASS (0)  DRIFT (1)
 Spec OK   CI fails
```

---

## Run a Conformance Check

```bash
cherenkov validate --spec api.yaml --target http://localhost:8000
```

Output:

```
CHERENKOV Conformance Report
════════════════════════════
✅ GET  /pets             200 — Conformant
✅ POST /pets             201 — Conformant
❌ GET  /pets/{petId}     Expected: 200, Got: 404 — DRIFT DETECTED
   Field 'name' required by spec but missing in response body
✅ DELETE /pets/{petId}   204 — Conformant

Summary: 3/4 passed · 1 drift · Exit: 1
```

---

## Types of Drift Detected

| Drift Type | Example |
|-----------|---------|
| **Status code mismatch** | Spec: 200, Server: 404 |
| **Missing required field** | Spec: `name` required, Response: `name` absent |
| **Wrong field type** | Spec: `integer`, Response: `string` |
| **Extra undocumented field** | Response has `internal_id` not in spec |
| **Schema constraint violation** | Spec: `minimum: 0`, Response: `-1` |
| **Missing endpoint** | Spec: `PUT /pets/{id}`, Server: 404 Not Found |

---

## Generating Tests Without Executing

```bash
# Generate only — don't run
cherenkov generate --spec api.yaml --output ./tests

# Review generated tests
ls ./tests/
# GET_pets_test.ts
# POST_pets_test.ts
# GET_pets_{petId}_test.ts
```

---

## 6-Gate Review

Every generated test passes 6 automated quality gates before being written:

1. TypeScript syntax valid
2. Required test structure present
3. AST: no forbidden patterns
4. Meaningful assertions present
5. `tsc --noEmit` passes (type-safe)
6. Prism dry-run validates against spec

Only tests passing all 6 gates are accepted. Others loop back to the LLM for correction or go to the HITL queue for human review.

---

## Evidence-Based Reporting

Every divergence includes raw evidence:

```json
{
  "endpoint": "GET /pets/{petId}",
  "hypothesis": "Server returns 404 for valid pet IDs",
  "request": { "method": "GET", "url": "/pets/1" },
  "expected": { "status": 200, "schema": "Pet" },
  "actual": { "status": 404, "body": "{\"error\": \"Not Found\"}" },
  "evidence": "Response diff attached",
  "confidence": 0.97
}
```
