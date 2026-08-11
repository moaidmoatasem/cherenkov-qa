# CHERENKOV QA — Documentation Index

Welcome to the Cherenkov QA documentation hub. Content is organized according to the **Diátaxis Framework** into four distinct quadrants based on user intent.

---

```
                       PRACTICAL
                           │
       Tutorials           │         How-To Guides
    (Learning-oriented)    │       (Task-oriented)
                           │
  ─────────────────────────┼─────────────────────────
                           │
      Explanations         │         Reference
  (Understanding-oriented) │   (Information-oriented)
                           │
                       THEORETICAL
```

---

## 1. 🎓 Tutorials (Learning-Oriented)
*Step-by-step, linear guides designed to help new users build confidence and run their first tests.*

- [Getting Started Guide](GETTING_STARTED.md): Install Cherenkov QA and execute your first local validation.
- [Petstore Walkthrough](../QUICKSTART_PETSTORE.md): Interactive 5-minute tutorial running against a sample OpenAPI 3.1 Petstore API.
- [Knowledge Transfer Onboarding Script](KT_ONBOARDING_SCRIPT.md): Complete walkthrough script for new team members.

---

## 2. 🛠️ How-To Guides (Task-Oriented)
*Problem-solving recipes for specific, real-world tasks.*

- [GitHub Actions Setup](guides/github-actions-setup.md): Integrate Cherenkov into a CI pipeline. Templates for GitLab CI and Jenkins live in [`ci/`](../ci/).
- [Template & MCP Tool Publishing](README-MCP-PUBLISH.md): Package and publish custom test templates to local/remote registries.
- [Kubernetes Deployment](guides/k8s-deployment.md): Deploy the operator and CRDs to a cluster.
- [Migrating from Dredd](guides/migrating-from-dredd.md) · [Postman Migration](guides/postman-migration.md): Move an existing suite over.
- [Petstore Case Study](guides/case-study-petstore.md): A worked end-to-end example.

> **Documentation gap.** This section previously linked to `guides/spec_guardian.md`,
> `guides/saml_sso.md` and `guides/slm_training.md`. None of those files has ever existed,
> so the links were dead. The underlying features are real — Spec Guardian
> ([ADR-009](adr/ADR-009-spec-guardian-daemon.md), `cherenkov guardian start`), SAML/SSO
> (`cherenkov/enterprise/saml.py`, `cherenkov enterprise saml configure`) and SLM training
> (`cherenkov train`) — but they ship with no user-facing how-to guide. Tracked rather than
> papered over; see `docs/TEST_PLAN_AGENTIC_2026-08.md` §5.1, which gates exactly this class
> of claim-without-evidence.

---

## 3. 📋 Reference (Information-Oriented)
*Exhaustive, structured technical descriptions for rapid lookup.*

- [CLI Command Reference](cli-reference.md): Complete list of commands, options, and flags.
- [Architecture & Map](ARCHITECTURE_MAP.md): Detailed inventory of domain ports, adapters, and core orchestrators.
- [Error Handling Reference](ERROR_HANDLING.md): Standardized error codes, exceptions, and exit codes.
- [Master Roadmap](ROADMAP.md): Tracking status for Phases -1 through 16.
- [Architecture Decision Records (ADRs)](adr/INDEX.md): Formal log of design choices.
- [Agentic Test Plan (2026-08)](TEST_PLAN_AGENTIC_2026-08.md): The eight-axis composite coverage gate, the agent pipeline that reaches it, and the measured baseline it starts from.

---

## 4. 💡 Explanations (Understanding-Oriented)
*High-level discussions on design philosophy, trade-offs, and vision.*

- [System Design Document](SYSTEM_DESIGN.md): Technical architecture and modular decomposition.
- [D7 Validation Invariants](../AGENTS.md): Core non-negotiable rules governing test generation and self-healing.
- [Sync Driven Development (SDD)](engineering/SYNC_DRIVEN_DEV.md): Deep dive into token-efficient agent memory protocols.
- [Autonomous Quality Fabric (AQE 2026 Vision)](VISION_AQE_2026.md): The 10-year vision for AI quality governance.
