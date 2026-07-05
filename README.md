# ☢️ CHERENKOV-QA

**The AI-Native API Conformance Testing Platform**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version: 1.1.1](https://img.shields.io/badge/Version-1.1.1-green.svg)](https://github.com/moaidmoatasem/cherenkov-qa/releases/tag/v1.1.1)
[![PyPI](https://img.shields.io/pypi/v/cherenkov-qa.svg)](https://pypi.org/project/cherenkov-qa/)

Every API has an OpenAPI spec, but those specs silently drift from the real server implementations every day. Moreover, AI-generated tests often hallucinate expected outcomes or silently weaken assertions to force a "green" build.

**CHERENKOV-QA** is an **API Integrity Auditor**. It mathematically proves that your test suites actually enforce your OpenAPI contract using pure AST (Abstract Syntax Tree) analysis. It detects Weakened, Deleted, and Hallucinated assertions without relying on an LLM, and then provides a spec-derived local LLM engine to generate conformant Playwright tests.

*Zero vendor lock-in. 100% private. Pure Python AST Integrity Moat.*

---

## 🚀 See it in 60 seconds (no setup required)

```bash
pip install cherenkov-qa
cherenkov check-suite --demo
```

Watch it catch the AI attempting to cheat by loosening assertions or deleting tests. Zero network calls, zero LLM, pure static AST analysis.

**Then run the generative pipeline against your own API:**

```bash
cherenkov verify --url http://localhost:8080 --spec ./openapi.yaml
```

---

## 💡 Why CHERENKOV?

### 1. The Integrity Moat (`check-suite`)
AI coding tools are notorious for weakening assertions (e.g., changing `==` to `in`) just to make tests pass. CHERENKOV-QA uses pure Python AST analysis to catch **Weakened**, **Deleted**, or **Hallucinated** assertions in your test suites. It mathematically binds your tests to your OpenAPI spec.

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

---

## 🛠️ Features
- **6-Gate Review Pipeline**: Tests are syntax-checked, AST-validated, type-checked, and mock-tested before ever hitting a real server.
- **OWASP Mutation Engine**: Automatically injects DAST (Dynamic Application Security Testing) payloads to test edge-cases.
- **Visual Dashboard**: Explore conformance maps and test results via the built-in React UI (`npx cherenkov dashboard`).
- **K8s Native Operator**: Deploy the `ConformanceCheck` CRD to run CHERENKOV natively in your Kubernetes CI/CD pipelines.

---

## 📚 Documentation
- [Getting Started Guide](https://moaidmoatasem.github.io/cherenkov-qa/getting-started/)
- [CLI Reference](https://moaidmoatasem.github.io/cherenkov-qa/cli/reference/)
- [Architecture & Design Decisions](https://moaidmoatasem.github.io/cherenkov-qa/architecture/)

---

## 🤝 Contributing
We love community contributions! Whether it's adding support for a new OpenAPI standard, improving the prompt chains, or building integrations with CI/CD platforms, please see our [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get started.

---
*Built with ❤️ for developers who hate writing manual API tests.*
