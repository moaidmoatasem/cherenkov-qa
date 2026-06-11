# CHERENKOV — Documentation Index

Welcome. This is the **single entry point** for everything in the CHERENKOV
docs tree. Pick the path that matches who you are.

> **Status check first?** → [STATUS.md](STATUS.md) — the one place that says
> what's done, what's blocked, and what's next.

---

## 🚀 If you're new here

| Step | Doc | What it gives you |
|:----:|-----|-------------------|
| 1 | [GETTING_STARTED.md](GETTING_STARTED.md) | Install + first test in 5 minutes |
| 2 | [CLI_DEMO.md](CLI_DEMO.md) | Terminal walk-through of the full flow |
| 3 | [TESTING.md](TESTING.md) | How the test pipeline works under the hood |

If you only have 2 minutes, read **§ "What it does (30 seconds)"** in
[../README.md](../README.md) and run the Quick Start in
[GETTING_STARTED.md](GETTING_STARTED.md#-prerequisites--installation).

---

## 🛠️ If you're building on CHERENKOV

| Doc | What's in it |
|-----|--------------|
| [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) | Core architecture policy: device targets, startup health check |
| [engineering/SYSTEM_DESIGN.md](engineering/SYSTEM_DESIGN.md) | System design, clean architecture per ADR-004 |
| [engineering/ARCHITECTURE_PRINCIPLES.md](engineering/ARCHITECTURE_PRINCIPLES.md) | Non-negotiable engineering tenets |
| [engineering/BEST_PRACTICES.md](engineering/BEST_PRACTICES.md) | Coding standards, testing, security |
| [PHASE_PLAN.md](PHASE_PLAN.md) | Consolidated Phase -1 → 8 plan, all tracks, all tickets |
| [adr/](adr/) | Architecture Decision Records (why we chose what we chose) |
| [HANDOVER.md](HANDOVER.md) | Authoritative state for agents and contributors |

### Subsystem references

- [LOGGING.md](LOGGING.md) — structured logging policy
- [ERROR_HANDLING.md](ERROR_HANDLING.md) — error model + graceful degradation
- [config_cookbook.md](config_cookbook.md) — config knobs and recipes
- [MIGRATION.md](MIGRATION.md) / [MIGRATION_INVENTORY.md](MIGRATION_INVENTORY.md) — schema and data migrations
- [ASSUMPTIONS.md](ASSUMPTIONS.md) — explicit non-goals and assumptions
- [vision/19_QA_REASONING.md](vision/19_QA_REASONING.md) — QA Reasoning Engine: artifact-adaptive QA workflows ([ADR-007](adr/ADR-007-qa-reasoning-engine.md))

---

## 🤖 If you're an agent

**Read in this order:**

1. [../AGENTS.md](../AGENTS.md) — operating rules, deltas, track status (DO NOT SKIP)
2. [STATUS.md](STATUS.md) — current state of every phase
3. [HANDOVER.md](HANDOVER.md) — what is real, what is fabricated, what to do next
4. [PHASE_PLAN.md](PHASE_PLAN.md) — full plan with tickets
5. The relevant ADR in [adr/](adr/) before you touch a module
6. [engineering/BEST_PRACTICES.md](engineering/BEST_PRACTICES.md) before you write code

**Skills (autonomous workflows):** [../skills/](../skills/) — read the
stack-specific markdown before executing complex tasks.

**Agent memory:** [../agent_memory/](../agent_memory/) — document your state,
findings, and context to prevent AI amnesia.

---

## 🧪 If you're QA

| Doc | What's in it |
|-----|--------------|
| [qa/TEST_PLAN.md](qa/TEST_PLAN.md) | Test plan |
| [qa/BUSINESS_REGRESSION_SUITE.md](qa/BUSINESS_REGRESSION_SUITE.md) | Business regression suite |
| [process/QA_VALIDATION_RUNBOOK.md](process/QA_VALIDATION_RUNBOOK.md) | Validation runbook for the 5-QA gate |
| [QA_DEMO_KIT.md](QA_DEMO_KIT.md) | Demo script |
| [QA_OUTREACH_TEMPLATES.md](QA_OUTREACH_TEMPLATES.md) | Templates for recruiting QA reviewers |
| [process/VALIDATION_EVIDENCE_LEDGER.md](process/VALIDATION_EVIDENCE_LEDGER.md) | Evidence ledger for validation |
| [CHERENKOV_QA_TEST_EXECUTION_REPORT.md](../CHERENKOV_QA_TEST_EXECUTION_REPORT.md) | Test execution report |
| [QA_TEST_REPORT.md](../QA_TEST_REPORT.md) | QA test report |

---

## 🗂️ Reference and history

These exist for context. Most readers don't need them.

- [ROADMAP_NEXT.md](ROADMAP_NEXT.md), [ROADMAP_PACKAGING.md](ROADMAP_PACKAGING.md),
  [ROADMAP_RECONCILIATION.md](ROADMAP_RECONCILIATION.md) — earlier roadmap
  drafts. The consolidated [PHASE_PLAN.md](PHASE_PLAN.md) supersedes them.
- [SCOPE_LEDGER.md](SCOPE_LEDGER.md) — honest scope map
- [GAP_REPORT.md](GAP_REPORT.md) — known gaps
- [DEFERRED_VISION_ARCHIVE.md](DEFERRED_VISION_ARCHIVE.md) — earlier vision
  material kept for history. **Do not cite as current.**
- [INTEGRATION_HANDOVER_REPORT.md](INTEGRATION_HANDOVER_REPORT.md) —
  ⚠️ **DEPRECATED.** Superseded by [HANDOVER.md](HANDOVER.md) and
  [PHASE_PLAN.md](PHASE_PLAN.md). Retained for traceability only.

### Process and reviews
- [process/GITHUB_PM.md](process/GITHUB_PM.md) — GitHub project management
- [process/evidence/](process/evidence/) — collected validation evidence
- [proof_run/](proof_run/) — proof-run logs
- [reviews/](reviews/) — external and internal reviews

### Spikes and federation
- [spikes/](spikes/) — investigation notes
- [federation/](federation/) — federation model and corpus
- [federation/corpus.md](federation/corpus.md), [federation/specialist-model.md](federation/specialist-model.md)

### Plans
- [plans/](plans/) — phase context briefs

### Vision
- [vision/](vision/) — earlier vision docs. Many are stale; for current
  direction use [PHASE_PLAN.md](PHASE_PLAN.md). The archive of the deferred
  vision lives at [DEFERRED_VISION_ARCHIVE.md](DEFERRED_VISION_ARCHIVE.md).

### Dashboard, engineering, wiki
- [dashboard/](dashboard/) — frontend design + audit docs
- [engineering/](engineering/) — architecture, system design, best practices
- [wiki/](wiki/) — lightweight wiki (FAQ, Way of Work, Roadmap)

### Diagrams
- [diagrams/](diagrams/) — system diagrams ([DIAGRAMS.md](diagrams/DIAGRAMS.md) is the index)

---

## How this index is organized

```
docs/
├── INDEX.md             ← you are here
├── STATUS.md            ← canonical status (one place, not duplicated)
├── GETTING_STARTED.md   ← new user entry point
├── CLI_DEMO.md          ← terminal walk-through
├── TESTING.md           ← testing policy
├── HANDOVER.md          ← agent + contributor handover (authoritative)
├── PHASE_PLAN.md        ← consolidated plan
├── TECHNICAL_DESIGN.md  ← core arch policy
├── adr/                 ← architecture decision records
├── engineering/         ← system design, principles, best practices
├── dashboard/           ← frontend design + audit
├── diagrams/            ← system diagrams
├── federation/          ← federation model
├── plans/               ← phase context briefs
├── process/             ← GitHub PM, validation, evidence
├── proof_run/           ← proof-run logs
├── qa/                  ← test plan, regression suite
├── reviews/             ← external + internal reviews
├── spikes/              ← investigation notes
├── vision/              ← earlier vision (most is stale; see DEFERRED_VISION_ARCHIVE.md)
└── wiki/                ← lightweight wiki
```

---

## Doc conventions

- **Markdown only.** One H1 per file. H2 for sections, H3 for subsections.
- **Tables over prose** for status, flags, options, decisions.
- **Code blocks for commands**, with the actual command a copy-paste away.
- **Link, don't restate.** Prefer linking to a single SSOT over duplicating
  content across files.
- **Date every status block** so readers know how fresh it is.
- **Show evidence.** Per [AGENTS.md](../AGENTS.md) rule 2, claims are not
  evidence. State the file, the line, the command, or the test result.
