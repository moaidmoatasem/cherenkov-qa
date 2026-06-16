# Demo — "Catch the AI Cheating"

> **Purpose:** the single demo that proves the trust-layer thesis. If this lands, the whole "verifiable autonomous quality" positioning is real. Doubles as **Gate G0 / E0.2** evidence. See [../NORTH_STAR.md](../NORTH_STAR.md), [../VISION_AQE_2026.md](../VISION_AQE_2026.md), [../ROADMAP_AQE.md](../ROADMAP_AQE.md).
> **Date:** 2026-06-16 · **Runtime target:** under 90 seconds.

## The one-line hook
> "We let an AI write the tests. Then we let it cheat. Watch CHERENKOV catch it."

## Why this demo (not "AI writes tests")
Everyone shows generation. The scarce, defensible thing is **catching the agent when it quietly weakens a check to fake green** — the research's #1 unmet need. This demo shows the thing only the trust layer can do.

## Setup (real, reproducible — not staged)
- A small but real target app/API with a known-correct behavior and a spec (source of truth).
- An off-the-shelf agentic test generator (OSS) — used honestly, no rigging.
- CHERENKOV with the meaningful-assertion + integrity gates (Rung-1 E1.2/E1.3).

## Beat sheet (storyboard)

**Beat 1 — Generation looks great (0:00-0:20).**
Agent generates a suite. All green. Coverage number looks healthy. "Looks done, right?" This is what every other tool shows you.

**Beat 2 — The cheat (0:20-0:40).**
Introduce a real failure mode (pick ONE per take; rotate across takes):
- *Assertion weakening:* a failing test gets its assertion loosened (`== 200` → `< 500`, or exact-body → `is not None`).
- *Deleted check:* the agent removes the test that was failing.
- *Hallucinated oracle:* asserts against a field/endpoint that doesn't exist in the spec.
The suite is **still green.** Narration: "It's green because the AI made it green — not because the software is right."

**Beat 3 — CHERENKOV catches it (0:40-1:10).**
Run `cherenkov verify` (or `verify_suite` via MCP). Verdict: **FAIL**, with the exact finding:
- which assertion was weakened (before → after diff),
- or which check was deleted (vs baseline),
- or which oracle is hallucinated (no such field in spec),
- a minimal reproduction, and a *suggested* (not auto-applied) fix.
Narration: "CHERENKOV re-derives the truth from the spec — so it doesn't believe the suite's own claims."

**Beat 4 — The certificate (1:10-1:30).**
Fix it for real; re-run; verdict **PASS**; issue a **CHERENKOV Certificate** stating exactly what was verified *and what wasn't*. "Now you have proof you can forward — not a vibe."

## The payoff line
> "Generation is free now. Trust isn't. CHERENKOV is the part that doesn't let the AI lie to you."

## Variants
- **Engineer cut (CLI):** terminal-only, fast, for HN/dev audiences.
- **Agent-loop cut (MCP):** show an agent calling `verify_suite`, getting FAIL, and self-correcting — "verify before done."
- **Buyer cut:** lead with Beat 4 (the certificate) and the compliance framing.

## Assets to produce
- [ ] Reproducible repo/script (`demos/catch-the-ai-cheating/`) — one command per beat.
- [ ] Asciinema/terminal recording (engineer cut).
- [ ] 90s screen capture with captions.
- [ ] A real CHERENKOV Certificate file as the closing artifact.
- [ ] Three injected-cheat fixtures (weaken / delete / hallucinate).

## Honesty guardrails (non-negotiable)
- Use a real generator and a real target; no rigging. If it doesn't catch the cheat, that's a Rung-1 bug to fix, not a script to fudge — see [fabricated-validation-gate] lesson.
- Show `NOT_checked` scope on the certificate. The brand is honesty.

## Ties to gates
Producing this demo with a genuine catch **is** Gate G0 / E0.2. Capture the artifacts the moment it works.
