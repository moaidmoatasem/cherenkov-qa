# FAQ & Objections Handling — CHERENKOV QA

> **Audience:** Engineering leads, QA practitioners, architects, and executive stakeholders.
> **Purpose:** Honest, thorough answers to the most common questions and objections.
> **Last updated:** 2026-08-02

---

## 🔧 Technical Questions

---

### 1. Does CHERENKOV support Swagger 2.0 / OAS 2.0 specs, or only OAS 3.x?

**Short answer:** OAS 3.0+ is the primary supported format. OAS 2.0 (Swagger) support is available via automatic conversion.

CHERENKOV's parser targets OpenAPI Specification 3.0 and 3.1 natively. If your team is still on Swagger 2.0, note that CHERENKOV recognises the legacy `swagger` (v2.0) field at ingest but has no built-in conversion step — migrate your spec to OAS 3.x first (e.g. with the `swagger2openapi` CLI). This conversion is lossy for certain Swagger-specific extensions, so it is strongly recommended to review the converted spec. For most real-world Swagger 2.0 specs (standard REST endpoints with JSON bodies), the conversion works without manual intervention. Edge cases — particularly specs using custom `x-` extensions or Swagger-only `formData` parameters — may require minor spec cleanup. Run `cherenkov validate --target <base-url> --spec swagger.json` for a pre-flight check: the spec is validated before ingestion (reachability, YAML/JSON parse, required fields, `$ref` resolution) and errors abort the run with a non-zero exit.

---

### 2. What LLM models are supported? Can I use GPT-4 or Claude instead of the local Qwen model?

**Short answer:** Yes. CHERENKOV supports multiple LLM backends via a tier-routing system.

By default, CHERENKOV uses a locally-hosted model (Qwen via Ollama) to ensure zero data egress and air-gap compatibility. The `cherenkov.toml` config exposes `[substrate.tiers]` sections (`small`, `deep`, `vision`) where you can configure each backend: `provider = "openai"` with your API key, `provider = "anthropic"` for Claude, or `provider = "ollama"` for the default self-hosted path. Tier routing (Phase 2) automatically selects the cheapest capable model for each task — lightweight paraphrasing goes to the local model; complex multi-step repair chains escalate to a stronger model. GPT-4o and Claude 3.5 Sonnet have been tested and are fully supported. To use them, set `CHERENKOV_TIER_SMALL_PROVIDER=openai` (and `OPENAI_API_KEY=...`) in your environment, or update the corresponding `[substrate.tiers.*]` section in `cherenkov.toml`. Enterprise teams can pin a specific model version for reproducibility.

---

### 3. How does CHERENKOV handle APIs that require authentication (Bearer tokens, API keys, OAuth)?

**Short answer:** Authentication headers are injected via environment variables or a `cherenkov.toml` `[auth]` block.

CHERENKOV never hardcodes credentials. Instead, the `[auth]` section in `cherenkov.toml` supports Bearer token (`bearer_token`), API key header (`api_key_header`, `api_key_value`), and static header injection (`headers = {Authorization = "..."}`). For OAuth2, you can pre-obtain a token in your CI script and export it as `CHERENKOV_AUTH_TOKEN`; CHERENKOV will inject it into every probe. CHERENKOV does not currently implement a full OAuth2 PKCE flow automatically — this is on the roadmap for Phase 4 enterprise hardening. For short-lived tokens (e.g., JWT with 1-hour expiry), CHERENKOV supports a `token_refresh_command` hook that re-runs a shell command before each probe batch.

---

### 4. What happens if the `--repair` self-healing loop fails after 3 attempts?

**Short answer:** The failing test is placed into the HITL (Human-in-the-Loop) queue, and a structured report is emitted. Nothing is auto-committed.

The `--repair` flag triggers up to 3 LLM repair cycles on a test that fails to parse or execute. If all 3 fail, CHERENKOV emits a `HITL_ESCALATION` event, writes the failed test stub and all 3 error traces to the HITL queue (`hitl_queue.jsonl`), and continues generating the remaining tests. The overall `generate` command exits with a non-zero code so CI can detect the escalation. The D7 invariant holds throughout: CHERENKOV never silently drops or auto-applies broken code. QA engineers review the queue with `cherenkov hitl list` and either approve, reject, or manually edit the suggestion. The audit trail for each escalation is preserved in `hitl_audit.jsonl` with timestamps, LLM attempt logs, and the final human decision.

---

### 5. Can I run tests in parallel across multiple endpoints for faster CI runs?

**Short answer:** Yes, probe-level parallelism is available via the `--workers N` flag.

`cherenkov validate --target http://localhost:8000 --workers 8` runs up to 8 probe goroutines concurrently. The default is 4. Parallelism is per-probe, not per-endpoint, so CHERENKOV correctly handles rate-limited APIs by respecting the `rate_limit_rps` setting in `cherenkov.toml`. For large specs (100+ endpoints), parallel probing typically reduces wall-clock time by 60–80%. Note that parallel probes share a single HTTP connection pool; if your API has strict per-connection concurrency limits, reduce `--workers` accordingly. Test generation (`cherenkov generate`) is also parallelisable via `--workers`; LLM calls are batched and sent concurrently up to the model's rate limit.

---

### 6. Can I write custom assertion templates or extend the generation prompts?

**Short answer:** Yes. CHERENKOV has a first-class plugin system for both custom assertions and prompt overrides.

Custom assertion templates are placed in `cherenkov/templates/assertions/` and follow a Jinja2 schema. CHERENKOV ships built-in templates for status code matching, JSON schema validation, response time bounds, and header checks; you can add templates like `check_pagination.j2` that validate your own pagination envelope format. Prompt extension is handled via the `[prompts]` section in `cherenkov.toml`: set `system_prompt_override = "prompts/my_system.txt"` to inject additional context (e.g., your internal API conventions) into every LLM call. For deeply custom generation, the `cherenkov.sdet` module exposes a Python `GenerationPlugin` interface that can be sub-classed. This is the approach used internally for the GraphQL and gRPC proof-of-concept adapters.

---

### 7. Does CHERENKOV support GraphQL or gRPC APIs, or only REST/OpenAPI?

**Short answer:** REST/OpenAPI is production-ready. GraphQL and gRPC have experimental adapters; they are not yet at parity with REST.

The source adapter system (`cherenkov/truth/sources/graphql.py`, `grpc.py`) was built in Phase 2 (E2.4) and can ingest GraphQL introspection schemas and Protobuf definitions to generate probe scenarios. However, the assertion engine and probe planner are currently optimised for HTTP/REST semantics. GraphQL adapters generate basic query/mutation probes and status-code checks, but do not yet validate GraphQL error envelopes or field-level nullability. gRPC support is similarly early — it generates stubs but cannot yet validate streaming RPCs. If REST/OpenAPI is your primary target, CHERENKOV is production-ready today. If GraphQL or gRPC is critical for you, expect a rough edge and plan to contribute or wait for Phase 4 GA. The roadmap explicitly includes full GraphQL+gRPC parity.

---

### 8. How does CHERENKOV integrate with GitHub Actions and Jenkins CI pipelines?

**Short answer:** Native GitHub Actions workflow and a Jenkins Shared Library are both shipped.

For GitHub Actions, add `.github/workflows/cherenkov.yml` (a template is in `docs/guides/github-actions-setup.md`; `cherenkov init` also scaffolds `.github/workflows/cherenkov.yml` for you) and configure the `cherenkov-action` step with your `--target` URL, `--spec` path, and exit-code behaviour. The `cherenkov certify` command can post a badge to your README on every green run. For Jenkins, Phase 10 delivered `ci/jenkins/vars/cherenkovValidate.groovy` — a Shared Library step callable as `cherenkovValidate(target: 'http://staging:8000', spec: 'openapi.yaml')`. Both integrations support fail-fast (non-zero exit on any divergence) and warn-only modes (always exit 0 but emit a structured report). A Docker image (`ghcr.io/cherenkov-qa/cherenkov:latest`) is available for containerised CI runners. The `--output report.json` flag feeds structured results to any CI dashboard (Allure, ReportPortal, DataDog, etc.).

---

### 9. What is the HITL (Human-in-the-Loop) queue and when does it trigger?

**Short answer:** The HITL queue is a curated list of items that CHERENKOV cannot resolve autonomously and requires a human decision on.

HITL triggers in three situations: (1) `--repair` exhausts 3 self-heal attempts on a generated test, (2) the validation engine detects an ambiguous spec (e.g., a `oneOf` with overlapping schemas where CHERENKOV can't determine the intended branch), and (3) a probe returns an undocumented status code that is outside the spec but may be intentional (e.g., a `429 Too Many Requests` not in the spec). In each case, CHERENKOV writes a structured `HitlItem` to `hitl_queue.jsonl` with the failing artefact, the error trace, and a ranked list of suggested resolutions. Engineers review the queue with `cherenkov hitl list`, act with `approve`/`reject`/`edit`, and the decision is logged to `hitl_audit.jsonl` with a timestamp and author. This audit trail is the compliance artefact for SOC2 and GDPR change-management requirements. The D7 invariant is the formal guarantee: CHERENKOV will never auto-apply any change to test code without a human decision on record.

---

## 🔒 Trust & Compliance Questions

---

### 10. Does my OpenAPI spec or test code ever leave my machine?

**Short answer:** Only if you configure an external LLM provider. With the default local (Ollama) backend, nothing leaves your machine.

The default CHERENKOV configuration uses a locally-hosted Qwen model via Ollama, running entirely on your workstation or CI runner. In this mode, your OpenAPI spec, generated test code, API request/response payloads, and any business-logic details never leave the machine. If you configure an external LLM provider (OpenAI, Anthropic, etc.), your spec fragments and test generation prompts are sent to that provider's API under your account's terms of service — the same as any other OpenAI API call you might make. CHERENKOV does not have its own cloud backend; there is no CHERENKOV cloud service that receives your data. The `cherenkov certify` command signs certificates locally using a keypair you control.

---

### 11. Can CHERENKOV run in an air-gapped environment with no internet access?

**Short answer:** Yes. Air-gap mode is a first-class deployment scenario.

Install CHERENKOV from source: clone the repository (or mirror it to your internal Git host) and run `pip install .` (or `pip install -e .` for development). There is no prebuilt wheel — the package is not yet published to PyPI (M2-gated); `install.sh` automates the source install. Pre-pull the Ollama images and Qwen model weights (`qwen2.5-coder:7b`, `deepseek-r1:8b`, `qwen2.5-vl:7b`) to your internal registry, and point the tiers at them: `OLLAMA_URL=http://your-internal-ollama:11434/api/generate` (or `CHERENKOV_VLM_LOCALAI_URL=http://your-internal-localai:8080` for the VLM tier), and keep `egress = "internal"` (the default). With these settings, CHERENKOV makes zero outbound network calls. The `eject` command produces a pure pytest/requests suite with no runtime CHERENKOV dependency, so even CI runners without CHERENKOV installed can execute the ejected tests. The Tauri desktop app (Phase 3) bundles the LocalAI sidecar, making it fully self-contained for offline workstations. Contact the team for an air-gap deployment guide with pre-tested model configurations.

---

### 12. How does the HITL audit trail work for SOC2 or GDPR compliance?

**Short answer:** Every HITL decision is append-only, timestamped, and author-attributed in `hitl_audit.jsonl`.

Each entry in `hitl_audit.jsonl` records: the item ID, the original artefact (test stub + error), all LLM repair attempts with their outputs, the human action (`approve`/`reject`/`edit`), the editor's identity (from `git config user.email` or `CHERENKOV_AUDIT_USER` env var), and an ISO 8601 timestamp. The file is append-only by design; CHERENKOV never rewrites or deletes audit entries. For SOC2 Type II, this log provides evidence that AI-generated test changes were reviewed by a named human before being applied. For GDPR Article 22 (automated decision-making), the HITL audit demonstrates that test logic decisions are not made solely by AI. The audit log can be exported to JSON, shipped to a SIEM, or committed to a compliance repository. A `cherenkov audit csv` command is planned for Phase 4.

---

### 13. What is the D7 invariant and why does CHERENKOV never auto-edit test code?

**Short answer:** D7 is the architectural principle that AI-generated suggestions are always proposals, never auto-applied changes. It exists to preserve human accountability over test assertions.

The D7 invariant (Design Invariant 7) states: *"Validate and healing produce reports/suggestions only. Never auto-commit or auto-apply."* This was established early in CHERENKOV's design after recognising that auto-editing test code creates a risk of silently degrading test coverage — the AI might "fix" a test by weakening its assertion to match a broken API rather than flagging the API as non-conformant. D7 means that all suggestions from the repair loop, the healing engine, and the validation engine are written as human-readable diffs with rationale. The human must explicitly `approve` before any change is written to the test file. This makes CHERENKOV safe to run in regulated environments and ensures that test coverage decisions remain auditable and human-owned. D7 is tested in the CI pipeline via `demos/catch-the-ai-cheating/`, which verifies the engine correctly fails (rather than silently weakening) when a conformance bug is injected.

---

### 14. How does the `eject` command work, and what files are produced?

**Short answer:** `cherenkov eject --output ejected/` produces a directory of standalone pytest files, a `requirements.txt`, and a `README.md`. No CHERENKOV imports remain.

The eject command iterates all test files in the CHERENKOV project, strips the `from cherenkov.sdet import *` imports and CHERENKOV-specific fixtures, replaces them with equivalent `requests` and `pytest` code, and writes the result to `ejected/`. The produced files are: one `.py` test file per original test, `requirements.txt` (containing only `requests` and `pytest`), `conftest.py` (with any shared fixtures that were portable), and `README.md` (with run instructions). The ejected suite is validated by running `pytest ejected/ --collect-only` during the eject command itself — if collection fails, CHERENKOV reports it rather than silently producing broken files. The pet-store ejected suite is used as a CI regression test: `tests/eject/petstore_suite/` runs 37/37 green on every PR to prove the eject command remains functional.

---

### 15. Is CHERENKOV safe to run against production APIs, or should I always use a mock?

**Short answer:** Use a mock or staging environment for automated runs. CHERENKOV is safe by design (read-only probes where possible), but production side effects from write probes are your team's responsibility to manage.

CHERENKOV probes follow the spec's documented HTTP methods — GET probes are safe; POST/PUT/DELETE probes write data to the target. Against production, this means CHERENKOV will create, update, and delete real resources unless you configure `read_only_mode = true` in `cherenkov.toml`, which restricts probes to GET and HEAD requests only. For comprehensive conformance testing (including write-path validation), run CHERENKOV against a staging environment or a Prism mock (as in Phase 3 of the demo). The `docker run stoplight/prism:5 mock` pattern in the demo harness is the recommended approach for zero-risk testing of write endpoints. If your spec marks certain endpoints as idempotent, CHERENKOV honours that and will attempt cleanup of created resources after each probe. Cleanup hooks are configurable via `[cleanup]` in `cherenkov.toml`.

---

### 16. Who has access to my generated tests and spec data if using the cloud-hosted version?

**Short answer:** There is currently no CHERENKOV cloud-hosted version. All data remains local.

CHERENKOV is distributed as an open-source CLI tool and a self-hostable service. There is no SaaS offering at present; your generated tests, spec files, and API response data are stored only on the machines where you run CHERENKOV. A cloud-hosted offering is on the extended roadmap (Phase 11 per `docs/PRODUCT_STRATEGY_ROADMAP.md`) and will include explicit data-residency controls, customer-managed encryption keys, and a published privacy policy before launch. If your organisation has a strict data classification policy, the recommended deployment today is: install CHERENKOV on your own infrastructure, use the LocalAI backend, and never configure an external LLM provider. This guarantees zero third-party data exposure.

---

### 17. Does CHERENKOV store or log the API responses it captures during validation?

**Short answer:** Response bodies are held in memory during a run and written to the run artefact (`run_store.db`) only when you explicitly enable response logging.

By default, CHERENKOV captures API responses for in-session comparison but does not persist them to disk. Response bodies are discarded after the probe completes. To enable persistent response logging (useful for debugging divergences), set `log_responses = true` in `cherenkov.toml` or pass `--log-responses` to `validate`. Logged responses are stored in `run_store.db` (SQLite) in the project directory. If your API responses contain PII or sensitive data, keep `log_responses = false` (the default) and use the `--summary-only` flag, which logs only status codes and schema-match results without any response body content. The run store is local to your machine and is never transmitted to CHERENKOV's servers (which don't exist) or to any LLM provider.

---

## 💼 Business Questions

---

### 18. What is the TCO (Total Cost of Ownership) compared to manual test writing?

**Short answer:** CHERENKOV typically reduces API conformance test authoring time by 70–85% and ongoing maintenance by 40–60%.

A mid-size API with 50 endpoints requires roughly 3–5 days for an experienced QA engineer to write a comprehensive conformance suite manually. CHERENKOV reduces initial authoring to 2–4 hours (generate + HITL review). The larger saving is in maintenance: when the spec changes, CHERENKOV re-generates only the affected tests and surfaces diffs for human approval, eliminating the "manual update treadmill" that is the dominant hidden cost of hand-written API tests. Infrastructure cost is low: LocalAI runs on a single GPU-optional server (CPU inference is supported for Qwen-7B); no GPU is required for test generation at typical spec sizes. Cloud LLM costs (if you choose OpenAI/Anthropic) run approximately $0.10–$0.50 per full spec generation for a 50-endpoint API. The break-even vs. manual authoring is typically within the first 2 spec changes.

---

### 19. How long does it take a new engineer to get productive with CHERENKOV?

**Short answer:** Most engineers complete the zero-to-first-passing-test workflow in under 30 minutes. Full workflow fluency (HITL, daemon, certify, eject) takes 1–2 days.

The `GETTING_STARTED.md` guide is designed to take a new user from zero to first green validation run in under 30 minutes on a standard Python environment. The Session A recording (`session_a.cast`) provides a visual walk-through. The steeper learning curve is around HITL triage and custom assertion templates — these typically take 4–8 hours of hands-on practice. CHERENKOV's opinionated defaults (LocalAI backend, spec-auto-detect, sensible worker counts) mean most engineers never need to touch `cherenkov.toml` for standard use cases. The onboarding package (`~/teamwork_projects/cherenkov_onboarding/`) includes 3 KT sessions, a pitch deck, FAQ, and demo harness specifically to accelerate this ramp. E0.3 (the practitioner validation gate) requires 3 engineers to complete the quickstart unaided — this is the formal evidence target.

---

### 20. What is the license? Can my company modify and redistribute the tool?

**Short answer:** The license is specified in the `LICENSE` file in the repository root. Review it before redistribution.

Check `cherenkov-qa/LICENSE` for the authoritative license text. The project is structured as open-core: the CLI and core conformance engine are open-source; premium features (enterprise dashboard, cloud cert registry, SLA-backed support) are planned as commercial add-ons. Internal modification for your own use is generally permitted under open-source licenses; redistribution or white-labelling requires review of the specific license terms. If your organisation has a Legal review process for open-source dependencies, the relevant SPDX identifier is in `pyproject.toml`. For enterprise licensing enquiries (e.g., OEM embedding or proprietary forks), contact the maintainers via the GitHub Discussions page.

---

### 21. How does CHERENKOV handle our existing Playwright test suite? Will it conflict?

**Short answer:** CHERENKOV and Playwright address different test layers and coexist without conflict.

CHERENKOV targets the API conformance layer (does the API match its OpenAPI spec?). Playwright targets the UI/end-to-end layer (does the user interface work correctly?). They run in separate processes, test different surfaces, and their assertions don't overlap. You can run both in the same CI pipeline: CHERENKOV first (fast, 30–120 seconds), then Playwright (slower, minutes). CHERENKOV's ejected test suite produces standard `pytest` files that live in the same repo as your Playwright tests without any import conflicts. If your Playwright tests call the same API that CHERENKOV validates, CHERENKOV is a stronger pre-flight check — if the API is non-conformant, CHERENKOV will catch it before Playwright even runs, saving you minutes of flaky UI test debugging. The recommended CI order: lint → unit tests → CHERENKOV validate → Playwright E2E.

---

### 22. What ROI metrics can I show to justify CHERENKOV to my engineering leadership?

**Short answer:** Lead with: conformance bug detection time (before vs. after), regression prevention rate, and spec drift incidents avoided.

Key metrics to instrument: **(1) Time to detect conformance bugs** — measure how long spec drift goes undetected without vs. with CHERENKOV (typical: days to months vs. minutes). **(2) Regression prevention rate** — count how many spec-breaking changes CHERENKOV catches in CI before they reach staging/production. **(3) QA engineering hours saved** — compare hours spent on API test authoring and maintenance before vs. after adoption. **(4) Audit compliance time** — for SOC2/GDPR, measure time to produce conformance evidence before vs. after (HITL audit log is the evidence artefact). The demo harness (`run_demo.sh`) produces a live demonstration of regression detection that is directly presentable to leadership. For the executive pitch, use the `PITCH_DECK.html` in the onboarding package, which frames CHERENKOV as risk reduction (preventing spec drift in production) rather than a QA tooling cost.

---

### 23. What support options are available? Is there enterprise support?

**Short answer:** Community support via GitHub Issues and Discussions is available now. Enterprise SLA-backed support is on the roadmap but not yet offered.

Currently, support is community-driven: file a GitHub Issue for bugs, use GitHub Discussions for questions, and consult the `docs/` tree and FAQ for self-service guidance. The documentation is extensive (see `docs/INDEX.md`) and covers architecture decisions, runbooks, and engineering best practices. Enterprise support (SLA, dedicated channel, private bug triage) is planned for Phase 11 (Market Launch) per `docs/PRODUCT_STRATEGY_ROADMAP.md`. If your organisation needs enterprise support before Phase 11, reach out to the maintainers via GitHub Discussions to discuss a custom arrangement. The HITL audit trail and certificate system were specifically designed to meet enterprise compliance requirements, so the tooling is enterprise-grade even if the support tier is not yet formalised.

---

### 24. How does CHERENKOV compare to tools like Postman, Pact, or Schemathesis?

**Short answer:** CHERENKOV occupies a distinct niche: it is the only tool that combines AI-generated test scenarios with spec-derived assertion validation, a HITL audit trail, and a no-lock-in eject command.

**vs. Postman:** Postman is a manual/collection-based API testing tool. It does not auto-generate tests from a spec, does not validate spec conformance programmatically, and has no HITL mechanism. CHERENKOV is a better fit for continuous spec conformance in CI. **vs. Pact:** Pact is a contract testing tool for consumer-driven contracts between microservices. CHERENKOV validates server-side conformance against a provider-owned OpenAPI spec. They are complementary, not competing. **vs. Schemathesis:** Schemathesis is the closest direct comparison — it also generates fuzz tests from OpenAPI specs. The key CHERENKOV differentiators are: AI-generated scenario descriptions (more semantically meaningful assertions than pure fuzz), the HITL review gate (D7 invariant), the conformance certificate, and the eject command (Schemathesis does not produce a portable, dependency-free test suite). Schemathesis is excellent for finding crashes and unexpected status codes; CHERENKOV is better for spec-as-truth conformance and compliance evidence.

---

### 25. If CHERENKOV shuts down tomorrow, what happens to our tests?

**Short answer:** Nothing bad. Your tests are yours, and the eject command produces a fully independent suite.

This is the purpose of the `eject` command and the anti-lock-in design invariant. At any time, run `cherenkov eject --output ejected/` to produce a directory of standard `pytest`/`requests` files with zero CHERENKOV imports. These files run with `pytest ejected/` and depend only on `pytest` and `requests` — two of the most stable Python packages in existence. The ejected suite is validated as part of CHERENKOV's own CI (37/37 pet-store tests pass). Your OpenAPI spec is your source of truth; if you ever need to regenerate tests, you can use any other spec-to-test tool (Schemathesis, Dredd, etc.) from the same spec. CHERENKOV's certificate format is documented as an open spec (`docs/specs/CHERENKOV_CERTIFICATE.md` v1.0 STABLE), so certificates remain readable without CHERENKOV tooling. In short: the tool is designed so that your investment survives the tool's existence.

---

*For questions not covered here, open a GitHub Discussion or file an Issue with the label `question`.*
