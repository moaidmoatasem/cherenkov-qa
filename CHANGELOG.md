# Changelog

All notable changes to CHERENKOV are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

> Product status: **Track A is built; not yet shipped** — shipping is gated by the 5-QA validation gate (see `docs/HANDOVER.md` §5 and issue #79).

## [Unreleased]
### Added
- **Governance & PM kit:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `docs/process/GITHUB_PM.md`, `.github/` issue/PR templates, `CODEOWNERS`, `scripts/github_sync.sh`.
- **Planning docs:** `docs/vision/06_AUTONOMOUS_QA_FABRIC.md`, `docs/vision/07_MASTER_PLAN.md`, `docs/dashboard/FE_REDESIGN.md`, `docs/diagrams/DIAGRAMS.md`.
- **Roadmap tickets:** Validation Gate epic (#79), Epoch 7 Reflector (#84) + tasks, Epochs 8–13 + FE redesign epics (#89–#97).
- This `CHANGELOG.md`.
### Changed
- Closed implemented roadmap issues (Epochs 0–4 + E6-4); milestones/labels extended for Epochs 7–13 + Validation Gate.

## [foundation-v0] — Foundation (pre-release)
The model-agnostic Reality-Engine foundation. Built and unit/smoke-tested; **not validated by the QA gate**.
### Added
- **L0 Substrate Router** (`substrate/`, `ai/{cache,accounting}`) — model-agnostic routing by capability tier + egress dial, fallback, cost/latency accounting. _(Epoch 1)_
- **L1 Truth Model** (`core/truth_model.py`, `truth/sources/{openapi,traffic,db_schema}`, `truth/index.py`, `stages/map_cmd`). _(Epoch 2)_
- **L2 Divergence Engine** (`divergence/{skeptic,witness,self_play,proof_run}`) — D1–D5 hypotheses, independent reproduction, adversarial self-play. _(Epoch 3 — THE BET)_
- **L3 Artifacts** (`truth/emitters/{playwright,spec_patch,pr_comment}`, `execution/{eject,validate,…}`).
- **L4 Continuity** (`continuity/pr_diff_action`, `stages/daemon_cmd`, behavioral-diff GitHub Action). _(Epoch 4)_
- **Self-healing** (`healing/{diagnose,auth_expiry,contract_drift,sandbox_healer}`) — suggest-only.
- **Federation** scaffolding (`federation/{corpus,cross_check,protocol}`) + divergence-specialist research. _(Epoch 6)_
- **Track A generator** (`stages/{ingest,plan,generate,review}`, `execution/*`) — OpenAPI → Playwright with 6-gate review and zero-lock-in eject.
- **CI/security:** invariant-check CI, CodeQL, behavioral-diff workflows.
### Invariants proven
- Spec-derived expected status (caught real 422-vs-400 bug); suggest-only healing; eject runs standalone; model never hardcoded (routed by tier).

[Unreleased]: https://github.com/moaidmoatasem/cherenkov-qa/compare/foundation-v0...HEAD
[foundation-v0]: https://github.com/moaidmoatasem/cherenkov-qa/releases/tag/foundation-v0
