# CHERENKOV QA — Roadmap (the work queue)

> **Plan of record (2026-10-06):** the "Current state" block at the top of [`HANDOVER.md`](../HANDOVER.md) plus this file. Everything else that looks like a plan is superseded — see the list at the bottom. Changing this file is how the plan changes; do not open a new roadmap doc. A weekly [oversight report](https://github.com/moaidmoatasem/cherenkov-qa/issues?q=label%3Aoversight) checks for drift.

## Focus decision

Cherenkov is **the integrity gate for AI-written tests**: before an agent's change to a test suite is merged, prove the tests still catch bugs. Generation is an assist, not the product.

- **Core** (the only things a new user sees): `check` (integrity verdict, no LLM), `demo`, `init`, `doctor`, `validate`, `verify`; the PR-comment GitHub Action; the agent skill (`agent init`).
- **Assist:** `generate`, `eject`, `author`, and similar.
- **Labs:** desktop, K8s operator, mobile, federation, enterprise, training/fine-tune, marketplace, openclaw, copilot, chat, brainmap, reflector. Still callable; frozen for new features and out of the default CLI, UI nav and critical CI path.

Why: [PREMORTEM_2026-10](reviews/PREMORTEM_2026-10.md) and [MARKET_SCAN_2026-10](reviews/MARKET_SCAN_2026-10.md).

**Kill criteria — checked 2026-12-15** (measured, not claimed):
1. Install to first verdict on the user's own repo in under 5 minutes, no LLM — measured by a CI job on a clean container.
2. Public held-out benchmark: gate catches ≥80% of weakening cases at ≤10% false positives.
3. ≥5 external QA/SDET practitioners run it on their own repos; ≥3 keep it in CI after two weeks. If this fails, archive the platform and salvage `check-suite` as a small library plus Action.

## Now

| Item | Where |
|---|---|
| Redesign Phase 1 — **done, merged in #1031/#1043:** one identity, Core/Assist/Labs tiers, `cherenkov check`, first-value CI job, `mode: check` PR-comment Action (M3, due 2026-10-07), Labs nav + removed invented UI values, `agent init` referee rule. **Remaining:** slim core install (553 MB today), sample-findings banner (#1041), `check` SARIF output | #1031, #1043 |
| ~~Default-path meaningful-assertion gate uses a mutant that catches 0/3 cheat classes~~ — fixed: gate now runs the single-axis battery (status/value/enum) | #1032 |
| ~~Groups shadow `review`/`enterprise`/`routine` commands; dashboard launch broken~~ — fixed: no same-named groups, `cherenkov review --port` works again | #1039 |
| `init` scaffolds a project `doctor` rejects, plus a broken CI workflow — init half fixed (valid config keys, real `mode: check` workflow); **remaining:** `doctor` assumes Ollama and checks `npx playwright` instead of what `validate` needs | #1040 |
| Dashboard shows sample/invented data as real | #1041 |
| Walkthrough defects: #995 #996 #997 #998 | issues |

Done in #1031: #993, #994, routines RCE (allowlist), testerarmy stub removed.

## Next

- Onboarding: one path, accurate docs, MCP default policy — #1042, #999, #1000, #1010, #1026.
- Spec-drift workflow posts mock findings — #1038 (resolved by the real Action).
- Hollow automation — #1037. Unwired loops — #1033. Regenerate caps — #1034. Guardian daemons — #1035. Routine CLI — #1036.
- Rebase draft PR #1025 (walkthrough defects 6/7).

## Strategic bets (from the market scan)

- Bring `check-suite` `.ts` analysis to parity with `.py`; parse WebdriverIO/Mocha specs. Reach into the healer-agent crowd (Playwright healer, WDIO v10 `ai-service`, Checksum, QA Wolf) without adding a runner.
- Position `check`/`verify` as the verifier step inside agent loops (CLI + skills; keep the MCP tool count small).
- Do **not** compete on API test generation (Keploy, BrowserStack).
- Public held-out benchmark of AI-weakened test diffs (kill criterion 2).

## Blocked on the maintainer

M1 practitioner validation (never simulate), the Tauri signing key, PyPI publish (gated on M1), and the Dependabot backlog (~15 PRs open since 2026-08-16, including GitHub Actions major bumps).

## Deferred (no-paid-tier decision, 2026-08-01)

Phase 13/15/16 epics: #754, #773, #779, #780, #781, #785, #787, #789, #763. Fine-tuned-model items (#773/#779/#780) are candidates to close as not-planned.

## Superseded plan files (kept for history; each carries a banner)

`docs/STATUS.md`, `PHASE_PLAN.md`, `EXECUTION_PLAN.md`, `SCOPE_LEDGER.md`, `MODULE_STATUS.md`, `GAP_REPORT.md`, `wiki/Roadmap.md`, `vision/02_ROADMAP.md`, `vision/07_MASTER_PLAN.md`, `vision/08_DELIVERY_PLAN.md`, the Unified Master Plan, `INNOVATION_ROADMAP_V2.md`, `PROJECT.md`, `.agents/*`, `open_issues.txt`.
