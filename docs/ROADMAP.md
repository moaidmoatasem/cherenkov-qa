# CHERENKOV QA — Master Roadmap

This document serves as the unified source of truth for the Cherenkov QA product strategy, market roadmap, and technical implementation plan. It consolidates previous roadmaps into a single, cohesive vision.

## 1. Where We Stand
- **Phases -1 through 16 are Complete**: Core engine, CLI, desktop host (Tauri), chat agents, dashboard, SAML 2.0 SSO (Phase 13), Spec Guardian hot-reload & trend CLI (Phase 14), Fine-Tuned SLM pipeline (Phase 15), and Platform & Marketplace (Phase 16) are built and validated.
- **Technical Moat**: Spec-driven generation, local-first LLM design, strict D7 validation invariants, and isolated sandboxing.

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

## 4. Growth & Revenue Strategy
- **Open Core Model**: The core validation engine and local-LLM runners remain open source and free.
- **Commercial Offerings**: Enterprise Tier (Phase 13) monetizes SSO, audit logs, distributed testing, and hosted infrastructure.

## 5. The 10-Year Vision
Cherenkov QA will evolve from an API testing tool into the **Autonomous Quality Fabric (AQE)**. It will sit as the ubiquitous referee between AI-generated code and production reality, ensuring that as software generation accelerates, quality and compliance accelerate even faster.
