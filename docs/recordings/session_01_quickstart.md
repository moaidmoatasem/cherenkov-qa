# Session 1: 60-Second Quickstart

> **Duration:** 2-3 minutes
> **Audience:** Developers
> **API:** Petstore (live public API)
> **Key Message:** Speed + zero-config
> **Difficulty:** Beginner

---

## Hook (5 seconds)

**Voiceover:**
> "I'll go from zero to a verified API test suite in under 60 seconds. No mocks. No config files. Just one command."

*Visual: Clean terminal, cursor blinking at prompt.*

---

## Prerequisites

Run these BEFORE recording:

```bash
# Python venv activated
source .venv/bin/activate

# Ollama running (for LLM generation)
ollama serve &

# Pull the model (one-time)
ollama pull qwen2.5-coder:7b

# Node.js + Playwright installed
npm install -g playwright
npx playwright install --with-deps chromium
```

---

## Step 1: Install CHERENKOV (10 seconds)

**Voiceover:**
> "First, install CHERENKOV."

**Command:**
```bash
pip install cherenkov-qa
```

*Expected: Installation success message.*

**Voiceover:**
> "Done. One package."

*[PAUSE — 1 second]*

---

## Step 2: Initialize Project (10 seconds)

**Voiceover:**
> "Now, initialize a project with zero config."

**Command:**
```bash
mkdir /tmp/quickstart && cd /tmp/quickstart
cherenkov init
```

*Expected:*
```
Created cherenkov.toml with defaults:
  - Spec source: local file
  - Emitter: playwright
  - Oracle: spec + prism
  - LLM: ollama/qwen2.5-coder:7b
```

**Voiceover:**
> "One config file. Sensible defaults. Ready to go."

*[PAUSE — 1 second]*

---

## Step 3: Get a Spec (10 seconds)

**Voiceover:**
> "Grab the standard Petstore OpenAPI spec."

**Command:**
```bash
curl -s https://petstore3.swagger.io/api/v3/openapi.json -o petstore.json
```

*Expected: File downloaded silently.*

**Voiceover:**
> "38 endpoints. Full contract. Ready."

*[PAUSE — 1 second]*

---

## Step 4: Generate Tests (15 seconds)

**Voiceover:**
> "Generate the test suite. Watch CHERENKOV plan scenarios, call the LLM, and verify against the spec — all in one pass."

**Command:**
```bash
cherenkov generate --spec petstore.json --output-dir tests/ --no-repair
```

*Expected (may take 30-60 seconds on first run):*
```
Ingesting spec... 38 endpoints found
Planning scenarios... 102 test cases
Generating via local LLM (qwen2.5-coder:7b)...
Gate 1: Syntax check — PASS
Gate 2: AST validation — PASS
Gate 3: Type check — PASS
Gate 4: Assertion verification — PASS
Gate 5: Dry-run — PASS
Gate 6: Spec alignment — PASS

Generated 102 test scenarios → tests/
```

**Voiceover:**
> "102 tests generated. Every assertion derived from the spec. Six gates verified. Zero hallucinated outcomes."

*[PAUSE — 2 seconds to let output sink in]*

---

## Step 5: Run Against Live API (15 seconds)

**Voiceover:**
> "Now let's run them against the real Petstore API — live, across the internet."

**Command:**
```bash
cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json
```

*Expected (partial output):*
```
Running 102 scenarios against https://petstore3.swagger.io/api/v3...

  ✓ POST /pet                    happy_path              200 OK
  ✓ POST /pet                    missing_name            400
  ✓ POST /pet                    missing_photoUrls       400
  ✓ GET /pet/findByStatus        happy_path              200
  ...
  ✓ DELETE /pet/{petId}          happy_path              200
  ✗ POST /store/order            create_order            422 vs 400  ← DRIFT

Results: 101/102 passed, 1 drift detected
```

**Voiceover:**
> "101 pass. 1 drift detected — the Petstore spec promises 422 for invalid orders, but the live server returns 400. That's a real conformance bug."

*[PAUSE — 2 seconds]*

---

## Closing CTA (5 seconds)

**Voiceover:**
> "That's CHERENKOV. Zero to verified suite, real API, real bugs found. Try it with `cherenkov init` today."

*Visual: Show the project URL / GitHub link.*

---

## Post-Recording Checklist

- [ ] Total duration under 3 minutes
- [ ] Terminal font is readable at 1080p
- [ ] All commands succeeded on first run
- [ ] Output is clean (no errors, no weird paths)
- [ ] Voice is clear, no background noise
- [ ] The drift finding is visible and explained

---

## Editing Notes

- **Cut** the `pip install` wait time (speed up to 2x)
- **Cut** the `cherenkov generate` wait time (speed up to 4x, add progress bar overlay)
- **Zoom in** on the drift finding line for 2 seconds
- **Overlay text:** "101/102 passed — 1 real drift found" at the end
