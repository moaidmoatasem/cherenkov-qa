# Session A: Zero to Hero Developer Quickstart

> **Target Audience:** Backend Developers and Software Engineers.
> **Format:** Loom-style walk-through with screen recording and live narration.
> **Estimated Duration:** 10 Minutes

---

## 🎬 Act 1: The Pitch & Core Architecture (2 Minutes)

**[Timing: 00:00 - 02:00]**

**[Visual: Title Slide: "CHERENKOV QA — Zero to Hero Developer Quickstart". Underneath: "OpenAPI as the Single Source of Truth". The background shows a clean VS Code layout with an OpenAPI specification next to a Playwright test file.]**

**Presenter (Voiceover):**
"Hey everyone! Welcome to CHERENKOV QA. Today, we're going to show you how to go from a bare OpenAPI specification to a fully validated, production-grade test suite in under ten minutes.

If you are building APIs today, you know that AI code generators can write hundreds of tests in seconds. But here is the problem: AI-generated tests frequently hallucinate expected values. If the AI expects the wrong status code or payload structure, it will write a test that passes even when your server is broken. We call this 'silent test erosion'.

CHERENKOV is designed on a single, uncompromising principle: **The OpenAPI Specification is the Single Source of Truth (SSOT).**

Instead of blindly trusting the LLM, CHERENKOV takes the generated tests and runs them through a series of rigid, deterministic compilation and dry-run gates. If the AI hallucinates, CHERENKOV catches it statically. If the implementation diverges from the specification, CHERENKOV flags the spec drift immediately. Let's see it in action."

---

## 🛠️ Act 2: Local Setup & Initialization (2 Minutes)

**[Timing: 02:00 - 04:00]**

**[Visual: A clean, empty WSL terminal screen inside `/home/moaid/cherenkov_onboarding`.]**

**Presenter:**
"Let's start by setting up our local workspace. First, we need to create our virtual environment, activate it, and install our Python dependencies. Then, we will configure the Node environment inside our stub directory."

**[Action: Type the setup commands in the terminal.]**

```bash
# 1. Set up the Python virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r target/requirements.txt

# 2. Navigate to the Playwright stub directory and install Node packages
cd stub
npm install
npx playwright install
cd ..
```

**Presenter:**
"Perfect. Now that our dependencies are ready, we will initialize our CHERENKOV project. The `cherenkov init` command automatically detects any OpenAPI specifications in the workspace (filenames matching `openapi.*` or `*spec*`) and creates a local configuration file called `cherenkov.toml` with offline-first, local-first settings. In this workspace it picks up the repo's own spec files — `mut_spec.json` and `stub/target_spec.json`. We'll point it at the Petstore spec explicitly in the next act."

**[Action: Type init command.]**

```bash
./bin/cherenkov init
```

**[Visual: Terminal logs showing the project initialization.]**

```
$ ./bin/cherenkov init

============================================================
  CHERENKOV init -- zero-config setup
============================================================

  [1/4] Ollama:     OK Ollama daemon is running
  [2/4] Device:     CPU
  [3/4] Spec files: 2 found
         - mut_spec.json
         - stub/target_spec.json
  [4/4] Profile:    laptop

  [OK] Generated cherenkov.toml
  [OK] Generated .github/workflows/cherenkov.yml

------------------------------------------------------------
  Next steps:
    Run:    ./bin/cherenkov doctor    # verify your setup
    Run:    ./bin/cherenkov validate --target <url>  # run tests

  Defaults: offline, free, deterministic
  Upgrade:  edit profile in cherenkov.toml, or set CHERENKOV_* env vars
============================================================
```

---

## 🚀 Act 3: Generating Tests (3 Minutes)

**[Timing: 04:00 - 07:00]**

**[Visual: Return to terminal. Download the public Petstore OpenAPI spec.]**

**Presenter:**
"With our configuration in place, let's download the classic Petstore OpenAPI specification. We'll use this spec to generate our E2E Playwright tests."

**[Action: Download spec using curl.]**

```bash
curl -s https://petstore3.swagger.io/api/v3/openapi.json -o petstore.json
```

**Presenter:**
"Now we will run `cherenkov generate`. This command will ingest the Petstore specification, extract all defined routes, plan out happy paths and boundary edge cases, and use our local LLM—a local Qwen 2.5 coder model—to generate standard TypeScript Playwright tests. We'll add the `--no-repair` flag to bypass the self-healing loop for now so we can inspect the raw generation."

**[Action: Run the generator.]**

```bash
./bin/cherenkov generate --spec petstore.json --output-dir stub/generated_tests --no-repair
```

**[Visual: Terminal output showing the ingestion and code generation logs.]**

```
$ ./bin/cherenkov generate --spec petstore.json --output-dir stub/generated_tests --no-repair

================================================================================
🤖 CHERENKOV TEST GENERATOR
================================================================================
Ingesting spec: petstore.json (32 endpoints detected)
Planning scenarios...
  - [GET]  /pet/{petId} -> happy_path, invalid_id
  - [POST] /pet -> happy_path, missing_required
  - [GET]  /store/inventory -> happy_path
  - [GET]  /user/login -> happy_path, invalid_credentials
Generating Playwright test suites...
[INFO] Routing requests to local LLM (qwen2.5-coder:7b)
✓ Generated post_pet_missing_photourls.spec.ts
✓ Generated get_store_inventory.spec.ts
✓ Generated get_pet_by_id_zero.spec.ts
✓ Generated get_user_login_headers.spec.ts
================================================================================
```

---

## 🔍 Act 4: Running Validation & Detecting Spec Drift (3 Minutes)

**[Timing: 07:00 - 10:00]**

**[Visual: A clean terminal window.]**

**Presenter:**
"Now we have our tests. But here is the critical part: we want to run these tests against the live, public Swagger Petstore API to see if the actual implementation matches the spec contract. We run the `cherenkov validate` command. 

CHERENKOV runs these tests, programmatically intercepting all HTTP exchanges, and diffs them against the spec. Let's see what happens."

**[Action: Execute validate command.]**

```bash
./bin/cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json
```

**[Visual: Terminal displaying validation results, showing the 4 conformance failures in bright red.]**

```
$ ./bin/cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json

================================================================================
🔍 CHERENKOV VALUE ASSERTION TIGHTENING REPORT
================================================================================
Target Server URL: https://petstore3.swagger.io/api/v3
Scenarios Verified: 4
================================================================================

Scenario: post_pet_missing_photourls [ FAILED ]
--------------------------------------------------------------------------------
🚫 Failure Error: Error: expect(received).toBeLessThan(500)

Expected: < 500
Received: 500

   at post_pet_missing_photourls.spec.ts:12
> 12 |   expect(response.status).toBeLessThan(500);

Captured HTTP Exchange:
  Sent Payload:     {"name":"test-dog","status":"available"}
  Received Status:  500 Internal Server Error
  Received Body:    {"code":500,"type":"unknown","message":"something went wrong"}


Scenario: get_store_inventory [ FAILED ]
--------------------------------------------------------------------------------
🚫 Failure Error: Error: expect(received).toBe(expected)

Expected: 200
Received: 500

   at get_store_inventory.spec.ts:10
> 10 |   expect(response.status).toBe(200);

Captured HTTP Exchange:
  Sent Payload:     (empty)
  Received Status:  500 Internal Server Error
  Received Body:    {"code":500,"message":"There was an error processing your request..."}


Scenario: get_pet_by_id_zero [ FAILED ]
--------------------------------------------------------------------------------
🚫 Failure Error: Error: expect(received).toBe(expected)

Expected: 400
Received: 500

   at get_pet_by_id_zero.spec.ts:8
> 8 |   expect(response.status).toBe(400);

Captured HTTP Exchange:
  Sent Payload:     (empty)
  Received Status:  500 Internal Server Error
  Received Body:    {"code":500,"message":"something went wrong"}


Scenario: get_user_login_headers [ FAILED ]
--------------------------------------------------------------------------------
🚫 Failure Error: Error: expect(received).not.toBeUndefined()

Expected: header X-Rate-Limit not undefined
Received: undefined

   at get_user_login_headers.spec.ts:15
> 15 |   expect(response.headers['x-rate-limit']).toBeDefined();

Captured HTTP Exchange:
  Sent Payload:     (empty)
  Received Status:  200 OK
  Received Headers: { "content-type": "application/json", "content-length": "42" }

================================================================================
Git status verification:
✓ Git status is 100% clean — zero test files were auto-modified by validation. Suggest-only constraint honored.
================================================================================
```

**Presenter:**
"Look at that output! CHERENKOV has exposed **four major conformance bugs** between the public Swagger Petstore API and its official specification:

1. **D1 (POST /pet)**: The spec lists `photoUrls` as a required field. The server should validate and return a `4xx` error if omitted. Instead, the server crashes and returns a `500 Internal Server Error`.
2. **D2 (GET /store/inventory)**: The spec defines this endpoint as returning status counts. Instead, the live production server completely fails with a `500` error code.
3. **D3 (GET /pet/{petId})**: The spec promises that sending `petId=0` will return a `400 Bad Request` ('Invalid ID supplied'). However, the live server returns a `500` crash.
4. **D4 (GET /user/login)**: The spec dictates that a successful login must return headers `X-Rate-Limit` and `X-Expires-After`. The live server returns `200 OK`, but omits these headers entirely.

And notice that final line: CHERENKOV leaves our Git status 100% clean. It suggests tightening assertions but respects our strict **suggest-only** design invariant, preventing the tool from ever mutating your test codebase without human consent.

You've just initialized, generated, and uncovered four real-world API drifts in less than ten minutes. In the next session, we'll dive into how CHERENKOV heals these issues. Thanks for watching!"
