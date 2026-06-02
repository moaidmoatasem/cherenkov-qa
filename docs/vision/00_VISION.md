# CHERENKOV — The Reality Engine

**Status:** North-star vision · **Supersedes framing of:** `docs/TECHNICAL_DEVELOPMENT_PLAN.md` (now the *foundation layer*, not the whole product)
**Audience:** maintainers, contributors, and autonomous dev agents picking up issues.

---

## 1. The one-sentence pitch

> **CHERENKOV continuously maintains the *truth* about a software system — by ingesting every source of truth it has (spec, code, traffic, schema, UI, logs), detecting where those sources *disagree with each other*, proving each disagreement by reproduction, and emitting the artifact (a test, a patch, a report) that closes the gap.**

It is **model-agnostic** (bring any intelligence — tiny local model, self-hosted 32B, or a frontier API), **open at four seams** (sources, models, artifacts, oracles), and **easy by default** (`cherenkov init` → useful in minutes) while **deeply configurable on top**.

---

## 2. Why the old framing was too small

The original plan ships a competent **OpenAPI → Playwright generator** that runs locally on a fixed model pair (`deepseek-r1:8b` + `qwen2.5-coder:7b`) on one GPU. That is real and useful — but it is:

- **A crowded category.** Postman, Schemathesis, RestlerFuzzer, Hercules, and a dozen GPT wrappers occupy adjacent ground.
- **Pinned to a 2026 model snapshot.** Hardcoding the model makes the product obsolete at the next model release instead of stronger.
- **Stuck in the "produce artifacts" frame.** Every competitor answers *"given an artifact, produce tests."* That framing is the ceiling.

## 3. The reframe

The real, unsolved problem in software quality is **desynchronization**:

> Specs lie. Tests pass while users rage. The OpenAPI doc says one thing, the code does another, the database enforces a third, the frontend assumes a fourth, and the customer sees a fifth.

Nobody owns the tool that **measures and closes that gap**. CHERENKOV does. Tests become *one of many artifacts* it emits — the deliverable is **truth**, not test count.

| | Old frame (test generator) | New frame (Reality Engine) |
|---|---|---|
| Deliverable | A pile of generated tests | Evidence that sources of truth agree (or don't) |
| Success metric | "Generated 200 tests" | "Found 5 real, reproduced divergences humans missed" |
| Intelligence | Hardcoded model pair | Swappable substrate; any model, any deployment |
| Moat | "It's local" (erasable) | Accumulated, per-system truth that compounds over time |
| Category | #3 in a crowded space | A new category |

## 4. The model is a dependency, not the product

The single most important architectural commitment:

> **All product value lives *above* the intelligence layer. The model is rented through a routing substrate, decided per-call, configurable per-org.**

This is what OpenAI/Anthropic structurally *cannot* commoditize away — being model-agnostic is opposed to a model vendor's interest. CHERENKOV becomes Switzerland: a 3B local model, GPT-5, a Claude in a customer's VPC, or a model that doesn't exist yet all plug into the same harness.

## 5. The four open seams

Everything proprietary is the **reasoning harness in the middle**. Four edges are open plugin interfaces:

1. **Sources** — what truth flows in (OpenAPI, gRPC, GraphQL, traffic, OTel, DB schema, code, …).
2. **Models** — what intelligence reasons (Ollama, vLLM, OpenAI, Anthropic, …) via the Substrate Router.
3. **Artifacts** — what flows out (Playwright, k6, pytest, spec patch, PR comment, webhook, …).
4. **Oracles** — what counts as *correct* (the spec, prod behavior, a golden snapshot, a human, a sibling service).

## 6. The irreducible bet

Everything else is earned expansion. The core that proves the company is the **Divergence Loop**:

> Point CHERENKOV at a real system (its spec + real traffic). Within 30 minutes it surfaces **5 real, reproducible "your system is lying to itself" findings** that humans missed.

If that works on a project we don't own (e.g. a mid-size OSS service), we have a category. If it doesn't, we learned it in weeks, not years. See [`02_ROADMAP.md`](02_ROADMAP.md) Epoch 3.

## 7. The compounding moat

Each customer's CHERENKOV learns *their* system's idioms, divergence patterns, and domain semantics. After months of use it *knows their API* in a way no stateless competitor can match — and (opt-in, anonymized) the cross-customer **divergence corpus** becomes a dataset, a research contribution, and training data for a model better at this than any generalist LLM. Local-first means that data never has to leave the customer's machine.

## 8. What survives from the original plan

Nothing is thrown away — it is **inverted**. The generator was going to be the whole building; now it is the lobby. See the layer map in [`01_ARCHITECTURE.md`](01_ARCHITECTURE.md) and the migration in [`02_ROADMAP.md`](02_ROADMAP.md).

---

### Related documents
- [`01_ARCHITECTURE.md`](01_ARCHITECTURE.md) — diagrams: layers, agents, substrate, loops, seams.
- [`02_ROADMAP.md`](02_ROADMAP.md) — epochs, milestones, and how Track A maps in.
- [`03_CONFIGURATION.md`](03_CONFIGURATION.md) — easy-by-default + the full config surface.
- [`04_AGENT_WORKBOOK.md`](04_AGENT_WORKBOOK.md) — how dev agents pick up and ship issues.
