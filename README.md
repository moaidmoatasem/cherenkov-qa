# ☢️ CHERENKOV-QA

**The AI-Native API Conformance Testing Platform**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version: 1.1.1](https://img.shields.io/badge/Version-1.1.1-green.svg)](https://github.com/moaidmoatasem/cherenkov-qa/releases/tag/v1.1.1)
[![PyPI](https://img.shields.io/pypi/v/cherenkov-qa.svg)](https://pypi.org/project/cherenkov-qa/)

Every API has an OpenAPI spec, but those specs silently drift from the real server implementations every day. Writing tests to catch this manually is tedious and slow. 

**CHERENKOV-QA** solves this. It ingests your OpenAPI spec, uses a local LLM to generate a fully typed Playwright test suite, executes it against your real server, and delivers a conformance report. 

*Zero vendor lock-in. 100% private. Spec-derived truth.*

---

## 🚀 See it in 60 seconds (no setup required)

```bash
pip install cherenkov-qa
cherenkov demo
```

No Ollama. No API key. No running server. It shows you exactly what CHERENKOV catches that every other tool misses.

**Then point it at your own API:**

```bash
cherenkov verify --url http://localhost:8080 --spec ./openapi.yaml
```

---

## 💡 Why CHERENKOV?

### 1. Stop Spec Drift Automatically
Your OpenAPI spec is the contract. CHERENKOV generates the tests to ensure your backend actually honors it. If the spec says `422` and the server returns `400`, CHERENKOV catches it before you commit.

### 2. Hallucination-Resistant by Design
Other AI tools hallucinate assertions. CHERENKOV only uses the LLM to write the *structure* of the test. The *expected values* (status codes, response schemas) are derived strictly from your OpenAPI spec.

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
