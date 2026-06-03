<!-- One concern per PR. Small PRs review faster. -->

## What & why
Closes #
<!-- one or two sentences -->

## Raw evidence (required — claims are not evidence)
<!-- Paste terminal output: smoke/unit runs, git status, command output.
     A PR without evidence cannot be reviewed. -->
```
<paste here>
```

## Checklist
- [ ] One issue, one concern; branch named `feat|fix|docs|chore/<issue>-slug`
- [ ] Unit + smoke added/updated and **green** (evidence above)
- [ ] Docs updated; docs-drift gate passes
- [ ] No import from `track-b-c-deferred/`; quarantine respected
- [ ] Design invariants respected (D7 / anti-lock-in / suggest-only / spec-derived / model-agnostic)
- [ ] No secrets; CodeQL clean
- [ ] SSOT (`docs/HANDOVER.md`) updated if project state changed
