# CHERENKOV — Capability Coverage Audit

**Date:** 2026-08-11. **Method:** every claim below was checked against code, and every CLI
surface was invoked. Where a capability is claimed by `docs/ROADMAP.md` but not reachable by a
user, that is recorded as a gap rather than a feature.

> This audit exists because the failure mode in this repo is not missing code — it is **code that
> exists but is unreachable, unwired, or fabricated**. Three of the findings below are of exactly
> that shape.

---

## 1. Coverage matrix

| Area | State | Evidence |
|---|---|---|
| **API conformance — OpenAPI** | ✅ Core | `truth/sources/openapi.py`, `validate --source openapi` (default) |
| **API — GraphQL** | ✅ Wired | `sources/graphql/adapter.py`, `stages/plan_graphql.py`, `validate --source graphql` |
| **API — gRPC** | ✅ Wired | `stages/plan_grpc.py`, `validate --source grpc` |
| **API — AsyncAPI** | ⚠️ **Orphaned** | `sources/asyncapi/`, `validate/asyncapi.py`, `stages/plan_asyncapi.py` all exist, but `AsyncAPIScenarioPlanner` is imported **nowhere** and `asyncapi` is absent from `validate --source` choices |
| **API — SOAP / WebSocket** | ❌ Absent | No modules. Not currently claimed by the roadmap either |
| **Accessibility testing** | ✅ Present | `validate --source accessibility` |
| **Performance testing** | ✅ Present | `cherenkov perf`, `cherenkov bench`, `stages/perf/perf_stage.py`, `execution/perf_analyzer.py`, `web/routes/perf_routes.py`, k6 (`stub/generated_tests/k6_perf.js`, CI "Perf Baseline") |
| **Mobile testing** | ✅ **Fixed here** | Full pipeline (`stages/mobile_{cmd,plan,generate,review}.py`, Appium + Maestro ejectors, `rag/mobile_index.py`, k8s job, CI workflow). **Was unreachable — `mobile_cmd` was never registered in `cli/core.py`.** Now wired + documented + guarded by a test |
| **Web UI testing** | ✅ Present | `cherenkov visual` — pixel-diff regression plus an advisory VLM semantic gate (ANOMALY / HARMLESS_SHIFT / REDESIGN), baselines auto-init only, D7-safe |
| **UX / UI flows** | ✅ Present | 6 dashboard workspaces (Dashboard, Authoring, Triage, Intelligence, Enterprise, Settings); declarative journeys (`cherenkov/journeys/`) executed by the engine and rendered by the UI |
| **Anti-lock-in / eject** | ✅ Present | `execution/eject.py` emits vanilla Playwright + `playwright.config.ts` with zero CHERENKOV imports; mobile equivalents for Appium/Maestro |
| **Scalability** | ⚠️ Partial | `k8s/` has HPA, operator and prism deployments. **Known limit (documented):** rate limiter and APScheduler are per-process, so N replicas = N× rate and N× routine firings |
| **GitHub integration** | ✅ Strong | `action.yml`, `web/routes/webhooks_github.py`, `web/pr_comments.py`, `validate/github_exporter.py`, `export_github_ticket` MCP tool, `validate` PR flags (`--pr-number`, `--commit-sha`, `--head-branch`, `--base-branch`, `--deeplink`) |
| **GitLab integration** | ✅ Present | `ci/gitlab-ci-template.yml` — flags verified against the live CLI |
| **CircleCI** | ✅ Present | `ci/circleci/orb.yml` — flags verified |
| **Jenkins** | ✅ **Fixed** | `ci/jenkins/vars/cherenkovValidate.groovy` built an `--export-jira` option that exists on no command, and its catch block reported the resulting usage error as a conformance failure. Both corrected; now guarded by `check_cli_flags.py` (F2/F3) |
| **MCP surface** | ✅ Strong | 25+ tools: `generate`, `check_suite`, `verify`, `auto_heal_code`, `hitl_{list,approve,reject}`, `export_{github,jira,linear}_ticket`, `event_bus_*`, `mcp_registry_{list,publish}`, `policy_list`, chat tools. Plus `mcp/{auth,policy,sandbox,mesh_router}.py` and `server.json` |
| **Notifier connectors** | ✅ Present | `adapters/notifiers/`: Slack, Teams, PagerDuty, Opsgenie, Linear, generic webhook |
| **Issue trackers** | ✅ Present | Jira, Linear, GitHub via MCP export tools; Zephyr/Xray/Allure modules present |
| **LLM providers** | ✅ Strong | 11+ under `substrate/providers/`: Ollama, OpenAI, Anthropic, Bedrock, Azure OpenAI, LocalAI, HuggingFace, GitHub Models, AirLLM, NeMo, generic `openai_compat` |
| **IDE** | ✅ Present | `vscode/src/extension.ts` + `.github/workflows/vscode-ci.yml` |
| **Collaboration** | ✅ Present | HITL approve/reject store + MCP tools, `stages/review.py`, PR comments, federation mesh (`federation/mesh.py`), multi-tenant orgs + RBAC |
| **Observability connectors** | ❌ Gap | No SonarQube, Splunk, Okta, or Active Directory modules — all four are named in `ROADMAP.md` §3 Tiers 2/4 |
| **JetBrains IDE** | ❌ Gap | Named in `ROADMAP.md` §3 Tier 0; no module |

---

## 2. Findings requiring action

### F1 — `cherenkov mobile` was unreachable (**fixed in this change**)

`stages/mobile_cmd.py` defined a complete Click command and was never added to
`_register_commands()`. Mobile testing had stages, two ejectors, a RAG index, unit tests, a k8s
job and a dedicated CI workflow — and no way for a user to run it. Now registered, documented in
`GETTING_STARTED.md`, and guarded by `tests/unit/test_cli_command_registration.py`, which asserts
every capability surface resolves on the root CLI.

**Why nothing caught it:** every existing mobile test exercised the stages directly, never the CLI
entry point. The new test closes that class of gap for all ten capability commands.

### F2 — Jenkins template passed a flag that does not exist (**fixed**)

When `exportJira: true`, `ci/jenkins/vars/cherenkovValidate.groovy` appended an `--export-jira`
option to the `validate` invocation it builds. No command defines that option. The invocation
failed, and because the call sat inside `try { sh "${cmd}" } catch`, the failure surfaced as
*"CHERENKOV Conformance check failed"* — a usage error misattributed as a conformance result.

This is the same shape as the `action.yml` incident of 2026-08-07 (inert config reporting success).
Jira export does exist, but as the `export_jira_ticket` MCP tool, not a `validate` flag.

**Fixed:** the option is gone, and passing `exportJira` now emits an explicit notice pointing at the
MCP tool rather than silently ignoring it. The template also switched from `try/catch` to
`sh(returnStatus: true)` so the two failure classes are distinguishable — Click exits `2` when it
rejects an invocation, which is now reported as a usage error, never as drift.

### F3 — The flag guard did not cover `ci/` (**fixed**)

`scripts/check_cli_flags.py` validates documented flags against the live Click tree, but scanned only
`docs/` and `skills/` markdown. Every CI integration template — the GitLab, CircleCI and Jenkins
files users copy verbatim — was unguarded. F2 is the bug this gap allowed.

**Fixed:** the scan now covers `ci/**` (`.yml`, `.yaml`, `.groovy`) and `action.yml`. Three shapes
had to be handled, each of which defeats naive line-matching:

| Shape | Where | Handling |
|---|---|---|
| Backslash continuation — `cherenkov validate \` then 15 flag lines | `action.yml` | Logical lines are joined before matching; otherwise **every** flag there goes unchecked |
| Conditional append — `cmd += " --export-jira"` | Jenkins | Attributed to the file's command when the file invokes exactly one; multi-command files stay line-local to avoid false positives |
| Multiple commands in one file — `validate` and `report` | CircleCI orb | Flags resolve per logical line |

Comments are stripped first. Without that, the prose `// ... assuming cherenkov is installed on the
agent` parses as a command named `is installed`, which made the Jenkins file look multi-command and
silently disabled the append check — **the guard passed while the bug it was written for sat two
lines away.** Verified non-vacuous both ways: it fails on the real `--export-jira`, and still fails
when a fresh bogus flag is introduced.

### F4 — AsyncAPI is built but unreachable

`ROADMAP.md` Phase 12 claims "GraphQL, gRPC, and AsyncAPI". The first two are wired into
`validate --source`; AsyncAPI is not, and `AsyncAPIScenarioPlanner` has no importer. Either wire it
up (it appears to be a small change — add the choice and the dispatch branch, mirroring the
GraphQL/gRPC blocks in `cli/commands/validate.py`) or stop claiming it.

### F5 — Tier integrations claimed but absent

`ROADMAP.md` §3 commits to "25 external systems across 5 tiers". Missing entirely: **SonarQube**
(Tier 2), **Splunk, Okta, Active Directory** (Tier 4), **JetBrains** (Tier 0). Okta/AD in
particular read as already-covered because SAML SSO exists — SAML is the *protocol*, and a generic
SAML SP does cover Okta and AD FS in practice, so the honest statement is "supported via SAML, not
separately integrated". The §3 list should be reconciled to what exists.

---

## 3. What is genuinely strong

Worth stating plainly, because the findings above are all gaps: the **protocol breadth**
(OpenAPI + GraphQL + gRPC + accessibility), the **MCP surface** (25+ tools, both directions —
agents call CHERENKOV to verify, CHERENKOV calls out for context), the **provider neutrality**
(11+ LLM backends behind one interface), and the **eject guarantee** (vanilla Playwright/Appium/
Maestro, zero imports) are all real, wired, and tested. Those are the north-star-load-bearing
surfaces (`NORTH_STAR.md` §6), and they hold up.
