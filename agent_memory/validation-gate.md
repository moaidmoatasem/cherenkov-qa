# Validation Gate

Current state of the 5-QA user validation gate.
Source: `docs/process/VALIDATION_EVIDENCE_LEDGER.md` + `_TEMPLATE.md`

## Status (2026-06-07)

**Gate is OPEN — NOT passed.**

Tally: 0 Yes / 0 No / 5 pending

The prior "4/5 YES passed" claim was **fabricated** — backed only by an untracked,
anonymous JSON file in `.cherenkov/evidence/`. The claim has been retracted per
`docs/HANDOVER.md §5`.

## Gate Question (ask verbatim)

> "Would you keep these tests in your suite? What would make you keep more of them?"

A "Yes" means the reviewer would keep the generated tests in their own repo.

## Requirements for a Valid Review

Per `VALIDATION_EVIDENCE_LEDGER.md`:
1. Tracked in git — evidence lives in `docs/process/evidence/` (version controlled)
2. Attributable — real name + GitHub handle or work email (not "Senior Automation Engineer")
3. Raw evidence — verbatim `cherenkov validate` output pasted into `docs/process/evidence/<handle>.md`

### What does NOT count
- Anonymous role titles
- Reviewers the owner cannot contact
- Self-review by the project owner or an AI agent
- "Simulated" or "dogfooding" runs

## Evidence Template
Copy `docs/process/evidence/_TEMPLATE.md` for each reviewer.

## Current Plan
- **Gate blocker resolution**: Complete Phase 1 friction kill (Wave 2 honesty debt + Wave 3 UI-only loop + Wave 4 one-click install per ROADMAP_NEXT.md)
- **Target**: 5 real QA practitioners through the UI golden path
- **Runbook**: `docs/process/QA_VALIDATION_RUNBOOK.md`
- **Recruiting**: `docs/QA_OUTREACH_TEMPLATES.md`

## Cross-references
- See `dashboard-states.md` for UI screens that need live data before the gate
- See `docs/HANDOVER.md §5` for the authoritative gate status
- See `docs/ROADMAP_NEXT.md §8 Wave 5` for the gate execution plan
