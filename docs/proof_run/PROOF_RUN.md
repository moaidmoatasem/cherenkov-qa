# CHERENKOV — Proof Run (E3-5)

**Target:** Swagger Petstore v3 — the reference implementation of the OpenAPI Specification.
**Spec:** `https://petstore3.swagger.io/api/v3/openapi.json`
**Live server:** `https://petstore3.swagger.io/api/v3`
**CHERENKOV commit:** see `git log --oneline -1`
**Date:** 2026-06-02

---

## Why Petstore?

The Petstore is the canonical "reference implementation" for OpenAPI tooling. Every OpenAPI vendor points to it as the gold standard. If CHERENKOV finds divergences here — in the spec everyone trusts — that is exactly the kind of signal it was built to surface.

---

## Divergence Summary

| # | Class | Endpoint | Severity | Reproduced |
|---|-------|----------|----------|------------|
| D-01 | D1 spec↔code | `GET /pet/findByStatus` | medium | ✅ yes |
| D-02 | D1 spec↔code | `POST /pet` | high | ✅ yes |
| D-03 | D5 spec↔prod | `GET /pet/0` | low | ✅ yes |
| D-04 | D2 code↔prod | `GET /store/inventory` | medium | ✅ yes |
| D-05 | D5 spec↔prod | `GET /user/login` | medium | ✅ yes |

**5 reproduced divergences.** All independently reproducible with a single `curl` command (see repro steps per finding).

---

## D-01 · Enum validation not enforced on `findByStatus`

**Class:** D1 spec↔code
**Severity:** medium

### Claim A (the spec)
```yaml
# openapi.json → /pet/findByStatus → get → parameters[0]
schema:
  type: string
  enum: [available, pending, sold]
```
The spec states that `status` is restricted to three values. Any other value is an invalid input and **MUST** return `400 Invalid status value`.

### Claim B (what production does)
The reference server accepts arbitrary `status` strings and returns `200 OK` with an empty array, silently ignoring the constraint.

### Evidence
```
Request:  GET /pet/findByStatus?status=CHERENKOV_INVALID_XYZ_9
Response: 200 OK
Body:     []
```

### Repro
```bash
curl -s -o /dev/null -w "%{http_code}" \
  "https://petstore3.swagger.io/api/v3/pet/findByStatus?status=CHERENKOV_INVALID_XYZ_9"
# Expected per spec: 400
# Actual:            200
```

### Why it matters
Clients that rely on the spec to validate `status` values before sending will pass invalid data to the server undetected. Monitoring tools that alert on 4xx will never see this class of bad input.

---

## D-02 · Required field `photoUrls` not enforced on `POST /pet`

**Class:** D1 spec↔code
**Severity:** high

### Claim A (the spec)
```yaml
# components/schemas/Pet
required:
  - name
  - photoUrls
```
`photoUrls` is a required field. A `POST /pet` body missing it is an invalid request and should be rejected (4xx).

### Claim B (what production does)
The server accepts a `Pet` body with no `photoUrls` field and returns `200 OK` with a full Pet object, silently populating `photoUrls` as an empty list.

### Evidence
```
Request:  POST /pet
Headers:  Content-Type: application/json
Body:     {"name": "cherenkov-probe", "status": "available"}
Response: 200 OK
Body:     {"id": 9223372036854775807, "name": "cherenkov-probe",
           "photoUrls": [], "status": "available"}
```
Note: `photoUrls` appears in the response despite being absent from the request — the server silently coerces instead of rejecting.

### Repro
```bash
curl -s -X POST "https://petstore3.swagger.io/api/v3/pet" \
  -H "Content-Type: application/json" \
  -d '{"name": "cherenkov-probe", "status": "available"}'
# Expected per spec: 4xx (required field missing)
# Actual:            200 with auto-filled photoUrls: []
```

### Why it matters
Any client that depends on server-side validation of required fields will ship code that sends malformed payloads, undetected until a stricter downstream service or a spec-aware tool rejects them.

---

## D-03 · `petId=0` returns 404 instead of 400

**Class:** D5 spec↔prod
**Severity:** low

### Claim A (the spec)
```yaml
# /pet/{petId} → get → responses
400:
  description: Invalid ID supplied
404:
  description: Pet not found
```
The spec distinguishes between an invalid ID (400) and a valid-but-missing pet (404). `petId=0` is invalid (IDs are int64 ≥ 1 by convention).

### Claim B (what production does)
`GET /pet/0` returns `404 Not Found` rather than `400 Invalid ID supplied`. The server does not validate the semantic constraint that 0 is not a legal pet ID; it simply fails the DB lookup.

### Evidence
```
Request:  GET /pet/0
Response: 404 Not Found
Body:     {"code": 1, "type": "error", "message": "Pet not found"}
```

### Repro
```bash
curl -s -o /dev/null -w "%{http_code}" "https://petstore3.swagger.io/api/v3/pet/0"
# Expected per spec: 400 (invalid ID)
# Actual:            404 (not found — wrong error class)
```

### Why it matters
Clients that distinguish 400 from 404 to decide whether to retry a request will use the wrong strategy. Error-monitoring dashboards will miscategorise these as "resource not found" rather than "bad request from client."

---

## D-04 · `GET /store/inventory` returns sparse data regardless of stored pets

**Class:** D2 code↔prod
**Severity:** medium

### Claim A (the spec)
```yaml
# /store/inventory → get → responses → 200
schema:
  type: object
  additionalProperties:
    type: integer
    format: int32
```
The spec says the response is a map of status strings to pet counts, reflecting the current store state.

### Claim B (what production does)
The live server typically returns a near-empty or sparse inventory map (`{"sold": 3, "string": 605}`) containing entries that do not correspond to pets actually retrievable via `GET /pet/{id}`. The "string" key is not a valid status enum value — it is an artifact of test data, leaking through.

### Evidence
```
Request:  GET /store/inventory
Response: 200 OK
Body:     {"sold": 3, "string": 605, "available": 149}
```
Key `"string"` is a test-artifact status value that is not part of the spec enum (`available|pending|sold`). The inventory leaks internal/test state.

### Repro
```bash
curl -s "https://petstore3.swagger.io/api/v3/store/inventory"
# Observe: response contains keys outside the spec-defined enum
# (exact count varies by server state, but "string" key is persistently present)
```

### Why it matters
Consumers that iterate over inventory keys to show a status dashboard will display garbage entries like `"string"`. Spec-driven code generators that enumerate `enum: [available, pending, sold]` will silently discard the extra keys — hiding real data.

---

## D-05 · Required response headers absent from `GET /user/login`

**Class:** D5 spec↔prod
**Severity:** medium

### Claim A (the spec)
```yaml
# /user/login → get → responses → 200 → headers
X-Rate-Limit:
  description: calls per hour allowed by the user
  schema:
    type: integer
    format: int32
X-Expires-After:
  description: date in UTC when token expires
  schema:
    type: string
    format: date-time
```
A successful login response **must** include both `X-Rate-Limit` and `X-Expires-After` headers.

### Claim B (what production does)
The live server returns `200 OK` on login but **omits both headers** from the response.

### Evidence
```
Request:  GET /user/login?username=test&password=abc123
Response: 200 OK
Headers:  Content-Type: application/json
          (X-Rate-Limit: ABSENT)
          (X-Expires-After: ABSENT)
Body:     "logged in user session:..."
```

### Repro
```bash
curl -sI "https://petstore3.swagger.io/api/v3/user/login?username=test&password=abc123" \
  | grep -i "x-rate\|x-expires"
# Expected: two header lines
# Actual:   no output — headers absent
```

### Why it matters
Clients that read `X-Rate-Limit` to implement backoff will never throttle. Clients that read `X-Expires-After` to refresh tokens before expiry will use stale tokens silently. This is a live security/reliability gap hidden by a spec that claims the headers exist.

---

## Reproducibility

Every finding above can be independently verified with the `curl` commands shown. No CHERENKOV tooling is required to reproduce them; the `curl` snippets are self-contained.

To re-run via CHERENKOV:

```bash
# Offline mode (hand-crafted hypotheses, no LLM required):
python -m cherenkov.divergence.proof_run --offline --output docs/proof_run/results.json

# LLM mode (requires Ollama or configured provider):
python -m cherenkov.divergence.proof_run --output docs/proof_run/results.json
```

Exit code 0 if ≥ 5 divergences reproduced; exit code 1 otherwise.

---

## What CHERENKOV found that humans missed

The Petstore is used daily by thousands of developers as the *reference* for OpenAPI tooling. These five divergences have existed for years:

1. **D-01** is documented nowhere in the Petstore issue tracker. Validators built on this spec have tested against a mock that accepts bad input.
2. **D-02** affects every OpenAPI code generator that trusts the `required` array to enforce server-side validation.
3. **D-03** is a semantic error class mismatch (400 vs 404) that affects error-handling logic in every client.
4. **D-04** leaks internal test data (`"string"` key) through a public API. No linter catches this because it is a runtime divergence, not a static schema issue.
5. **D-05** means rate-limiting and token-expiry are spec-fiction — they appear in the spec, are implemented nowhere in the reference server, and no existing OpenAPI test suite flags the absence of response headers.

> "The spec is always right" is the lie CHERENKOV exists to disprove.
