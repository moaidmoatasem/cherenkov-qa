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

- [Getting Started Guide](file:///z:/home/moaid/cherenkov-qa/docs/GETTING_STARTED.md): Install Cherenkov QA and execute your first local validation.
- [Petstore Walkthrough](file:///z:/home/moaid/cherenkov-qa/QUICKSTART_PETSTORE.md): Interactive 5-minute tutorial running against a sample OpenAPI 3.1 Petstore API.
- [Knowledge Transfer Onboarding Script](file:///z:/home/moaid/cherenkov-qa/docs/KT_ONBOARDING_SCRIPT.md): Complete walkthrough script for new team members.

---

## 2. 🛠️ How-To Guides (Task-Oriented)
*Problem-solving recipes for specific, real-world tasks.*

- [Spec Guardian Drift Monitoring](file:///z:/home/moaid/cherenkov-qa/docs/guides/spec_guardian.md): Set up the continuous drift detection daemon with hot-reloading spec watching.
- [SAML 2.0 / SSO Integration](file:///z:/home/moaid/cherenkov-qa/docs/guides/saml_sso.md): Configure Enterprise SAML 2.0 identity providers and role mapping.
- [SLM Model Fine-Tuning](file:///z:/home/moaid/cherenkov-qa/docs/guides/slm_training.md): Collect local telemetry and fine-tune custom QA models via `cherenkov train`.
- [Template & MCP Tool Publishing](file:///z:/home/moaid/cherenkov-qa/docs/README-MCP-PUBLISH.md): Package and publish custom test templates to local/remote registries.
- [CI/CD Native Pipeline Setup](file:///z:/home/moaid/cherenkov-qa/ci/README.md): Integrate Cherenkov into GitHub Actions, GitLab CI, and Jenkins.

---

## 3. 📋 Reference (Information-Oriented)
*Exhaustive, structured technical descriptions for rapid lookup.*

- [CLI Command Reference](file:///z:/home/moaid/cherenkov-qa/docs/cli-reference.md): Complete list of commands, options, and flags.
- [Architecture & Map](file:///z:/home/moaid/cherenkov-qa/docs/ARCHITECTURE_MAP.md): Detailed inventory of domain ports, adapters, and core orchestrators.
- [Error Handling Reference](file:///z:/home/moaid/cherenkov-qa/docs/ERROR_HANDLING.md): Standardized error codes, exceptions, and exit codes.
- [Master Roadmap](file:///z:/home/moaid/cherenkov-qa/docs/ROADMAP.md): Tracking status for Phases -1 through 16.
- [Architecture Decision Records (ADRs)](file:///z:/home/moaid/cherenkov-qa/docs/adr/INDEX.md): Formal log of design choices.

---

## 4. 💡 Explanations (Understanding-Oriented)
*High-level discussions on design philosophy, trade-offs, and vision.*

- [System Design Document](file:///z:/home/moaid/cherenkov-qa/docs/SYSTEM_DESIGN.md): Technical architecture and modular decomposition.
- [D7 Validation Invariants](file:///z:/home/moaid/cherenkov-qa/AGENTS.md): Core non-negotiable rules governing test generation and self-healing.
- [Sync Driven Development (SDD)](file:///z:/home/moaid/cherenkov-qa/docs/engineering/SYNC_DRIVEN_DEV.md): Deep dive into token-efficient agent memory protocols.
- [Autonomous Quality Fabric (AQE 2026 Vision)](file:///z:/home/moaid/cherenkov-qa/docs/VISION_AQE_2026.md): The 10-year vision for AI quality governance.
