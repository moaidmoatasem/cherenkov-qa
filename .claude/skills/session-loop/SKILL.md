---
name: session-loop
description: Work the Cherenkov-QA queue one item at a time, with no orchestrator. Use whenever the user says "continue", "next item", "work the queue", "swarm", "what's next", or opens a session without a concrete task. Also use before starting any ROADMAP item, so the claim, work and stop steps are not skipped.
---

# Session loop

One item per session. Each step exists to keep a session cheap and to stop two sessions
colliding on the same work. The full rules live in `CLAUDE.md` ("Session loop"); this is the
runnable version.

1. **Wake.** Read only the "Current state" block at the top of `HANDOVER.md` and the open
   issue labelled `oversight`. Do not re-audit plan files: `scripts/oversight_check.py` does
   that weekly, and stale plan docs carry a `plan-status: superseded` banner.
2. **Claim.** Take the top unblocked row of "Now" in `docs/ROADMAP.md`. Confirm no open PR or
   branch already references its issue number, then assign the issue and add the
   `in-progress` label. If something already references it, take the next row.
3. **Work.** Only that item. Write the failing test first, then the fix. Grep before reading,
   and stage specific files, never `git add -A`. Develop on the branch the session names.
4. **Stop.** Add a dated entry at the top of `HANDOVER.md`, mark the ROADMAP row done (or note
   what remains), run `python scripts/oversight_check.py --offline`, push, open a draft PR and
   subscribe to it. Do not start a second item: the hard stop is what bounds cost.

Parallel work is the exception, not the default. Do it only when the user asks and the items
touch disjoint files: one branch per item, one sub-agent per branch, each following steps 2-4.
Never run a background orchestrator or scheduled wake-ups; the swarm in `.agents/` was
abandoned for exactly that reason.

When a step blocks on a human (M1 practitioner validation, publishing keys, the GitHub repo
description), say so once and move to the next unblocked row rather than simulating the human.
