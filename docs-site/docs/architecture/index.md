---
title: Architecture
description: How CHERENKOV-QA is built — Clean Architecture layers, the AI pipeline, the knowledge mesh, and the platform boundary that keeps quality verdicts independent.
---

# Architecture

CHERENKOV-QA is built around one idea: **keep the quality verdict independent of the AI that produced the work.** Everything here — the layered module structure, the AI pipeline, the knowledge mesh — exists to make that verdict reproducible, tamper-evident, and owned by a human.

If you read one page, read [System Design](system-design.md) — it frames the whole platform and where API conformance fits as the shipped core of an open Quality Intelligence Platform.

---

## Start Here

| Page | What it covers | Read it when |
|------|----------------|--------------|
| [System Design](system-design.md) | Module layers, dependency graph, and the platform boundary (core vs. adapters) | You want the big picture first |
| [Clean Architecture (ADR-004)](clean-architecture.md) | The Ports/Adapters decision and the strict inward-dependency rule | You're adding a module and need to know where it goes |
| [AI Pipeline](ai-pipeline.md) | LLM-powered generation, the 6-gate review, and divergence detection | You want to understand how tests are produced and audited |
| [Module Reference](module-reference.md) | A map of every Python module in the `cherenkov` package, by layer | You're navigating the source tree |
| [Second Brain (Knowledge Mesh)](second-brain.md) | The GraphRAG store of verdicts, idioms, and incidents | You want to know how CHERENKOV remembers |
| [Diagrams](diagrams.md) | 17 Mermaid diagrams: system context, pipeline, divergence loop, and more | You think in pictures |

---

## The One-Paragraph Version

Dependencies flow strictly inward (Clean Architecture, ADR-004). At the center is a small, independent **core** — quality policy, verdict schema, evidence integrity, certificates, and governed memory — that an agent cannot lower for itself. Around it, everything replaceable lives as **adapters**: test frameworks, model providers, source systems, CI, and IDEs. API conformance is the flagship, shipped evidence source; mobile, performance, and security executors are the platform's direction, not current scope. See [System Design → Platform Context](system-design.md#platform-context-the-independent-quality-layer) for the full boundary.

---

## Next Steps

- [System Design](system-design.md) — the platform boundary and module layers
- [CLI Reference](../cli/reference.md) — the commands these layers expose
- [Guides](../guides/index.md) — hands-on workflows built on this architecture
