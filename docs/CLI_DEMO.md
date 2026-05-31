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


[1;32m$ # 100% SUCCESS: The suite correctly caught the 400 Bad Request spec-drift regression![0m
```
