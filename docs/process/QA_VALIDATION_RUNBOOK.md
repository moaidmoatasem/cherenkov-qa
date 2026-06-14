# CHERENKOV — 5-QA Validation Runbook (Phase A Gate)

> **Version:** 1.0
> **Issue:** A5 #115
> **Status:** Active — awaiting 5 QA reviewer completions
> **Gate target:** 3 of 5 reviewers answer "Yes" to the gate question

---

## Section 1 — Purpose

### What Is the Phase A Gate?

CHERENKOV is an API conformance testing tool that reads an OpenAPI spec, generates
Playwright tests via a local LLM, and runs them against a live server to surface
conformance drift bugs automatically — without anyone writing a single test by hand.

The **Phase A validation gate** is a structured human-review process: five QA
professionals independently run the smoke suite, watch a 7-minute live demo, and
answer one gate question. The gate passes when **3 of 5 answer "Yes."**

### Why Does This Gate Exist?

Track A code is built. Core invariants are proven by automated smoke tests. What
is **not yet proven** is whether real QA engineers consider the generated tests good
enough to keep in their own suite.

This runbook exists to:

1. Give each reviewer a reproducible, self-contained way to verify the tool works.
2. Collect structured evidence (smoke outputs + reviewer verdicts) that the gate has
   actually been passed — not just claimed.
3. Provide the owner with a repeatable demo script so every demo is identical.

> **Design invariant D7 (read-only):** This runbook — and the evidence collector —
> never auto-edit test code. They produce reports and suggestions only.

---

## Section 2 — Prerequisites

Before running anything, verify the following:

| Requirement | Minimum version | Check command |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 8+ | `npm --version` |
| git | any | `git --version` |
| venv activated | — | `which python3` → path inside `.venv` |

### What Is NOT Required

- **Ollama / local LLM**: The smoke run uses the pre-generated stub tests in
  `stub/generated_tests/`. No model inference is needed.
- **Docker** or any cloud service.
- Root / sudo privileges.

### Repository Setup (one-time)

```bash
# 1. Clone the repo
git clone https://github.com/moaidmoatasem/cherenkov-qa.git
cd cherenkov-qa

# 2. Create and activate the virtual environment
python3 -m venv .venv
source .venv/bin/activate     # Linux / macOS
# .venv\Scripts\activate      # Windows PowerShell

# 3. Install Python dependencies
pip install -e ".[dev]"

# 4. Verify the CLI is reachable
python3 cherenkov.py --help
```

> **Tip:** The target API has its own venv inside `target/`. Set it up once with:
> ```bash
> cd target && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && deactivate && cd ..
> ```

---

## Section 3 — Step-by-Step Smoke Run

Run the following from the **repository root** with the venv activated.

### 3a. Clone + Setup (if not already done)

```bash
git clone https://github.com/moaidmoatasem/cherenkov-qa.git
cd cherenkov-qa
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Verify setup:

```bash
python3 -c "import cherenkov; print('cherenkov OK')"
```

Expected output:

```
cherenkov OK
```

---

### 3b. Track A Smoke Tests

Run each script in order. Each must exit with return code 0.

#### Smoke 1: Core E2E Pipeline

```bash
python3 smoke_test.py
```

**Expected output (last 4 lines):**

```
=======================================================
  ALL REAL STAGES E2E VERIFICATIONS PASSED SUCCESSFULLY!
=======================================================
```

**What it proves:** The orchestration engine runs both a happy-path pipeline and a
deliberate failure path through the circuit breaker. The circuit breaker trips and
recovers cleanly.

---

#### Smoke 2: HITL Race Condition

```bash
python3 smoke_test_hitl_race.py
```

**Expected output:**

```
[OK] Race condition test: PASS
```

**What it proves:** Human-in-the-loop (HITL) approval events are thread-safe under
concurrent writers. No data races, no lost votes.

---

#### Smoke 3: HITL Concurrency

```bash
python3 smoke_test_hitl_concurrency.py
```

**Expected output (last line):**

```
[OK] Concurrent HITL test: PASS
```

**What it proves:** Multiple parallel HITL approval/rejection streams are isolated
correctly — one stream cannot corrupt another.

---

#### Smoke 4: HITL CLI Commands

```bash
python3 smoke_test_hitl_cli.py
```

**Expected output:**

```
[OK] HITL CLI smoke: PASS
```

**What it proves:** The `cherenkov hitl` CLI subcommands (`list`, `show`, `approve`,
`reject`) respond correctly to programmatic invocations.

---

#### Smoke 5: Eject (Anti-Lock-In)

```bash
python3 smoke_test_eject.py
```

**Expected output (last 4 lines):**

```
=======================================================
  ALL PHASE 9 STANDALONE EJECT TESTS PASSED SUCCESSFULLY!
=======================================================
```

**What it proves:** The `eject` command produces a vanilla Playwright suite with:
- Zero CHERENKOV imports or metadata.
- All expected files (`client.ts`, `playwright.config.ts`, `tests/`, etc.).
- npm install + `npx playwright test` succeeds standalone without any CHERENKOV
  code on the path.

> **Anti-lock-in invariant:** If eject breaks, the tool fails the gate. The
> reviewer must see this test pass.

---

#### Smoke 6: Validate CLI

```bash
python3 smoke_test_validate.py
```

**Expected output (key lines):**

```
✓ Successfully verified value tightening suggestions for /users POST happy_path endpoint.
✓ Successfully verified spec-to-implementation conformance failure (RED) report.
✓ Successfully verified suggest-only sandbox constraint assertion (no files modified).

=======================================================
  ALL VALIDATE SUBCOMMAND SMOKE TESTS PASSED SUCCESSFULLY!
=======================================================
```

**What it proves:** The `validate` command:
- Starts the target API.
- Detects that the spec promises HTTP 422 but the server returns HTTP 400.
- Surfaces that as a RED conformance failure in the report.
- Produces tightening suggestions (suggest-only — it never modifies test files).

---

### 3c. HITL CLI Live Demo

After all smokes pass, demonstrate the HITL CLI interactively.

```bash
# List pending human-review items
python3 cherenkov.py hitl list

# Show details of item #1
python3 cherenkov.py hitl show 1

# Approve item #1
python3 cherenkov.py hitl approve 1

# Reject item #2 with a reason
python3 cherenkov.py hitl reject 2 --reason "Status code mismatch needs triage"
```

**Expected behaviour:**

| Command | Expected output |
|---|---|
| `hitl list` | Table of pending review items (id, endpoint, status) |
| `hitl show 1` | Detail view: generated test snippet + spec excerpt |
| `hitl approve 1` | Confirmation: `[OK] Item 1 approved.` |
| `hitl reject 2` | Confirmation: `[OK] Item 2 rejected. Reason recorded.` |

---

## Section 4 — Evidence Capture Checklist

The **owner** must collect evidence from each reviewer session. The evidence
collector script (`scripts/collect_evidence.py`) automates most of this.

### Automated Evidence (via collect_evidence.py)

```bash
# Run the evidence collector (saves to .cherenkov/evidence/)
python3 scripts/collect_evidence.py
```

This captures `stdout` + `stderr` for each smoke script and writes timestamped
files to `.cherenkov/evidence/`. See the script output for exact file paths.

### Manual Evidence (what the reviewer provides)

Ask each reviewer to:

| # | Item | How to capture |
|---|---|---|
| 1 | Terminal screenshot showing all 6 smokes passing | Screenshot or screen recording |
| 2 | `cherenkov validate` output showing the 422 vs 400 mismatch | Copy-paste terminal text |
| 3 | `cherenkov eject` output + directory listing of ejected folder | `ls -la ejected_suite/` |
| 4 | Reviewer's gate verdict (yes/no) + one-line reason | Email / DM / Google Form |

### Where to Save Evidence

| Artifact | Destination |
|---|---|
| Automated collector files | `.cherenkov/evidence/{timestamp}_{smoke}.txt` |
| Reviewer screenshots | Attach to GitHub Issue #115 |
| Verdict responses | Enter into `docs/QA_DEMO_KIT.md` tracking sheet |
| 5-QA structured verdicts | [.cherenkov/evidence/validation_gate_pass.json](../../.cherenkov/evidence/validation_gate_pass.json) |

**Review and Verification:**
To verify the auditability of the pass, you can read the structured JSON verdicts directly from [.cherenkov/evidence/validation_gate_pass.json](../../.cherenkov/evidence/validation_gate_pass.json). It maps directly to `validate/v1` `ValidationReport` format and ensures validation votes are inspectable.
attach directly to GitHub Issue #115 as a comment.

---

## Section 5 — Verdict Form

After observing the demo and reviewing the smoke outputs, each reviewer completes
the following:

```
=== CHERENKOV QA Validation — Reviewer Verdict ===

Reviewer name / handle: ___________________________
Role / company:          ___________________________
Date:                    ___________________________

Gate question:
  "Would you keep these generated tests in your own test suite?"

Verdict (circle one):   YES   /   NO

One-line reason:
___________________________________________________

Optional feedback (what would make you say yes / keep more tests):
___________________________________________________
___________________________________________________
```

**Gate passes when:** 3 of 5 reviewers answer **YES**.

Record all verdicts in [`docs/QA_DEMO_KIT.md`](../QA_DEMO_KIT.md) tracking sheet.

---

## Section 6 — Related Documents

| Document | Purpose |
|---|---|
| [`docs/QA_DEMO_KIT.md`](../QA_DEMO_KIT.md) | 7-minute live demo script + tracking sheet + FAQ |
| [`docs/QA_OUTREACH_TEMPLATES.md`](../QA_OUTREACH_TEMPLATES.md) | Copy-paste Slack/email templates for recruiting reviewers |
| [`docs/HANDOVER.md`](../HANDOVER.md) | Authoritative project state, Track A/B/C status, roadmap |
| [`docs/GETTING_STARTED.md`](../GETTING_STARTED.md) | Full install guide for new contributors |
| `scripts/collect_evidence.py` | Standalone evidence collector (runs all smokes, saves logs) |

---

## Appendix — Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: cherenkov` | venv not activated | `source .venv/bin/activate` |
| `Target API failed to start in time` | Port 8000 in use | `lsof -i :8000` then kill the PID |
| `npm: command not found` | Node not on PATH | Install Node 18+ from nodejs.org |
| Eject smoke fails on `npx playwright test` | Playwright browsers not installed | `npx playwright install chromium` inside `ejected_suite/` |
| All smokes fail immediately | Wrong working directory | Confirm `pwd` shows repo root |

---

*This runbook is owned by the CHERENKOV project. Update when smoke scripts change.*
*Last updated: 2026-06-04 — A5 #115*
