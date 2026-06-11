# Agent Memory: Repository Alignment Findings (2026-06-09)

## What I did this session
- Investigated a "consolidate 40+ unmerged branches" plan
- Found a destructive mid-merge on `main` (218 deletions, including test code)
- Recovered main via `git reset --hard 554f2d16`
- Wrote `ALIGNMENT_FINDINGS.md` (in repo root) with full evidence

## Key facts (verified 2026-06-09 01:19 UTC)

### HEAD state
- Local `main` is 6 commits ahead of `origin/main`
- The 6 unpushed commits are the legitimate Phase 7/8 work:
  ```
  554f2d16 Merge feat/phase7-remaining-screens
  b6c4bc5d Merge feat/phase8-security
  8fc0255f Merge feat/docs-update-track-status (#391)
  41651b56 docs: update status ... (#391)
  d2040eeb feat: add SECURITY.md (#389)
  9e6aa114 feat: Phase 7 wire endpoints ... (#377-#380)
  ```
- The "alignment" the user asked for is **already in local main** — just needs `git push`

### Stale branches (do NOT merge, would revert work)
- 11 stale local + 18 stale remote branches are pre-`epic-244-track-bc-reintegration`
- Each would delete 6K-64K lines (especially tests) if merged
- Examples: `feat/133-mcp-server` (-49K), `feat/horizon2-openclaw-tier2-healing` (-49K),
  `feat/92-coverage-sdet` (-64K), `feat/phase-0b-foundations` (-6.7K)

### Recovery actions taken
1. `git merge --abort` (created 30b4d34c, but it was destructive — 218 deletions)
2. `git reset --hard 554f2d16` (restored clean state)
3. `30b4d34c` is now orphan in reflog only — will GC in ~90 days

### What I did NOT do (and why)
- Did NOT push the 6 commits (needs human review per AGENTS.md "Get human review before merging to main")
- Did NOT delete any branches (needs human approval)
- Did NOT merge anything (would have been destructive)
- Did NOT run smoke tests (no value until next action is decided)

## Lessons for next agent

1. **Check `git status` first** — the mid-merge would have shipped broken UI + tests
2. **"Unmerged branches" ≠ "pending work"** — branches can be stale refs whose work
   was already integrated via a different path (e.g. `epic-244-track-bc-reintegration`)
3. **Use `git diff main..branch --stat`** to check what a merge would actually do
   before merging — never trust `git branch --no-merged` alone
4. **Test files are sacred** (D7) — any merge that deletes tests needs explicit human sign-off
5. **`git merge --abort` is not always safe** when conflicts are already resolved+staged;
   may create a destructive commit. Better: `git reset --hard <known-good-sha>` after abort
6. **AGENTS.md is authoritative** — "Get human review before merging to main" applies
   to all merges, including bulk cleanup

## State to hand back
```
HEAD:  554f2d16 (clean, 6 ahead of origin/main)
File:  ALIGNMENT_FINDINGS.md (full report in repo root)
Action: Awaiting user decision (push + cleanup vs stop here)
```
