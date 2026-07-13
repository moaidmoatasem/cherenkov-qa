---
name: agentic-exploration
description: "Drive a real browser through plain-language scenarios and judge semantic pass/fail live, feeding failures into the HITL queue."
scope: Agentic Exploration
invariants: [D7]
related_contracts: [Track A]
---

# Agentic Exploration Skill

## Purpose
Test what mechanical crawling and compiled scripts can't: whether a flow is
*semantically* correct — "does a visible confirmation appear after a valid
signup?", "is the error message specific enough?". An agent (this session,
or a dispatched subagent) reads a plain-language scenario, drives a real
browser, and judges the outcome live. This is distinct from the two other
E10 tools it composes with:

- `cherenkov explore` (`cherenkov/divergence/explorer.py`) — mechanical
  crawl for 5xx/4xx/JS errors/slow responses. No judgment, no browser
  required unless a UI probe is wired in.
- `cherenkov author` (`cherenkov/copilot/intent.py`) — compiles one
  plain-language intent into a static, ejectable `.spec.ts` file for
  regression use. No live judgment; the assertions are fixed at authoring
  time.

Agentic exploration is for the cases where you need an agent to *watch it
happen* and decide "is that actually a success?" — then it can also call
`cherenkov author` on any scenario it wants turned into a durable regression
test afterward.

## When to Use
- You have a running app/API and a set of plain-language QA scenarios
- You want semantic pass/fail judgment (not just error-code detection)
- You want failures triaged through the same HITL queue as everything else —
  not a separate defect tracker

## Workflow

### 1. Pre-flight (restate scope)
Run the existing risk digest first so both you and the human know what
you're walking into:
```bash
./bin/cherenkov explore --target <url> --path / --path /signup ...
```

### 2. List scenarios, get a go-ahead
Before executing anything, restate the target and list the scenarios you're
about to run (title + one-line expectation each) and wait for confirmation —
this mirrors the pre-flight gate other CHERENKOV skills use before mutating
state, and it's cheap: agentic scenarios drive a real browser against a real
target.

### 3. Execute
**Sequential (default):** run one scenario at a time. For each: navigate,
interact using role/text descriptions (never raw selectors — same
locator philosophy as `IntentAuthor._locator`), then judge the outcome
against the scenario's stated expectation. Pause after each scenario with a
PASS/FAIL line and evidence (console errors, a screenshot path, or the
actual text observed). Console errors or failed network calls count as a
defect even if the UI looks fine.

**Parallel (opt-in — only on an explicit "parallel"/"fast"/"autonomous"
request):** dispatch one subagent per scenario via the `Agent` tool, each
given its own working directory for screenshots/logs to avoid session
collisions, then merge results.

### 4. Record results
Write every scenario's outcome to a results file:
```json
{
  "run_id": "explore_2026-07-11_1",
  "scenarios": [
    {
      "title": "Signup with valid data shows confirmation",
      "target_url": "https://example.com/signup",
      "raw_intent": "submit valid signup form and confirm success message appears",
      "steps": [{"action": "navigate", "value": "/signup"},
                {"action": "fill", "target": "the Email field", "value": "a@b.com"},
                {"action": "click", "target": "the Sign up button"}],
      "passed": false,
      "expected": "A visible success/confirmation message appears",
      "actual": "Page stayed on the form; no confirmation and no error shown",
      "severity": "high"
    }
  ]
}
```
Only failed/uncertain scenarios need full detail — passes just need
`"passed": true`, they aren't findings.

### 5. Ingest into HITL
```bash
./bin/cherenkov record results.json --run-id explore_2026-07-11_1
./bin/cherenkov hitl list --severity high
```
`cherenkov record` (`cherenkov/stages/copilot_cmd.py::run_record`) converts
each failed scenario into a `DivergenceHypothesis` (class `D3_ui_spec`, via
`cherenkov/copilot/live_session.py`) and enqueues it into the same
`HitlQueue` every other finding uses — same triage commands, same severity
filter, no parallel defect-tracking system.

### 6. Optional: promote to a regression test
For any scenario worth keeping as a permanent check:
```bash
./bin/cherenkov author "<raw_intent>" --output ./tests --target <url>
```

## D7 invariant
This skill only ever produces `DivergenceHypothesis` records for human
triage via HITL — it never auto-confirms a defect or auto-edits application
code. Same suggest-only contract as `self-healing` and `hitl-review`.

## References
- `cherenkov/copilot/live_session.py` — `hypothesis_from_scenario()`, `enqueue_scenario_finding()`
- `cherenkov/stages/copilot_cmd.py` — `run_explore`, `run_author`, `run_record`
- `cherenkov/copilot/intent.py` — `IntentAuthor`, locator philosophy, `IntentSpec`/`IntentStep`
- `cherenkov/divergence/explorer.py` — mechanical crawl this composes with
- `cherenkov/hitl/store.py`, `cherenkov/hitl/contracts.py` — the queue findings land in
- `skills/hitl-review/SKILL.md` — how a human triages what this skill enqueues
