---
last_updated: 2026-06-07
source: smoke_test.py, smoke_test_validate.py, smoke_test_healing.py, tests/eject_fixtures/password_too_short.spec.ts
scope: Conformance drift patterns discovered by CHERENKOV smoke tests and validation
---

# Known Bugs

## 1. Spec-to-Implementation Conformance Drift (422 vs 400) [CANONICAL]

**Source:** `smoke_test_validate.py`, `tests/eject_fixtures/password_too_short.spec.ts`

The OpenAPI spec declares `422 Unprocessable Entity` for validation errors (POST /users), but the target API normalizes validation errors to `400 Bad Request`.

```typescript
// Test asserts 422 (per spec) - goes RED against live target
expect(response.status).toBe(422);  // actual: 400
```

This is the **canonical bug** that CHERENKOV exists to catch - the core demo scenario in `docs/QA_DEMO_KIT.md`.

## 2. Status Code Regression - Auth Expiry (201 -> 401)

**Source:** `smoke_test_healing.py:test_auth_expiry_detection()`

A historically-passing endpoint that returned `201` begins returning `401` due to expired authentication tokens.

- **Classification:** `FailureClass.AUTH_EXPIRY`
- **Detection:** Snapshot comparison (prior pass: status=201, body={id, email} vs. current: status=401, body={})
- **Suggestion:** Renew `BEARER_TOKEN` in test headers

## 3. Response Body Contract Drift (Missing Fields)

**Source:** `smoke_test_healing.py:test_contract_drift_detection()`

HTTP status stays `201` but the response body is missing a previously-present field (`email`).

- **Classification:** `FailureClass.CONTRACT_DRIFT`
- **Detection:** Snapshot `{id: 42, email: "test@example.com"}` vs. current `{id: 42}`
- **Flagged as:** `[RED REGRESSION]`
- **Suggestion:** Add `expect(data).toHaveProperty("email")` assertions

## 4. Value Tightening Opportunities

**Source:** `smoke_test_validate.py`

Tests pass but could be more precise. Validation suggests:
- Literal string assertions: `expect(data.email).toBe('test@example.com')`
- Payload-reflective assertions: `expect(data.email).toBe(body.email)`

## 5. Circuit Breaker / Graceful Degradation

**Source:** `smoke_test.py:run_failure_path()`

When a stage (e.g. INGEST) produces malformed output, the pipeline:
1. Retries via the retry ladder
2. Trips the circuit breaker after `error_threshold` failures
3. Returns `False` (graceful abort) instead of crashing with a raw Python stack trace

Invariant: `engine.breaker.tripped == True` and `engine.breaker.error_count == threshold`.

## 6. Suggest-Only / No Auto-Modification (D7)

**Source:** All three smoke tests

Files in `stub/generated_tests/` must **never** be auto-edited by validation or healing.
- Validate enforces via SHA-256 hash comparison (pre-run vs. post-run)
- Healing enforces via `git status --porcelain` diff
- **Invariant D7:** Healing and validation produce reports/suggestions only - zero files modified on disk

---

*Cross-ref: [endpoints.md](endpoints.md) for affected endpoints, [test-patterns.md](test-patterns.md) for test code exhibiting these patterns, [validation-gate.md](validation-gate.md) for demo context*
