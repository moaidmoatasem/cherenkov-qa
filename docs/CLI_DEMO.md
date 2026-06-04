# CHERENKOV CLI Terminal Flow Demo

This terminal recording simulation demonstrates the end-to-end flow of CHERENKOV:
1. **Validating Happy Path (Green)** against standard Target API.
2. **Injecting Conformance Drift Bug** (FastAPI ValidationError status 400).
3. **Catching Mismatches (Red)** showing expected 422 vs received 400 conformance failures.

---

## ⏺️ Terminal Playback Recording

```ansi
[1;36m$ ./bin/cherenkov validate --target http://localhost:8000[0m

================================================================================
🔍 CHERENKOV VALUE ASSERTION TIGHTENING REPORT
================================================================================
Target Server URL: http://localhost:8000
Scenarios Verified: 2
================================================================================

Scenario: happy_path [[1;32mPASSED[0m]
--------------------------------------------------------------------------------
Captured HTTP Exchange:
  Sent Payload:     {"email":"test@example.com","password":"password123"}
  Received Response: {"id":42,"email":"test@example.com"}

💡 Suggested Assertion Tightening (Suggest-only):
  consider -> expect(data.email).toBe('test@example.com')
  consider -> expect(data.email).toBe(body.email)

Scenario: password_too_short [[1;32mPASSED[0m] (Running Against Spec Spec-conformance Mock)
--------------------------------------------------------------------------------
Captured HTTP Exchange:
  Sent Payload:     {"email":"test@example.com","password":"short"}
  Received Response: {"detail":"Validation Error"}

💡 Suggested Assertion Tightening (Suggest-only):
  No value matching suggestions detected.

================================================================================
Git status verification:
✓ Git status is 100% clean — zero test files were auto-modified by validation. Suggest-only constraint honored.
================================================================================


[1;33m# --- INJECTING REGRESSION CONFORMANCE BUG ---[0m
[1;36m$ export REGRESSION_MODE=true[0m
[1;36m$ killall uvicorn && cd target && uvicorn target_api:app --host 127.0.0.1 --port 8000 &[0m
[1] 43810
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)

[1;36m$ cd .. && ./bin/cherenkov validate --target http://localhost:8000[0m

================================================================================
🔍 CHERENKOV VALUE ASSERTION TIGHTENING REPORT
================================================================================
Target Server URL: http://localhost:8000
Scenarios Verified: 2
================================================================================

Scenario: happy_path [[1;32mPASSED[0m]
--------------------------------------------------------------------------------
Captured HTTP Exchange:
  Sent Payload:     {"email":"test@example.com","password":"password123"}
  Received Response: {"id":42,"email":"test@example.com"}

💡 Suggested Assertion Tightening (Suggest-only):
  consider -> expect(data.email).toBe('test@example.com')
  consider -> expect(data.email).toBe(body.email)

Scenario: password_too_short [[1;31mFAILED[0m]
--------------------------------------------------------------------------------
🛑 Failure Error: Error: expect(received).toBe(expected) // Object.is equality

[1;31mExpected: 422[0m
[32mReceived: 400[0m

   at password_too_short.spec.ts:8

  6 |     body: { email: 'test@example.com', password: 'short' }
  7 |   });
> 8 |   expect(response.status).toBe(422);
    |                           ^
  9 | });
    at /home/moaid/cherenkov-qa/stub/generated_tests/password_too_short.spec.ts:8:27

================================================================================
Git status verification:
✓ Git status is 100% clean — zero test files were auto-modified by validation. Suggest-only constraint honored.
================================================================================


 [1;32m$ # 100% SUCCESS: The suite correctly caught the 400 Bad Request spec-drift regression! [0m
```

---

## ⏺️ HITL Terminal Queue Flow (A3 #111)

This terminal recording simulation demonstrates the workflow when a `REVIEW` stage generates a Human-In-The-Loop review finding and it is resolved via the CLI:

```ansi
 [1;36m$ ./bin/cherenkov validate --target http://localhost:8000 [0m

================================================================================
🔍 CHERENKOV VALUE ASSERTION TIGHTENING REPORT
================================================================================
Target Server URL: http://localhost:8000
Scenarios Verified: 3
================================================================================

Scenario: happy_path [ [1;32mPASSED [0m]
Scenario: create_user_missing_email [ [1;33mHITL REVIEW REQUIRED [0m]
--------------------------------------------------------------------------------
💡 Review Triggered:
  Quality Score: 0.78 (HITL Threshold: 0.70 - 0.90)
  Failed Gate:   gate_3_ast (Confidence Check)
  Endpoint:      POST /users
  Item enqueued: ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
--------------------------------------------------------------------------------

 [1;36m$ ./bin/cherenkov hitl list [0m
HITL queue — pending (1 item(s))
  id                                    status      info
  ------------------------------------  ----------  ----
  ck_1bc8ef7a-39c1-4b10-a9fa-80e98f...  pending     conf=0.78  gate=gate_3_ast  POST /users

 [1;36m$ ./bin/cherenkov hitl show ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a [0m
HITL item: ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
  status:             pending
  method/endpoint:    POST /users
  confidence:         0.78
  failed gate:        gate_3_ast
  run ID:             run_20260604T120000Z
  created at:         2026-06-04T12:00:05Z

 [1;36m$ ./bin/cherenkov hitl approve ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a --actor @alice --json [0m
{
  "schema_version": "hitl/v1",
  "ok": true,
  "command": "hitl.approve",
  "payload": {
    "id": "ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a",
    "action": "approve",
    "previous_status": "pending",
    "current_status": "approved",
    "actor": "@alice",
    "actor_at": "2026-06-04T12:01:10Z",
    "rows_affected": 1
  },
  "error": null
}

 [1;36m$ ./bin/cherenkov hitl list --all [0m
HITL queue — all (1 item(s))
  id                                    status      info
  ------------------------------------  ----------  ----
  ck_1bc8ef7a-39c1-4b10-a9fa-80e98f...  approved    conf=0.78  actor=@alice  POST /users

 [1;32m$ # 100% SUCCESS: HITL review items correctly listed, inspected, and approved! [0m
```
