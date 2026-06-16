# CHERENKOV — AQE Roadmap (future-work breakdown)

> Translates [NORTH_STAR.md](NORTH_STAR.md) (what world-class is) + [VISION_AQE_2026.md](VISION_AQE_2026.md) (why) into **ready-to-file epics and tickets**, ordered by the gate discipline in [EXECUTION_PLAN.md](EXECUTION_PLAN.md). Climb the ladder; don't skip rungs.
> **Date:** 2026-06-16 · Anchor: v1.0.0 on `main`.

## Sequencing principle
Each phase is **gated**: do not start phase N+1 until phase N's exit gate passes. The wedge (conformance) earns the right to build the platform; the platform earns the right to be the authority. Nothing here is greenlit for build until **Gate G0** (below) passes — G0 work itself is the only unconditionally-active phase.

---

## Phase 0 — Prove the wow (Gate G0) · ACTIVE
*Goal: undeniable, reproducible proof on systems we don't own, including the integrity catch.*

- **E0.1 — Real-divergence proof.** Run CHERENKOV against ≥3 third-party APIs; capture ≥2 genuine divergences with reproductions. *Exit: 2/3 yield real divergence.*
- **E0.2 — Integrity catch (the thesis test).** Have an agentic generator (e.g. an OSS test-gen agent) produce a suite; CHERENKOV's gates must catch a weakened/hallucinated assertion or a deleted check the generator let through. *Exit: ≥1 caught cheat, reproducible.*
- **E0.3 — Quickstart validation.** ≥3 practitioners complete the quickstart unaided and rate it useful.
- **E0.4 — One honest differentiation sentence** vs Schemathesis/property-based tools, written and defensible.

**GATE G0 (blocks everything below):** E0.1 ∧ E0.2 ∧ E0.3 ∧ E0.4. See [fabricated-validation-gate] history — anchor status to HANDOVER.md, never to a claimed pass.

---

## Phase 1 — Rung 1: the Tool people love
*Goal: a CLI a single engineer adopts in 10 minutes; integrity guarantee is real, not marketing.*

- **E1.1 — `cherenkov verify` UX.** One command, zero-config default, local-first, human-readable + JSON output.
- **E1.2 — Meaningful-assertion gate (port from `feat/92`).** Reimplement the concept on `main` cleanly — DO NOT merge the stale branch (542k-line deletions). Gate fails suites whose assertions don't actually constrain behavior.
- **E1.3 — Guardrails-can't-be-weakened proof.** Adversarial test corpus of "cheating" suites; CI proving the gates catch each. This is the audit behind the brand promise.
- **E1.4 — Eject command hardening.** Prove zero lock-in end-to-end.
- **E1.5 — Install friction to near-zero.** One-line install; ties to UX one-click board (EPIC #241).

**Exit:** an outside engineer installs, runs, catches a real issue, and can eject — without help.

---

## Phase 2 — Rung 2: the Platform (Reality Engine + MCP)
*Goal: continuous truth across sources; CHERENKOV becomes the verify step in agent loops.*

- **E2.1 — MCP verification server (publish).** Any agent calls CHERENKOV to verify a suite/system. Spec: [specs/MCP_VERIFICATION_SERVER.md](specs/MCP_VERIFICATION_SERVER.md).
- **E2.2 — MCP context consumer.** CHERENKOV consumes MCP for richer system context (the four open seams).
- **E2.3 — Continuous engine.** Watch spec/code/traffic/schema/UI/telemetry; surface divergence on change.
- **E2.4 — Source adapters.** Build out the source seam (OpenAPI/AsyncAPI/Postman already exist; add gRPC/GraphQL/traffic-capture).
- **E2.5 — "Verify an AI-generated suite" wedge.** Productize E0.2 into a one-command flow + the demo (below).

**Exit:** at least one agentic tool calls CHERENKOV via MCP in a real loop; engine runs continuously on a real project.

---

## Phase 3 — Rung 3: the Protocol / Authority (Certificate)
*Goal: a portable, signed, verifiable trust artifact others demand.*

- **E3.1 — Certificate format + signing.** Spec: [specs/CHERENKOV_CERTIFICATE.md](specs/CHERENKOV_CERTIFICATE.md). Cryptographically sound, tamper-evident.
- **E3.2 — `cherenkov certify` + public verify.** Issue a cert; anyone can verify offline + via a public endpoint.
- **E3.3 — CI gate + badge.** "Merge if verified"; a README badge with real meaning.
- **E3.4 — Open the spec.** Publish the cert spec so others can implement/verify — neutrality as moat.
- **E3.5 — Procurement/compliance mapping.** Map the cert to EU AI Act / ISO 26262 / SOC2 evidence needs.

**Exit:** one external party (CI gate, buyer, or marketplace) *requires* a CHERENKOV Certificate.

---

## Cross-cutting tracks (run alongside, gated by relevance)
- **T-Brand:** evolve positioning from conformance wedge to trust-layer ([brand-strategy], BRAND_STRATEGY.md §3). Hero/README/Figma reframe.
- **T-Demo:** "Catch the AI cheating" ([demos/CATCH_THE_AI_CHEATING.md](demos/CATCH_THE_AI_CHEATING.md)) — built in Phase 0/2, the public proof.
- **T-Honesty-debt:** Wave-2 items (#222-224/239) — never claim un-passed gates.
- **T-Corpus:** start (privately, locally) capturing divergence/cheat patterns for the long-term data moat.

---

## What to file in GitHub (when authorized)
One EPIC per phase (G0, Rung-1, Rung-2, Rung-3) + the cross-cutting tracks, each with the E-tickets above as children. Mirror into memory per the wave-roadmap convention (EPIC #241 lineage). **Not yet filed — awaiting go-ahead.**
