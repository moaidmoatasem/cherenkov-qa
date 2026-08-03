# CHERENKOV CLI Reference

Complete reference for the Click-based `cherenkov` CLI. This page is generated
against the live command registry (`cherenkov/cli/core.py`) — **40 commands**
organized into **7 command groups** (47 total registered names).

> **Source of truth for flags:** run `cherenkov <command> --help`. This page
> lists every command with its one-line purpose and the flags for the primary
> commands; the deep, worked walkthroughs live in
> [GETTING_STARTED.md](GETTING_STARTED.md).

**Invoke via** `cherenkov <command> [options]` (installed entry point) or, from a
source checkout, `python -m cherenkov.cli.core <command>`.

Two flags are honored by most commands for machine/CI use:

- `--json` — emit pure JSON to stdout.
- `--quiet, -q` — suppress non-error output; print only the final status line.

---

## Command index

| Command | Purpose |
|---|---|
| **Validation & integrity** | |
| [`verify`](#verify) | Verify a live API against its OpenAPI spec — find spec↔implementation divergences. |
| [`validate`](#validate) | Validate an E2E test suite against a real server. |
| [`check-suite`](#check-suite) | Catch AI cheating in a test suite — detect WEAKENED, DELETED, or HALLUCINATED assertions. |
| [`certify`](#certify) | Issue a signed verification certificate for a live API. |
| [`generate`](#generate) | Generate Playwright E2E tests from an OpenAPI specification. |
| [`report`](#report) | Summarise and diff cherenkov run reports. |
| [`diff`](#diff) | Compare two OpenAPI specs for breaking changes. |
| [`drift`](#drift) | Detect and report drift between spec, suite, and live API. |
| [`check-stale`](#check-stale) | Check whether generated tests are stale relative to the spec. |
| **Onboarding & project** | |
| [`init`](#init) | Zero-config project setup. |
| [`demo`](#demo) | 60-second offline demo — watch CHERENKOV catch the AI cheating. |
| [`examples`](#examples) | Show a gallery of common CHERENKOV one-liners. |
| [`self-test`](#self-test) | Live smoke test of the core pipeline (real Ollama generation + tsc compile). |
| [`doctor`](#doctor) | System health check. |
| [`eject`](#eject) | Eject generated tests to a standalone Playwright suite. |
| [`completion`](#completion) | Generate shell completion scripts. |
| **Dashboards & human review** | |
| [`dashboard`](#dashboard) | Visualise Truth Model + divergences. |
| [`review`](#review) | Start the review dashboard web UI (FastAPI + prebuilt frontend). |
| [`hitl`](#hitl) | Manage the Human-in-the-Loop review queue. |
| **Truth model & exploration** | |
| [`map`](#map) | Build + inspect the Truth Model from configured sources. |
| [`explore`](#explore) | Crawl a live surface and print a risk digest. |
| [`author`](#author) | Turn plain-language intent into an ejectable Playwright test. |
| [`daemon`](#daemon) | Continuously watch sources and rebuild the Truth Model, or run Spec Guardian. |
| **Data & quality** | |
| [`synthetic`](#synthetic) | Generate synthetic test data from an OpenAPI spec. |
| [`bench`](#bench) | Benchmark the REVIEW stage against a corpus of generated tests. |
| [`eval`](#eval) | Evaluate, grade, and optimize your test-suite quality. |
| [`visual`](#visual) | Run optional visual-regression checks against a rendered URL (Track B). |
| [`perf`](#perf) | Run optional performance baseline checks (Track B). |
| [`ocr`](#ocr) | Alibaba Open Code Review integration. |
| **Governance & platform** | |
| [`governance`](#governance) | Governance KPI panel (escape / FP / coverage / maintenance). |
| [`profile`](#profile) | Autonomy-ladder profile (assisted / augmented / agentic / predictive). |
| [`tokens`](#tokens) | Token consumption monitor — usage, cost, recommendations. |
| [`mcp`](#mcp) | Expose CHERENKOV over the Model Context Protocol. |
| [`teleport`](#teleport) | Manage cross-device session teleportation. |
| [`routine`](#routine) | Manage automated scheduling routines. |
| [`playbook`](#playbook) | Manage and run validation playbooks (auto-triggering skill rules). |
| [`enterprise`](#enterprise) | Enterprise-tier commands: org management, SSO, audit logs, compliance. |
| **Command groups** | |
| [`pipeline`](#command-groups) | Core API conformance pipeline group. |
| [`review`](#command-groups) | Human-in-the-loop review workflows group. |
| [`model`](#command-groups) | Model / VLM substrate commands group. |
| [`operate`](#command-groups) | Long-running operations and observability group. |
| [`admin`](#command-groups) | Setup, maintenance, and self-service group. |
| [`enterprise`](#command-groups) | Enterprise integrations and certification group. |
| [`routine`](#command-groups) | Scheduled routines group. |

---

## Command groups

The CLI organizes its 40 top-level commands into 7 logical command groups for
discoverability. Every command remains available at the top level for backwards
compatibility. See [CLI_GROUPS.md](CLI_GROUPS.md) for the full group reference.

| Group | Member commands |
|-------|-----------------|
| `pipeline` | `validate`, `verify`, `audit`, `check-suite`, `check-stale`, `synthetic`, `generate`, `bench`, `eval`, `drift` |
| `review` | `hitl`, `review`, `ocr` |
| `model` | `visual`, `perf`, `mcp`, `examples` |
| `operate` | `daemon`, `dashboard`, `explore`, `map`, `author`, `record`, `tokens`, `governance`, `profile`, `teleport` |
| `admin` | `init`, `doctor`, `self-test`, `eject`, `completion`, `report`, `diff`, `demo` |
| `enterprise` | `enterprise`, `certify`, `playbook`, `guardian` |
| `routine` | `routine` |

---

## Validation & integrity

### `verify`
Verify a live API against its OpenAPI spec — find spec↔implementation divergences.

```bash
cherenkov verify --url https://petstore3.swagger.io/api/v3 --spec ./openapi.yaml
```

| Flag | Default | Description |
|---|---|---|
| `--url, --base-url, -u` | *required* | Base URL of the live server to probe. |
| `--spec, -s` | built-in Petstore | Path or URL to the OpenAPI spec (JSON/YAML). |
| `--llm / --offline` | `--offline` | Use the LLM Skeptic for hypothesis generation (requires Ollama). |
| `--output, -o` | — | Write the divergence report to this file. |
| `--format` | `json` | Report format for `--output`: `json` or `text`. |
| `--fail-on-divergence` | off | Exit `1` if any divergences are found (CI gate). |
| `--coverage-report` | off | Print a spec coverage-gap report after the proof run (requires `--spec`). |
| `--rich-verdict / --simple` | `--rich-verdict` | Full multi-agent verdict engine; `--simple` for the lighter path. |
| `--no-mutation-oracle` | off | Skip the mutation-oracle dimension (faster, less thorough). |
| `--no-traffic-capture` | off | Skip golden-fixture capture from real traffic. |
| `--fixture-dir` | `.cherenkov/fixtures` | Directory for captured golden fixtures. |

> **Known limitation:** offline `verify` currently probes built-in Petstore
> hypotheses regardless of `--spec` (spec-derived probe planner is tracked as
> R1 in [HANDOVER.md](../HANDOVER.md)). Point `verify` at the Petstore target
> until that lands.

### `validate`
Validate an E2E test suite against a real server.

```bash
cherenkov validate --target http://localhost:8080 --spec ./openapi.yaml --fail-on-drift
```

| Flag | Default | Description |
|---|---|---|
| `--target, -t` | *required* | The real server target base URL. |
| `--spec` | — | Path to OpenAPI spec (JSON/YAML). |
| `--source` | `openapi` | Source type for ingestion (`openapi`, `grpc`, `graphql`). |
| `--format` | inferred | Output report format. |
| `--output` | `.cherenkov/report` | Output path (extension inferred from `--format`). |
| `--workers` | `1` | Parallel workers for Playwright tests. |
| `--no-html` | off | Disable automatic HTML report generation. |
| `--no-cache` | off | Disable incremental test-generation cache. |
| `--fail-on-drift` | off | Exit `1` on conformance violations (CI gate). |
| `--json-summary` | — | Write a machine-readable JSON summary to this path. |
| `--json` | off | Emit pure JSON to stdout. |
| `--quiet, -q` / `--verbose, -v` | — | Quiet = final status only; verbose = per-gate + per-scenario detail. |

### `check-suite`
Catch AI cheating in a test suite — detect WEAKENED, DELETED, or HALLUCINATED
assertions via pure Python AST analysis (no LLM). See
[demos/catch-the-ai-cheating](../demos/catch-the-ai-cheating/).

```bash
cherenkov check-suite --candidate ./tests --spec ./openapi.yaml --fail-on-finding
```

### `certify`
Issue a signed verification certificate for a live API. Supports
`--coverage-report`. Certificate format is STABLE v1.0 —
[docs/specs/CHERENKOV_CERTIFICATE.md](specs/CHERENKOV_CERTIFICATE.md).

### `generate`
Generate Playwright E2E tests from an OpenAPI specification.

```bash
cherenkov generate --spec ./openapi.yaml
```

| Flag | Default | Description |
|---|---|---|
| `--spec` | *required* | OpenAPI spec (JSON/YAML) to generate tests for. |
| `--output-dir` | `stub/generated_tests` | Directory for generated Playwright test files. |
| `--repair / --no-repair` | `--repair` | Route generation through the RepairLoop. |
| `--max-attempts` | `3` | Repair attempts (1–10). |

### `report`
Summarise and diff cherenkov run reports. `-o` JSON output, `-d` diff against a
baseline, `--run` / `--list` for RunStore mode.

### `diff`
Compare two OpenAPI specs for breaking changes.

### `drift`
Detect and report drift between spec, suite, and live API. (Subcommand group —
`cherenkov drift --help`.)

### `check-stale`
Check whether generated tests are stale relative to the spec.

---

## Onboarding & project

### `init`
Zero-config project setup — scaffolds `.cherenkov/` and config.

### `demo`
60-second offline demo — watch CHERENKOV catch the AI cheating. Zero network,
zero LLM, pure static AST analysis.

### `examples`
Show a gallery of common CHERENKOV one-liners.

### `self-test`
Live smoke test of the core pipeline: real Ollama generation + `tsc` compile.

### `doctor`
System health check — verifies Python, Node/npx, Playwright, Ollama + model, and
optional Docker/Prism.

### `eject`
Eject generated tests to a standalone Playwright suite with **zero CHERENKOV
dependency**. The result runs under plain `playwright test`.

```bash
cherenkov eject --output ./tests
```

| Flag | Default | Description |
|---|---|---|
| `--output, -o` | *required* | Target output directory for the standalone suite. |

### `completion`
Generate shell completion scripts. Install with, e.g.,
`eval "$(_CHERENKOV_COMPLETE=bash_source cherenkov)"`.

---

## Dashboards & human review

### `dashboard`
Visualise the Truth Model + divergences in the built-in web UI.

### `review`
Start the review dashboard web UI (FastAPI + prebuilt frontend).

```bash
cherenkov review --port 8000 --demo
```

| Flag | Default | Description |
|---|---|---|
| `--host` | `0.0.0.0` | Host to bind. |
| `--port, -p` | `8000` | Port to bind. |
| `--demo` | off | Load demo fixture data into the HITL queue on startup. |

### `hitl`
Manage the Human-in-the-Loop review queue: `list`, `show <id>`, `approve <id>`,
`reject <id>`, `classify <id>`, `explain <id>`. See
[GETTING_STARTED.md](GETTING_STARTED.md) for the full HITL workflow and error codes.

---

## Truth model & exploration

### `map`
Build + inspect the Truth Model from configured sources.

### `explore`
Crawl a live surface and print a risk digest.

```bash
cherenkov explore --target http://localhost:8080 --path / --method GET
```

| Flag | Default | Description |
|---|---|---|
| `--target, -t` | *required* | Base URL of the app/API to crawl. |
| `--path, -p` | `/` | Route to probe (repeatable). |
| `--method, -m` | `GET` | HTTP method. |

### `author`
Turn plain-language intent into an ejectable Playwright test.

### `daemon`
Continuously watch sources and rebuild the Truth Model, or run Spec Guardian.

```bash
cherenkov daemon --url http://localhost:8080 --interval 60
```

| Flag | Default | Description |
|---|---|---|
| `--interval, -i` | `60` | Poll interval in seconds. |
| `--max-loops, -n` | `0` | Max rebuild iterations (`0` = infinite). |
| `--url, -u` | — | Live server URL to probe for divergences each cycle. |
| `--guardian` | off | Run in Spec Guardian mode. |
| `--spec` | — | Path to spec (required for `--guardian`). |
| `--target` | — | Target URL (required for `--guardian`). |
| `--source` | `openapi` | Source type for guardian mode. |

---

## Data & quality

### `synthetic`
Generate synthetic test data from an OpenAPI spec.

### `bench`
Benchmark the REVIEW stage against a corpus of generated tests.

### `eval`
Evaluate, grade, and optimize your test-suite quality. (Subcommand group.)

### `visual`
Run optional visual-regression checks against a rendered URL (Track B).

### `perf`
Run optional performance baseline checks (Track B).

### `ocr`
Alibaba Open Code Review integration. (Subcommand group.)

---

## Governance & platform

### `governance`
Governance KPI panel (escape / FP / coverage / maintenance).

### `profile`
Autonomy-ladder profile (assisted / augmented / agentic / predictive).

### `tokens`
Token consumption monitor — usage, cost, recommendations. (Subcommand group.)

### `mcp`
Expose CHERENKOV over the Model Context Protocol. `cherenkov mcp install`
registers the server; see [docs/specs/MCP_VERIFICATION_SERVER.md](specs/MCP_VERIFICATION_SERVER.md).

### `teleport`
Manage cross-device session teleportation: `push <session_id>`, `pull <token>`.

### `routine`
Manage automated scheduling routines: `cherenkov routine list`, etc.

### `playbook`
Manage and run validation playbooks (auto-triggering skill rules).

### `enterprise`
Enterprise-tier commands: org management, SSO, audit logs, compliance.

---

## See also

- [GETTING_STARTED.md](GETTING_STARTED.md) — worked walkthroughs for every command (CI-parity-checked).
- [API_REFERENCE.md](API_REFERENCE.md) — REST API served by `cherenkov review` / `dashboard`.
- [config_cookbook.md](config_cookbook.md) — environment variables and configuration.
