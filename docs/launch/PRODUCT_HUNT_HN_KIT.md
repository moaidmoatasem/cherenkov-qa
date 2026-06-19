# Launch Kit: Product Hunt & Hacker News

This kit provides the exact copy, taglines, and "Maker Comments" needed for a successful launch on developer-focused platforms.

---

## 1. Taglines & Short Descriptions

### Product Hunt
- **Product Name:** CHERENKOV
- **Tagline:** The AI Reality Engine for API Conformance Testing
- **Description (Short):** CHERENKOV reads your OpenAPI spec, uses a local LLM to generate native Playwright tests, runs them, and proves drift. No cloud, zero lock-in, fully autonomous.

### Hacker News
- **Title:** Show HN: CHERENKOV – AI-native API testing with zero vendor lock-in

---

## 2. Product Hunt Maker Comment

**To be posted immediately after launching on PH:**

> Hey Product Hunt! 👋 I'm Moaid, the creator of CHERENKOV.
>
> We all know the pain of API specifications drifting from reality. You write an OpenAPI spec, hand it to the frontend team, and a week later the backend changes a field from an integer to a string, breaking production.
>
> Writing test coverage to prevent this is tedious, so nobody does it.
>
> **CHERENKOV** fixes this by generating the tests for you. But we built it with two strict rules:
> 
> 1. **Zero Data Egress:** CHERENKOV uses local LLMs (like `qwen2.5-coder:7b`) to generate tests. Your proprietary API specs never leave your laptop. No API keys, no cloud dependencies.
> 2. **Zero Lock-In:** Most testing platforms trap your test suites inside their walled garden. With CHERENKOV, a single command (`cherenkov eject`) strips our framework entirely, leaving you with vanilla, human-readable Playwright tests that run natively in your CI forever.
>
> Today, with our v1.1.0 release, CHERENKOV officially supports REST, GraphQL, gRPC (via Buf), and AsyncAPI/WebSockets. It even exports Jira tickets automatically on pipeline failure.
>
> We're building the **Reality Engine**—the platform that maintains continuous truth across every source.
>
> I'd love to hear your feedback on the DX and our zero lock-in approach! 🚀

---

## 3. Hacker News "Show HN" First Comment

**To be posted on Hacker News to spark technical discussion:**

> Hi HN,
>
> I'm sharing CHERENKOV, an open-source, local-first API conformance engine.
>
> The thesis behind CHERENKOV is simple: LLMs are great at writing boilerplate API tests, but passing your proprietary enterprise specs to a cloud endpoint is often a security non-starter. Furthermore, buying into an "AI testing platform" usually means your test suite is locked into their proprietary runner.
>
> CHERENKOV runs locally (defaults to `qwen2.5-coder` or `llama3`) to parse OpenAPI, GraphQL, gRPC, and AsyncAPI specs. It generates strongly-typed Playwright tests, executes them against your live server, and returns a drift report.
>
> We intentionally built an `eject` command. If you decide CHERENKOV isn't for you, `cherenkov eject` compiles the generated tests into standard Playwright + `openapi-fetch` TypeScript files. You own the code, and you can uninstall CHERENKOV without losing your test coverage.
>
> I built this to bridge the gap between "specs as documentation" and "specs as executable contracts."
>
> Repo: https://github.com/moaidmoatasem/cherenkov-qa
>
> Happy to answer any questions about the AST validation pipeline, the LLM prompt engineering, or our approach to CI/CD integrations!
