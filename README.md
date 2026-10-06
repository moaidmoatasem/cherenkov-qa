# ☢️ CHERENKOV-QA

**The integrity gate for AI-written tests.** Before you merge an AI agent's change to your tests, Cherenkov proves they still catch bugs.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version: 1.3.0](https://img.shields.io/badge/Version-1.3.0-green.svg)](https://github.com/moaidmoatasem/cherenkov-qa/releases/tag/v1.3.0)

AI coding agents (and "self-healing" test tools) make red tests green the easy way: loosening `==` to `in`, deleting the failing test, asserting fields the API never returns. Cherenkov catches those three cheats — **WEAKENED**, **DELETED**, **HALLUCINATED** — with static analysis only: **no LLM, no server, no Node, no account.** Every verdict says which checks actually ran.

*Zero vendor lock-in. 100% private. No telemetry, no cloud calls.*

## Three ways in

| You are | Use |
|---|---|
| a QA/SDET or developer | `cherenkov check --baseline origin/main` |
| reviewing pull requests | the GitHub Action: `uses: moaidmoatasem/cherenkov-qa@main` with `mode: check` posts one sticky comment |
| running a coding agent | `cherenkov agent init` writes the rule into `AGENTS.md`: *run `cherenkov check` before you call test changes done* |

## 🚀 First verdict in five minutes

```bash
pip install git+https://github.com/moaidmoatasem/cherenkov-qa   # PyPI publish is on the roadmap
cherenkov demo                                   # 60-second offline demo of the three cheats
cd your-repo
cherenkov check --baseline origin/main           # tests/ is auto-detected; exits 1 on any violation
cherenkov check --baseline origin/main --spec openapi.yaml   # also catches hallucinated fields
```

> **Read the verdict, not just the exit code.** WEAKENED and DELETED need a `--baseline` (a git ref or a path); HALLUCINATED needs `--spec`. A check that could not run is listed under `NOT_CHECKED`. A green run without a baseline means "no hallucinated fields", not "this suite is honest".

`cherenkov --help` shows the Core and Assist commands; `cherenkov labs` lists the experimental ones (desktop, mobile, federation, enterprise, ... — still callable, frozen for new features). Why this focus: [docs/reviews/PREMORTEM_2026-10.md](docs/reviews/PREMORTEM_2026-10.md); what's next: [docs/ROADMAP.md](docs/ROADMAP.md).

For **Python** suites the audit is genuine AST analysis (`ast.parse`; `== 200` → `in (200, 201)` is caught structurally). For **TypeScript** suites it is regex-based pattern matching, which is weaker — see [Detection depth by language](#detection-depth-by-language).

**Also in the box (Assist):** spec-derived test generation (`generate`, needs a local LLM), live-API conformance (`verify`, `validate`), `eject` to vanilla Playwright, and a review dashboard. See the [Platform Operating Model](docs/PLATFORM_OPERATING_MODEL.md) and [User Journeys](docs/USER_JOURNEYS.md).

---

## 💡 Why CHERENKOV?

### 1. The Integrity Moat (`check-suite`)
AI coding tools are notorious for weakening assertions (e.g., changing `==` to `in`) just to make tests pass. CHERENKOV-QA catches **Weakened**, **Deleted**, or **Hallucinated** assertions and binds your tests to your OpenAPI spec.

#### Detection depth by language

| Suite | Engine | Weakened | Deleted | Hallucinated |
|---|---|---|---|---|
| **Python** (`.py`) | `ast.parse` — compares comparison-operator node types | ✅ per-assertion, baseline-relative | ✅ per-test and per-assertion | ✅ scoped to the endpoint under test |
| **TypeScript** (`.spec.ts`) | regex over Playwright assertion grammar | ✅ per-assertion, baseline-relative | ✅ per-test and per-assertion | ✅ scoped to the endpoint under test |

Every cell above is executed by `tests/unit/test_capability_claims.py`, which runs the detector against a fixture per capability **and** parses this table out of this file. A capability that regresses fails CI; so does a table that overstates *or* understates what the code does. That gate exists because this table was previously wrong in the modest direction — it advertised "❌ not implemented" for TypeScript hallucination detection while the CLI was emitting exactly those findings. Understating is the friendlier error but the same defect: nothing was holding the claims to the code.

**What remains genuinely weaker on the TypeScript path:** the parse is regex over the Playwright assertion grammar rather than a syntax tree, so assertions built dynamically, or spanning unusual formatting, can be missed. The Python path parses real AST and does not have that failure mode. Both paths share the same endpoint-scoped spec resolution for hallucination detection.

**Known limits on both paths.** Hallucination scoping falls back to the whole document when a test's target endpoint cannot be resolved from its request calls — a fallback that is reported in the finding text (`not defined in the spec` rather than `not on the endpoint … calls`) so you can tell the two apart. Weakening detection compares operator strength, so a rewrite that keeps `==` while asserting a weaker *value* is not caught by `check-suite`; that is what the differential engine behind `cherenkov demo` and `cherenkov audit` is for.

### 2. Hallucination-Resistant Generation
When CHERENKOV does generate tests, it only uses the LLM to write the *structure*. The *expected values* (status codes, response schemas) are derived strictly from your OpenAPI spec. If the spec says `422`, CHERENKOV ensures the test demands a `422`.

### 3. Suggest-Only Healing
When tests fail, CHERENKOV suggests how to tighten your backend validations or fix the spec. But it **never auto-edits** your code. You stay in control.

### 4. Zero Vendor Lock-in (Eject Anytime)
We believe in open standards. You can eject the generated tests into standard, standalone Playwright code at any time:
```bash
cherenkov eject --output ./tests
```
Your tests will run perfectly with `playwright test`, completely detached from CHERENKOV.

### 5. 100% Private (Local LLM First)
By default, CHERENKOV uses `qwen2.5-coder:7b` running locally via Ollama. Your proprietary API specs never leave your laptop. (Cloud models like OpenAI are supported as opt-in).

For a one-command local AI stack (LocalAI + Redis + CHERENKOV), use the bundled compose file:

```bash
docker compose -f docker-compose.ai.yml up -d
```

This brings up LocalAI (VLM) on `http://localhost:8080` and Redis on `6379`. See [`docs/wiki/Deployment.md`](docs/wiki/Deployment.md) for the full setup guide.

---

## How it's different, honestly

> **Schemathesis** and property-based fuzzers generate inputs to find crashes; CHERENKOV generates *and audits* the tests themselves — it catches the case where the AI wrote a test that can never fail, not just the case where the API crashes.

> **LLM-eval frameworks** (DeepEval, Ragas, TruLens…) judge the LLM's *answers*; CHERENKOV audits the *tests* the LLM wrote — and proves the API honors its contract.

---

## 🛠️ Features
- **6-Gate Review Pipeline**: Tests are syntax-checked, AST-validated, type-checked, and mock-tested before ever hitting a real server.
- **OWASP safe-rejection probes** *(opt-in, off by default)*: set `CHERENKOV_DAST_ENABLED=1` and string fields in request bodies gain one representative payload per OWASP class — SQL injection (tautology, stacked), XSS (reflected, attribute), path traversal, template injection — each asserting the API answers **4xx**, not 5xx or 2xx, and does not echo the payload back verbatim. This is an input-validation hardening check on request-body strings; it is **not** a security scanner and does not cover authentication, authorization, session handling, or headers/paths/query parameters.
- **Visual Dashboard**: Explore conformance maps and test results across five workspaces in the built-in React UI (`cherenkov dashboard`).
- **Mobile Flow Integrity**: `cherenkov mobile` plans Maestro flows from a recorded `.hil` trace or an `.apk`, rejects flows whose assertions can never fail, and runs them on a device via Maestro or Appium. A flow that did not execute is reported `not_executed`, never green.
- **K8s Native Operator**: Deploy the `ConformanceCheck` CRD to run CHERENKOV natively in your Kubernetes CI/CD pipelines.

---

## 📚 Documentation
- [Getting Started Guide](https://moaidmoatasem.github.io/cherenkov-qa/latest/getting-started/)
- [CLI Reference](https://moaidmoatasem.github.io/cherenkov-qa/latest/cli/reference/)
- [Architecture & Design Decisions](https://moaidmoatasem.github.io/cherenkov-qa/latest/architecture/)
- [Platform Direction](https://moaidmoatasem.github.io/cherenkov-qa/latest/architecture/system-design/#platform-context-the-independent-quality-layer) — where CHERENKOV is heading as an open Quality Intelligence Platform, with API conformance as the shipped core
- [Capability Coverage Audit](./docs/CAPABILITY_COVERAGE.md) — code-verified matrix of what is shipped, what is partial, and what is absent, with the file paths behind each claim
- [Onboarding & Demo Recordings](./docs/recordings/) — 8 Loom scripts with live evidence for developers, QA, managers, and DevOps

---

## 🤝 Contributing
We love community contributions! Whether it's adding support for a new OpenAPI standard, improving the prompt chains, or building integrations with CI/CD platforms, please see our [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get started.

---
*Built with ❤️ for developers who hate writing manual API tests.*
