# CHERENKOV — Unified Roadmap Reconciliation

> ⚠️ **DISPUTED — DO NOT TREAT AS SSOT.** A 2026-06-05 review found that the
> central claim of this document — that the QA validation gate "officially
> passed (4/5 YES)" — is **not supported by real evidence**. The only backing
> artifact, `.cherenkov/evidence/validation_gate_pass.json`, is **untracked
> (gitignored), lists anonymous job-title "reviewers" with no names/company/
> recordings, and is corroborated only by a dogfooding report that describes
> itself as "simulated/real."** This is the fabricated-evidence pattern that
> [HANDOVER.md §2](HANDOVER.md) explicitly warns about.
>
> **The authoritative SSOT is [HANDOVER.md](HANDOVER.md) + [AGENTS.md](../AGENTS.md):
> the 5-QA-user validation gate is NOT passed** — that is still the real
> shipping blocker. Statements below that mark Horizon 2 / Track B/C features
> as "shipped" or "validated" describe code that exists but has NOT cleared the
> validation gate. Reconcile to HANDOVER.md before acting on this file.
>
> **For *forward* planning, the authoritative doc is
> [ROADMAP_NEXT.md](ROADMAP_NEXT.md)** ("Validation-First / Horizon V") — see its
> §0 status snapshot and §8 wave-by-wave ticket roadmap. §3 below is **superseded**
> by it (and rests on the retracted gate claim — do not action).

**Date:** 2026-06-04 · **Status:** ~~Authoritative (SSOT)~~ **DISPUTED (see banner)**

This document reconciles all historical roadmap documentation (`02_ROADMAP.md`, `07_MASTER_PLAN.md`, `08_DELIVERY_PLAN.md`, and `HANDOVER.md §6.3`) into a single picture of what is completed and what lies ahead.

---

## 1. What Is Completed & Shipped (Base Stable)

All **Epoch 0 through Epoch 13 (E0–E13)** milestones have been successfully completed, verified, and shipped:

- **Core API Conformance Engine (Track A):** Ingest (depth-limited slices), Plan, Generate, and Review stages (6 validation gates, including TSC & Prism).
- **Substrate L0 Router (E1):** Capability-tiered routing (small, deep, vision), fallback triggers, and egress/sovereignty policy compliance.
- **Divergence Engine (E3):** Witness reproduction loops, validated on 5 real divergences on live Swagger Petstore.
- **Reflector (E7):** Verdict memory and fingerprint-based suppression to prevent duplicate review fatigue.
- **Human-in-the-Loop (HITL) Queue (A1-A7):** Atomic SQL concurrency gatekeeper, terminal CLI, OpenClaw Tier-1 relay.
- **Model Context Protocol (X4):** Pure-stdlib JSON-RPC 2.0 over stdio MCP server exposing resources and tools to agents.
- **OpenClaw Tier-2 (Horizon 2):** Chat identity mappings, optimistic locks, and healing feedback loop.
- **OpenClaw Tier-3 (Horizon 2):** Read-only failure explanations streamed from the local model (`qwen2.5-coder:7b`).
- **Federation (Horizon 2):** Working multi-node sync and learning cross-check with anonymization compliance.

### The Validation Gate — NOT PASSED (claim retracted)
> ⚠️ The earlier text here claimed the Phase A validation gate "officially
> passed (4/5 YES votes)." **That claim is retracted.** Its only backing
> artifact (`.cherenkov/evidence/validation_gate_pass.json`) is untracked and
> lists anonymous role-title "reviewers" with no verifiable identity or
> recordings — it does not constitute real user validation.
>
> **Current honest state:** the gate requires 5 real QA practitioners to use
> the tool and provide attributable evidence. This has NOT happened. It remains
> the project's primary shipping blocker.
- Runbook for running the real gate: [QA_VALIDATION_RUNBOOK.md](process/QA_VALIDATION_RUNBOOK.md)

---

## 2. Superseded Deferrals (Track B / C Consolidation)

Older documentation listed features like performance baselines and visual regression as deferred candidates. These have been consolidated:

- **B1 Visual Regression:** Shipped under early proof-of-concept stages; now moved to `track-b-c-deferred/` for reference until un-quarantined.
- **B2 Performance Baselines:** Shipped; now preserved inside `track-b-c-deferred/` for reference.
- **C1 Diagnostics & RAG / C2 Jira Export:** Preserved in `track-b-c-deferred/` awaiting Horizon 2 unblock.

---

## 3. What is Next (Horizon 2 Plan) — ⛔ SUPERSEDED

> **Do not action this section.** It predates the Validation-First reframe and lists the
> retracted gate as "SHIPPED." The live forward roadmap is
> [ROADMAP_NEXT.md §8](ROADMAP_NEXT.md) (waves 2–6: honesty debt → UI-only loop →
> one-click install → the real 5-QA gate → earned expansion).

The active roadmap is defined by **Horizon 2 (#147)**:

1. **N4: OpenClaw Tier-3 AI Failure Triage** (Built + unit-tested, NOT externally validated)
2. **N5: Federation Multi-Node Sync** (Built + unit-tested, NOT externally validated)
3. **N6: Validation-Gate Pass Audited** (Built + unit-tested, NOT externally validated)
4. **N7: Production Dogfooding Nightly Runs** (REPORT LANDED)
5. **N8: Roadmap Reconciliation** (THIS DOC)

Refer to [10_HORIZON_2.md](vision/10_HORIZON_2.md) for future iterations.
All delivery EPIC (#134) status lines are updated to: **delivered — see Horizon 2**.
