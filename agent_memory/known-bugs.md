# Known Bugs

Documented conformance drift and regression patterns caught by CHERENKOV.
Source: `smoke_test.py`, `smoke_test_validate.py`, `smoke_test_generate_live.py`

## Critical Bug: 422 vs 400 Conformance Drift

### Pattern
- **Spec says**: `POST /users` with invalid data returns HTTP 422 (Validation Error)
- **Server returns**: HTTP 400 (Bad Request)
- **Impact**: The generated test expects `expect(response.status).toBe(422)` but receives 400
- **Detection**: Track A `validate` command catches this automatically
- **Evidence**: `smoke_test.py` line 72-85 documents the exact failure

### How to reproduce
```bash
export REGRESSION_MODE=true
# restart target API with regression mode
./bin/cherenkov validate --target http://localhost:8000
```
Expected: `password_too_short [FAILED] — Expected: 422, Received: 400`

## Auth Token Expiry
- **Pattern**: Expired auth tokens cause 401 responses on otherwise valid requests
- **Detection**: `cherenkov/healing/auth_expiry.py` suggests token refresh
- **Status**: Suggest-only — never auto-modifies test headers

## Contract Drift
- **Pattern**: Server response schema changes without spec update
- **Detection**: `cherenkov/healing/contract_drift.py` compares actual vs spec-expected response shape
- **Suggestion**: Reports the drift as a suggestion; user decides whether to update spec or fix server

## Known Flaky Endpoints
- (None documented yet — agents should record discovered flakiness here)

## Cross-references
- See `endpoints.md` for endpoint schemas
- See `test-patterns.md` for test templates that expose these bugs
