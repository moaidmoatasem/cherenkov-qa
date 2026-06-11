<!-- One concern per PR. Small PRs review faster. Fill every field. -->

## What & why

Closes #
<!-- One or two sentences: what changed and why it matters. -->

## Type of change

<!-- Check all that apply -->
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation only
- [ ] Refactoring (no behaviour change)
- [ ] Test improvement
- [ ] CI / tooling

## How to test it

<!-- How should a reviewer verify this works? -->

```bash
# Commands a reviewer can run to see the change working
```

## Raw evidence (required — claims are not evidence)

<!-- Paste terminal output: smoke/unit runs, git status, command output.
     A PR without evidence cannot be reviewed.
     "Tests pass" is not evidence. The terminal output is. -->

```
<paste here>
```

## Checklist

**Core**
- [ ] One issue, one concern; branch named `feat|fix|docs|chore/<issue>-slug`
- [ ] Unit + smoke added/updated and **green** (evidence above)
- [ ] Docs updated if behaviour changed; `scripts/ci_docs_check.py` passes

**Invariants** *(check each one you touched; leave unchecked if untouched)*
- [ ] D7 — healing/validate never write to test files
- [ ] Anti-lock-in — `eject` produces zero-CHERENKOV-import Playwright
- [ ] Suggest-only — no auto-apply, no auto-commit in healing
- [ ] Spec-derived — expected HTTP status from OpenAPI spec, not hardcoded
- [ ] Model-agnostic — no model name in code; uses `ReasoningRequest{capability_tier}`

**Quality**
- [ ] No secrets or API keys committed
- [ ] CodeQL scan clean
- [ ] No import from `track-b-c-deferred/` (quarantined)
- [ ] `docs/HANDOVER.md` updated if project state changed

<!-- AI agent? Add co-author trailer to your commit message. -->
