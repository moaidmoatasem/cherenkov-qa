---
title: Guides
description: Practical guides for using CHERENKOV-QA — from test generation to production monitoring.
---

# Guides

Hands-on guides for every part of the CHERENKOV workflow. Each guide is self-contained — start with whichever matches your current task.

---

## Core Workflow

| Guide | Audience | Description |
|-------|----------|-------------|
| [API Conformance Testing](api-conformance.md) | Developer, QA | Run the full validate pipeline: spec in, divergences out |
| [Test Generation & Repair](test-generation.md) | Developer, QA | Generate Playwright tests from OpenAPI specs with a 6-gate review pipeline |
| [Check Suite (Integrity Audit)](check-suite.md) | Developer, QA, DevOps | Detect weakened, deleted, or hallucinated assertions in your test suite |
| [Human-in-the-Loop Workflow](hitl.md) | QA, Manager | Approve or reject AI-generated findings via CLI or dashboard |

## Observability & Monitoring

| Guide | Audience | Description |
|-------|----------|-------------|
| [Dashboard & UI](dashboard.md) | Developer, QA, Manager | Navigate the five dashboard workspaces for real-time conformance visibility |
| [Continuous Monitoring](continuous-monitoring.md) | DevOps, SRE | Run CHERENKOV as a daemon or Spec Guardian for ongoing drift detection |

## Compliance & Certification

| Guide | Audience | Description |
|-------|----------|-------------|
| [Certificates & Compliance](certificates.md) | DevOps, Compliance, Security | Issue tamper-evident verification certificates and map to regulatory frameworks |

## Deployment

| Guide | Audience | Description |
|-------|----------|-------------|
| [Docker & Deployment](docker.md) | DevOps, SRE | Deploy CHERENKOV with Docker Compose — full stack, AI stack, and production configs |
| [K8s Operator](k8s-operator.md) | DevOps, SRE | Kubernetes-native deployment with CRDs and Helm |
| [Local LLM Setup](local-llm.md) | Developer, DevOps | Configure Ollama, model selection, and GPU acceleration |

## Security & Operations

| Guide | Audience | Description |
|-------|----------|-------------|
| [Security](security.md) | Security, DevOps | Network egress policies, auth, and air-gapped operation |
| [Eject](eject.md) | Developer | Remove all CHERENKOV dependencies from generated tests |
| [OpenAPI Spec Guide](openapi-spec.md) | Developer, QA | Write specs that produce better generated tests |

---

## Where to Go First

- **"I want to try CHERENKOV"** — start with [Quickstart](../getting-started/quickstart.md), then come back to [Test Generation](test-generation.md)
- **"I want to add CHERENKOV to CI"** — go to [CI/CD Integration](ci-cd.md) and [Check Suite](check-suite.md)

- **"I want continuous monitoring"** — read [Continuous Monitoring](continuous-monitoring.md) and [Dashboard](dashboard.md)
- **"I need compliance evidence"** — start with [Certificates & Compliance](certificates.md)
