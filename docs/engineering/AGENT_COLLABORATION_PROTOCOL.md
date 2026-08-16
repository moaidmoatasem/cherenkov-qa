# CHERENKOV-QA Agent Collaboration Protocol

**Date:** 2026-08-04
**Status:** Active
**Applies to:** All autonomous coding agents and humans working the same repository
**Related docs:** [WAYS_OF_WORKING.md](WAYS_OF_WORKING.md) · [SYNC_DRIVEN_DEV.md](SYNC_DRIVEN_DEV.md) · [CONTRIBUTING.md](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/CONTRIBUTING.md) · [AGENTS.md](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/AGENTS.md)

---

Multiple agents — plus the humans they report to — work the same live tree on the same `main`. This protocol exists to make that **safe, non-colliding, and auditable**. The three laws:

1. **One agent owns one branch.** Never touch another agent's unmerged work.
2. **The tree is shared; the diff is not.** Stage only your own files. Never `git add -A`.
3. **Every agent action leaves evidence and memory.** Nothing is claimed without raw output; nothing learned is lost.

---

## 1. Ownership & branching

- **One issue = one branch = one agent.** Claim an issue before branching so nobody else picks it up. Announce ownership in the issue and in `agent_memory/`.
- **Branch prefixes are scoped** to the change type: `feat/`, `fix/`, `docs/`, `chore/`. Add the issue slug.
- **Never commit to another agent's branch.** If work overlaps, coordinate via the issue thread — don't cherry-pick onto someone else's branch without saying so.
- **Prerequisite chains.** When PRs depend on each other (e.g. a CI-touching PR that other PRs' checks rely on), sequence them and say so in each PR body. Reviewers merge in dependency order.

## 2. Shared working tree hygiene

The checkout is shared. This is the single biggest collision risk.

- **Stage specific files only.** `git add <path> <path>` — never `git add -A` / `git add .`.
- **Leave `agent_memory/` SDD state alone.** `session.json`, `tokens.json`, and the FTS5 memory DB are auto-touched by `scripts/agent_sync.py` every session. They are not your PR's content. Do not stage them (they are gitignored by default; if tracked, leave them unstaged).
- **Check `git status` before staging** to see what is already dirty — it may be another agent's in-progress work. Only stage paths you changed.
- **Rebase/merge discipline:** prefer rebasing your short-lived branch onto `main` over merging `main` into it, to keep history linear (squash-merge on `main` requires it anyway).
- **Never force-push** on a shared branch.

## 3. The SDD session contract

Every agent session follows the [SDD protocol](SYNC_DRIVEN_DEV.md). It is the memory that prevents collisions and amnesia:

```bash
# BEFORE work — load relevant past context, start session, set token budget
python scripts/agent_sync.py before --task <task_type>

# DURING — record decisions, findings, pitfalls, token usage
python scripts/agent_sync.py log --type <decision|finding|pitfall> "<message>"

# AFTER — close session, persist experience
python scripts/agent_sync.py after --summary "what was done"

# Query past experience instead of rediscovering it
python scripts/agent_sync.py experience query "<pattern>"
```

- Findings an *uncommitted* PR relies on go in `agent_memory/sync/findings/` **and** a committed copy under `docs/evidence/`.
- A session that touches code **must** log a `finding` for anything non-obvious (a bug class found, a stale citation corrected, a design decision) — that is what makes the next session faster.

## 4. Concurrency & the Conductor

- **Phase CC-2 `cherenkov/agents/conductor/`** provides fan-out/fan-in over the MCP mesh: one conductor can dispatch subtasks to worker agents and merge results. Use it for *intra-run* parallelism where subtasks are independent.
- **Cross-tool federation** (Qwen Code): generation/coding tasks may be federated to Qwen Code via the `run_qwen_code_agent` MCP tool. Qwen Code keeps its own `.qwen/skills/` + `.qwen/memory/` synced with CHERENKOV. **CHERENKOV retains the D7 invariant** — validation and testing stay in CHERENKOV; never let a federated agent auto-edit test code.
- **Concurrency rule:** the MCP mesh is for *tool* parallelism. Repo *mutations* (branches, commits, staging) are strictly serialized by ownership — one writer per branch.

## 5. Evidence & the anti-fabrication rule

- **Every claim carries raw terminal output** — pasted in the PR, not summarized. "Tests pass" is a claim; the output is evidence.
- **Verify citations before trusting them.** Docs carry stale file paths, commit hashes, and counts. Before a PR relies on one, check it against the live tree, and correct the citation in the same PR. Never carry a stale fact forward silently.
- **Do not fabricate completeness.** An unreachable target passing "clean" is the worst failure for an integrity product.
- **D7 / suggest-only / anti-lock-in / spec-derived** apply to agents exactly as to humans (see [WAYS_OF_WORKING.md](WAYS_OF_WORKING.md) §4).

## 6. Review & merge handoff

- **Human review is mandatory.** No self-merge to `main`. Resolve all threads.
- **The PR body tells the next agent what it needs to know:** what changed, the evidence, what's next, and any new dependency. If the change alters project state, mirror it in the handover.
- **Squash-merge** with Conventional Commit message; the issue auto-closes.
- **After your PR merges, update the handover** if reality changed (`docs/HANDOVER.md` and, for short-term operating state, `AGENTS.md`).

## 7. Failure modes & recovery

| Failure mode | Symptom | Recovery |
|---|---|---|
| Staged foreign files | `git status` shows files you didn't change | Unstage with `git restore --staged <path>`; re-stage only yours |
| Branch diverge | `git pull` refuses / conflict spam | Rebase onto `main`; do not resolve by force-push |
| Lost context | New session can't recall prior work | `agent_sync.py experience query`; read `docs/HANDOVER.md` |
| Stale citation | PR cites a file/count that no longer matches tree | Correct the citation in the PR; log a `finding` |
| Soft gate masking a real failure | Green CI despite a broken property | Audit `continue-on-error` — a gate that can't fail is a lie |

---

**The mission test for any agent action:** *does it help the system detect, prove, or close a divergence between sources of truth?* If not, keep it minimal and don't expand scope.
