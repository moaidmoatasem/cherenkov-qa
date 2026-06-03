# Way of Work

Full version: [`CONTRIBUTING.md`](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/CONTRIBUTING.md). Quick card:

## The five non-negotiables
1. SSOT = `docs/` (v3.1 + delta). No invented versions.
2. Show **raw evidence**, never a summary. Claims ≠ evidence.
3. Scope = Track A. `track-b-c-deferred/` is quarantined — don't extend/import pre-gate.
4. Design invariants are law (D7 no auto-edit · anti-lock-in eject · suggest-only healing · spec-derived oracle · model-agnostic).
5. The real blocker is validation, not code.

## The loop
pick `status:ready` issue → branch `feat/<issue>-slug` → build small (reuse contracts) → unit+smoke green → PR (template + evidence, `Closes #NN`) → human review → squash-merge.

## Required checks on `main`
Documentation Coverage · Healing Suggest-Only · CLI Help + Docs Gate · CodeQL. PR required, ≥1 review, linear history, no force-push. See [PM/ALM doc](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/docs/process/GITHUB_PM.md) §5.

## Definition of Done
code + unit/smoke green + raw evidence in PR + docs updated + CI green + reviewed.
