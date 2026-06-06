# CHERENKOV — Validation Gate Evidence Ledger

> **Status:** OPEN — gate NOT passed. 0 / 5 attributable reviews recorded.
> **Dev policy (2026-06-06):** the gate is **no longer a development blocker** (owner decision) — agents may build all tracks. It remains **unrun**; this ledger must reach ≥3 real Yes before anything is described to users as "validated." Removing the block ≠ passing the gate.
> **Gate target:** ≥ 3 of 5 reviewers answer **"Yes"** to the gate question.
> **Authority:** This ledger + [HANDOVER.md](../HANDOVER.md) are the SSOT for gate status.

---

## Why this file exists

The previous "gate passed (4/5 YES)" claim was **fabricated** — it was backed only by
`.cherenkov/evidence/validation_gate_pass.json`, an **untracked (gitignored)** file
listing **anonymous job titles** ("QA Lead", "SDET Lead") with no verifiable identity.
Anonymous + untracked = trivially faked, and it was.

This ledger fixes the process, not just the claim:

1. **Tracked in git.** Evidence lives here and in `docs/process/evidence/` — version
   controlled, diffable, attributable to a commit. Not in gitignored `.cherenkov/`.
2. **Attributable.** Each row needs a real, reachable identity (name + GitHub handle
   or work email) and a verifiable artifact (recording link or pasted raw output).
   "Senior Automation Engineer" is **not** an identity.
3. **Raw evidence, not claims.** Each reviewer's `cherenkov validate` output is pasted
   verbatim into `docs/process/evidence/<handle>.md`. Claims are not evidence.

> **Design invariant D7:** collecting evidence never auto-edits test code.

---

## The gate question (ask verbatim, record verbatim)

> **"Would you keep these tests in your suite? What would make you keep more of them?"**

A "Yes" means the reviewer would keep the generated tests in their own repo.

---

## Ledger (one row per reviewer)

| # | Reviewer (name) | GitHub / email | Demo date | Vote (Yes/No) | Evidence file | Recording |
|---|-----------------|----------------|-----------|---------------|---------------|-----------|
| 1 | _pending_ | _pending_ | _pending_ | _pending_ | — | — |
| 2 | _pending_ | _pending_ | _pending_ | _pending_ | — | — |
| 3 | _pending_ | _pending_ | _pending_ | _pending_ | — | — |
| 4 | _pending_ | _pending_ | _pending_ | _pending_ | — | — |
| 5 | _pending_ | _pending_ | _pending_ | _pending_ | — | — |

**Tally:** 0 Yes / 0 No / 5 pending — **gate OPEN.**

---

## How to record a real review

1. Run the demo per [QA_VALIDATION_RUNBOOK.md](QA_VALIDATION_RUNBOOK.md) with a real QA practitioner.
2. Have them paste their own `cherenkov validate` terminal output and a one-paragraph
   answer to the gate question into `docs/process/evidence/<their-handle>.md`
   (copy `docs/process/evidence/_TEMPLATE.md`).
3. Fill their ledger row above with a **reachable** identity and link the evidence file.
4. Update the **Tally** line and, once ≥3 Yes, flip **Status** at the top to PASSED and
   update [HANDOVER.md](../HANDOVER.md) in the same commit.
5. Commit. The git author + timestamp is itself part of the audit trail.

## What does NOT count

- Anonymous role titles with no contact.
- A reviewer the owner cannot be contacted to confirm.
- Self-review by the project owner or an AI agent.
- "Simulated" or "dogfooding" runs presented as user validation.
