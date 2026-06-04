# CHERENKOV — Horizon 2: Adoption, Voice & Prove-in-the-Wild

**Status:** Active plan of record · **Date:** 2026-06-04 · **EPIC:** #147
**Predecessor:** [`08_DELIVERY_PLAN.md`](08_DELIVERY_PLAN.md) (delivered — E0–E13 shipped, 5-QA gate passed)

---

## Where we are

We built the whole thing. E0–E13 shipped, the base is green, and the Validation
Gate passed — 4 of 5 real QA professionals said they'd use it (`QA_DEMO_KIT.md`).
The irreducible bet is proven: CHERENKOV found and reproduced **5 real
divergences in live Swagger Petstore v3** (`docs/proof_run/PROOF_RUN.md`).

That means the original plan is *done*, not abandoned. Horizon 2 is the next
honest question: **does a real team actually reach for this every day?** Three
bets get us there.

---

## Bet 1 — Prove it in the wild

Petstore is the reference spec; everyone half-expects it to be wrong. The
convincing story is pointing CHERENKOV at an API a team genuinely depends on and
showing what it finds.

- **#148 (N1)** — reproduce divergences on 2–3 real production APIs (GitHub REST,
  Stripe test mode, PokéAPI, or an internal staging service). Same shape as
  `PROOF_RUN.md`, every finding reproducible with a single `curl`. Zero
  divergences on a target is also a finding — document it honestly.

## Bet 2 — Finish the voice

OpenClaw Tier-1 (notify + trigger) shipped in `cherenkov/openclaw/`. The part
that made people lean in — approving review items from chat, async, on a phone —
is still ahead. The gate is passed, so the block is lifted.

- **#149 (N2)** — approve/reject HITL items from chat over `hitl/v1`, reusing the
  atomic concurrency model in `hitl/store.py`. Honest conflict UX (render from
  `current_status`, don't assume "approved"). Identity map enforced.
- **#150 (N3)** — healing/contract-drift notifications + a `classify` command and
  the CQRS feedback loop (append-only log → recomputed thresholds, Laplace
  confidence, suggest at ≥0.70 & ≥3). **D7 stays sacred: suggest-only.**
- **#151 (N4)** — read-only **Explain 🤖** triage streamed from the local model
  via the substrate router, injection-hardened, always `[AI 🤖]`-labelled, never
  recommends a decision.

## Bet 3 — Make it boring

A tool you trust runs unattended and doesn't cry wolf.

- **#152 (N5)** — federation: take `cross_check.py` from scaffolding to a working
  two-node corpus sync that respects the `egress` dial.
- **#153 (N6)** — capture the gate pass into `.cherenkov/evidence/` via
  `collect_evidence.py` so "it passed" is something you can open, not just prose.
- **#154 (N7)** — point the continuity daemon at a real spec and let it run
  nightly for a week; log signal vs noise; file the papercuts.
- **#155 (N8)** — one honest reconciliation of the three roadmap framings
  (epochs / delivery plan / HANDLER §6.3 build-over) so a cold reader knows
  what's done and what's next.

---

## Suggested order

Both **#148** and **#155** are `agent-ready` and stand alone — good starts.
**#149** is the headline; **#150 → #151** build on it. **#153** is quick and
closes our own evidence loop. **#154** and **#148** want a real target API
lined up, so secure a staging service early.

## Carried-over rules

Everything layers **on top of** validated Track A and goes through the existing
seams (`hitl/v1`, substrate tiers, `ReasoningRequest`). No core forks. No model
names in stages. Suggest-only healing (D7). Eject stays clean. And per
`AGENTS.md`: **raw evidence, never claims.**

---

## Still-open cross-cutting (gate era)

`X1` prune stale branches (#130) · `X2` branch-protection on `main` (#131) ·
`X3` CI runners for env-dependent smokes (#132) · `X4` MCP server, post-E9 (#133).
Do **X2 before** any multi-agent fan-out so `main` stays green by construction.
