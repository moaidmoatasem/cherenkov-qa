# continue-on-error audit — classification matrix (2026-08-04)

Raw evidence: `grep -rc "continue-on-error: true" .github/workflows/*.yml`
**30 instances across 11 workflow files.** Each classified as **GATE**
(must fail red — flag removed) or **ADVISORY** (informational — flag retained
with rationale comment). Aligned with `CONTRIBUTING.md:41` required checks
(Documentation Coverage · Healing Suggest-Only · CLI Help + Docs Gate · CodeQL).

## GATE — continue-on-error removed (23)

| Workflow | Job/step | Why it must fail red |
|---|---|---|
| ci.yml | docs-drift-gate (Documentation Coverage) | **Required check #1** — a coverage gate that cannot fail is a lie |
| ci.yml | healing-invariant (Healing Suggest-Only) | **Required check #2** — enforces D7/suggest-only invariant |
| ci.yml | polish-invariant (CLI Help + Docs Gate) | **Required check #3** — CLI/docs drift detection |
| ci.yml | codeql-analysis (CodeQL Security Analysis) | **Required check #4** — security analysis must block |
| ci.yml | certification-gate (E12 Certification Gate C11) | Certification smoke — real verification |
| ci.yml | governance-kpi (E12 Governance KPI C12) | Governance smoke — real verification |
| ci.yml | copilot-e10 (E10 Explorer + Copilot C8-C10) | E10 exit-criteria tests |
| ci.yml | ai-interface-unit (AI InferenceClient Seam) | Unit tests — contract seam |
| ci.yml | smoke-eject-node (Eject + Playwright E2E) | Anti-lock-in invariant E2E |
| ci.yml | smoke-perf-k6 (Perf Baseline k6) | Perf regression smoke |
| ci.yml | validate-smoke (Validate CLI E2E) | Core verify command E2E |
| ci.yml | mobile-pipeline-unit (Mobile Pipeline Unit) | Unit tests |
| ci.yml | snyk-scan (Snyk Dependency Scan) | Dependency vuln scan (its own step already exits 1 on crit/high) |
| ci.yml | docs-parity (CLI Docs Parity) | Docs drift detection |
| ci.yml | sandbox-provider-unit (Sandbox Provider Unit) | Unit tests |
| ci.yml | policy-engine-unit (MCP Policy Engine Unit) | Unit tests |
| ci.yml | model-runner-unit (Model Runner Adapter Unit) | Unit tests |
| validation-gate.yml | golden-path (Golden Path E2E) | The named validation gate — must gate |
| security-scan.yml | semgrep (Security Analysis job) | Security scan must block |
| publish.yml | publish (Docker Hub publish) | A publish that "succeeds" on failure ships nothing silently |
| mobile-ci.yml | unit-dry-run (Mobile unit tests) | Unit tests |
| self-dogfood.yml | dogfood (CHERENKOV verifies itself) | Self-verification must block |
| desktop-build.yml | build (Cargo build matrix) | Build must block |

## ADVISORY — continue-on-error retained with rationale (7)

| Workflow | Job/step | Rationale (comment added/kept) |
|---|---|---|
| ci.yml | windows-smoke → `doctor` step | doctor exits 1 when Ollama/Docker absent — expected in CI; we only verify it doesn't crash (ImportError etc.) |
| security-scan.yml | upload-sarif step | SARIF upload needs GitHub Advanced Security; must not block |
| action-self-test.yml | upload-sarif step | Same — SARIF upload needs Advanced Security |
| behavioral-diff.yml | behavioral-diff job | Informational only — spec-diff comment, not a merge gate |
| mobile-ci.yml | integration-android-emulator job | Advisory — needs Android emulator + Maestro; steps use `\|\| true` by design |
| supply-chain.yml | SLSA provenance step | Inline L2 approximation (reusable workflow ref), not a real attestation |
| docs-deploy.yml | auto-generate CLI reference step | Script emits a fallback message when cherenkov not installed |

## Acceptance

- Zero `continue-on-error` on any of the 4 CONTRIBUTING.md:41 required checks ✓
- Every remaining instance has an inline rationale comment ✓
- All 11 affected workflows parse as valid YAML ✓
