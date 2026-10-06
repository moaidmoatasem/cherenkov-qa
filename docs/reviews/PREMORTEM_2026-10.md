# Premortem, critique, assessment and verdict — 2026-10-06

Written after a code, plan, CI and market audit. Companion: [MARKET_SCAN_2026-10](MARKET_SCAN_2026-10.md). Outcome: [docs/ROADMAP.md](../ROADMAP.md).

## Measured size

628 Python files, ~91k lines in `cherenkov/`, 65 subpackages; 31 CLI command modules (53 top-level names), 31 web route modules, 38 workflows, ~290 docs. The integrity core (`integrity`, `divergence`, `verdict`, `truth`, `check_suite`) is under 10% of the code. One maintainer plus agent sessions; no externally validated users (milestone M1 never ran).

## Premortem — October 2027, Cherenkov is dead. Why?

1. **No one used it.** M1 practitioner validation never happened; all seven September PRs were defect fixes found by manual audits of our own surfaces.
2. **Sprawl ate the core.** Desktop, K8s operator, mobile, federation, enterprise, fine-tuning, marketplace — each needing its own audits; each agent session re-discovers them.
3. **The trust product shipped fake greens:** `check-suite` PASS with 2 of 3 checks not run (fixed #1012), hardcoded compliance badges, a mock PR comment in `spec-drift.yml`, an echo-only competitor-clone CLI, hollow workflow steps, a fabricated roadmap reconciliation, and a default-path gate that catches 0/3 cheat classes. One public "your verifier lied" story ends a trust tool.
4. **Platforms commoditised generation** (Playwright agents, WDIO v10, Keploy, BrowserStack, QA Wolf).
5. **Too heavy to try:** four docs, four install paths, Node/Playwright/Prism/LLM before first value; `init` produces a project `doctor` rejects.
6. **Agent-driven rot:** ~15 contradicting plan files and docs steering agents to wrong sources of truth.

## Critique

- Four names for one thing ("API conformance test generator", "Reality Engine", "The Forensic QA Protocol", "Autonomous Quality Fabric").
- Breadth before depth: platform features before one user validated the core loop.
- It repeatedly shipped surfaces that lie, in a product whose job is catching tests that lie.
- Quality depended on periodic heroic audits rather than gates; HANDOVER grew to ~1,800 lines of narrative.

## Assessment — what is genuinely good

- `check-suite` is the real product: WEAKENED / DELETED / HALLUCINATED verdicts on an AI-modified suite, AST-based, no LLM, honest about which checks ran.
- Spec-derived mutants prove a test catches a real regression.
- `demo` tells the 60-second story; `eject` means no lock-in (though #1000).
- Hygiene is real now: green CI, real-backend E2E gated on PRs, claim tests.
- The market is moving toward the problem: healer agents weaken tests silently; mabl's survey says ~20% of a week goes to checking AI-generated tests.

## Enhancement

Autonomy needs a referee the agent cannot game. Cherenkov becomes that referee:

1. One sentence: "Before you merge an AI agent's change to your tests, Cherenkov proves the tests still catch bugs."
2. Three entry points: `cherenkov check`, the PR-comment GitHub Action, the agent skill (`agent init`).
3. Zero-config first value: no LLM, Node, Prism or config file for the first verdict.
4. Humans review verdicts, not code (HITL queue for uncertain cases).
5. Generation is an assist. Core / Assist / Labs tiers; nothing deleted.
6. Prove it publicly: held-out benchmark of AI-weakened diffs; mutant battery on the default path.
7. One name everywhere.

## Verdict

**Keep going — only as the narrowed integrity gate, with kill criteria.** The problem is real, growing and barely owned. The 65-package platform as it stands is not worth continuing: it produces audit work instead of users.

Kill criteria, checked 2026-12-15: (1) install to first verdict on the user's own repo in under 5 minutes with no LLM, enforced by a CI job; (2) public benchmark ≥80% catch at ≤10% false positives; (3) ≥5 external practitioners, ≥3 keeping it in CI after two weeks. If (3) fails, archive the platform and salvage `check-suite` as a small library plus Action.
