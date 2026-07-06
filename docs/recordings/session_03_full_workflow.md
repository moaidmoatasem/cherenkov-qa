# Session 3: Spec to Verified Suite (Full Workflow)

> **Duration:** 7-10 minutes
> **Audience:** QA Engineers / SDETs
> **API:** Controllable target (localhost)
> **Key Message:** End-to-end QA workflow — generate, validate, find drift, fix, eject
> **Difficulty:** Intermediate

---

## Hook (5 seconds)

**Voiceover:**
> "I'll show you the complete CHERENKOV workflow — from OpenAPI spec to a verified, ejected Playwright test suite that catches a real conformance bug."

*Visual: Split screen — terminal left, spec file right.*

---

## Prerequisites

Run these BEFORE recording:

```bash
# Terminal 1: Start controllable target (normal mode — no bugs)
cd /home/moaid/cherenkov-qa/target
source .venv/bin/activate
uvicorn target_api:app --host 127.0.0.1 --port 8000

# Terminal 2: Main workspace
cd /home/moaid/cherenkov-qa
source .venv/bin/activate
```

---

## Part 1: Understand the Contract (90 seconds)

### Step 1.1: Show the OpenAPI Spec

**Voiceover:**
> "This is our OpenAPI spec. Two endpoints. Clean contract."

**Command:**
```bash
cat stub/target_spec.json | python3 -m json.tool
```

*Expected:*
```json
{
  "openapi": "3.0.0",
  "info": { "title": "Target API", "version": "1.0.0" },
  "paths": {
    "/auth/register": {
      "post": {
        "operationId": "register",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                  "email": { "type": "string", "format": "email" },
                  "password": { "type": "string", "minLength": 8 }
                }
              }
            }
          }
        },
        "responses": {
          "201": { "description": "User created" },
          "422": { "description": "Validation error" }
        }
      }
    }
  }
}
```

**Voiceover:**
> "POST /auth/register. Returns 201 on success, 422 on validation error. Simple contract. Now let's generate tests from it."

*[PAUSE — 1 second]*

### Step 1.2: Show the Server

**Voiceover:**
> "Our server is running locally on port 8000. It matches the spec — for now."

**Command:**
```bash
curl -s http://localhost:8000/openapi.json | python3 -m json.tool | head -20
```

*Expected: Server's OpenAPI spec output.*

**Voiceover:**
> "Server is live and serving its spec. Let's generate tests."

---

## Part 2: Generate the Suite (2 minutes)

### Step 2.1: Generate Tests

**Voiceover:**
> "Generate a full Playwright test suite from the spec."

**Command:**
```bash
cherenkov generate --spec stub/target_spec.json --output-dir stub/generated_tests/ --no-repair
```

*Expected:*
```
Ingesting spec... 2 endpoints found
Planning scenarios... 6 test cases
Generating via local LLM (qwen2.5-coder:7b)...
Gate 1: Syntax check — PASS
Gate 2: AST validation — PASS
Gate 3: Type check — PASS
Gate 4: Assertion verification — PASS
Gate 5: Dry-run — PASS
Gate 6: Spec alignment — PASS

Generated 6 test scenarios → stub/generated_tests/
```

**Voiceover:**
> "6 tests. Happy paths, error cases, validation checks. All spec-derived."

### Step 2.2: Inspect a Generated Test

**Voiceover:**
> "Let's look at what was generated. Standard Playwright TypeScript."

**Command:**
```bash
cat stub/generated_tests/happy_path.spec.ts
```

*Expected:*
```typescript
import { test, expect } from '@playwright/test';
import createClient from 'openapi-fetch';
import type { paths } from './generated-types';

const client = createClient<paths>({ baseUrl: 'http://localhost:8000' });

test('POST /auth/register — happy path', async () => {
  const body = { email: 'test@example.com', password: 'password123' };
  const { data, error } = await client.POST('/auth/register', { body });
  expect(error).toBeFalsy();
  expect(data).toHaveProperty('id');
  expect(data).toHaveProperty('email');
  expect(data.email).toBe('test@example.com');
});
```

**Voiceover:**
> "No magic. Standard Playwright, standard openapi-fetch client. You can read every line. Assertions are derived from the spec's response schema."

*[PAUSE — 2 seconds]*

---

## Part 3: Validate Against Live Server (2 minutes)

### Step 3.1: Run Validation

**Voiceover:**
> "Now run the suite against our live server."

**Command:**
```bash
cherenkov validate --target http://localhost:8000 --spec stub/target_spec.json
```

*Expected:*
```
================================================================================
CHERENKOV VALUE ASSERTION TIGHTENING REPORT
================================================================================
Target Server URL: http://localhost:8000
Scenarios Verified: 6
================================================================================

Scenario: happy_path [PASSED]
--------------------------------------------------------------------------------
  Sent Payload:     {"email":"test@example.com","password":"password123"}
  Received Response: {"id":42,"email":"test@example.com"}

  Suggested Assertion Tightening (Suggest-only):
    consider -> expect(data.email).toBe('test@example.com')

Scenario: password_too_short [PASSED]
--------------------------------------------------------------------------------
  Sent Payload:     {"email":"test@example.com","password":"short"}
  Received Response: {"detail":"Validation Error"}

  Suggested Assertion Tightening (Suggest-only):
    No value matching suggestions detected.

...

Git status verification:
  Git status is 100% clean — zero test files were auto-modified by validation. Suggest-only constraint honored.
```

**Voiceover:**
> "All pass. Server matches spec. Notice the tightening suggestions — CHERENKOV suggests improvements but never auto-applies. Suggest-only healing."

*[PAUSE — 2 seconds]*

---

## Part 4: Inject and Catch a Bug (2 minutes)

### Step 4.1: Inject Conformance Drift

**Voiceover:**
> "Now let's break the server. I'll flip a switch that makes it return 400 instead of 422 for validation errors."

**Command:**
```bash
export REGRESSION_MODE=true
killall uvicorn
cd target && uvicorn target_api:app --host 127.0.0.1 --port 8000 &
```

*Expected: Server restarting.*

**Voiceover:**
> "Same server. Same spec. But now it's lying."

*[PAUSE — 2 seconds]*

### Step 4.2: Re-run Validation

**Voiceover:**
> "Let's re-run the exact same validation."

**Command:**
```bash
cd /home/moaid/cherenkov-qa
cherenkov validate --target http://localhost:8000 --spec stub/target_spec.json
```

*Expected:*
```
Scenario: happy_path [PASSED]

Scenario: password_too_short [FAILED]
--------------------------------------------------------------------------------
  Failure Error: Error: expect(received).toBe(expected) // Object.is equality

  Expected: 422
  Received: 400

     at password_too_short.spec.ts:8

  6 |     body: { email: 'test@example.com', password: 'short' }
  7 |   });
> 8 |   expect(response.status).toBe(422);
    |                           ^
  9 | });

Git status verification:
  Git status is 100% clean — zero test files were auto-modified by validation. Suggest-only constraint honored.
```

**Voiceover:**
> "There it is. Expected 422 — what the spec promises. Got 400 — what the server actually returns. That's a real conformance drift bug. The test caught it without anyone writing it by hand."

*[PAUSE — 3 seconds for impact]*

---

## Part 5: Eject to Standalone (60 seconds)

### Step 5.1: Eject the Suite

**Voiceover:**
> "Now let's eject the entire suite to standalone Playwright. Zero lock-in."

**Command:**
```bash
cherenkov eject --output /tmp/ejected_suite
```

*Expected:*
```
Ejected 6 test files + client.ts + generated-types.ts
Output: /tmp/ejected_suite/
No CHERENKOV dependencies remain.
```

### Step 5.2: Verify Standalone

**Voiceover:**
> "Let's verify it's truly standalone."

**Command:**
```bash
ls /tmp/ejected_suite/
grep -r "cherenkov" /tmp/ejected_suite/ || echo "No CHERENKOV references found"
```

*Expected:*
```
client.ts
generated-types.ts
happy_path.spec.ts
password_too_short.spec.ts
...

No CHERENKOV references found
```

**Voiceover:**
> "Zero CHERENKOV references. This is vanilla Playwright. If you stop using the tool tomorrow, your tests still run."

*[PAUSE — 2 seconds]*

---

## Closing CTA (5 seconds)

**Voiceover:**
> "Full workflow: spec → generate → validate → catch drift → eject. No lock-in. No hallucinated tests. That's CHERENKOV."

*Visual: Project URL.*

---

## Post-Recording Checklist

- [ ] Total duration under 10 minutes
- [ ] The spec is readable on screen
- [ ] The drift detection (422 vs 400) is clearly visible
- [ ] The eject output shows zero CHERENKOV references
- [ ] Voiceover explains *why* each step matters for QA
- [ ] The "suggest-only healing" constraint is mentioned

---

## Editing Notes

- **Split screen** during Part 1 (spec left, server right)
- **Overlay** the test code as a callout during Step 2.2
- **Red highlight** on "Expected: 422 / Received: 400" during Step 4.2
- **Speed up** `cherenkov generate` wait time to 4x
- **Add** text overlay: "100% clean — no files auto-modified" after validation
