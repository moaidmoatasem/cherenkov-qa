# TesterArmy teardown — what to steal, what to ignore, what to build

**Date:** 2026-08-07
**Subject:** [TesterArmy](https://tester.army) — `testerarmy` / `ta` CLI, npm **v0.9.0**
**Status of this doc:** a review, not a roadmap. `docs/ROADMAP_2026H2.md` + `HANDOVER.md`
remain the forward plan; every action proposed in §6 maps onto an existing milestone
(M2, M3, or the T track) rather than opening a new one.

---

## 1. Scope and method — read this before trusting anything below

The request was to review `https://docs.tester.army/get-started`. **That page was never
read.** `docs.tester.army`, `tester.army`, and `context7.com` are all blocked by this
environment's network egress policy (the proxy answers `403` to `CONNECT`). Only
`github.com` / `raw.githubusercontent.com` / `registry.npmjs.org` were reachable.

So the product was reconstructed from what *is* public and reachable:

| Source | What it gave |
|---|---|
| `npm pack testerarmy` → **v0.9.0** | The shipped CLI. `dist/` is obfuscated with `js-confuser`, but the string table survives intact and yields every command, flag, error message, and — usefully — the entire body of `ta docs <topic>`, which is the same copy the docs site is built from |
| [`tester-army/cli`](https://github.com/tester-army/cli) README | Positioning, quickstart, skill-install path |
| `examples/TESTER.md` in that repo | Their scenario file format |

**Confidence:** high on *what the CLI does* (read directly off the shipped artifact),
lower on *what the docs page says* (never seen — it may lead or lag v0.9.0). Anything
below that depends on the docs page specifically is marked as such. Nothing here is
taken from marketing copy, because none was reachable.

**Maturity note:** they are at **0.9.0**. This is a young product, which makes the
comparison in §5 sharper, not softer.

---

## 2. What TesterArmy actually is

**A hosted browser-QA agent. The CLI is a control plane, not the product.** This is
their framing, not an inference — it is the text `ta agent init` writes into your
repo's `AGENTS.md`:

> The CLI is a control plane for the TesterArmy dashboard: use it to manage projects,
> environments, and saved tests, and to queue remote runs that execute in TesterArmy cloud.

and, from `ta docs local-run`:

> The CLI is primarily a dashboard control plane; local runs are for quick exploration only.

**Object model:** `project → { environments, credentials, files, memories } → tests → groups → runs`.
API surface is `/api/v1/{projects,tests,groups,ai}`.

**Tests** are plain-language steps, each typed `act | assert | login | screenshot`:

```json
{"title":"Login flow","steps":[
  {"title":"Navigate to /login","type":"act"},
  {"title":"Dashboard loads","type":"assert"}]}
```

**Engine**, from `package.json` dependencies: `@playwright/mcp@^0.0.68`, `ai@7.0.2`,
`@ai-sdk/gateway@4.0.2`, `playwright@1.59.0-alpha`. So: Playwright driven by an LLM
through the Playwright MCP server, with inference routed through *their* AI gateway on
*their* key. There is no BYO-LLM path in the bundle.

**Command surface** (reconstructed complete):

| Group | Commands |
|---|---|
| `agent` | `init` |
| — | `auth`, `status`, `docs <topic>` |
| `projects` | `list`, `get`, `create`, `environments`, `environments-create`, `environments-delete`, `credentials`, `files` |
| `memories` | `list`, `create`, `delete` |
| `tests` | `list`, `get`, `create`, `update`, `delete`, `run` |
| `groups` | `list`, `get`, `create`, `add-test`, `remove` |
| `runs` | `list`, `get`, `wait`, `cancel` |
| — | `ci`, `run "<prompt>"`, `pr` |

**Mobile is real, not a stub:** iOS Simulator `.app` / `.app.zip` / `.zip` and Android
`.apk` / `.apks`, 2 GB cap, with explicit rejections for `.ipa`, `.aab`, `.xapk`, and
legacy `.tar.gz` archives. Flags include `--device-model`, `--simulator-region`,
`--remove-after`, `--delete-app-after-run`.

**Their agent's browser toolset** — worth reading as a requirements list:

```
ui_navigate  ui_click  ui_click_vision  ui_double_click  ui_fill  ui_fill_credential
ui_type_focused  ui_press  ui_select  ui_check  ui_uncheck  ui_hover  ui_scroll
ui_drag_and_drop  ui_long_press  ui_dismiss_keyboard  ui_upload_file  ui_tabs
ui_get_text  ui_verify_text  ui_take_screenshot  ui_get_clipboard
ui_get_network_requests  ui_console_messages  ui_get_notifications
browser_evaluate  browser_execute_code  browser_runtime_init
```

Three of those are hard-won and worth noting: `ui_click_vision` (a vision fallback for
when ref-based clicking fails — *"If the target is visible on the screenshot, click it
with ui_click_vision instead of retrying the same ref"*), `ui_get_clipboard` (verifying
copied API keys, invite links, OTPs), and `ui_get_notifications`.

---

## 3. Is there any good use of it *to us*?

Three questions, three different answers.

### 3a. Should we use TesterArmy on CHERENKOV itself? **No.**

Not on principle — on three concrete grounds:

1. **It would send our dashboard to their cloud.** Remote is the default and the
   supported path; `--local` is explicitly deprecated in their own docs to "quick
   exploration." Our app-under-test, our fixtures, and our credentials would transit a
   third-party gateway.
2. **We already have the coverage.** `playwright-suite/` + `tests/qa/*.spec.ts` run 260
   headed E2E locally with no external dependency. Adding a cloud QA vendor to test the
   QA tool buys us nothing we don't have.
3. **It contradicts the 2026-08-01 product decision** (fully open source, self-hosted, no
   monetization). Depending operationally on a closed hosted competitor is a posture we'd
   have to explain.

### 3b. Is any *piece* of it directly reusable? **Yes — one, and it isn't theirs.**

`@playwright/mcp` is an open Microsoft package. If `agentic-exploration` (`skills/agentic-exploration/`,
`cherenkov record`) grows a real browser-driving layer, that is the substrate to build on
— TesterArmy is simply a worked example of what a good tool surface over it looks like.
Their own `ui_*` layer is obfuscated and MIT-licensed-in-name-only in practice (the source
repo `tester-army/tester-army` is not public; only `tester-army/cli` is). Read it for
ideas; don't vendor it.

### 3c. Is it useful as a **reference implementation**? **Yes. This is the real value.**

Their agent-onboarding surface (§5.1–5.3) is the best worked example I've seen of
"make a CLI discoverable to a coding agent that has never heard of it." That pattern is
free of their cloud architecture, costs us nothing to adopt, and is precisely what M1 and
M2 need. That is what §6 is a plan for.

---

## 4. Where we are ahead — do not chase these

Searched the full 1.2 MB bundle. **There is no integrity check of any kind.** No mutation
testing, no assertion-meaningfulness gate, no equivalent of `check-suite`. A TesterArmy
test that asserts nothing passes forever and nobody finds out. That is the entire
CHERENKOV thesis (`cherenkov/sdet/`, `cherenkov/divergence/mutant_synth.py`,
`demos/catch-the-ai-cheating/`) and it is uncontested.

Also uncontested, and not to be traded away in pursuit of anything in §5:

| We have | They have |
|---|---|
| Spec-derived oracles, divergence proof runs, coverage reports | Plain-language assertions judged by an LLM |
| Signed certificates + compliance mapping (`cherenkov/core/certificate.py`) | — |
| `eject` to vanilla Playwright, zero lock-in (verified against a real `npm install`) | Tests live in their dashboard |
| Self-hostable, Apache 2.0, BYO-LLM across 8+ providers (`cherenkov/substrate/providers/`) | Their gateway, their key |
| API/contract depth | UI/browser depth, web + mobile |

The last row is the honest summary of the relationship: **we are not really competitors.**
They test *interfaces a human clicks*; we test *contracts a machine relies on*. The
overlap is the go-to-market surface, not the engine.

---

## 5. What we are missing — ranked, with evidence

### 5.1 One-command agent bootstrap — **the sharpest gap**

`ta agent init` does two things in one command: installs a public skill
(`npx skills add tester-army/cli`) *and* writes a delimited block into the host repo's
`AGENTS.md`:

```
<!-- TESTERARMY:START -->
This project can use TesterArmy for agent-driven QA coverage and validation.
- **Auth check:** start with `ta status --json`…
- **Discover scope:** use `ta projects list --json`…
<!-- TESTERARMY:END -->
```

**Our position:** half-built and we get no credit for it. `skills/README.md` already
documents `npx skills add moaidmoatasem/cherenkov-qa` across 20 skills — the hard part is
done. What's missing is the bootstrap command and the repo-level discovery block:
`grep -rln 'AGENTS.md' cherenkov/ --include=*.py` returns **nothing**. An agent that lands
cold in a stranger's repo has no way to learn CHERENKOV exists.

**Maps to:** M2 (installable by a stranger).

### 5.2 Machine-readable docs

`ta docs <topic> --json` returns `{summary, commands, notes}` per topic — docs as data,
addressable, written *at* agents. Sample notes, verbatim: *"Use IDs exactly as returned"*,
*"Do not print real API keys or saved credentials in final messages"*, *"Before non-trivial
QA work, list memories for the project."*

**Our position:** `cherenkov examples` (`cherenkov/cli/commands/examples_cmd.py:8`) is a
flat printed list of one-liners with no `--json`, no topics, and no agent-directed notes.

**Maps to:** M2.

### 5.3 `--json` coverage is uneven

**10 of 23** command modules define a `--json` or `--format` option
(`advanced check_stale drift_cmd enterprise epoch eval_cmd ocr_cmd playbook_cmd simple validate`).
The other 13 — including `certify`, `check-suite`, `verify`, `generate_cmd`, `report`,
`audit`, `guardian_cmd` — are human-text only. For a tool whose stated audience includes
coding agents, that is the line between parseable and not.

**Maps to:** T track.

### 5.4 Distribution is not actually done

| Package | Registry | Status |
|---|---|---|
| `testerarmy` | npm | **published, 0.9.0** |
| `cherenkov` | npm | **404** |
| `cherenkov-qa` | npm | **404** |
| `cherenkov-qa` | PyPI | **404** |

And we carry *two* divergent unpublished npm package dirs: `npm/package.json` (name
`cherenkov-qa`, v1.0.0) and `npm-package/package.json` (name `cherenkov`, v1.0.0, with a
`postinstall` shim) — both stale against the project's real 1.3.0. PyPI is correctly gated
behind M1 per `HANDOVER.md`; **the npm duplication is not gated by anything** and is
unblocked cleanup today.

**Maps to:** M2 (#792 sits here).

### 5.5 No named environments

Theirs: `ta tests run <id> --env staging`, with environments as first-class project
children, Production and PR-Preview built in and undeletable, and a clear error when a
name doesn't resolve (*"Available environments: …"*).

Ours: `--url <target>`, retyped every invocation. The journeys work (2026-08-06,
`cherenkov/journeys/`) is the natural home — `POST /api/v1/journeys/{id}/runs` already
exists and has nowhere to name a target.

**Maps to:** T track, after M1.

### 5.6 Credentials are inline

They model credentials as first-class objects (`kind: login | inbox`, with
`label` / `authInstructions` / `username` / `password`), referenced from a step by
`credentialId` or `temporaryEmail` — the `inbox` kind is the OTP path. Their guidance:
*"Use login steps with credentialId or temporaryEmail instead of putting secrets in step text."*

Ours: `grep -rlniE 'credential' cherenkov/cli/` returns **nothing**. E0.3 practitioners
will point this at authenticated APIs; "paste your token into the command" is friction
we will read about in the friction log.

**Maps to:** T track. Relevant to M1 prep (#816).

### 5.7 Project memory is half-wired

`ta memories` persists durable app knowledge across runs — categories `site_structure`,
`test_insights`, `user_preferences`, each with an importance level, consulted *before*
non-trivial work.

We have the Knowledge hub in the dashboard, but `grep -rln 'knowledge' cherenkov/cli/`
returns **nothing** — the half agents can reach is the half that's missing.

**Maps to:** T track.

### 5.8 PR ergonomics

M3's PR-comment Action is delivered (#766) and `action.yml` exists. Theirs goes further:
`--pr-number`, `--pr-title`, `--pr-description`, `--commit-sha`, `--head-branch`,
`--base-branch`, plus `--deeplink` for per-PR dynamic preview environments and
`--artifact-url` / `--artifact-filename` for build artifacts.

Worth reading as a checklist *before* M3's remaining items close, not as new scope.

**Maps to:** M3.

### 5.9 UI/browser depth — noted, not a gap to close

Their `ui_*` toolset (§2) is the mature version of what `explore` / `record` /
`skills/agentic-exploration/` gestures at. This is a *different product*, and chasing it
wholesale would be the single fastest way to lose the API-contract focus that makes
CHERENKOV worth using. Recorded here as a reference spec for if and when
`agentic-exploration` is invested in — particularly the vision-click fallback and the
network/console capture tools.

---

## 6. The plan

> **Status, 2026-08-07:** Phase A is **shipped** (A1 and A2 complete; A3 partial — `check-suite`
> only). Phase B–D are **not started**. `HANDOVER.md` carries the current state and wins over this
> section if the two disagree — this doc is a point-in-time review, not a live tracker.

Sequenced by dependency, mapped to existing milestones. Nothing here opens new scope; §6.4
is explicitly the "don't" list.

### Phase A — agent-installability (M2, unblocked now)

The three items in §5.1–5.3 are one coherent piece of work: *make CHERENKOV discoverable
and parseable by an agent that has never heard of it.* Do them together.

| # | Deliverable | Acceptance criterion |
|---|---|---|
| A1 | `cherenkov agent init` — installs the public skills (`npx skills add moaidmoatasem/cherenkov-qa`, with a graceful skip + printed fallback when `npx` is absent or times out) and writes a `<!-- CHERENKOV:START -->…<!-- CHERENKOV:END -->` block into the repo's `AGENTS.md`, creating it if absent and replacing the block idempotently if present. `--skip-agents-md` and `--json` flags. | Run twice in a scratch repo → identical `AGENTS.md`, exit 0 both times. Block names the 4 entry commands and the auth check. |
| A2 | `cherenkov docs <topic>` with `--json`, seeded from `examples_cmd.py`. Topics: `auth`, `generate`, `verify`, `check-suite`, `certify`, `eject`, `journeys`, `mcp`, `ci`. Each returns `{summary, commands[], notes[]}`. | `cherenkov docs --json \| jq -e '.topics \| length >= 8'` passes. Unknown topic exits non-zero listing available topics. |
| A3 | `--json` on the 13 modules that lack it, starting with `verify`, `certify`, `check-suite`, `report`, `audit` — the five an agent is most likely to call. Shape must be stable and documented. | Golden-output test per command; no human-text parsing needed to get verdict + exit code. |

**Why together:** A1 without A2/A3 points an agent at commands it can't parse. A3 without
A1 is invisible.

### Phase B — distribution hygiene (M2, unblocked now)

| # | Deliverable | Acceptance criterion |
|---|---|---|
| B1 | Resolve `npm/` vs `npm-package/` — pick one name, delete the other, sync the version to the real release. | One package dir; `version` matches `pyproject.toml`; a release-check asserts they can't drift. |
| B2 | Decide and record the npm story: publish a thin launcher, or delete the dirs and stop implying an npm install exists. **Either is defensible; the current state — two unpublished, divergent, stale package dirs — is not.** | Decision recorded in `HANDOVER.md`. If publish: `npx cherenkov --help` works from a clean machine. |
| B3 | PyPI publish — **stays gated behind M1.** No action now; listed so it isn't lost. | — |

### Phase C — run-target ergonomics (T track, after M1 opens)

| # | Deliverable | Acceptance criterion |
|---|---|---|
| C1 | Named environments on the journeys model (§5.5): `cherenkov ... --env staging` resolving through `cherenkov.toml`, with a resolution error that lists available names. | Round-trips through both CLI and `POST /api/v1/journeys/{id}/runs`. |
| C2 | Credential references (§5.6): a `credentials` block keyed by id, referenced as `--credential <id>`, never echoed in logs or reports. | `grep` the run log for the secret after an authenticated run → no hit. |
| C3 | Surface the Knowledge store to the CLI (§5.7) — a `knowledge` command with `list` / `add` subcommands and JSON output. | An agent can read prior findings without opening the dashboard. |

C1 and C2 should be validated against the #816 friction log rather than designed in the
abstract — if practitioners don't hit the pain, they don't earn the complexity.

### Phase D — M3 checklist review (M3)

D1: read `action.yml` against §5.8's flag list and file whatever is genuinely missing as
issues on M3. Not a build item; a 30-minute comparison that either closes cleanly or
produces two small issues.

### 6.4 Explicitly rejected — do not build

- **A hosted run backend.** Their whole architecture. Contradicts the 2026-08-01
  open-source decision.
- **Depending on TesterArmy in our own CI** (§3a).
- **Vendoring their `ui_*` layer.** Obfuscated, source not public. `@playwright/mcp` is
  the legitimate substrate if we ever need one.
- **A mobile testing track.** Their mobile support is genuinely good and entirely outside
  our thesis.
- **Chasing UI/E2E breadth** (§5.9). The overlap with them is go-to-market, not engine —
  competing on their axis costs us ours.

---

## 7. The one-line lesson

They shipped at 0.9.0 with a worse engine and a better front door. **The gap that matters
isn't capability — it's that a stranger can install their tool in one command and an agent
can discover it without being told.** Phase A and B close that, and neither requires
giving up anything in §4.

---

## Provenance

- Reconstructed from `testerarmy@0.9.0` (npm), `tester-army/cli` README + `examples/TESTER.md`.
- `docs.tester.army` was **not** reachable from this environment; no claim here rests on it.
- CHERENKOV-side claims verified by grep against the tree at `de2974a`, cited inline.
