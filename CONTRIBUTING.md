# Contributing to CHERENKOV (humans & agents)

This project is built by both people and autonomous agents. The same rules apply to both. **Read [`docs/HANDOVER.md`](docs/HANDOVER.md) first** — it is the single source of truth for what is real. If anything here contradicts it, the handover wins.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 1. The five non-negotiables (anti-drift)

1. **SSOT = `docs/` (v3.1 + delta).** There is no v4/v6/"v3.1 + delta." If you cite a term not in `docs/`, stop and re-anchor.
2. **Show RAW EVIDENCE, never a summary.** "Tests pass" is a claim; the terminal output is evidence. PRs without evidence are not reviewable.
3. **All tracks are open.** The Track A validation gate passed on 2026-06-08. `track-b-c-deferred/` has been **fully re-integrated and deleted** — all code lives in the live tree. See [`AGENTS.md`](AGENTS.md) for the current track status.
4. **Design invariants are law** (§4).
5. **Build on real evidence.** Don't claim completion without raw terminal output. Don't fabricate test matrices.

---

## 2. Way of work (the loop every contributor follows)

1. **Pick an issue** that is `status:ready` (and `agent-ready` if you are an agent). One issue = one branch.
2. **Branch:** `feat/<issue>-slug` | `fix/…` | `docs/…` | `chore/…`. Never commit to `main`.
3. **Build small.** Reuse existing contracts (`core/contracts.py`); add a versioned plugin, never a core fork.
4. **Test:** add/extend unit + smoke; run them; keep them green.
5. **Open a PR** with the template filled, `Closes #NN`, and **pasted raw evidence**.
6. **Get human review.** No self-merge to `main`. Resolve all threads.
7. **Squash-merge** once checks are green + approved. The issue auto-closes; the milestone burns down.

State is tracked on the GitHub Project board via `status:` labels — see [`docs/process/GITHUB_PM.md`](docs/process/GITHUB_PM.md).

---

## 3. Git flow, commits, PRs

- **Trunk-based:** `main` is protected and always releasable. The `develop` branch was deleted (stale, 57 behind main).
- **Conventional Commits:** `feat(scope): … (#NN)`, `fix(scope): …`, `docs:`, `chore:`, `test:`. Imperative, issue-referenced.
  - **CRITICAL:** We use **Release Please** for automated changelog generation and version bumping. You MUST use Conventional Commits. The bots will automatically generate the `CHANGELOG.md` entries and bump `package.json`/`pyproject.toml` based on these prefixes.
  - **Do NOT manually edit `CHANGELOG.md` or version strings.** Let the bots handle it via the automated Release PRs.
- **Co-author trailer** for agent work where applicable.
- **PRs:** one concern, small, template-complete, evidence attached, squash-merged.
- **Required checks on `main`:** Documentation Coverage · Healing Suggest-Only · CLI Help + Docs Gate · CodeQL. Branch protection details in [`GITHUB_PM.md` §5](docs/process/GITHUB_PM.md).

---

## 4. Design invariants (never violate)

| Invariant | Rule |
|---|---|
| **D7 — no auto-edit** | Validate/healing produce **reports/suggestions only**; never modify user test files. |
| **Anti-lock-in** | `eject` must yield standalone Playwright that runs with zero `cherenkov` on the path. |
| **Suggest-only healing** | Healing never auto-commits or auto-applies. |
| **Spec-derived oracle** | Expected HTTP status comes from the OpenAPI spec, not hardcoded guesses. |
| **Model-agnostic** | Agents never name a model; they emit a `ReasoningRequest{capability_tier}` and route via the Substrate Router. |
| **Open tracks** | All tracks (A–F) are active. `track-b-c-deferred/` no longer exists — code is in the live tree under `cherenkov/`. |

---

## 5. Restrictions (hard stops)

- ❌ No commits to `main`; no force-push; no history rewrite on shared branches.
- ❌ No fabricating completeness claims, test matrices, or phase status without raw evidence.
- ❌ No new top-level "vision/version" terms; no fabricated completeness or test matrices.
- ❌ No secrets in code, prompts, commits, or issues.
- ❌ No auto-editing user test files; no auto-applying healing.
- ❌ No merging without green checks + human review + raw evidence.

---

## 6. Definition of Ready / Done

**Ready:** acceptance criteria written · labels set (`type`/`priority`/`area`) · dependencies noted · no open decisions.
**Done:** code + unit/smoke green · raw evidence in PR · docs updated (docs-drift gate passes) · CI green · reviewed & threads resolved. Gate/owner epics additionally require owner sign-off.

---

## 7. Handover protocol (so the next agent isn't lost)

- The authoritative state lives in [`docs/HANDOVER.md`](docs/HANDOVER.md). Update it when reality changes — never let it drift.
- When you finish a chunk, leave: what changed, the evidence, what's next, and any new dependency — in the PR and (if it changes project state) in the handover.
- Never write a triumphant "100% complete" handover. Describe exactly what is proven and what is not.
- Treat [`AGENTS.md`](AGENTS.md) as the short operating card; this file is the long form.

---

## 8. Local setup (quick)

WSL2 Ubuntu, Python 3.10+, Node (openapi-typescript + Playwright), Docker (Prism), Ollama (`qwen2.5-coder:7b`, `deepseek-r1:8b`). Keep the repo on the WSL filesystem.

**Note on test layout:** Smoke tests live flat at the repo root (e.g., `smoke_test_*.py`, `test_*.py`), not under a `tests/` directory. This is a deliberate choice to keep discovery simple and each file independently runnable. See [#159](https://github.com/moaidmoatasem/cherenkov-qa/issues/159) for context was considered but deferred.
