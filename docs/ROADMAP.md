# CHERENKOV QA — Master Roadmap

This document serves as the unified source of truth for the Cherenkov QA product strategy, market roadmap, and technical implementation plan. It consolidates previous roadmaps into a single, cohesive vision.

## 1. Where We Stand

> **Corrected 2026-08-11 by backlog reconciliation.** This section previously read "Phases -1 through 16 are Complete". That was not true: a code-level audit of every open issue found 7 items either simulated, placeholder, or entirely unimplemented. The per-issue GitHub comments are the authoritative record of what is actually shipped.

- **Phases -1 through 12: Complete.** Core engine, CLI, desktop host (Tauri), chat agents, dashboard.
- **Phase 13 — Enterprise Tier: 7/9 complete.** SAML 2.0 SSO, RBAC, multi-tenant orgs, audit log, GDPR, SOC2 reports, and BYO-LLM are real and wired. **Open:** SLA dashboard (#762) and support portal (#763) — both currently render fabricated data and are tracked as integrity defects, not missing features.
- **Phase 14 — Spec Guardian: Complete.** Daemon, CLI entrypoint, dashboard routes, conformance trend and regression detection.
- **Phase 15 — Fine-Tuned Model: 5/7 complete.** The training pipeline (collection → curation → fine-tune → eval) runs end-to-end via `cherenkov train`. **Open:** model release (#779) and self-hosted serving (#780) — no code yet; both parked behind Gate G0.
- **Phase 16 — Platform & Marketplace: 5/8 complete.** Public API, Plugin SDK, template marketplace, federation, and webhooks are real. **Open:** LLM provider marketplace (#785), CHERENKOV Certified (#787), Analytics API (#789).
- **Technical Moat**: Spec-driven generation, local-first LLM design, strict D7 validation invariants, and isolated sandboxing.

**The single highest-value open item is #787 (CHERENKOV Certified)** — it is Rung 3 of `NORTH_STAR.md` §3, the move from platform to standard. Everything else open is convenience or cleanup.

## 2. The Execution Plan (Phases 9 - 16)

### Horizon 1: Distribution & Market Launch (Months 1-3)
- **Phase 9 — Market Launch**: Cut v1.0.0, execute Product Hunt / Hacker News launch kit, demo video arcs.
- **Phase 10 — CI/CD Native**: Provide native GitHub Actions (`action.yml`), GitLab CI templates, and Jenkins pipelines.
- **Phase 11 — VS Code Extension**: Bring the "Catch AI Cheating" experience directly to where developers live.

### Horizon 2: Ecosystem Expansion (Months 3-9)
- **Phase 12 — Protocol Expansion**: Add support for GraphQL, gRPC, and AsyncAPI alongside OpenAPI 3.1.
- **Phase 13 — Enterprise Tier**: Introduce SSO/SAML, role-based access control (RBAC), and team workspaces.

### Horizon 3: Platform Dominance (Months 9-30)
- **Phase 14 — Spec Guardian**: Active daemon monitoring spec-to-server drift in real-time.
- **Phase 15 — Fine-Tuned Model**: Release a custom SLM (Small Language Model) hyper-optimized for QA generation and validation.
- **Phase 16 — Platform & Marketplace**: Open the MCP Ecosystem for third-party integrations, custom evaluators, and public test templates.

## 3. Integration Strategy
Our goal is to integrate into 25 external systems across 5 tiers:
1. **Tier 0 (Dev)**: VS Code, Cursor, Zed, JetBrains.
2. **Tier 1 (Team)**: GitHub, GitLab, Jira, Slack, Teams.
3. **Tier 2 (Quality)**: SonarQube, Zephyr, Xray, Allure.
4. **Tier 3 (AI)**: Ollama, LocalAI, vLLM, OpenAI, Anthropic.
5. **Tier 4 (Enterprise)**: Datadog, Splunk, Okta, Active Directory.

## 4. Growth & Adoption Strategy

> **Corrected 2026-08-11.** This section previously described an "Open Core Model" in which "Enterprise Tier (Phase 13) monetizes SSO, audit logs, distributed testing, and hosted infrastructure." That contradicts the product decision recorded on issue #754 (2026-08-01) and is withdrawn.

- **Fully open source.** CHERENKOV-QA is Apache-2.0 in its entirety. There is no paid tier, no pricing page, no "contact sales", and no license-gating. Phase 13's SSO/RBAC/audit/GDPR features are ordinary free, self-hosted capabilities like everything else in the CLI.
- **Growth is adoption-led, not revenue-led.** The sequence is `NORTH_STAR.md` §3's product ladder: earn the verb at the CLI (Rung 1), own the workflow (Rung 2), then define the standard via the Certificate (Rung 3).
- **Neutrality is never sold** (`NORTH_STAR.md` §9.4). Vendor-preferential placement, sponsored provider ranking, and CHERENKOV-operated inference are all structurally excluded — independence is the product.

## 5. The 10-Year Vision
Cherenkov QA will evolve from an API testing tool into the **Autonomous Quality Fabric (AQE)**. It will sit as the ubiquitous referee between AI-generated code and production reality, ensuring that as software generation accelerates, quality and compliance accelerate even faster.
