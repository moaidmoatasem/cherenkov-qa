---
title: FAQ
description: Frequently asked questions about CHERENKOV-QA — capabilities, limitations, and how it compares to alternatives.
---

# Frequently Asked Questions

---

## How is CHERENKOV different from Schemathesis?

They solve different problems.

**Schemathesis** is a property-based API fuzzer. It generates random inputs based on your schema and looks for crashes, 500 errors, and schema violations. It answers: "Can I break this API with unexpected inputs?"

**CHERENKOV** is an open Quality Intelligence Platform whose shipped core is API conformance testing and test-suite integrity auditing. It generates structured Playwright tests from your spec, runs them against your API, and reports where the implementation diverges from the contract. It also audits your *existing* test suite for weakened or hallucinated assertions.

CHERENKOV answers: "Does this API do what the spec says it does?" and "Do our tests actually test what the spec requires?"

They are complementary. Use Schemathesis to find edge cases. Use CHERENKOV to verify conformance and audit test quality.

---

## Does it work without an LLM?

Yes. Several core commands need no LLM at all:

| Command | LLM needed? |
|---------|-------------|
| `check-suite` | No |
| `verify` | No |
| `certify` | No |
| `daemon` | No |
| `guardian` | No |
| `hitl` | No |
| `doctor` | No |
| `report` | No |
| `eject` | No |
| `generate` | Yes (or use `--no-repair` for template fallback) |
| `validate` | Yes (calls `generate` internally) |

For test generation without an LLM, use the template fallback:

```bash
cherenkov generate --spec openapi.yaml --no-repair
```

This produces working Playwright tests from templates rather than LLM generation. The tests are less sophisticated but require zero LLM infrastructure.

---

## What OpenAPI versions are supported?

- **OpenAPI 3.0.x** — fully supported
- **OpenAPI 3.1.x** — fully supported
- **OpenAPI 3.2.x** — fully supported

OpenAPI 2.0 (Swagger) files should be converted to 3.x first. Tools like `swagger2openapi` handle this conversion.

---

## Can I use cloud LLMs instead of local?

Yes. By default, CHERENKOV uses Ollama for local inference. To use a cloud provider:

**OpenAI:**

```bash
export PROVIDER=openai
export OPENAI_API_KEY=sk-...
cherenkov generate --spec openapi.yaml
```

**GitHub Models:**

```bash
export PROVIDER=github_models
export GITHUB_TOKEN=ghp_...
cherenkov generate --spec openapi.yaml
```

Other supported providers: LocalAI, AirLLM, NemoClaw. See the substrate provider documentation for configuration details.

The privacy trade-off is yours to make. Local inference means no API spec data leaves your network. Cloud providers may offer better model quality for complex specs.

---

## Does it support GraphQL and gRPC?

Yes. Use the `--source` flag:

**GraphQL:**

```bash
cherenkov validate --spec schema.graphql --source graphql --target http://localhost:4000/graphql
```

**gRPC:**

```bash
cherenkov validate --spec service.proto --source grpc --target localhost:50051
```

CHERENKOV also supports:

- **AsyncAPI** — for event-driven APIs
- **Accessibility** — for web accessibility testing
- **Mobile** — for mobile API testing

The default source type is `openapi`.

---

## What about TypeScript test detection?

Honest limitation: TypeScript test detection uses regex-based parsing, which is less accurate than Python's AST-based detection.

**What works well:**

- Standard Jest/Vitest/Playwright test patterns
- Simple assertion chains
- Common test structure (`describe`/`it`/`test` blocks)

**What may be missed:**

- Complex dynamic test generation
- Tests using heavily abstracted helper patterns
- Tests with unusual assertion libraries

Python test detection uses full AST parsing and is more reliable. If you use TypeScript, review `check-suite` findings for false negatives — it may miss some tests rather than hallucinate them.

---

## Can I self-host everything?

Yes. CHERENKOV is designed for self-hosting:

- **No cloud calls by default.** The LLM runs locally via Ollama. Validation runs locally. The dashboard is a local web server.
- **No telemetry.** CHERENKOV does not phone home.
- **No license server.** Apache 2.0 — no activation, no seat counting.
- **Docker and Kubernetes support.** Deploy however you deploy everything else.

The only scenario where data leaves your network is if you explicitly configure a cloud LLM provider (OpenAI, GitHub Models).

---

## What is the performance impact?

**`verify` (probe-only):** Runs 40 probes by default. On a spec with 81 paths, this completes in approximately 9 seconds. Adjust with `--max-probes`.

**`validate` (full generation + execution):** Depends on spec size and LLM speed. On a GPU with Ollama, generating and running tests for a 20-endpoint spec takes 1-3 minutes. On CPU, generation is slower (5-10 minutes) but execution time is the same.

**`check-suite` (static analysis):** Parses test files and the spec. No API calls, no LLM. Typically completes in under 5 seconds regardless of suite size.

**CI impact:** Add 1-3 minutes to your pipeline for `validate`, or under 10 seconds for `verify` or `check-suite`.

---

## Is there an enterprise tier?

No. Everything is free under Apache 2.0:

- SSO/SAML authentication
- RBAC (role-based access control)
- Kubernetes operator and ConformanceCheck CRD
- Continuous monitoring (daemon, guardian)
- Conformance certificates
- OpenTelemetry integration
- Dashboard with all 5 workspaces
- Unlimited APIs, unlimited users, unlimited runs

There is no paid tier, no "contact sales," no feature gating. The entire feature set ships in the open-source release.

---

## Can CHERENKOV auto-fix my code?

No — by design. CHERENKOV follows a **suggest-only** healing model. It will:

- Detect where your implementation diverges from the spec
- Report exactly what the expected vs actual behavior is
- Queue findings for human review (HITL)

It will **never** automatically edit your source code, modify your tests, or change your spec. Every fix is a human decision.

---

## What happens if I stop using CHERENKOV?

Nothing breaks. CHERENKOV is designed for zero lock-in:

- **Eject your tests** with `cherenkov eject --output ./tests` to get standalone Playwright tests with no CHERENKOV dependencies.
- **Generated tests** are standard Playwright files you already own.
- **Conformance certificates** are self-contained documents.
- **No data is stored in the cloud.** Everything is on your infrastructure.

---

## What specs produce the best results?

CHERENKOV works best with OpenAPI specs that include:

- **Response schemas** with concrete types and examples
- **Multiple response codes** (200, 400, 404, etc.)
- **Request body schemas** with examples
- **Path and query parameter definitions**

Minimal specs (just paths and descriptions, no schemas) will still work but generate less thorough tests. Use `cherenkov doctor` to check spec richness.

---

## Next Steps

- [Common Issues](common-issues.md) — solutions to specific problems
- [Getting Started](../getting-started/index.md) — installation and first run
- [CLI Reference](../cli/reference.md) — full command documentation
