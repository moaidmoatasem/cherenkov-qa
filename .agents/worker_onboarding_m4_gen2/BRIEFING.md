# BRIEFING — 2026-07-07T00:55:40+03:00

## Mission
Perform docs site integration for onboarding and execute end-to-end verification.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /home/moaid/cherenkov-qa/.agents/worker_onboarding_m4_gen2/
- Original parent: e116e557-e912-4f0a-b2d7-3aaf9386dfe1
- Milestone: onboarding_verification

## 🔒 Key Constraints
- CODE_ONLY network mode: no external HTTP/network access.
- Minimal change principle.
- No dummy/facade implementations or cheating.
- Authoritative handover: docs/HANDOVER.md.
- Invariant D7: Never auto-edit test code.
- Sync Driven Development (SDD) rules: agent_sync before/during/after.

## Current Parent
- Conversation ID: e116e557-e912-4f0a-b2d7-3aaf9386dfe1
- Updated: not yet

## Task Summary
- **What to build**: Docs site integration for onboarding section in INDEX.md, verification of onboarding demo harness, validation of casts.
- **Success criteria**: INDEX.md has onboarding section, run_demo.sh runs successfully & cleans up, casts run successfully in simulation.
- **Interface contracts**: /home/moaid/cherenkov-qa/docs/INDEX.md
- **Code layout**: Standard layout.

## Key Decisions Made
- Follow SDD protocol if agent_sync is active (let's check first if python script exists and works).

## Artifact Index
- /home/moaid/cherenkov-qa/docs/INDEX.md — Main index document for docs site
- /home/moaid/cherenkov-qa/.agents/worker_onboarding_m4_gen2/handoff.md — Handoff report
- /home/moaid/cherenkov-qa/.agents/worker_onboarding_m4_gen2/progress.md — Heartbeat progress file
