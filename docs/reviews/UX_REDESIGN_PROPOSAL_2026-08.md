# UX Redesign Proposal — Extensibility, Test Management, OSS Readiness

**Date:** 2026-08-01
**Branch:** `claude/cherenkov-qa-ux-redesign-b6s2i7`
**Status:** Proposal, not yet built. Supersedes any prior "UI redesign" narrative describing an Intent Studio / Execution Sandbox / PRD ingestion engine — that work does not exist in this repository (see "What's real" below).

## 0. Branch/main alignment note

Before writing this, I checked whether this branch was behind `main`. The local git proxy's cached `origin/main` ref reported this branch 63 commits ahead, which would have meant a large divergence to reconcile. Cross-checked against the GitHub API directly: real `main` tip is `8cdcdf4`, identical to this branch's base — there was no actual divergence, just a stale local cache. No merge/rebase was needed. Also checked all ~90 branches in the repo for competing in-flight redesign work; nothing overlaps this proposal.

## 1. What's real vs. what a prior session claimed

A previous session's write-up described `prd_routes.py`, `sandbox_routes.py`, `outbound_dispatcher.py`, `FlowBuilder.tsx`, `TestManagementScreen.tsx`, and a 5-hub sidebar consolidation as already built, plus test-count and lint-pass claims. None of those files exist anywhere in git history or on disk. The only three things from that narrative that are real: `IntegrityHeatmap.tsx`, `SpecVsRealityScreen.tsx` (built, but renders hardcoded mock data, not live data), and the VS Code CodeLens provider. Everything below is scoped only to what's actually in the tree today, plus `docs/ROADMAP_2026H2.md`'s real M0–M5 milestones.

## 2. Product identity

Cherenkov is a **trust layer**, not an authoring tool. Momentic and TestSprite write and run tests for you; Cherenkov's differentiator is proving whether AI-generated tests are *honest* — that they'd actually catch real API drift instead of being quietly weakened — and backing that proof with a signed, open-spec certificate (`docs/specs/CHERENKOV_CERTIFICATE.md`, STABLE v1.0, Rung 3 already 5/5 complete). The core loop is **Spec → Generate → Verify/Certify → Triage (HITL) → Heal**, CLI-first, with the dashboard and MCP server as secondary surfaces onto the same engine.

## 3. Extensibility is already half-built — don't reinvent it

The request to support "variant tools and frameworks, not only Playwright, not only Ollama" is mostly already true in the backend. The redesign's job is to *surface* this, not build a new plugin system:

| Axis | Already exists | Where |
|---|---|---|
| Model/inference substrate | 8 providers wired: OpenAI, Anthropic, Azure OpenAI, Bedrock, Ollama, LocalAI, NemoClaw, VLM | `cherenkov/substrate/providers/` |
| Truth sources (what gets tested against) | OpenAPI, gRPC, GraphQL, traffic capture, DB schema — behind one `SourceAdapter` interface | `cherenkov/truth/sources/interface.py` + 5 adapters |
| Execution engines | Playwright (web), Appium + Maestro (mobile, behind an abstract `MobileRunnerBase` with `run_test`/`health_check`), k6 (load/perf) | `cherenkov/execution/*_runner.py`, `mobile_runner_base.py` |
| IDE/agent integration | MCP server, 34 tools including 3 Sentinel integrity tools (`audit-test-file`, `check-assertion`, `suggest-spec-fix`) — already the "connects to Cursor/Windsurf/Claude Code" story TestSprite sells | `cherenkov/mcp/` |

None of this shows up in the UI today — the dashboard's own copy and nav imply "Playwright + Ollama" as the whole product, when the backend already spans far more than that. **Proposed change is UI-only**: a Settings surface that lists active providers/adapters/runners as what they are (read from existing config/flags), not a new abstraction. If a future runner needs adding (Cypress, WebdriverIO, Postman/Newman), it extends `MobileRunnerBase`'s proven ABC pattern to a sibling `ExecutionRunnerBase` — same shape, new implementation, no framework redesign.

## 4. Connectors — MCP first, not a new dispatcher

An earlier (fabricated) report proposed a bespoke outbound webhook dispatcher for Jira/Slack/PagerDuty. Nothing in `docs/ROADMAP_2026H2.md` calls for this, and building vendor-specific push integrations is exactly the kind of maintenance burden an OSS project should avoid — every new integration is another API to keep working against another company's changing surface.

Cherenkov already has the right shape of connector story: an MCP server (the same protocol TestSprite showcases for IDE integration), a GitHub Action + Smithery registry entry (Horizon-0), an inbound GitHub webhook receiver (`webhooks_github.py`), and a plain REST API (`/api/v1/divergences`, `/api/v1/runs`, `/api/v1/review/*`). That's enough surface for the community to wire Jira/Slack/PagerDuty themselves via n8n, Zapier, or a GitHub Action step — Cherenkov's job is to keep that surface well-documented and stable, not to own every downstream integration. **No new backend code proposed here.** If a specific integration becomes a real, named ask later, revisit — but don't build ahead of demand.

## 5. Test management, made explicit

There's no test-authoring GUI and none is proposed (Cherenkov generates from specs, it doesn't need a manual test builder). "Test management" here means: what exists, what ran, how healthy is it, and is it certified. All four already have real, working endpoints with no UI home:

- **Inventory** — generated suites under `stub/generated_tests/` and `eject` output
- **Run history & trend** — `runs_router.py` (`/api/v1/runs` list + detail), `cherenkov report --diff`
- **Coverage** — `cherenkov/divergence/coverage.py`, rendered today only as `IntegrityHeatmap.tsx` buried inside Overview
- **Integrity & certification** — `/api/v1/integrity/audit` (TIaaS), `cherenkov certify`, compliance mapping to OWASP LLM Top 10 / ISO 42001

Proposal: one **Test Management & Certification** hub that is a UI stitch of these four already-real endpoints — no new backend surface, just the dashboard the roadmap already implies it should have.

## 6. One genuinely new idea, built on what's already done

Rung 3 (certificates) is complete and its spec is already open and stable — and almost entirely invisible in the product. The certificate is Cherenkov's actual point of differentiation from Momentic and TestSprite (neither has a signed proof-of-honesty artifact), and right now it's a CLI output, not a surface. Proposal: a public **certificate verification page** — paste or link a certificate, see it validated against the open spec, badge-style (in the spirit of a Codecov badge, but for "this test suite isn't gaming its assertions" rather than line coverage). This uses only what M3/M4 already plan to ship (certificate adoption, external repos running `cherenkov certify` in CI) — it's a UI on top of a finished backend feature, which is the cheapest, highest-leverage move available here.

## 7. Proposed IA (five hubs, down from 24 items)

1. **Overview** — merges Overview + Truth Map + Signals + Verdict (currently four screens answering the same "is my target healthy" question)
2. **Author & Generate** — merges Spec Ingest + Pipeline + Author by Intent + Healing Options (the real generate/repair loop)
3. **Triage** *(promoted)* — merges Review Gate + Divergences + Spec vs Reality (also fixes the mock-data bug by folding it into the live divergence view)
4. **Test Management & Certification** *(new — see §5, currently zero nav presence)*
5. **Knowledge** — merges Memory & Pairing + Knowledge + Chat

`System` (Governance, Devices, Mobile, Eject, SDD, Setup Wizard) stays as a secondary, collapsed catch-all. Settings gains the extensibility inventory from §3.

## 8. Phased plan — what needs new backend work (mostly: nothing)

| Phase | What | New backend? |
|---|---|---|
| A | Wire `SpecVsRealityScreen.tsx` to real `/api/v1/divergences`, drop the mock array | None |
| B | Ship Test Management & Certification hub against `/api/v1/integrity/audit`, `/api/v1/runs`, coverage report | None |
| C | Simplify first-run path (Spec Ingest → Pipeline → first `verify`) — serves M1/E0.3's practitioner-quickstart gate | None |
| D | Promote Triage to first-class + coverage/health trend chart (aggregate client-side over existing `/api/v1/runs`) — serves M5 | None |
| E | Settings extensibility inventory (§3) + certificate verification page (§6) | None (reads existing config/certs) |

Every phase reuses an endpoint that already exists. If a later phase genuinely needs new backend surface, it should be scoped and justified at that point, not assumed up front.

## 9. Open questions (unchanged from prior review, still open)

- Start with Phase A (same-day mock-data fix) or Phase B (bigger differentiator, needs a screen pass first)?
- Cut the sidebar over in one PR, or merge hubs incrementally as each phase lands?
- Is a certificate verification page (§6) worth prioritizing into Phase E now, or does it wait until M4 (certificate adoption) actually has external adopters to point at?
