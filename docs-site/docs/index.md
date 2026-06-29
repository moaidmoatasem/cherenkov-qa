---
title: CHERENKOV-QA — AI-Native API Conformance Testing
description: OpenAPI spec to typed Playwright tests, executed locally, with zero vendor lock-in.
---

<div class="cherenkov-hero" markdown>

# CHERENKOV-QA

**AI-native API conformance testing.**  
Spec in → Tests out → Drift caught. Locally. Privately. Zero lock-in.

<div class="hero-buttons">
  <a href="getting-started/" class="hero-btn primary">Get Started →</a>
  <a href="cli/reference/" class="hero-btn secondary">CLI Reference</a>
</div>

</div>

---

## What It Does

CHERENKOV reads your **OpenAPI specification**, uses a **local LLM** (no cloud, no API keys) to generate typed Playwright API tests, executes them against your real server, and delivers **conformance violation reports** — all in a single command.

```bash
cherenkov validate --spec petstore.yaml --target http://localhost:8000
```

If your live API drifts from its spec, CHERENKOV catches it. Every time.

---

## Why CHERENKOV

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
<div class="icon">🤖</div>

### Offline-First AI
Uses `qwen2.5-coder:7b` via Ollama by default. No internet. No API keys. Your spec never leaves your machine.
</div>

<div class="feature-card" markdown>
<div class="icon">🔌</div>

### Zero Lock-In
`cherenkov eject` strips all proprietary imports and leaves you with vanilla Playwright tests that run forever without CHERENKOV.
</div>

<div class="feature-card" markdown>
<div class="icon">🎯</div>

### CI/CD Native
Returns exit code `1` on spec drift. JUnit XML + SARIF output. GitHub Actions marketplace action. Pre-commit hooks.
</div>

<div class="feature-card" markdown>
<div class="icon">🧠</div>

### Second Brain
GraphRAG knowledge mesh remembers past verdicts, idioms, and incidents. Gets smarter every run.
</div>

<div class="feature-card" markdown>
<div class="icon">🛡️</div>

### Security Testing
Embedded OWASP mutation payloads for DAST-lite security testing without a separate tool.
</div>

<div class="feature-card" markdown>
<div class="icon">☸️</div>

### K8s Native
`ConformanceCheck` CRD + Go operator for scheduled in-cluster conformance scanning.
</div>

</div>

---

## Quick Start

=== "pip (Python)"

    ```bash
    pip install cherenkov-qa
    cherenkov validate --spec your-api.yaml --target http://localhost:8000
    ```

=== "npx (Node)"

    ```bash
    npx cherenkov-cli init
    npx cherenkov-cli validate --spec your-api.yaml --target http://localhost:8000
    ```

=== "Docker"

    ```bash
    docker compose up -d
    # Dashboard at http://localhost:8000
    ```

---

## Trusted By

CHERENKOV has been validated against real APIs:

| API | Divergences Found |
|-----|------------------|
| Petstore (OpenAPI example) | 4 |
| HTTPBin | 1 |
| GitHub API | 1 |

---

## Cost: $0

CHERENKOV runs entirely locally. No subscriptions. No usage fees. No data exfiltration.

| Tier | Monthly Cost |
|------|-------------|
| Bare CLI + SQLite | **$0** |
| + Ollama (local LLM) | **$0** |
| + Docker + LocalAI | **$0** |
| + Full stack (mobile, desktop) | **$0** |
| Enterprise (K8s operator, SSO) | $300+/mo |

[See full cost tier breakdown →](getting-started/cost-tiers.md)

---

## License

Apache 2.0. Open source. Self-hosted. Yours to keep.

[GitHub](https://github.com/moaidmoatasem/cherenkov-qa){ .md-button } 
[Discord](https://discord.gg/cherenkov){ .md-button }
