# Session 4: Live Case — Real API

> **Duration:** 5-7 minutes
> **Audience:** Developers + QA Engineers
> **API:** JSONPlaceholder (live public API)
> **Key Message:** Real test data, real network calls, no mocks
> **Difficulty:** Beginner-Intermediate

---

## Hook (5 seconds)

**Voiceover:**
> "No mocks. No local servers. Let's generate a test suite and run it against a real production API — live, across the internet."

*Visual: Terminal with `curl` to jsonplaceholder.typicode.com proving it's live.*

---

## Prerequisites

Run these BEFORE recording:

```bash
# Verify internet connectivity
curl -s https://jsonplaceholder.typicode.com/posts/1 | head -5

# CHERENKOV installed and venv active
cd /home/moaid/cherenkov-qa
source .venv/bin/activate
```

---

## Part 1: The Spec (60 seconds)

### Step 1.1: Show the JSONPlaceholder Spec

**Voiceover:**
> "We have a minimal OpenAPI spec defining JSONPlaceholder's /posts endpoint. Standard REST — GET, POST, PUT, DELETE."

**Command:**
```bash
cat demos/live-case-data/jsonplaceholder_spec.json | python3 -m json.tool
```

*Expected: OpenAPI 3.0 spec with /posts endpoints, request/response schemas.*

**Voiceover:**
> "This is a minimal spec for demonstration. We define what the API should do — and CHERENKOV will verify it actually does that."

### Step 1.2: Prove It's Live

**Voiceover:**
> "Let me prove we're hitting a real server."

**Command:**
```bash
curl -s https://jsonplaceholder.typicode.com/posts/1 | python3 -m json.tool
```

*Expected:*
```json
{
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur..."
}
```

**Voiceover:**
> "Real data. Real server. Across the internet. Now let's generate tests for it."

*[PAUSE — 1 second]*

---

## Part 2: Generate Against a Live API (2 minutes)

### Step 2.1: Generate Tests

**Voiceover:**
> "Generate a test suite from the spec."

**Command:**
```bash
cd demos/live-case-data
cherenkov generate --spec jsonplaceholder_spec.json --output-dir tests-jsonplaceholder/ --no-repair
```

*Expected:*
```
Ingesting spec... 4 endpoints found (GET /posts, POST /posts, PUT /posts/{id}, DELETE /posts/{id})
Planning scenarios... 12 test cases
Generating via local LLM...
Gate 1-6: PASS

Generated 12 test scenarios → tests-jsonplaceholder/
```

**Voiceover:**
> "12 tests generated. Happy paths, error cases, CRUD operations. All from a 20-line spec."

### Step 2.2: Show a Generated Test

**Command:**
```bash
cat tests-jsonplaceholder/happy_path.spec.ts
```

*Expected:*
```typescript
import { test, expect } from '@playwright/test';
import createClient from 'openapi-fetch';
import type { paths } from './generated-types';

const client = createClient<paths>({ baseUrl: 'https://jsonplaceholder.typicode.com' });

test('GET /posts/{id} — happy path', async () => {
  const { data, error } = await client.GET('/posts/{id}', {
    params: { path: { id: 1 } }
  });
  expect(error).toBeFalsy();
  expect(data).toHaveProperty('id');
  expect(data).toHaveProperty('title');
  expect(data).toHaveProperty('body');
  expect(data).toHaveProperty('userId');
});
```

**Voiceover:**
> "Standard Playwright. Hitting the real JSONPlaceholder API. Assertions from the spec. Readable, maintainable, real."

*[PAUSE — 2 seconds]*

---

## Part 3: Validate Against Production (2 minutes)

### Step 3.1: Run Validation

**Voiceover:**
> "Now the real test — run the suite against the production JSONPlaceholder API."

**Command:**
```bash
cherenkov validate --target https://jsonplaceholder.typicode.com --spec jsonplaceholder_spec.json
```

*Expected:*
```
Running 12 scenarios against https://jsonplaceholder.typicode.com...

  ✓ GET /posts/{id}            happy_path              200 OK
  ✓ GET /posts/{id}            not_found               404
  ✓ POST /posts                happy_path              201 Created
  ✓ POST /posts                missing_title           422
  ✓ PUT /posts/{id}            happy_path              200 OK
  ✓ DELETE /posts/{id}         happy_path              200 OK
  ...

Results: 12/12 passed [SUCCESS]
```

**Voiceover:**
> "12 out of 12. Every test passed against a real production API. Real HTTP requests, real responses, real validation. No mocks anywhere in this pipeline."

*[PAUSE — 2 seconds]*

### Step 3.2: Show the Report

**Command:**
```bash
cat .cherenkov/report.sarif | python3 -m json.tool | head -40
```

*Expected: SARIF report with test results.*

**Voiceover:**
> "SARIF report generated. Machine-readable. Ready to pipe into GitHub Code Scrolling, SonarQube, or your CI dashboard."

---

## Part 4: What Just Happened (30 seconds)

**Voiceover:**
> "Let me recap. In under 2 minutes, we:
> 1. Took a minimal OpenAPI spec
> 2. Generated 12 Playwright tests via local LLM
> 3. Verified every assertion against the spec
> 4. Ran all 12 against a real production API
> 5. Got a SARIF report ready for CI
>
> Zero mocks. Zero local servers. Real test data. That's the CHERENKOV difference."

---

## Closing CTA (5 seconds)

**Voiceover:**
> "Try it with your own API. `cherenkov generate --spec your-spec.yaml`."

*Visual: Project URL.*

---

## Post-Recording Checklist

- [ ] Total duration under 7 minutes
- [ ] `curl` output proves the API is live
- [ ] Generated tests are readable on screen
- [ ] All 12 tests pass
- [ ] Voiceover emphasizes "no mocks" at least twice
- [ ] The SARIF report is shown

---

## Editing Notes

- **Overlay** a world map graphic showing "request travels to jsonplaceholder.typicode.com" during validation
- **Speed up** `cherenkov generate` to 4x
- **Add** text overlay: "Live API — No Mocks" during Step 3.1
- **Zoom** on "12/12 passed" for 2 seconds
