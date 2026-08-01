# Session A: Zero to Hero Developer Quickstart

> **Target Audience:** Backend Developers and Software Engineers.
> **Format:** Loom-style walk-through with screen recording and live narration.
> **Estimated Duration:** 12 Minutes

---

## 🛠️ Act 0: Prerequisites & Workspace Provisioning (2 Minutes)

**[Timing: 00:00 - 02:00]**

**[Visual: Terminal showing `git clone`, venv creation, and `pip install` completing successfully. A clean WSL Ubuntu shell inside the freshly cloned `cherenkov-qa` directory.]**

**Presenter (Voiceover):**
"Before we write a single test, let's provision a cold workspace. CHERENKOV is not published to PyPI yet, so we install it straight from the source repository. This act clones the repo, creates a Python virtual environment, and installs CHERENKOV's **own** runtime dependencies — `httpx`, `requests`, `PyYAML`, `Jinja2`, and the rest — from the **root** `requirements.txt`. Don't confuse that with `target/requirements.txt`: that file only holds the demo *target server's* dependencies (FastAPI/uvicorn/pydantic) and is installed later in Act 2."

**Prerequisites (verified before starting the recording):**

| Tool | Requirement | Purpose |
|------|-------------|---------|
| Git | any recent version | Clone the repository |
| Python | 3.10+, 3.12 recommended | CHERENKOV runtime (`requires-python = ">=3.10"`) |
| Node.js + npm | v18+ | Playwright test runner in `stub/` |
| Ollama | optional | Local LLM for `cherenkov generate` (Act 3) |

**[Action: Type the provisioning commands in the terminal.]**

```bash
# 1. Clone the repository (CHERENKOV is installed from source — not on PyPI yet)
git clone https://github.com/moaidmoatasem/cherenkov-qa.git
cd cherenkov-qa

# 2. Create and activate the Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install CHERENKOV itself + its runtime dependencies (repo ROOT requirements.txt,
#    not target/) — this is the step that makes `./bin/cherenkov` work
pip install -r requirements.txt
pip install -e .          # editable install → `cherenkov` command is also on PATH

# 4. Sanity-check the CLI before going further
./bin/cherenkov --help

# 5. Verify Node.js + npm (used for the Playwright runner in Act 2)
node --version            # v18 or higher
npm --version
```

**Presenter:**
"If you are on WSL — like this recording — run everything inside your WSL Ubuntu shell. Note: `pip install -r target/requirements.txt` only installs the demo server's FastAPI/uvicorn/pydantic stack; CHERENKOV's own runtime comes from the root `requirements.txt` above. Playwright browser binaries are downloaded in Act 2 with `npx playwright install`."

**Presenter:**
"Ollama is optional and only needed for the LLM-backed generation path in Act 3. If you want that, pull the local coding model now — otherwise CHERENKOV still runs offline; the generate step is the only one that touches the LLM:"

```bash
# 6. (Optional) Local LLM for `cherenkov generate` — only needed for LLM-backed generation
ollama pull qwen2.5-coder:7b
```

---

## 🎬 Act 1: The Pitch & Core Architecture (2 Minutes)

**[Timing: 02:00 - 04:00]**

**[Visual: Title Slide: "CHERENKOV QA — Zero to Hero Developer Quickstart". Underneath: "OpenAPI as the Single Source of Truth". The background shows a clean VS Code layout with an OpenAPI specification next to a Playwright test file.]**

**Presenter (Voiceover):**
"Hey everyone! Welcome to CHERENKOV QA. Today, we're going to show you how to go from a bare OpenAPI specification to a fully validated, production-grade test suite in under ten minutes.

If you are building APIs today, you know that AI code generators can write hundreds of tests in seconds. But here is the problem: AI-generated tests frequently hallucinate expected values. If the AI expects the wrong status code or payload structure, it will write a test that passes even when your server is broken. We call this 'silent test erosion'.

CHERENKOV is designed on a single, uncompromising principle: **The OpenAPI Specification is the Single Source of Truth (SSOT).**

Instead of blindly trusting the LLM, CHERENKOV takes the generated tests and runs them through a series of rigid, deterministic compilation and dry-run gates. If the AI hallucinates, CHERENKOV catches it statically. If the implementation diverges from the specification, CHERENKOV flags the spec drift immediately. Let's see it in action."

---

## 🛠️ Act 2: Local Setup & Initialization (2 Minutes)

**[Timing: 04:00 - 06:00]**

**[Visual: The provisioned CHERENKOV workspace from Act 0 (`~/cherenkov-qa`), with the virtual environment activated.]**

**Presenter:**
"Act 0 already gave us a working CHERENKOV install inside our virtual environment. Now we add the *demo target server's* dependencies — that's what `target/requirements.txt` is for — and then we configure the Node environment inside our Playwright stub directory."

**[Action: Type the setup commands in the terminal.]**

```bash
# 1. (Re-activate the venv from Act 0 if you opened a new terminal)
source .venv/bin/activate

# 2. Install the demo target server dependencies (FastAPI/uvicorn/pydantic —
#    used by the local demo API / run_demo.sh, NOT by CHERENKOV itself)
pip install -r target/requirements.txt

# 3. Navigate to the Playwright stub directory and install Node packages
cd stub
npm install
npx playwright install
cd ..
```

**Presenter:**
"Perfect. Now that our dependencies are ready, we will initialize our CHERENKOV project. The `cherenkov init` command automatically detects any OpenAPI specifications in the workspace and creates a local configuration file called `cherenkov.toml` with offline-first, local-first settings."

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

  [OK] Generated ./cherenkov.toml

------------------------------------------------------------
  Next steps:
    Run:    ./bin/cherenkov doctor    # verify your setup
    Run:    ./bin/cherenkov validate --target <url>  # run tests

  Defaults: offline, free, deterministic
============================================================
```

> If Ollama is not installed, `[1/4] Ollama` simply reports it as unavailable and
> initialization still succeeds — Ollama is only needed for the LLM-backed
> generation step in Act 3.

---

## 🚀 Act 3: Generating Tests (3 Minutes)

**[Timing: 06:00 - 09:00]**

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

Ingesting OpenAPI spec: petstore.json
Planned 38 scenarios. Handing off to AI Generator...
  Mode: single-pass (--no-repair)
  Generating tests for scenario: happy_path...
  Generating tests for scenario: unauthorized...
  ...
Successfully generated 38/38 test suites.
Output located in stub/generated_tests/
```

> **Note:** the per-file log lines above are illustrative — the generator
> prints one progress line per scenario. Each scenario persists its own file
> named `METHOD_endpoint_mutation.spec.ts` (e.g. `POST_pet_happy_path.spec.ts`),
> so all 38 generated suites land on disk as distinct files.

---

## 🔍 Act 4: Running Validation & Detecting Spec Drift (3 Minutes)

**[Timing: 09:00 - 12:00]**

**[Visual: A clean terminal window.]**

**Presenter:**
"Now we have our tests. But here is the critical part: we want to run these tests against the live, public Swagger Petstore API to see if the actual implementation matches the spec contract. We run the `cherenkov validate` command.

CHERENKOV runs these tests, programmatically intercepting all HTTP exchanges, and diffs them against the spec. Let's see what happens."

**[Action: Execute validate command.]**

```bash
./bin/cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json
```

**Presenter:**
"Two things to notice. First, the Petstore spec declares OpenAPI `3.0.4` — a valid patch release — and CHERENKOV accepts it without complaint. Second, this unscoped run picked up every `*.spec.ts` under `stub/generated_tests/`, including the 13 demo/golden fixture files CHERENKOV ships for the catch-the-AI-cheating demos. Those fixtures intentionally assert things the API doesn't guarantee, so they fail by design — noise that drowns out our real results. They are demos, not validation failures. Scope the run to the suites we just generated with `--tests` (a glob or substring against the filenames)."

**[Action: Run validate scoped to the generated tests.]**

```bash
./bin/cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json --tests 'happy_path'
```

**[Visual: Terminal displaying validation results, showing the conformance failures in bright red.]**

```
$ ./bin/cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json --tests 'happy_path'

Running tests against https://petstore3.swagger.io/api/v3 ...

Results: 14/17 passed  [DONE]
  FAIL  POST_pet_happy_path  expect(received).toBeLessThan(500)

         Expected: < 500
         Received: 500
  FAIL  GET_pet_petId_happy_path  expect(received).toBe(400)

         Expected: 400
         Received: 500
  FAIL  GET_user_login_happy_path  expect(response.headers['x-rate-limit']).toBeDefined()
```

> **Note:** output above is illustrative from a live run — exact counts and
> error text vary with spec version and the API's state at run time.

**Presenter:**
"Look at that output! CHERENKOV has exposed **real conformance drift** between the public Swagger Petstore API and its official specification:

1. **D1 (POST /pet)**: The spec says validation failures should return a `4xx` error. Instead, the server crashes with a `500 Internal Server Error`.
2. **D2 (GET /pet/{petId})**: The spec promises that an invalid pet id returns `400 Bad Request` ('Invalid ID supplied'). Instead, the live server returns a `500` crash.
3. **D3 (GET /user/login)**: The spec dictates that a successful login returns headers `X-Rate-Limit` and `X-Expires-After`. The live server returns `200 OK`, but omits these headers entirely.

For CI, pass `--fail-on-drift` to make the command exit with code `1` whenever any conformance violations are found — without it, `validate` reports the results and exits `0`, since failure semantics belong to your pipeline:

```bash
./bin/cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json --tests 'happy_path' --fail-on-drift
```

And one more thing to appreciate: CHERENKOV leaves the test files untouched — it suggests tightening assertions but respects our strict **suggest-only** design invariant, preventing the tool from ever mutating your test codebase without human consent.

You've just initialized, generated, and uncovered real-world API drift in less than ten minutes. In the next session, we'll dive into how CHERENKOV heals these issues. Thanks for watching!"
