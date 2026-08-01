# ☢️ CHERENKOV-QA

**The AI-Native API Conformance Testing Platform**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version: 1.2.0](https://img.shields.io/badge/Version-1.2.0-green.svg)](https://github.com/moaidmoatasem/cherenkov-qa/releases/tag/v1.2.0)

Every API has an OpenAPI spec, but those specs silently drift from the real server implementations every day. Moreover, AI-generated tests often hallucinate expected outcomes or silently weaken assertions to force a "green" build.

**CHERENKOV-QA** is an **API Integrity Auditor**. Point it at any test suite and it will tell you, with no LLM involved, whether your tests actually enforce your OpenAPI contract — detecting Weakened, Deleted, and Hallucinated assertions. It also verifies your live API conforms to the spec, and generates conformant Playwright tests locally.

For **Python** suites the audit is genuine AST analysis: `check-suite` parses with `ast.parse` and decides WEAKENED by comparing comparison-operator node types, so `== 200` → `in (200, 201)` is caught structurally rather than textually. For **TypeScript** suites it uses a per-subject regex engine (proven against the labelled corpus: **4/4 cheat classes caught**, including hallucination).

*Zero vendor lock-in. 100% private. No telemetry, no cloud calls.*

---

## 🚀 See it in 60 seconds (no setup required)

```bash
git clone https://github.com/moaidmoatasem/cherenkov-qa && cd cherenkov-qa
pip install .
cherenkov demo
```

Watch it catch the AI attempting to cheat by loosening assertions or deleting tests. No LLM, no API key, no internet — the demo starts two throwaway HTTP servers on `127.0.0.1:18800/18801` (one spec-conforming, one deliberately broken) and runs the suite against both, so a test that passes the broken one is provably vacuous.

**Then audit a real test suite and verify your own API:**

```bash
# Audit: is your existing test suite actually enforcing the spec?
cherenkov audit --spec ./openapi.yaml --target http://localhost:8080 --test-cmd "npx playwright test"

# Check-suite: find weakened / deleted / hallucinated assertions against a baseline
cherenkov check-suite --candidate ./tests --spec ./openapi.yaml --fail-on-finding

# Verify: probe the live API directly against the spec
cherenkov verify --url http://localhost:8080 --spec ./openapi.yaml

# Verify with known real identifiers (to probe templated endpoints like /users/{id})
cherenkov verify --url http://localhost:8080 --spec ./openapi.yaml \
  --identifiers identifiers.json --allow-mutations
```

---

## 💡 Why CHERENKOV?

### 1. Baseline-Free Audit (`cherenkov audit`) — **the wedge**
Point it at any test suite you already have — no baseline, no adoption cost. CHERENKOV records a green run against your live target, then replays the suite against deliberately-broken responses (one mutant per axis: wrong status, wrong value type, enum violation, missing required field). A test that still passes against a broken response is **provably vacuous**. All three AI cheat classes (Weakened, Deleted, Hallucinated) are caught.

### 2. The Integrity Moat (`check-suite`)
AI coding tools are notorious for weakening assertions (e.g., changing `==` to `in`) just to make tests pass. CHERENKOV catches **Weakened**, **Deleted**, or **Hallucinated** assertions and binds your tests to your OpenAPI spec.

#### Detection depth by language

| Suite | Engine | Weakened | Deleted | Hallucinated |
|---|---|---|---|---|
| **Python** (`.py`) | `ast.parse` — compares comparison-operator node types | ✅ per-assertion, baseline-relative | ✅ per-test | ✅ cross-referenced against the spec |
| **TypeScript** (`.spec.ts`) | Per-subject regex engine (validated: 4/4 cheat classes) | ✅ per-test | ✅ per-test | ✅ implemented |

### 3. Spec-Shape Robustness
Proven against **10 real-world production API specs** (Stripe, GitHub, Twilio, Kubernetes, OpenAI, Slack, Box, SendGrid, DigitalOcean, Petstore) — **3,428 endpoints analyzed, 0 silent drops**. Every endpoint that can't be probed is explicitly reported with a machine-readable reason. See the full corpus report: [`docs/marketing/E0.5d_conformance_corpus.md`](docs/marketing/E0.5d_conformance_corpus.md).

### 4. Hallucination-Resistant Generation
When CHERENKOV generates tests, it only uses the LLM to write the *structure*. The *expected values* (status codes, response schemas) are derived strictly from your OpenAPI spec. If the spec says `422`, CHERENKOV ensures the test demands a `422`.

### 5. Suggest-Only Healing
When tests fail, CHERENKOV suggests how to tighten your backend validations or fix the spec. But it **never auto-edits** your code. You stay in control.

### 6. Zero Vendor Lock-in (Eject Anytime)
```bash
cherenkov eject --output ./tests
```
Your tests run perfectly with `playwright test`, completely detached from CHERENKOV.

### 7. 100% Private (Local LLM First)
By default, CHERENKOV uses `qwen2.5-coder:7b` running locally via Ollama. Your proprietary API specs never leave your laptop.

---

## How it's different, honestly

> **Schemathesis** and property-based fuzzers generate inputs to find crashes; CHERENKOV generates *and audits* the tests themselves — it catches the case where the AI wrote a test that can never fail, not just the case where the API crashes.

> **LLM-eval frameworks** (DeepEval, Ragas, TruLens…) judge the LLM's *answers*; CHERENKOV audits the *tests* the LLM wrote — and proves the API honors its contract.

---

## 🛠️ Key Commands

| Command | What it does |
|---|---|
| `cherenkov demo` | Self-contained demo, no setup. Catches all 3 AI cheat classes in ~10s. |
| `cherenkov audit` | Baseline-free oracle: record → perturb → replay. Works on any existing test suite. |
| `cherenkov verify` | Probe the live API against the spec. Reports every unprobed endpoint with an explicit reason. |
| `cherenkov check-suite` | AST / regex analysis to detect Weakened, Deleted, Hallucinated assertions. |
| `cherenkov generate` | Generate conformant Playwright tests from an OpenAPI spec via local LLM. |
| `cherenkov eject` | Strip all CHERENKOV imports — tests run standalone with `playwright test`. |
| `cherenkov dashboard` | Launch the React UI for conformance maps, triage, and healing suggestions. |

---

## 📚 Documentation
- [Getting Started Guide](https://moaidmoatasem.github.io/cherenkov-qa/getting-started/)
- [CLI Reference](https://moaidmoatasem.github.io/cherenkov-qa/cli/reference/)
- [Architecture & Design Decisions](https://moaidmoatasem.github.io/cherenkov-qa/architecture/)
- [Corpus Benchmark Report](docs/marketing/E0.5d_conformance_corpus.md) — 10 real-world APIs, 3,428 endpoints, 0 silent drops
- [Roadmap](docs/ROADMAP_2026H2.md)

---

## 🤝 Contributing
We love community contributions! Whether it's adding support for a new OpenAPI standard, improving the prompt chains, or building integrations with CI/CD platforms, please see our [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get started.

---
*Built with ❤️ for developers who hate writing manual API tests.*
