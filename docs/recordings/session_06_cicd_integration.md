# Session 6: CI/CD Integration

> **Duration:** 5-7 minutes
> **Audience:** DevOps Engineers / Tech Leads
> **API:** Controllable target (localhost)
> **Key Message:** One command to gate your CI pipeline on API conformance
> **Difficulty:** Intermediate

---

## Hook (5 seconds)

**Voiceover:**
> "Your tests pass, but does your API actually match its spec? I'll show you how to gate your CI pipeline on API conformance — one command, zero config."

*Visual: Terminal with CI YAML file.*

---

## Prerequisites

Run these BEFORE recording:

```bash
# Terminal 1: Start controllable target
cd /home/moaid/cherenkov-qa/target
source .venv/bin/activate
uvicorn target_api:app --host 127.0.0.1 --port 8000

# Terminal 2: Main workspace
cd /home/moaid/cherenkov-qa
source .venv/bin/activate
```

---

## Part 1: The Problem (60 seconds)

### Step 1.1: Explain the Gap

**Voiceover:**
> "Most CI pipelines run tests and check if they pass. But that's not enough. Your tests might pass while your API drifts from its spec. You need a conformance gate — a checkpoint that verifies your implementation matches your contract."

*Visual: Overlay diagram:*

```
Traditional CI:
  Build → Test → Pass/Fail → Deploy

CHERENKOV CI:
  Build → Test → Conformance Gate → Deploy
                     ↓
              Spec vs Implementation
              Drift detected? BLOCK DEPLOY
```

**Voiceover:**
> "CHERENKOV adds a conformance gate between tests and deployment. If the API drifts from the spec, the build fails."

*[PAUSE — 1 second]*

---

## Part 2: The Certify Command (2 minutes)

### Step 2.1: Run Certify

**Voiceover:**
> "The `certify` command is the CI/CD entry point. One command. It validates the API against the spec and exits with a non-zero code if drift is detected."

**Command:**
```bash
cherenkov certify --url http://localhost:8000 --spec stub/target_spec.json
```

*Expected:*
```
CHERENKOV CERTIFICATION GATE
================================================================================
Target: http://localhost:8000
Spec:   stub/target_spec.json
================================================================================

Running conformance check...
  Scenario: happy_path              → 201 OK
  Scenario: password_too_short      → 422 OK (matches spec)
  ...

Certification: PASSED
  Total scenarios: 6
  Passed: 6
  Failed: 0
  Drift: 0

Exit code: 0
```

**Voiceover:**
> "Exit code 0. All clear. The API matches its spec. In CI, this means the build proceeds."

### Step 2.2: Show the Failure Case

**Voiceover:**
> "Now let's see what happens when drift is detected."

**Command:**
```bash
export REGRESSION_MODE=true
killall uvicorn
cd target && uvicorn target_api:app --host 127.0.0.1 --port 8000 &
sleep 3
cd /home/moaid/cherenkov-qa
cherenkov certify --url http://localhost:8000 --spec stub/target_spec.json
```

*Expected:*
```
CHERENKOV CERTIFICATION GATE
================================================================================
Target: http://localhost:8000
Spec:   stub/target_spec.json
================================================================================

Running conformance check...
  Scenario: happy_path              → 201 OK
  Scenario: password_too_short      → 400 FAIL (expected 422)
  ...

Certification: FAILED
  Total scenarios: 6
  Passed: 5
  Failed: 1
  Drift: 1

  DRIFT DETECTED:
    POST /auth/register → Expected 422, Got 400

Exit code: 1
```

**Voiceover:**
> "Exit code 1. Drift detected. In CI, this would block the deployment. The build fails until the spec or the implementation is fixed."

*[PAUSE — 2 seconds for impact]*

---

## Part 3: CI Pipeline Integration (2 minutes)

### Step 3.1: GitHub Actions

**Voiceover:**
> "Here's how it looks in GitHub Actions."

**Command:**
```bash
cat .github/workflows/conformance.yml 2>/dev/null || echo "---
name: API Conformance Gate
on: [push, pull_request]

jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install cherenkov-qa
      - name: Start API server
        run: docker compose up -d
      - name: Conformance Gate
        run: cherenkov certify --url http://localhost:8000 --spec openapi.yaml
" > .github/workflows/conformance.yml && cat .github/workflows/conformance.yml
```

*Expected: GitHub Actions workflow YAML.*

**Voiceover:**
> "6 lines of YAML. Install CHERENKOV, start your API, run the certify command. If the API drifts from the spec, the build fails. That's your conformance gate."

### Step 3.2: Jenkins

**Command:**
```bash
cat ci/jenkins/vars/cherenkovValidate.groovy | head -30
```

*Expected: Jenkins shared library snippet.*

**Voiceover:**
> "For Jenkins users, we have a shared library. Same concept — one function call in your Jenkinsfile."

### Step 3.3: Exit Code Explanation

**Voiceover:**
> "The key contract: exit code 0 means pass, non-zero means fail. Every CI system understands this. GitHub Actions, Jenkins, GitLab CI, CircleCI — they all respect exit codes."

*Visual: Overlay:*

```
Exit code 0  → Build proceeds
Exit code 1  → Build fails, deployment blocked
```

---

## Part 4: What You Get (30 seconds)

**Voiceover:**
> "In summary:
> 1. `cherenkov certify` — one command, exit code based
> 2. GitHub Actions, Jenkins, GitLab CI — all supported
> 3. Drift detection blocks deployment automatically
> 4. Full audit trail in SARIF format for compliance
>
> No custom scripts. No fragile test runners. Just a conformance gate."

---

## Closing CTA (5 seconds)

**Voiceover:**
> "Add `cherenkov certify` to your pipeline. Gate your deploys on API conformance."

*Visual: Project URL.*

---

## Post-Recording Checklist

- [ ] Total duration under 7 minutes
- [ ] The certify pass AND fail cases are shown
- [ ] The GitHub Actions YAML is readable
- [ ] The exit code contract is explained
- [ ] Voiceover emphasizes "one command" at least twice
- [ ] The drift detection output is clear

---

## Editing Notes

- **Overlay** the CI pipeline diagram during Step 1.1
- **Red highlight** on "Exit code: 1" during failure case
- **Speed up** the `certify` wait time to 2x
- **Add** text overlay: "Zero config. One command. Conformance gate."
- **Split screen** during Part 3: terminal left, CI YAML right
