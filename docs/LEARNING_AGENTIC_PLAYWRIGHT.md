# Learning from `idavidov13/agentic-playwright`

Source: https://github.com/idavidov13/agentic-playwright (read 2026-08-13, README + docs only —
the repo was not cloned, so every claim about *their* side is README-level and should be
re-checked against their tree before any of it is copied verbatim).

Every claim about **this** repo below was verified against the working tree; file:line refs are
given so a reader can disagree with the evidence rather than with the summary.

## What it is

A Playwright + TypeScript scaffold whose product is not the tests — it is the **guardrails that
make an LLM emit acceptable tests on the first prompt**. Three layers:

1. An always-loaded orchestrator (`CLAUDE.md` / `.cursor/rules` / `copilot-instructions.md`)
   carrying a **Constitution**: an explicit MUST / WON'T list (dependency injection, semantic
   `getByRole` locators, `z.strictObject()`, web-first assertions — never `waitForTimeout()`,
   XPath, `any`, hardcoded secrets, multiple tags per test).
2. **17 scoped skills** loaded on demand, one per concern (selectors, page-objects, api-testing,
   data-strategy…), with `ai-native-workflow` as the sole entry point for non-trivial work.
3. **Mechanical enforcement** of the subset of the Constitution that is grep-detectable — a
   Claude Code `PreToolUse` hook (`.claude/scripts/enforce_constitution.py`) that blocks the write
   *before* the file lands, plus pre-commit lint gates for skill drift and rule-anchor integrity.

The interesting move is layer 3. Everyone writes a style guide into a prompt; they assumed the
prompt would be ignored and made the machine refuse the write.

## The one structural insight worth taking

**They and we validate different axes of "is this generated test any good", and neither axis
substitutes for the other.**

| Axis | Question | Who owns it |
|---|---|---|
| Behavioural | Does the test fail when the implementation is broken? | **cherenkov** — `cherenkov/sdet/assertion_gate.py`, `cherenkov/coverage/assertion_gate.py`, `cherenkov/divergence/self_play.py` |
| Structural | Is the test deterministic, readable, and maintainable next quarter? | **agentic-playwright** — Constitution + write-time hook |

Cherenkov's whole thesis is the behavioural axis: a test that passes a spec-conforming mock *and*
a deliberately-broken one has vacuous assertions and is rejected. That is strictly stronger than
anything a linter can say — and it is also completely blind to a test that catches every bug while
sitting on `waitForTimeout(3000)` and an XPath selector. Such a test passes our gate today and
will be flaky in CI next month.

Our structural coverage of generated specs is currently **six regexes** in
`cherenkov/stages/review.py:37-42`:

```python
_RE_FETCH_CLIENT   = re.compile(r"\bclient\.(GET|POST|PUT|DELETE|PATCH)\b")
_RE_CLIENT_CALL    = re.compile(r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'")
_RE_FORBIDDEN_HTTP = re.compile(r"\b(fetch|axios)\b|\.request\b|throw new Error")
_RE_STATUS_TOBE    = re.compile(r"\.status\)?\s*\)?\s*\.toBe\(\s*\d{3}\s*\)")
_RE_STATUS_LITERAL = re.compile(r"toBe\(\s*(200|201|204|400|401|404|422|500)\s*\)")
_RE_BODY_SHAPE     = re.compile(r"toHaveProperty\(|typeof\s")
```

That is a real static layer, but it is ad-hoc, undocumented as a contract, and applies only in
`review`. There is no ESLint config for either `cherenkov/web/ui` or `playwright-suite` — the UI's
`lint` script is `tsc --noEmit` (`cherenkov/web/ui/package.json:11`), and the only ESLint configs
in the tree are `landing-page/eslint.config.js` and `vscode/.eslintrc.json`, neither of which
covers a generated or hand-written spec.

## Ranked adoption list

### 1. Promote the review regexes into a declared rule set — *highest value, contained*

Turn the six ad-hoc patterns into a declarative table (rule id, severity, pattern, rationale,
fix hint) and extend it with the grep-detectable half of their Constitution that applies to us:
`waitForTimeout(`, XPath locators, `any`, `z.object(` where `z.strictObject()` is meant,
hardcoded credentials, `test.describe()`-level tags.

Why it fits: it is a *cheap pre-filter in front of an expensive gate*. Behavioural validation
spins up mocks and runs the suite twice (spec-conforming + broken impl). A structural violation is
detectable in microseconds and does not need a mock at all. Ordering static-then-behavioural saves
real time on a bad batch and gives the author a specific line to fix instead of a kill-rate.

Precedent for the shape already exists in-tree: `cherenkov/reflector/introspect.py` defines a
`SmellType` enum with a rationale per smell for *memory* self-audit. The same treatment for
*generated-spec* smells would be idiomatic here, not an import of foreign style.

Landing spot: `cherenkov/stages/review.py`, surfaced through the existing `check-suite` skill's
6-gate pipeline.

### 2. A write-time hook, not just a prompt rule

We have `.claude/settings.json` with a `SessionStart` hook only. Their `PreToolUse` hook is the
mechanism that makes a Constitution non-optional for an agent — and this repo has already been
burned by exactly the failure mode it prevents: `HANDOVER.md` records a Playwright suite that
loaded **zero** tests because `api_mocks.ts` was missing, and a docs file that carried fabricated
gate results. Prompt-level rules did not stop either.

Worth scoping carefully: a hook that blocks writes is high-friction in a repo where parallel agents
share a volatile tree (see `CLAUDE.md`, "do not commit without checking that no parallel agent is
mid-edit"). Start it as **warn-only on `stub/generated_tests/**` and `playwright-suite/tests/**`**,
and only promote to blocking once the false-positive rate is known.

### 3. Single-tag discipline + `@destructive` wins

Their tagging rule — exactly one tag per test, `@destructive` for anything mutating shared state,
run on a single worker — is the cheapest reliability win on the list, and it is a *generator*
change rather than a validator change: `cherenkov/stages/generate.py` and
`cherenkov/stages/ui_generate.py` would emit the tag, and rule set (1) would enforce it. This
matters more for us than for them, because our generated suites are machine-authored in bulk and
nobody is hand-reviewing tag hygiene.

### 4. Confidence-gated planning (`confidence < 5 → ask the human`)

Their `ai-native-workflow` skill requires a plan to carry a confidence score, rationale, and
explicit unknowns, and to stop for a human below a threshold. We have the routing half of this
already — `skills/find-skills/SKILL.md` is a meta-skill that picks the skill for a task, the same
role their `ai-native-workflow` plays — and we have a HITL queue (`cherenkov/hitl/`) that is the
natural destination for a low-confidence stop. What is missing is the *scored stop* itself.
Cheapest version: extend the `find-skills` skill to require the score, before touching any code.

### 5. Static data as `.ts as const`, never JSON

Small, but it is the kind of thing that costs nothing at adoption time and is expensive to retrofit:
typed static fixtures give the compiler a chance to catch a stale fixture, JSON gives it none.
Relevant to `tests/fixtures/` and `bench/fixtures/`.

## What not to take

- **Page Object Model as doctrine.** Their POM layer (getters for locators, JSDoc only on actions,
  three locator sections) is aimed at a hand-maintained UI suite. Our UI specs are far fewer than
  our API specs, and cherenkov's value is in the API/contract direction; adopting a full POM
  discipline would be ceremony for a surface we barely have.
- **Their fixture DI stack wholesale** (`mergeTests()`, `test-options.ts` as single import point).
  Worth reading, not worth porting until we have a UI suite big enough to hurt.
- **Skill-tree mirroring across three tools** (`.claude/` + `.cursor/` + `.github/instructions/`)
  with drift-check scripts to keep them in sync. That is real maintenance cost bought to support
  three agent vendors. We support one; the drift checker would be guarding a copy we never made.
- **The Pro-tier framing.** The free scaffold is the useful artefact; the AST lint rules and CI
  parity gates are behind their paid tier, so treat the README's description of them as
  advertising, not as a design we can inspect.

## Honest summary

The transferable idea is one sentence: *cherenkov proves generated tests are meaningful and does
almost nothing to prove they are maintainable, and the second problem is cheaply solvable with a
declared rule set in front of the expensive gate.* Items 1 and 3 are the ones that pay for
themselves. Item 2 is right in principle and needs a careful rollout. Items 4 and 5 are cheap.
Everything under "what not to take" is a good fit for their repo and a poor fit for ours.

Nothing in this document has been implemented. It is a reading note, not a status report.
