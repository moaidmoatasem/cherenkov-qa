# CHERENKOV QA — Recorded Session Evidence

**Captured:** 2026-07-06
**Environment:** WSL Ubuntu-24.04, Python 3.12.3, Node v22.23.0, Playwright 1.61.1

---

## Demo Run Summary

| Demo | Status | Key Finding |
|------|--------|-------------|
| Catch the AI Cheating (Python) | PASS | 1 cheat caught out of 3, kill rate 33% |
| Catch the AI Cheating (TypeScript) | PASS | 2/3 cheats caught statically (Gate 4), 1 requires Docker (Gate 6) |
| Validate (target API, normal mode) | MIXED | 10/16 passed, 6 failed (Petstore tests fail — no /pets endpoint on target) |
| Validate (key drift finding) | CAUGHT | `password_too_short`: Expected 422, Got 400 — real conformance drift |
| Validate (hallucinated field) | CAUGHT | `demo_hallucinated`: asserts `auth_token` not in spec |
| Eject | PASS | 17 files ejected, client.ts + package.json clean of CHERENKOV deps |
| Doctor | PASS | All systems healthy (Ollama, Node, Playwright, Docker/Prism) |
| Demo mode | PASS | 4-beat narrative: generate → cheat → catch → certificate |
| HITL queue | 16 items | Pending review items with confidence scores |
| HITL approve | PASS | Item approved by @demo-user, queue 16 → 15 |
| Check-suite | CAUGHT | DELETED cheat detected via static analysis |
| Spec diff | PASS | 19 breaking + 2 additive changes detected between Petstore and Target |
| Governance | PASS | KPI panel rendered (health 0.70, escape rate 0.0%) |
| Examples | PASS | 7 one-liners for common workflows |

---

## Session 2: Catch the AI Cheating — Python Demo

```
Beat 1 — AI generates a suite (all green)
  [AI output] Generated 3 tests. Running against target... 3 passed.
  Coverage: 100%  |  Status: DONE

Beat 2 — The cheat (AI weakens an assertion to fake green)
  test_create_user: assert status == 201 and email present
    -> changed to: assert status < 500          # still green!
  Suite is still green. The AI made it green. Not the software.

Beat 3 — CHERENKOV catches the cheats
  test_create_user [WEAKENED]: CAUGHT
    Reason: Test passes both the correct mock and the broken implementation
  test_create_user [STRICT]: MEANINGFUL
  test_create_order [STRICT]: MEANINGFUL
  Gate summary: 2 meaningful, 1 caught
  Kill rate: 33%

Beat 4 — Fix it for real -> CHERENKOV Certificate
  Status: PASS
  Verified: test_create_user, test_create_order
  Method: adversarial self-play (broken-impl kill test)

  "Generation is free now. Trust isn't.
   CHERENKOV is the part that doesn't let the AI lie to you."
```

---

## Session 2: Catch the AI Cheating — TypeScript Demo

```
Beat 1 — Baseline: correct test
  Gate [syntax]            PASS
  Gate [structure]         PASS
  Gate [ast]               PASS
  Gate [assertion]         PASS
  Gate [tsc]               PASS
  Gate [prism-dryrun]      SKIP
  Verdict: PASS (100%)

Beat 2+3 — The cheats
  Cheat 1: Weakened assertion [toBeLessThan(500) instead of toBe(201)]
    Gate [assertion]        FAIL — Missing expectation asserting specific status code
    Verdict: HITL (80%)

  Cheat 2: Deleted check [body assertions removed]
    Gate [assertion]        FAIL — Missing expectation asserting response body property
    Verdict: HITL (80%)

  Cheat 3: Hallucinated oracle ['auth_token' not in spec]
    All gates PASS (100%) — caught by Gate 6 (Prism) when Docker available

  Cheats 1+2: caught STATICALLY by Gate 4 — zero server, zero runtime
  Cheat 3: caught by Gate 6 (Prism dynamic dry-run) when Docker available
```

---

## Session 3: Validate Against Target API

```
CHERENKOV CONFORMANCE REPORT
Target: http://localhost:8000
Scenarios: 16  |  Passed: 10  |  Failed: 6

  [PASS]  demo_deleted          — POST /users, 201 OK
  [PASS]  demo_correct_q        — POST /users, 201 OK
  [PASS]  demo_correct          — POST /users, 201 OK
  [PASS]  happy_path            — POST /users, 201 OK
  [PASS]  demo_weakened_v       — POST /users, 201 OK
  [PASS]  demo_weakened         — POST /users, 201 OK
  [PASS]  demo_tighten          — POST /users, 201 OK
  [PASS]  demo_deleted_v        — POST /users, 201 OK
  [PASS]  golden_weakened       — GET /pets, 404 (no /pets on target)
  [PASS]  weakened_assertion    — GET /pets, 404 (no /pets on target)

  [FAIL]  password_too_short    — Expected 422, Got 400  ← REAL DRIFT
  [FAIL]  demo_hallucinated     — asserts auth_token not in spec  ← HALLUCINATION
  [FAIL]  correct_petstore      — Expected 200, Got 404 (no /pets on target)
  [FAIL]  deleted_check_petstore — Expected 200, Got 404
  [FAIL]  golden_deleted        — Expected 200, Got 404
  [FAIL]  golden_correct        — Expected 200, Got 404

  6 conformance drift(s) detected

Git status verification:
  Git status is clean — zero test files were auto-modified. Suggest-only constraint honored.
```

### Key Drift Finding
```
Scenario: password_too_short [FAILED]
  Expected: 422
  Received: 400
  at password_too_short.spec.ts:19

  The spec promises 422 for validation errors. The server returns 400.
  That's a real conformance drift bug.
```

### Hallucination Finding
```
Scenario: demo_hallucinated [FAILED]
  Expected path: "auth_token"
  Received value: {"email": "demo_xxx@cherenkov.dev", "id": 42}

  The AI asserted on 'auth_token' — a field that doesn't exist in the spec.
  CHERENKOV caught it.
```

---

## Session 8: Eject to Standalone

```
Ejected 17 test files + client.ts + generated-types.ts
Output: /tmp/ejected_suite/
All CHERENKOV metadata and hooks stripped successfully.
Ejected folder is 100% standard and runs standalone.
```

### Ejected client.ts (CLEAN — no CHERENKOV imports):
```typescript
// Standalone openapi-fetch client configuration
// Stripped of all trace and interception metadata.
import createClient from "openapi-fetch";
import type { paths } from "./generated-types";
export const client = createClient<paths>({
  baseUrl: process.env.API_URL ?? "http://localhost:8000",
});
```

### Ejected package.json (CLEAN — no CHERENKOV deps):
```json
{
  "name": "ejected-playwright-tests",
  "version": "1.0.0",
  "dependencies": {
    "openapi-fetch": "^0.17.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.60.0",
    "typescript": "^5.0.0"
  }
}
```

---

## Doctor Output

```
CHERENKOV doctor — system health check

  ollama binary         [OK]  /usr/local/bin/ollama
  ollama daemon         [OK]  reachable
  device                [WARN]  CPU (GPU recommended)
  model qwen2.5-coder:3b [OK]  available
  node                  [OK]  v22.23.0
  playwright            [OK]  Version 1.61.1
  prism (docker)        [OK]  Docker 29.5.1 (Prism ready)
  egress policy         [OK]  consistent
  spec files            [OK]  3 found
  demo mode             [OK]  run with --demo for first look
```

---

## HITL Queue

```
HITL queue — pending (16 item(s))
  id                          status   info
  demo-hitl-2                 pending  GET /pets/{petId}
  demo-hitl-3                 pending  POST /pets
  correct_petstore.spec       pending  conf=0.80  gate=tsc
  missing_password            pending  conf=0.80  gate=tsc
  email_too_long              pending  conf=0.80  gate=tsc
  password_too_short          pending  conf=0.80  gate=tsc
  missing_name                pending  conf=0.83  gate=prism-dryrun
  missing_species             pending  conf=0.83  gate=prism-dryrun
  demo_weakened               pending  conf=0.80  gate=assertion
  demo_deleted                pending  conf=0.80  gate=assertion
  demo_weakened_v             pending  conf=0.80  gate=assertion
  demo_deleted_v              pending  conf=0.80  gate=assertion
  golden_weakened             pending  conf=0.80  gate=assertion
  golden_deleted              pending  conf=0.80  gate=assertion
  deleted_check_petstore.spec pending  conf=0.80  gate=assertion
  weakened_assertion_petstore pending  conf=0.80  gate=assertion
```

---

## Check-Suite: Integrity Catch

```
check-suite: demo_weakened.spec.ts
  FAIL — 1 integrity violation(s):
    [CAUGHT] DELETED test case removed: 'post /users happy_path'
```

---

## HITL Approve Workflow

```
[OK] hitl.approve
  id: demo-hitl-2
  action: approve
  previous_status: pending
  current_status: approved
  actor: @demo-user
  actor_at: 2026-07-06T21:59:18Z
  rows_affected: 1
```

Queue went from 16 → 15 pending items after approval.

---

## Spec Diff: Petstore vs Target API

```
BREAKING CHANGES (19):
  [PUT] /pet — Endpoint PUT /pet was removed
  [POST] /pet — Endpoint POST /pet was removed
  [GET] /pet/findByStatus — Endpoint GET /pet/findByStatus was removed
  ... (16 more endpoints removed)

ADDITIVE CHANGES (2):
  [GET] /health — New endpoint GET /health added
  [POST] /users — New endpoint POST /users added

Run cherenkov validate to re-generate tests for affected endpoints.
```

---

## Governance Panel

```
E12 Governance KPI Panel
  Health Score:      0.70
  Escape Rate:       0.0%
  False Positive:    0.0%
  Coverage:          0.0%
  Maintenance Score: 1.00
  Pass Rate:         0/0 passed
  Active Idioms:     0
```

---

## One-Liners (cherenkov examples)

```
Validate against staging:   cherenkov validate --target https://api.staging.example.com --spec openapi.yaml
Strict CI mode:             cherenkov validate --target http://localhost:8080 --spec openapi.yaml --fail-on-drift --quiet
JSON output for JQ:         cherenkov validate --target http://localhost:8080 --spec openapi.yaml --json
Generate tests:             cherenkov generate --spec openapi.yaml --output tests/
Launch dashboard:           cherenkov dashboard 3000
Push session state:         cherenkov teleport push my_session_123
```
