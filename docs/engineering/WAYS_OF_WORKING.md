# CHERENKOV-QA Ways of Working

**Date:** 2026-08-04
**Status:** Active
**Owner:** repo maintainers + all agents
**Related docs:** [CONTRIBUTING.md](../../CONTRIBUTING.md) (long form) · [AGENTS.md](../../AGENTS.md) (operating card) · [GITHUB_PM.md](../process/GITHUB_PM.md) (tracking)

---

This file is the **way of work** for every change to CHERENKOV-QA, by humans and by autonomous agents alike. The same rules apply to both. It governs **branching, PRs, reviews, CI gates, and the definition of ready/done**. For how multiple agents coordinate without colliding, see [AGENT_COLLABORATION_PROTOCOL.md](AGENT_COLLABORATION_PROTOCOL.md).

> SSOT rule: if this file, CONTRIBUTING.md, or AGENTS.md disagree, the handover wins for *state* and CONTRIBUTING.md wins for *process* — then fix the drift. Nothing here overrides the design invariants (D7, anti-lock-in, suggest-only healing, spec-derived oracle).

---

## 1. Branching

Trunk-based with short-lived branches. `main` is protected, always green, always releasable.

- **Never commit to `main`.** All work happens on a feature branch.
- **One issue = one branch.** Branch naming: `feat/<issue>-slug`, `fix/<issue>-slug`, `docs/<issue>-slug`, `chore/<issue>-slug`. Always reference an issue.
- **Branch lifetime:** days, not weeks. A branch that lives past its issue is a smell — split it or close it.
- **Shared working tree.** This repo is worked on by concurrent agents in a shared checkout. **Stage only the specific files your PR touches; never `git add -A` / `git add .`.** Leave `agent_memory/` SDD state files (`session.json`, `tokens.json`) unstaged unless a PR explicitly owns them.

## 2. Commits

- **Conventional Commits** — `feat(scope): …`, `fix(scope): …`, `docs:`, `chore:`, `test:`, `refactor(scope): …`. Imperative mood, scoped, issue-referenced (`#NN`).
- **Release Please** auto-generates changelog and bumps versions from commit prefixes. **Do not manually edit `CHERENKOV.md`, `CHANGELOG.md`, or version strings** unless a PR explicitly fixes version drift (see PR-6 pattern).
- **Small commits, small PRs.** One concern per PR. Many verifiable PRs beat one big bang.
- **Co-author trailer** (`Co-authored-by:`) for agent work where applicable.

## 3. PRs

- Open a PR per issue with the template filled, `Closes #NN`, and **pasted raw evidence** — terminal output, not summaries. "Tests pass" is a claim; the output is evidence. PRs without evidence are not reviewable.
- **Small and reviewable.** If a reviewer needs more than ~20 minutes, the PR is too big.
- **Required checks on `main`** (branch protection): Documentation Coverage · Healing Suggest-Only · CLI Help + Docs Gate · CodeQL. In addition, the architecture layer-guard and spec-drift gates run on PRs. A green PR shows all applicable gates passing.
- **No self-merge.** Get human review. Resolve all threads.
- **Squash-merge** once checks are green + approved. The issue auto-closes.

## 4. Reviews

- **≥1 approving human review** required. Stale approvals are dismissed automatically.
- Reviewer checks, in order:
  1. **Evidence:** is raw terminal output pasted, and does it match the claim?
  2. **Scope:** does the PR touch files outside its issue? (Guard against `git add -A` spill-over.)
  3. **Invariants:** does it violate D7 (never auto-edit test code), anti-lock-in, suggest-only healing, spec-derived oracle?
  4. **Architecture:** does it respect layer boundaries (core/ports vs adapters/web/cli)?
  5. **Docs:** does the docs-drift gate pass; are claims corrected, not papered over?
- Reviewers may request a rerun of any gate; **green status is not a substitute for reading the diff.**

## 5. CI gates

The checks below are the contract between a PR and `main`. Unless a check is explicitly documented **ADVISORY** (with an inline rationale in the workflow), a red gate **blocks merge**.

### Required on `main` (branch protection)

| Gate | What it verifies |
|---|---|
| **Documentation Coverage** (`ci.yml` docs-drift-gate) | Every doc change has its references updated; no dead links to missing docs |
| **Healing Suggest-Only** (`ci.yml` healing-invariant) | Healing produces reports/suggestions only — never auto-applies or auto-commits (D7) |
| **CLI Help + Docs Gate** (`ci.yml` polish-invariant) | CLI help text and docs stay in sync |
| **CodeQL Security Analysis** (`ci.yml` codeql-analysis) | Static security analysis |

### PR gates

| Gate | What it verifies |
|---|---|
| **Architecture: Enforce Stack Layer Boundaries** (`layer-guard.yml`) | `cherenkov/core` + `cherenkov/ports` never depend on adapters/web/cli; adapter → core, never core → adapter |
| **Spec-drift** (`spec-drift.yml`) | OpenAPI spec and generated contract expectations stay aligned (spec-derived oracle) |
| **Behavioral-diff** (`behavioral-diff.yml`) | ADVISORY — informational spec-diff comment on PRs, not a merge gate |

### Hard-fail rule

Since 2026-08-04 every gate that *can* fail **does** fail red. There is no `continue-on-error: true` on any real verification step. A gate that cannot fail is a lie — it gives the false signal that the property is checked when it is not. The only retained advisory flags are SARIF uploads (needs GitHub Advanced Security), the optional Android emulator job, and informational diff steps; each carries an inline rationale comment. See the [continue-on-error audit](../evidence/continue-on-error-audit-2026-08-04.md) (lands in PR-2, `fix/ci-gate-integrity`).

## 6. Definition of Ready / Done

**Ready** (before work starts):
- Acceptance criteria written.
- Labels set (`type` / `priority` / `area`).
- Dependencies and blockers noted.
- No open decisions blocking implementation.

**Done** (before a PR merges):
- Code implemented + unit/smoke tests green (raw evidence pasted).
- Docs updated — docs-drift gate passes; SSOT claims corrected against reality.
- All applicable CI gates green (no advisory-flag masking of a real failure).
- Reviewed by a human; all threads resolved.
- Gate/owner epics additionally require owner sign-off.

## 7. Agent-specific rules

- **Read the operating card first:** `AGENTS.md` + [SDD protocol](SYNC_DRIVEN_DEV.md) (`scripts/agent_sync.py before/log/token/after`).
- **D7 applies to agents absolutely:** never auto-edit test code. Test additions are new standalone files; validation and healing produce reports/suggestions only.
- **Never fabricate completeness.** A claim without raw terminal output is a hypothesis. An unreachable target passing "clean" is the worst failure for an integrity product.
- **Evidence drift rule:** when a doc cites a file path, commit hash, or count, verify it against the live tree before trusting it. Stale citations get corrected in the PR that touches them, not silently carried forward.
- **Findings live in `agent_memory/sync/findings/`** (local SDD layer) **and** (for anything a PR must rely on) a committed copy under `docs/evidence/`.

---

**The mission test for any change:** *does this help the system detect, prove, or close a divergence between sources of truth?* If not, it's plumbing — keep it minimal.
