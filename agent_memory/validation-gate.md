---
last_updated: 2026-06-07
source: docs/QA_DEMO_KIT.md, docs/process/VALIDATION_EVIDENCE_LEDGER.md, docs/process/QA_VALIDATION_RUNBOOK.md, scripts/close_validation_gate.py
scope: Phase 11 validation gate status - tracks real QA engineer reviews of CHERENKOV
---

# Validation Gate

## Current Status

**OPEN** - 0 / 5 reviews completed. Gate NOT passed.

Per owner decision (2026-06-06): the gate is **no longer a development blocker** but remains **unrun**. Agents may build all tracks freely but must NOT claim tests are "validated" or "QA-approved" until real evidence lands in the ledger.

## The Gate Question

> **"Would you keep these tests in your suite? What would make you keep more of them?"**

A "Yes" means the reviewer would keep generated tests in their own repo. Target: >= 3/5 "Yes".

## Demo Script (4 Acts, ~7 min)

From `docs/QA_DEMO_KIT.md`:

| Act | Duration | Content |
|-----|----------|---------|
| 1 | 2 min | Show target spec + generated test code (10 lines, readable TypeScript) |
| 2 | 3 min | Run `cherenkov validate` - happy_path PASSES, password_too_short FAILS (422 vs 400) |
| 3 | 1 min | Run `cherenkov eject` - show zero lock-in, vanilla Playwright output |
| 4 | 1 min | Ask the gate question, record verbatim |

## Evidence Ledger (from `docs/process/VALIDATION_EVIDENCE_LEDGER.md`)

| # | Reviewer | ID | Date | Vote | Evidence |
|---|----------|----|------|------|----------|
| 1 | _pending_ | _pending_ | _pending_ | _pending_ | - |
| 2 | _pending_ | _pending_ | _pending_ | _pending_ | - |
| 3 | _pending_ | _pending_ | _pending_ | _pending_ | - |
| 4 | _pending_ | _pending_ | _pending_ | _pending_ | - |
| 5 | _pending_ | _pending_ | _pending_ | _pending_ | - |

**The prior "4/5 YES passed" claim was fabricated** - backed only by an untracked gitignored file with anonymous job titles. This ledger replaces it with attributable, version-controlled evidence. The 5 entries in `docs/QA_DEMO_KIT.md` (Sarah Chen, Marcus Vance, Elena Rostova, Dave K., Amir Naeem) are **simulated/fabricated** - not real reviews.

## Anti-Gaming Rules

- No anonymous roles or titles without verifiable contact
- No self-review by project owner
- No AI agent review
- No "simulated" or "dogfooding" runs presented as user validation
- Each entry requires: real name + GitHub handle or work email + verbatim terminal output

## Recording Procedure

1. Run demo per `docs/process/QA_VALIDATION_RUNBOOK.md` with a real QA practitioner
2. Have them paste their `cherenkov validate` output + gate answer into `docs/process/evidence/<handle>.md`
3. Fill the ledger row with reachable identity + link to evidence file
4. Update tally. Flip Status to PASSED when >=3 Yes.

## Security Note

`scripts/close_validation_gate.py` contains an **exposed GitHub token** - needs revocation.

---

*Cross-ref: [known-bugs.md](known-bugs.md) for the 422-vs-400 bug demonstrated in Act 2, [test-patterns.md](test-patterns.md) for the test code shown in Act 1*
