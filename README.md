# ☢️ CHERENKOV-QA

**The AI-Native API Conformance Testing Platform**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version: 1.3.0](https://img.shields.io/badge/Version-1.3.0-green.svg)](https://github.com/moaidmoatasem/cherenkov-qa/releases/tag/v1.3.0)

Every API has an OpenAPI spec, but those specs silently drift from the real server implementations every day. Moreover, AI-generated tests often hallucinate expected outcomes or silently weaken assertions to force a "green" build.

**CHERENKOV-QA** is an **API Integrity Auditor**. It checks whether your test suite actually enforces your OpenAPI contract, detecting Weakened, Deleted, and Hallucinated assertions with no LLM involved — then provides a spec-derived local LLM engine to generate conformant Playwright tests.

For **Python** suites the audit is genuine AST analysis: `check-suite` parses with `ast.parse` and decides WEAKENED by comparing comparison-operator node types, so `== 200` → `in (200, 201)` is caught structurally rather than textually. For **TypeScript** suites it is regex-based pattern matching, which is weaker — see [Detection depth by language](#detection-depth-by-language).

*Zero vendor lock-in. 100% private. No telemetry, no cloud calls.*

---

## 🚀 See it in 60 seconds (no setup required)

```bash
git clone https://github.com/moaidmoatasem/cherenkov-qa && cd cherenkov-qa
pip install .
cherenkov demo
```

Watch it catch the AI attempting to cheat by loosening assertions or deleting tests. No LLM, no API key, no internet — the demo starts two throwaway HTTP servers on `127.0.0.1:18800/18801` (one spec-conforming, one deliberately broken) and runs the suite against both, so a test that passes the broken one is provably vacuous. (PyPI publish is on the roadmap — until then, install from source as above, or use the one-liner: `curl -fsSL https://raw.githubusercontent.com/moaidmoatasem/cherenkov-qa/main/install.sh | bash`.)

**Then audit a real test suite, and verify your own API:**

```bash
cherenkov check-suite --candidate ./tests --spec ./openapi.yaml --fail-on-finding
cherenkov verify --url http://localhost:8080 --spec ./openapi.yaml
```

---

## 💡 Why CHERENKOV?

### 1. The Integrity Moat (`check-suite`)
AI coding tools are notorious for weakening assertions (e.g., changing `==` to `in`) just to make tests pass. CHERENKOV-QA catches **Weakened**, **Deleted**, or **Hallucinated** assertions and binds your tests to your OpenAPI spec.

#### Detection depth by language

| Suite | Engine | Weakened | Deleted | Hallucinated |
|---|---|---|---|---|
| **Python** (`.py`) | `ast.parse` — compares comparison-operator node types | ✅ per-assertion, baseline-relative | ✅ per-test | ✅ cross-referenced against the spec |
| **TypeScript** (`.spec.ts`) | regex over Playwright assertion grammar | ⚠️ file-level heuristic only | ⚠️ per-test-name only | ❌ **not implemented** |

The TypeScript path is materially weaker than the Python path, and hallucination detection there is not implemented at all. This is stated plainly because CHERENKOV exists to catch tools that overstate what they verify; it would be self-defeating to do the same. Closing the gap is tracked as M0b in [`docs/ROADMAP_2026H2.md`](docs/ROADMAP_2026H2.md).

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
- **OWASP Mutation Engine**: Automatically injects DAST (Dynamic Application Security Testing) payloads to test edge-cases.
- **Visual Dashboard**: Explore conformance maps and test results across five workspaces in the built-in React UI (`cherenkov dashboard`).
- **K8s Native Operator**: Deploy the `ConformanceCheck` CRD to run CHERENKOV natively in your Kubernetes CI/CD pipelines.

---

## 📚 Documentation
- [Getting Started Guide](https://moaidmoatasem.github.io/cherenkov-qa/latest/getting-started/)
- [CLI Reference](https://moaidmoatasem.github.io/cherenkov-qa/latest/cli/reference/)
- [Architecture & Design Decisions](https://moaidmoatasem.github.io/cherenkov-qa/latest/architecture/)
- [Platform Direction](https://moaidmoatasem.github.io/cherenkov-qa/latest/architecture/system-design/#platform-context-the-independent-quality-layer) — where CHERENKOV is heading as an open Quality Intelligence Platform, with API conformance as the shipped core
- [Onboarding & Demo Recordings](./docs/recordings/) — 8 Loom scripts with live evidence for developers, QA, managers, and DevOps

---

## 🤝 Contributing
We love community contributions! Whether it's adding support for a new OpenAPI standard, improving the prompt chains, or building integrations with CI/CD platforms, please see our [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get started.

---
*Built with ❤️ for developers who hate writing manual API tests.*
