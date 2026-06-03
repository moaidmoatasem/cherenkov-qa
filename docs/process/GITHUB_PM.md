# CHERENKOV — Project Management, ALM & GitHub Way-of-Work

**Authority:** subordinate to [`docs/HANDOVER.md`](../HANDOVER.md) and [`AGENTS.md`](../../AGENTS.md). If this doc contradicts the handover, the handover wins.
**Purpose:** one place for how work is tracked, reviewed, and shipped through GitHub — milestones, labels, tickets, branch rules, ALM cadence, and the architecture/design standards every contributor (human or agent) follows.

---

## 0. The reconciliation that governs all tickets (read first)

Two facts from the SSOT decide priority and override any roadmap enthusiasm:

1. **The real blocker is not code — it's the Track A validation gate.** Show the tool to 5 QA professionals; **3 of 5 "yes" = Track A shipped** ([`HANDOVER.md` §5](../HANDOVER.md)). This is an **owner task**, and it is **issue #1**.
2. **`track-b-c-deferred/` (incl. the React dashboard) is quarantined.** Do not extend or import it **until Track A validates** ([`HANDOVER.md` §4](../HANDOVER.md)).

**Consequence for the expansion work in this repo's `docs/vision/` (Reality Engine, E7–E13) and `docs/dashboard/FE_REDESIGN.md`:** these are **gated backlog**. They are captured as tickets so the plan is visible, but every one carries the label `blocked:validation-gate` and stays closed-to-start until the gate passes. We document the dependency rather than silently ignore it. The owner may override — but the dependency is explicit.

> Net: **close the genuinely-done E0–E6 *implementation* tickets, elevate the *validation gate* to the top milestone, and stage E7–E13 + FE as blocked backlog.**

---

## 1. Codebase review — honest current state

| Area | Modules | State |
|---|---|---|
| Track A generator | `core/`, `ai/`, `stages/{ingest,plan,generate,review}`, `execution/`, `healing/` | **Built; invariants proven; NOT yet validated by the QA gate** |
| L0 Substrate Router | `substrate/`, `ai/{cache,accounting}` | **Done & tested** (Epoch 1 closed) |
| L1 Truth Model | `core/truth_model.py`, `truth/sources/*`, `truth/index.py`, `stages/map_cmd` | Implemented |
| L2 Divergence engine | `divergence/{skeptic,witness,self_play,proof_run}` | Implemented (E3-1…E3-5) |
| L3 Artifacts | `truth/emitters/*`, `execution/{eject,validate,…}` | Implemented |
| L4 Continuity | `continuity/pr_diff_action`, `stages/daemon_cmd`, `.github/workflows/behavioral-diff.yml` | Implemented |
| Federation | `federation/{corpus,cross_check,protocol}` | Implemented + E6-4 research |
| Security/CI | `.github/workflows/{ci,codeql,behavioral-diff}.yml` | Implemented |
| **Quarantined (do not extend)** | `track-b-c-deferred/**` (visual, perf, rag, compliance, jira, **dashboard**) | Reference-only until gate |

CI exposes three required checks: **Documentation Coverage**, **Healing Suggest-Only**, **CLI Help + Docs Gate**, plus **CodeQL**.

---

## 2. Ticket ledger (the action)

> Issue numbers are not hard-coded here (the repo is private; this doc was authored without API access). The sync script (§7) matches by **title prefix** so it's robust. Confirm against the live tracker.

### 2a. CLOSE — implemented, evidence in git history
Close every open task whose title starts with these prefixes (implementation done; see commits/closeout):
`E0-1, E0-2, E0-3` · `E1-1…E1-6` · `E2-1…E2-6` · `E3-1…E3-5` · `E4-1…E4-5` · `E6-4`
Closing comment template: *"Implemented in `<module>` (commit `<sha>`); smoke/unit green. Closing as done. NOTE: product-level 'shipped' still depends on the Track A validation gate (#GATE)."*

### 2b. KEEP OPEN / VERIFY — partial or unverified
- `E0-4` tag `foundation-v0` — verify a tag exists; if not, do it or close-wontfix.
- `E5-1…E5-3` (`init`, layered config, `doctor`) — `init_cmd`/`doctor_cmd` exist; verify against acceptance, then close.
- `E5-4` Dashboard — **re-label `blocked:validation-gate`** (it is the quarantined dashboard).
- `E5-5` Docs getting-started — keep open.
- `E6-1…E6-3` Federation protocol/cross-check/corpus — code exists; verify acceptance, then close.

### 2c. CREATE — top priority
- **#GATE · EPIC: Track A Validation Gate (owner task)** — milestone `M0 · Ship Track A`. Body: run [`QA_DEMO_KIT.md`], recruit 5 QA (templates exist), count yeses, 3/5 = ship. Sub-tasks: recruit, run demo ×5, log verdicts, decision.
- **Docs SSOT reconciliation task** — note that `docs/vision/*` + `docs/dashboard/*` are *gated backlog*; add a banner to each pointing at this §0.

### 2d. CREATE — gated backlog (label `blocked:validation-gate`, milestone-per-epic, do not start pre-gate)
Epics, each with the task breakdown from the plan docs:
- **EPIC E7 · Reflector & Verdict Memory** → tasks E7-1…E7-4 ([`07_MASTER_PLAN.md` §4](../vision/07_MASTER_PLAN.md))
- **EPIC E8 · Perf Intelligence** (scale up `track-b-c-deferred` perf → on Track A) · **EPIC E9 · Vision** · **EPIC E10 · Explorer + Copilot** · **EPIC E11 · Coverage SDET** · **EPIC E12 · Cert + Governance** · **EPIC E13 · Copilot v2 + Pairing**
- **EPIC FE · Dashboard Redesign** → tasks FE-0…FE-10 ([`docs/dashboard/FE_REDESIGN.md` §7](../dashboard/FE_REDESIGN.md)). Extra label `area:frontend` + `do-not-extend-until-gate`.

Each gated epic body must start: *"BLOCKED by #GATE (Track A validation). Captured for visibility; do not start until 3/5 QA yeses. See `docs/process/GITHUB_PM.md` §0."*

---

## 3. Milestones (ALM phases)

| Milestone | Meaning | Contains |
|---|---|---|
| **M0 · Ship Track A** | pass the validation gate | #GATE epic + E5 finish (init/doctor/docs) + `foundation-v0` |
| **M1 · Foundation hardened** | substrate/truth/divergence proven on a real OSS target | verify E1–E4/E6 acceptance, the Epoch-3 proof-run publish |
| **M2 · Reflector** | E7 (first post-gate build) | EPIC E7 |
| **M3 · Signals** | E8 perf + E9 vision (un-quarantine in priority order) | EPIC E8, E9 |
| **M4 · Author & Trust** | E10 Copilot, E11 SDET, E12 governance | EPIC E10–E12 |
| **M5 · Pairing & FE** | E13 + dashboard redesign | EPIC E13, EPIC FE |

Post-gate order follows [`HANDOVER.md` §6.3](../HANDOVER.md): Visual → Perf → Diagnostics/RAG → Jira/compliance/dashboard.

---

## 4. Label taxonomy

```
type:        type:epic  type:task  type:bug  type:docs  type:chore  type:research
area:        area:substrate area:truth area:divergence area:artifact area:continuity
             area:healing area:perf area:visual area:frontend area:ci area:security
status:      status:ready  status:in-progress  status:in-review  status:blocked
priority:    P0-critical  P1  P2  P3
gating:      blocked:validation-gate   do-not-extend-until-gate
agent:       agent-ready   needs-human   needs-evidence
```
Rule: every issue has exactly one `type:`, one `priority:`, ≥1 `area:`. `agent-ready` only on issues with crisp acceptance + no human-only steps (the gate is `needs-human`).

---

## 5. Git flow & repository rulesets

**Branching (trunk-based with short-lived branches):**
- `main` — protected, always green, releasable.
- `develop` — optional integration branch (CI already triggers on it); use if batching.
- Work branches: `feat/<issue>-slug`, `fix/<issue>-slug`, `docs/<issue>-slug`, `chore/…`. Always reference an issue.

**Commits:** Conventional Commits — `feat(divergence): … (#NN)`, `fix(truth): …`, `docs:`, `chore:`, `test:`. Imperative, scoped, issue-referenced (matches existing history).

**PRs:** small, one issue, fill the PR template, link `Closes #NN`, attach **raw evidence** (terminal output) per the anti-drift rule. Squash-merge to `main`.

**Branch protection / ruleset for `main`** (apply via Settings → Rules, or the script):
- Require PR before merge; ≥1 approving review; dismiss stale approvals.
- Require status checks to pass & be up to date: **Documentation Coverage**, **Healing Suggest-Only**, **CLI Help + Docs Gate**, **CodeQL** (and **behavioral-diff** once stable).
- Require conversation resolution; require linear history (squash).
- Block force-push and deletion; restrict who can push (owner/maintainers).
- No bypass except repo admin for emergencies (logged).

---

## 6. Application lifecycle & PM cadence (through GitHub)

- **Board:** a GitHub Project (Table + Board views), columns = `status:` labels (`ready → in-progress → in-review → done`); swimlane by milestone.
- **Flow per ticket:** issue (acceptance written) → `status:ready`/`agent-ready` → branch → PR (`in-review`) → checks green + review → squash-merge (auto-closes issue) → milestone burndown updates.
- **Definition of Ready:** clear acceptance, labels set, dependencies noted, no missing decisions.
- **Definition of Done:** code + unit/smoke + raw evidence in PR + docs updated + CI green + reviewed. (Gate epics add: owner sign-off.)
- **Cadence:** weekly milestone review (burndown + reprioritize); release notes per milestone (`RELEASE_NOTES.md`); tag releases (`vX.Y`).
- **Traceability:** issue ↔ branch ↔ PR ↔ commit ↔ milestone, all linked; every claim backed by evidence.

---

## 7. How to apply this (you must run it — I have no GitHub access)

`gh` is not installed in this environment and the repo is private (no token). Run, authenticated, from the repo root:

```bash
# one-time
winget install GitHub.cli   # or: brew install gh / apt install gh
gh auth login

# preview every change (no mutations)
bash scripts/github_sync.sh            # dry-run by default
# apply
bash scripts/github_sync.sh --apply
```

The script is **idempotent**: it ensures labels + milestones, creates missing issues by title (skips existing), and prints the close-candidates (E0–E4/E6-4) for confirmation (`--apply --close-done` to auto-close). It never deletes.

---

## 8. System architecture & design standards (the bar every contributor holds)

- **Architecture:** stable core + **pluggable capability layers**; four open SPIs (Source / Model / Artifact / Oracle), each a versioned **Pydantic contract** in `core/contracts.py`. New capability = new plugin, never a core fork.
- **Design patterns in use:** Strategy (Substrate Router picks a provider per `capability_tier`), Adapter (Source/Artifact/Oracle SPIs), Pipeline/Chain (INGEST→PLAN→GENERATE→REVIEW), Agent/role separation (Skeptic/Witness), Circuit-breaker (REVIEW dry-run loop, 2-fail break), Provenance/event-sourcing (Truth Model claims).
- **Invariants (never violate — from `AGENTS.md`):** D7 never auto-edit user test code; anti-lock-in (`eject` strips all imports); suggest-only healing; spec-derived expected status; agents never name a model (route via tier).
- **Quality:** every module ships unit + smoke; show raw evidence; CI green; docs-drift gate passes.
- **Security:** CodeQL on PR; secrets never in prompts/commits; quarantined code stays quarantined.

See [`CONTRIBUTING.md`](../../CONTRIBUTING.md) for the contributor/agent way-of-work and [`CODE_OF_CONDUCT.md`](../../CODE_OF_CONDUCT.md).
