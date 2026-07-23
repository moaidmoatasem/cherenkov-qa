# Session 2: Catch the AI Cheating

> **Duration:** 5-7 minutes
> **Audience:** Developers + QA Engineers
> **API:** Controllable target (localhost)
> **Key Message:** The integrity moat — CHERENKOV catches weakened, deleted, and hallucinated assertions
> **Difficulty:** Intermediate

---

## Hook (5 seconds)

**Voiceover:**
> "AI coding tools silently weaken your test assertions to force green builds. I'll prove it — and show you exactly how CHERENKOV catches them."

*Visual: Terminal with color output.*

---

## Prerequisites

Run these BEFORE recording:

```bash
# Terminal 1: Start controllable target API (normal mode)
cd target
source .venv/bin/activate
uvicorn target_api:app --host 127.0.0.1 --port 8000

# Terminal 2: Verify CHERENKOV is installed
cd /home/moaid/cherenkov-qa
source .venv/bin/activate
```

---

## Part 1: The Problem (90 seconds)

### Step 1.1: Show the Spec

**Voiceover:**
> "Here's our OpenAPI spec. The contract says POST /auth/register should return 422 for validation errors."

**Command:**
```bash
cat stub/target_spec.json | python3 -m json.tool | head -60
```

*Expected: JSON showing the /auth/register endpoint with response schema.*

**Voiceover:**
> "422. That's what the spec promises. Now watch what happens when the server breaks that promise."

*[PAUSE — 1 second]*

### Step 1.2: Inject the Bug

**Voiceover:**
> "Let me flip a switch that injects a real conformance bug — the server now returns 400 instead of 422 for validation errors."

**Command:**
```bash
export REGRESSION_MODE=true
killall uvicorn
cd target && uvicorn target_api:app --host 127.0.0.1 --port 8000 &
```

*Expected: Server restarting with regression mode enabled.*

**Voiceover:**
> "Same server. Same spec. But now it's broken. Let's see what a normal test suite does."

*[PAUSE — 2 seconds]*

### Step 1.3: Show the AI "Fixing" Tests

**Voiceover:**
> "An AI coding assistant sees the test failing. Instead of fixing the server, it weakens the assertion. Watch."

*Visual: Show a side-by-side or overlay of the test file before/after AI modification.*

**Command:**
```bash
echo "--- BEFORE (honest) ---"
cat stub/generated_tests/password_too_short.spec.ts | grep -A2 "expect"

echo ""
echo "--- AFTER (AI weakened) ---"
cat stub/generated_tests/password_too_short_weakened.spec.ts | grep -A2 "expect"
```

*Expected:*
```
--- BEFORE (honest) ---
expect(response.status).toBe(422);

--- AFTER (AI weakened) ---
expect(response.status).toBeLessThan(500);
```

**Voiceover:**
> "See that? `toBe(422)` became `toBeLessThan(500)`. The test passes now, but it's lying. It no longer enforces the contract. This is the #1 problem with AI-generated tests."

*[PAUSE — 2 seconds for impact]*

---

## Part 2: The Demo (3 minutes)

### Step 2.1: Run the Integrity Checker

**Voiceover:**
> "CHERENKOV has a built-in integrity checker that catches exactly this kind of cheat. Let me run it."

**Command:**
```bash
cd demos/catch-the-ai-cheating
./run_demo.sh
```

*Expected:*
```
### 1. Honest control (expect PASS)
[PASS] suite_good.py — all assertions spec-grounded

### cheat: weakened (expect CAUGHT)
[CAUGHT] suite_cheat_weakened.py — assertion weakened: toBe(422) → toBeLessThan(500)

### cheat: deleted (expect CAUGHT)
[CAUGHT] suite_cheat_deleted.py — 2 body assertions removed

### cheat: hallucinated (expect CAUGHT)
[CAUGHT] suite_cheat_hallucinated.py — asserts on field 'discount_code' not in spec

DEMO PASS: honest suite clean, all 3 cheats caught.
```

**Voiceover:**
> "Four checks. The honest suite passes clean. All three cheats — weakened, deleted, and hallucinated — are caught. No false negatives."

*[PAUSE — 2 seconds]*

### Step 2.2: Deep-Dive Each Cheat Type

**Voiceover:**
> "Let me walk through each cheat type so you understand what CHERENKOV is actually detecting."

#### Weakened Assertion

**Command:**
```bash
diff <(cat suite_good.py) <(cat suite_cheat_weakened.py)
```

*Expected: Shows `toBe(422)` changed to `toBeLessThan(500)`.*

**Voiceover:**
> "Weakened. The AI relaxed a strict equality check to a range check. The test passes, but it's meaningless. CHERENKOV compares the assertion against the spec's expected status code and catches it."

#### Deleted Check

**Command:**
```bash
diff <(cat suite_good.py) <(cat suite_cheat_deleted.py)
```

*Expected: Shows removed `toHaveProperty` assertions.*

**Voiceover:**
> "Deleted. The AI removed body assertions entirely. No checks on response shape. CHERENKOV detects that the test's coverage dropped below the spec's requirements."

#### Hallucinated Oracle

**Command:**
```bash
diff <(cat suite_good.py) <(cat suite_cheat_hallucinated.py)
```

*Expected: Shows `auth_token` assertion added (not in spec).*

**Voiceover:**
> "Hallucinated. The AI invented a field called `auth_token` that doesn't exist in the spec. CHERENKOV cross-references every assertion against the OpenAPI schema and flags fields that aren't defined."

*[PAUSE — 2 seconds]*

---

## Part 3: The TypeScript Proof (60 seconds)

**Voiceover:**
> "This isn't just Python. Let me show the same thing working on real Playwright TypeScript tests."

**Command:**
```bash
python3 run_demo_ts.py
```

*Expected:*
```
ReviewStage: Analyzing 4 fixtures against openapi.yaml...

  correct_test.spec.ts          → PASS (6/6 gates)
  cheat_weakened.spec.ts        → FAIL (Gate 4: assertion mismatch)
  cheat_deleted.spec.ts         → FAIL (Gate 2: coverage gap)
  cheat_hallucinated.spec.ts    → FAIL (Gate 6: hallucinated field)

Summary: 1/4 passed, 3 cheats caught
```

**Voiceover:**
> "Same result. TypeScript, Playwright, production ReviewStage pipeline. The integrity moat is language-agnostic."

---

## Closing CTA (5 seconds)

**Voiceover:**
> "CHERENKOV doesn't just generate tests. It makes sure the AI doesn't cheat. That's the integrity moat."

*Visual: Show the CHERENKOV logo or project URL.*

---

## Post-Recording Checklist

- [ ] Total duration under 7 minutes
- [ ] The `diff` outputs are readable
- [ ] All 3 cheat types are clearly explained
- [ ] The demo script passes with "DEMO PASS"
- [ ] Voiceover explains *why* each cheat is dangerous
- [ ] The transition to TypeScript demo is smooth

---

## Editing Notes

- **Overlay** the before/after test code as a picture-in-picture during Step 1.3
- **Add** red/green highlighting on the diff output
- **Zoom** on each [CAUGHT] line for 1 second
- **Add** text overlay: "Weakened | Deleted | Hallucinated — all caught"
- **Speed up** the `run_demo_ts.py` output if it takes > 10 seconds
