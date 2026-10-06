# Market scan — October 2026

**Method and confidence.** Vendor sites (tester.army, webdriver.io, testmuai.com, news.ycombinator.com) and the GitHub API were not reachable from the research environment. Claims below come from npm/PyPI registry data and search-result snippets, each with a source. Treat vendor positioning as second-hand; treat registry versions and dates as first-hand. Where sources disagree, it is said.

## Bottom line

Test **generation** is being commoditised by platform vendors, and **healer** agents that silently rewrite tests until they pass are now shipping everywhere. That is the problem Cherenkov's integrity gate exists for. The opportunity is the verifier; generation is not where to compete.

## Vendors (newest first)

| Vendor | Latest update | Positioning | Overlap with Cherenkov | Source |
|---|---|---|---|---|
| WebdriverIO | v10.0.0 on npm, 2026-10-05: `@wdio/session` (an agent drives a browser/phone/desktop app, then exports the steps as a test), `@wdio/ai-service` (`browser.act()`/`extract()`, cached and healed when the page changes); `@wdio/mcp` 3.14.0. Needs Node 22.19 and Appium 3. Pitched as "verification loops for coding agents". | Open source | Low on engine; the "verification" wording collides with ours | [blog](https://webdriver.io/blog/2026/10/05/webdriverio-v10-release), [MCP post](https://webdriver.io/blog/2026/02/04/introducing-webdriverio-mcp/) |
| Keploy | v3.6.93, 2026-10-06 | Open source + paid; eBPF traffic recording + AI tests from OpenAPI/Postman/cURL | **High** on API test generation | [release](https://github.com/keploy/keploy/releases/tag/v3.6.93) |
| Schemathesis | 4.29.3 on PyPI, 2026-10-05; stateful + GraphQL since 4.18; no AI features found | Open source property-based fuzzing | Complementary | pypi.org/pypi/schemathesis |
| Checksum | runtime 5.5.0 on npm 2026-10-02; Sept 2026 session recovery; `/checksum` commands for Claude Code and Cursor | Paid; generates and heals Playwright tests | Medium; produces healed tests our gate should check | [Yahoo](https://finance.yahoo.com/technology/ai/articles/checksum-enables-engineering-teams-recover-130000234.html) |
| QA Wolf | Mapping AI 2026-09-01, Automation AI 2026-09-08, MCP server 2026-09-29 | Paid managed service; outputs plain Playwright | Medium | [changelog](https://www.qawolf.com/changelog) |
| Playwright | 1.63.0, 2026-09-04; test agents (planner, generator, **healer**) since 1.56; `@playwright/mcp` 0.0.83 and `@playwright/cli` 0.1.22 (2026-09-28); recommends CLI over MCP for coding agents | Open source (Microsoft) | The healer can weaken tests to pass — exactly what `check-suite` detects | [release notes](https://playwright.dev/docs/release-notes) |
| Momentic | "Mo" agent, 2026-09-28 ("there's no tests in the future") | Paid | Medium; the story that agents verify directly cuts against test artifacts | [SiliconANGLE](https://siliconangle.com/2026/09/28/momentic-debuts-mo-ai-agent-to-automate-software-testing-without-scripts/) |
| TesterArmy | CLI 0.10.0, 2026-09-22 dropped `@playwright/mcp`/`ai`/`playwright` deps (1.29 MB → 178 KB; inferred cloud-only). ~$1.2M pre-seed (Sept); free 5 runs, $99/250, $299/1000. Sources disagree on YC batch and founding year. | Paid hosted browser + mobile QA agent | Low on engine, medium on go-to-market | npm registry, [Vestbee](https://www.vestbee.com/insights/articles/tester-army-raises-1-2-m) |
| Stagehand | v4 2026-08-10; npm 4.1.0 2026-09-09 | Open-source browser-agent SDK | Low | [changelog](https://www.browserbase.com/changelog/stagehand-v4) |
| BrowserStack | Test Companion (IDE, includes API tests) 2026-07-29 | Paid | Medium on API generation | [PR](https://www.prnewswire.com/news-releases/browserstack-launches-test-companion-agentic-ai-that-brings-complete-test-automation-into-the-ide-302837727.html) |
| mabl | Agentic "Active Coverage" 2026-04-23; its survey says teams spend ~20% of a week manually checking AI-generated tests | Paid | Medium; the survey supports the problem statement | [PR Newswire](https://www.prnewswire.com/news-releases/mabl-unveils-next-generation-agentic-testing-platform-for-the-ai-development-era-302751783.html) |
| Diffblue | Testing Agent GA 2026-03-24 (Java; checks tests compile and pass) | Paid | Medium on "verified tests" wording | [BusinessWire](https://www.businesswire.com/news/home/20260324227278/en/New-Diffblue-Testing-Agent-Automatically-Generates-Comprehensive-Regression-Test-Suites-To-Derisk-Application-Modernization) |
| Applitools | Eyes MCP server tools (2026-04) | Paid visual AI | Low | [blog](https://applitools.com/blog/agentic-sdlc-reliability/) |
| Octomind | **Shut down** end of May 2026 | — | Signal: AI-E2E startups struggle to find a market | [TestGuild](https://testguild.com/tools/octomind) |
| Qodo Cover-Agent, Shortest | Unmaintained / dormant (last activity 2025) | Open source | Low | qaskills.sh, npm registry |

Mutation-gating AI-written tests is now a public pattern ([awesome-testing, Aug 2026](https://www.awesome-testing.com/2026/08/mutation-testing-for-agent-written-code), [zylos, 2026-08-15](https://zylos.ai/research/2026-08-15-mutation-testing-verification-gate-ai-generated-tests/)). The "only player" claim in earlier reports no longer holds.

## WebdriverIO v10

No WebdriverIO code exists in this repo. Cherenkov emits Playwright TypeScript, pytest/jest, k6, Maestro/Appium; integrity analysis supports only Playwright and pytest, with reduced `.ts` analysis. v10's `ai-service` self-healing and `@wdio/session` export are new sources of silently weakened tests. **Recommendation:** parse WDIO/Mocha specs in `check-suite` (reach without a new runner); do not build a WDIO runner.

## TesterArmy

Hosted browser/mobile QA agent; the earlier teardown ([TESTERARMY_TEARDOWN_2026-08](TESTERARMY_TEARDOWN_2026-08.md)) found it has no integrity check at all. 0.10.0 moved further cloud-only. It remains a different product; the echo-only `testerarmy` command group in this repo was removed.

## Paperclip — a loop reference, not a dependency

[Paperclip](https://github.com/paperclipai/paperclip) (MIT, ~98k stars) is a Node 24 + Postgres control plane for teams of agents with adapters for Claude Code, Codex, Cursor, Gemini CLI and others. Its loop: agents wake on a heartbeat (assigned work, follow-up, or schedule) via a coalesced DB-backed wake queue; atomic task checkout with execution locks; scoped budgets with warning thresholds and hard stops; approval/review stages; durable audit trail.

**Not adopted:** it needs an always-on server and database, heartbeat wakes spend tokens on a schedule, and the repo's own earlier swarm (`.agents/`) was abandoned mid-run — a second orchestration layer would rot the same way.

**Patterns borrowed, at near-zero cost** (see CLAUDE.md "Session loop" and `scripts/oversight_check.py`): wake only on change (the oversight issue is edited only when its content hash changes); atomic checkout (assign + `in-progress` label + no existing PR/branch); a hard stop after one item per session; draft PR plus dated HANDOVER entry as the approval gate and audit trail.

**Product angle:** Paperclip's review stage, WebdriverIO's "verification loops" and Playwright's healer all need a verifier a test-writing agent cannot game. Recipe: run `cherenkov check-suite --candidate ./tests --baseline <base-tests-dir>` as the last step of an agent loop and block on a non-zero exit (a git-ref `--baseline` arrives with the Phase 1 `check` command).

## Implications

1. Lead with verification, not generation. Keploy/BrowserStack/Playwright agents commoditise generation.
2. Target healer output: bring `.ts` integrity analysis to parity with `.py`; add WDIO/Mocha parsing.
3. CLI + skills first; keep the MCP tool count small (Playwright now steers agents to its CLI).
4. Soften the "only player" claim; back the differentiator with a public held-out benchmark.
5. Octomind's shutdown is a reminder paid AI-testing is hard; stay open source (2026-08-01 decision).
