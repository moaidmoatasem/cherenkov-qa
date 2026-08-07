# Session B: Advanced QA Lead Guide & Live Case Study

> **Target Audience:** QA Leads, SDETs, and QA Managers.
> **Format:** Advanced step-by-step Loom-style workflow demonstration.
> **Estimated Duration:** 15 Minutes

---

## 🎬 Act 1: Mocking Complex APIs with Prism (3 Minutes)

**[Timing: 00:00 - 03:00]**

**[Visual: Slide: "Session B: Advanced QA Lead Guide". Subtext: "Mocking, Self-Healing, HITL, and Ejecting". The slide shows the workflow diagram: Spec -> Prism -> Generator -> Validate -> HITL Queue -> Eject.]**

**Presenter (Voiceover):**
"Welcome back! In our first session, we saw the Zero-to-Hero setup against the public Petstore. Today, we're taking it to the next level. We're going to look at how QA Leads and SDETs can use CHERENKOV on complex enterprise APIs, manage human-in-the-loop validation, self-heal generated code, and completely eject the tests to vanilla Playwright to avoid vendor lock-in.

When testing complex APIs like Stripe, you don't want to hit the live sandbox with random generated traffic—you'll run into rate limits, data pollution, and high latency. Instead, we use **Prism**, an open-source mock server that serves a fully typed, spec-compliant replica of the Stripe API locally."

**[Action: Switch screen to terminal. Navigate to the demo directory and view the docker-compose file.]**

```bash
# Navigate to the live-case demo directory
cd demos/live-case-data/

# Start the local Prism mock server
docker-compose up -d
```

**[Visual: Terminal logs showing Docker spinning up the Prism mock server.]**

```
$ docker-compose up -d
Creating network "live-case-data_default" with the default driver
Pulling prism (stoplight/prism:5)...
Creating live-case-data_prism_1 ... done
Prism mock server is listening on http://localhost:4010
```

**Presenter:**
"Now we have a local, high-fidelity replica of the Stripe Charges API running on port 4010. Any request sent to it must match Stripe's strict OpenAPI definition down to the exact field type, or it will be rejected."

---

## 🤖 Act 2: Spec-Driven Code Generation & `--repair` Self-Healing (4 Minutes)

**[Timing: 03:00 - 07:00]**

**[Visual: Terminal window showing generation command.]**

**Presenter:**
"Stripe payloads are notoriously complex, with nested metadata and strict constraints. If the LLM generates a slightly incorrect type, standard test frameworks would fail.

But CHERENKOV uses a multi-gate generator. If we pass the `--repair` flag, CHERENKOV will run a 6-gate review process. Gate 6 performs a dry-run against our local Prism mock. If Prism rejects the LLM's payload, CHERENKOV captures the exact validation error, packages it up, and feeds it back to the LLM to fix itself. Let's run it."

**[Action: Type and run the generate command with --repair.]**

```bash
cherenkov generate --spec stripe_spec.json --output-dir tests-stripe/ --repair
```

**[Visual: Terminal shows CHERENKOV running, failing Gate 6, and performing self-healing.]**

```
$ cherenkov generate --spec stripe_spec.json --output-dir tests-stripe/ --repair

================================================================================
🤖 CHERENKOV MULTI-GATE GENERATION LOOP
================================================================================
Ingesting spec: stripe_spec.json (Charges endpoint)
Scenario Plan: create_charge_happy_path, create_charge_bad_card

[Attempt 1] Generating create_charge_happy_path.spec.ts...
Running Verification Gates:
  ✓ Gate 1: Syntax check passed
  ✓ Gate 2: Spec structure compliance passed
  ✓ Gate 3: AST validation passed
  ✓ Gate 4: Assertion validation passed
  ✓ Gate 5: TSC compiler (tsc --noEmit) passed
  ❌ Gate 6: Prism Dry-Run FAILED!
     [Prism Error]: /request/body/amount must be integer (received float: 29.99)

[Attempt 2] Triggering Self-Healing Loop...
  Sending validation failure logs to local LLM for repair...
  Regenerating test...
Running Verification Gates:
  ✓ Gate 1: Syntax check passed
  ✓ Gate 2: Spec structure compliance passed
  ✓ Gate 3: AST validation passed
  ✓ Gate 4: Assertion validation passed
  ✓ Gate 5: TSC compiler (tsc --noEmit) passed
  ✓ Gate 6: Prism Dry-Run PASSED!
     [Prism Status]: 200 OK (Payload matches spec schema perfectly)

✓ Success! Generated create_charge_happy_path.spec.ts after 1 self-healing repair.
================================================================================
```

**Presenter:**
"See that? On the first attempt, the LLM generated a decimal number for the Stripe payment amount, but Stripe requires payments in cents (integers). Gate 6 caught the Prism validation error, prompted the LLM with the error log, and the LLM successfully repaired the code to use an integer. That is the power of deterministic verification loops."

---

## 🔍 Act 3: Finding Bugs & Human-in-the-Loop Triage (5 Minutes)

**[Timing: 07:00 - 12:00]**

**[Visual: Terminal screen.]**

**Presenter:**
"Now let's switch gears and validate our target API. We'll run the validation command against our target app running on port 8000."

**[Action: Run validate command against target API.]**

```bash
./bin/cherenkov validate --target http://localhost:8000
```

**[Visual: Terminal showing validation output with a failed test and a HITL queue item.]**

```
$ ./bin/cherenkov validate --target http://localhost:8000

================================================================================
🔍 CHERENKOV VALUE ASSERTION TIGHTENING REPORT
================================================================================
Target Server URL: http://localhost:8000
Scenarios Verified: 3
================================================================================

Scenario: happy_path [ PASSED ]
--------------------------------------------------------------------------------
Captured HTTP Exchange:
  Sent Payload:     {"email":"test@example.com","password":"password123"}
  Received Response: {"id":42,"email":"test@example.com"}

💡 Suggested Assertion Tightening (Suggest-only):
  consider -> expect(data.email).toBe('test@example.com')
  consider -> expect(data.email).toBe(body.email)


Scenario: password_too_short [ FAILED ]
--------------------------------------------------------------------------------
🚫 Failure Error: Error: expect(received).toBe(expected) // Object.is equality

Expected: 422
Received: 400

   at password_too_short.spec.ts:8
> 8 |   expect(response.status).toBe(422);

Captured HTTP Exchange:
  Sent Payload:     {"email":"test@example.com","password":"short"}
  Received Status:  400 Bad Request
  Received Body:    {"detail":"Password must be at least 8 characters"}


Scenario: create_user_missing_email [ HITL REVIEW REQUIRED ]
--------------------------------------------------------------------------------
💡 Review Triggered:
  Quality Score: 0.78 (HITL Threshold: 0.70 - 0.90)
  Failed Gate:   gate_3_ast (Confidence Check)
  Endpoint:      POST /users
  Item enqueued: ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
================================================================================
```

**Presenter:**
"Let's look at what happened here.
First, our `password_too_short` test failed. The spec promises that sending a short password will return a `422 Unprocessable Entity` validation error. However, our actual FastAPI target server returned `400 Bad Request`. That is a classic status code mismatch drift bug!

Second, our `create_user_missing_email` test was enqueued in the **Human-in-the-Loop (HITL)** queue. Why? Because the LLM generated a test that got a confidence score of 0.78, falling right into our validation boundary. CHERENKOV refuses to make silent decisions on ambiguous tests. Instead, it puts them in a durable SQLite database so a human reviewer can triage them.

Let's check the HITL queue from our terminal."

**[Action: Type HITL command to list pending items.]**

```bash
./bin/cherenkov hitl list
```

**[Visual: Terminal logs showing the pending items.]**

```
$ ./bin/cherenkov hitl list
HITL queue — pending (1 item(s))
  id                                    status      info
  ------------------------------------  ----------  ----
  ck_1bc8ef7a-39c1-4b10-a9fa-80e98f...  pending     conf=0.78  gate=gate_3_ast  POST /users
```

**Presenter:**
"We can inspect this item in detail to see why the AST check failed."

**[Action: Type show command.]**

```bash
./bin/cherenkov hitl show ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
```

**[Visual: Details of the HITL item.]**

```
$ ./bin/cherenkov hitl show ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
HITL item: ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a
  status:             pending
  method/endpoint:    POST /users
  confidence:         0.78
  failed gate:        gate_3_ast
  run ID:             run_20260604T120000Z
  created at:         2026-06-04T12:00:05Z
```

**Presenter:**
"Everything looks clean. We can approve the test scenario right from the terminal using the `approve` command with a JSON flag to integrate it into external tooling."

**[Action: Approve the item.]**

```bash
./bin/cherenkov hitl approve ck_1bc8ef7a-39c1-4b10-a9fa-80e98ffb191a --actor @alice --json
```

**[Visual: JSON response output from approval command.]**

```json
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
```

**Presenter:**
"Approved! And for teams that prefer visual triaging over CLI, we can launch the local web interface."

**[Action: Type review web launch command.]**

```bash
./bin/cherenkov review --demo
```

**[Visual: Switch view to browser displaying the CHERENKOV Dashboard, specifically focusing on the Triage (Kanban) workspace showing divergence claims and evidence.]**

**Presenter:**
"This brings up our pre-built web dashboard. QA engineers can manage their work across the 5-hub workspace, author test journeys, triage divergence claims in the Kanban view, and inspect evidence payloads."

---

## 🏃 Act 4: The Eject Command & Zero Vendor Lock-in (3 Minutes)

**[Timing: 12:00 - 15:00]**

**[Visual: Return to terminal.]**

**Presenter:**
"Now, the number one fear with AI test tools is vendor lock-in. What happens if you stop using the tool? Do you lose your tests? With CHERENKOV, the answer is absolutely not. 

We provide the `eject` command. This copies the generated specifications and TypeScript compiler configurations, strips out all CHERENKOV-specific interception metadata, and emits standard Playwright tests."

**[Action: Run eject command.]**

```bash
./bin/cherenkov eject --output ejected_suite
```

**[Visual: Terminal showing ejection files.]**

```
$ ./bin/cherenkov eject --output ejected_suite
================================================================================
🏃 CHERENKOV SUITE EJECTION
================================================================================
Ejecting to directory: ejected_suite
✓ Copied Playwright configuration...
✓ Emitted clean client.ts (stripped of trace metadata)...
✓ Cleaned TypeScript compiler configurations...
✓ Standard package.json written...
✓ Standalone test suite is ready!
================================================================================
```

**Presenter:**
"Let's navigate into that ejected directory and inspect the files."

**[Action: List files and run npm install & test.]**

```bash
cd ejected_suite
ls
npm install
npx playwright test
```

**[Visual: Terminal showing vanilla Playwright running and passing tests.]**

```
$ cd ejected_suite && npx playwright test

Running 3 tests using 1 worker
  ✓  happy_path.spec.ts (120ms)
  ✓  create_charge_happy_path.spec.ts (155ms)
  ✓  create_user_missing_email.spec.ts (95ms)

  3 passed (370ms)
```

**Presenter:**
"Look at that. Vanilla Playwright, standard `openapi-fetch` client, running with zero dependency on the CHERENKOV runtime. If you choose to walk away from CHERENKOV tomorrow, your tests still run, and your team keeps all the generated assets.

In this session, we mocked the Stripe API using Prism, watched CHERENKOV self-heal integer validation issues, triaged our HITL review queue via CLI, and ejected our entire test suite to vanilla Playwright. 

This is the robust, developer-first tooling that scales quality engineering. Thanks for watching!"
