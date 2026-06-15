# CHERENKOV — Critique, Premortem & Execution Plan

> **Status:** Execution source of truth. Pairs with [BRAND_STRATEGY.md](BRAND_STRATEGY.md) (the *why/what*) — this is the *how/when/what-could-kill-it*.
> **Author:** working plan for Moayed Badawy · **Date:** 2026-06-16
> **One line:** The brand is ready. The *proof* is not. Do not launch the brand until the demo is externally reproduced. Everything below is sequenced around that.

---

## 1. Honest critique (what's strong, what's fragile)

### Strong
- **Real, working core.** Track A is built — 258 tests passing, 6-gate review, eject, conformance run. This is not vaporware.
- **Authentic founder–product fit.** A QA lead with fintech/telecom/UK API-testing experience building an API conformance tool is a credible, unfakeable story.
- **Coherent brand.** One master brand, sharp message hierarchy, ownable name/metaphor, distinctive identity. The strategy and identity work is done and good.
- **Smart structural choices.** Open-core + Apache-2.0 + eject + local-first is a defensible, trust-building shape.

### Fragile (ranked by danger)
1. **The irreducible bet is unproven where it counts.** The "30 min → 5 real divergences on a system we don't own" claim — and the 5-QA validation gate — were **declared passed "per owner decision," not validated by external QA practitioners** (see [HANDOVER.md](HANDOVER.md)). The entire brand promise rests on a capability that has not been demonstrated on a third party's API in front of strangers. **This is the #1 risk. Branding ahead of proof is the classic way to burn launch credibility once.**
2. **Documentation integrity debt.** HANDOVER documents a *pattern of agents fabricating test matrices and reports* in this repo. Before anything public, every load-bearing claim (test counts, "production ready," benchmarks) must be re-verified by actually running it. A single debunked claim on Show HN ends the launch.
3. **Schemathesis problem (positioning).** Schemathesis already does deterministic OpenAPI conformance/property testing — **free, no LLM, no hallucination risk.** The brand does not yet answer *"why not just use Schemathesis?"* Until that answer is crisp and demonstrated, "AI-native conformance" reads as "a heavier, riskier Schemathesis."
4. **Time scarcity / solo founder with a full-time job.** OSS maintenance + content + services + commercial tier = three jobs. Default outcome of an over-scoped solo plan is stall. Ruthless sequencing is survival, not preference.
5. **Employer conflict-of-interest (legal).** Celfocus is a software-quality/testing consultancy. A competing QA *product and consulting service* built while employed there is a real moonlighting / IP-assignment / non-compete exposure. **Unaddressed, this can void the wealth path or create a dispute.** Must be checked before any paid services or public commercial framing.
6. **Monetization is harder than the doc implies.** OSS API-testing tools have a weak monetization track record (Schemathesis, Dredd, etc. never became large businesses). Devs expect free; the buyer is fragmented; the enterprises the sovereignty pitch attracts are also the hardest to serve solo (they want SOC2, contracts, support). Wealth via product is *possible but slow*; services is the realistic near-term engine.
7. **Scope sprawl.** Reality Engine, K8s, mobile, VLM, chat agent, desktop — most "in progress." Breadth with nothing finished to *shippable, demoable* quality is a launch liability, not an asset.
8. **Identity/asset loose ends.** Two names (Moaid Moatasem / Moayed Badawy), repo under old handle, `cherenkov-security.com` is an empty shell, `cherenkov.dev` unowned, no exported logo/favicon, services pricing is placeholder. None of this is "ready" to send to a stranger yet.

---

## 2. Premortem — it's June 2027 and CHERENKOV failed. Why?

| # | Failure mode | Leading indicator (watch for this) | Severity | Likelihood | Pre-mortem countermeasure |
|---|---|---|---|---|---|
| F1 | **Demo didn't hold up.** Couldn't reproduce "5 real divergences" on third-party APIs; Show HN verdict: "worse Schemathesis + hallucinating LLM." | The de-risk gate (§3) slips or quietly gets skipped. | Fatal | High | **Gate everything on §3. No public launch until 3 external APIs are reproduced + 3 real QA practitioners validate.** |
| F2 | **Ran out of time.** Got 2–3 hrs/week after the day job; momentum died post-burst. | Two weeks pass with no shipped artifact. | Fatal | High | Fixed weekly time budget; one phase at a time; phase gates; everything else is backlog. |
| F3 | **Employer dispute / IP claim.** Celfocus flagged the competing product/services. | Any paid service or "founder" framing goes public before contract review. | High | Medium | **Resolve §4.0 legal first.** Keep it OSS-and-portfolio until cleared; defer paid services. |
| F4 | **Polished the brand, not the product.** Spent the energy on logo/landing (fun, visible) while the boring P0 (frictionless install, reproducible demo, one case study) never got done. | More commits to brand/docs than to install-UX/proof. | Fatal | High | **Brand is now FROZEN.** Energy shifts to proof + distribution. This doc enforces it. |
| F5 | **No monetization.** Free CLI used a little; nobody upgraded; enterprise unservable solo; services didn't sell (no reach yet). | Stars rise, revenue zero, no design partners. | High | Medium | Lead wealth with *services to warm network*, not product MRR. Validate willingness-to-pay early with 1 paid audit. |
| F6 | **Findability/trust diluted.** Two names, two domains, repo under old handle; nobody could cite or find it. | Inbound references inconsistent. | Medium | High | Pick ONE name + ONE primary domain + rename repo/org early (cheap, unblocks everything). |
| F7 | **Integrity hit.** A fabricated benchmark/claim got debunked publicly. | Any public number not personally re-run. | High | Medium | Re-verify every load-bearing claim by running it; cut anything unverifiable. |
| F8 | **Scope sprawl ate the runway.** Chasing mobile/K8s/desktop instead of nailing the one wedge. | Work items span >1 track in a phase. | Medium | High | Single wedge (API conformance, local) until traction. Everything else = post-traction backlog. |

**Synthesis:** the top three killers are *unproven demo*, *time*, and *building brand instead of proof*. The plan below is built to defeat exactly those.

---

## 3. The master gate (do this BEFORE anything public)

> **Gate G0 — External Proof of the Irreducible Bet.** Nothing in Phase 2+ (public launch, services, content) starts until G0 passes. This is the single highest-leverage thing in the whole plan.

**Experiment:**
1. Pick **3 real, public, OSS API projects** with published OpenAPI specs and a runnable instance (e.g. a popular FastAPI/Express service you don't own).
2. Run CHERENKOV end-to-end, locally, on each. Record everything (asciinema + raw output).
3. **Success = on ≥2 of 3, CHERENKOV surfaces ≥1 genuine, reproducible spec↔implementation divergence** that you confirm by hand and that a maintainer would accept as a real issue. Bonus: open the PR/issue upstream.
4. **Head-to-head:** run **Schemathesis** on the same targets. Document precisely what CHERENKOV found that Schemathesis didn't (and vice-versa). This *is* your positioning.
5. **Human validation:** get **3 real QA practitioners** (not you, not friends-being-nice) to run the quickstart cold and report whether it delivered value. This is the *real* 5-QA gate the repo still owes.

**Pass criteria:** ≥2/3 APIs yield a real divergence **and** ≥3 practitioners complete the quickstart and rate it useful **and** you can articulate the Schemathesis differentiation in one honest sentence.

**Kill/pivot criteria:** if it can't beat or meaningfully complement Schemathesis on real APIs, **stop and pivot the positioning** (e.g. "AI test *authoring & maintenance* on top of deterministic conformance," or narrow to a niche) *before* spending reach. Better to learn this privately in 2 weeks than publicly at launch.

### ⚠️ Methodological caveat (read before picking targets)
**Auto-generated OpenAPI specs barely drift by construction.** Frameworks that *derive* the spec from the code (FastAPI, PostgREST, drf-spectacular, most Go `swag` setups) will show little spec↔impl divergence because the spec *is* the impl — running G0 against them will under-sell the tool and risk a false "it doesn't find anything" (premortem F1). **Drift lives where the spec is authored separately from the server** (spec-first projects, hand-maintained docs, or one shared spec with multiple independent implementations). Pick those.

### Recommended G0 targets (systems you don't own)
1. **RealWorld / Conduit API** — one community-authored OpenAPI spec with *many independent backend implementations* (Node, Go, Rust, etc.). Drift across impls is near-guaranteed and the spec is maintained separately → the ideal headline target and a clean Schemathesis head-to-head. Runnable via the reference Docker images.
2. **Gitea** — mature, self-hostable Git service; Docker-runnable in minutes; ships a Swagger/OpenAPI spec (`/swagger.v1.json`) maintained alongside (not purely generated from) the Go handlers → real-world, credible, large surface.
3. **A third spec-first OSS service you can run** — e.g. **Gotify** (notifications, OpenAPI + Docker) or **Kanboard**/**Miniflux**; pick one that runs locally and whose spec is hand-maintained.
4. **Positive control — Swagger Petstore (with an injected divergence).** Run Petstore, deliberately change the server to violate the spec (e.g. return 400 where spec says 422), and confirm CHERENKOV catches the *known* drift. This proves the detector works even if the wild targets happen to be clean — and makes the demo bulletproof.

> Source a 5th wildcard from APIs.guru if needed, but it must be **runnable locally** — never test against someone's production API.

---

## 4. Detailed plan (phased, gated, time-boxed for a solo founder with a day job)

> Assume a realistic **~8 focused hrs/week**. Durations are in *calendar weeks at that pace*. Do phases in order; do not parallelize across phases.

### Phase 0 — Unblock & de-risk (Weeks 1–3)  ·  *cost: low · leverage: highest*
**0.0 Legal/CoI check (do first, ~1 evening).** Read your Celfocus contract for moonlighting / IP-assignment / non-compete. If unclear, ask HR or a lawyer. Decide: OSS-only-for-now vs cleared-for-services. **Blocks all paid-services work.**
**0.1 Identity lockdown.** Pick ONE public name (recommend **Moayed Badawy**). Secure domains: **`cherenkov.dev` is already taken (registered)** — recommend **`cherenkov.io`** as primary (both available as of 2026-06-16: `cherenkov.io`, `cherenkov.sh`, `getcherenkov.com`, `cherenkov-engine.dev`), **`cherenkov.sh`** as a CLI alias, and keep **`cherenkov-security.com`** (already owned) as the enterprise/redirect. Reserve GitHub org `cherenkov`, npm name, PyPI name.
**0.2 Integrity sweep.** Re-run the test suite yourself; confirm the 258-passing claim. Grep docs for unverifiable benchmarks/"production ready"/version matrices; delete or caveat anything you can't reproduce. Add a one-line "claims policy: nothing stated unless reproduced."
**0.3 Run Gate G0 (§3).** This is the bulk of the phase.
**Exit gate:** G0 passed (or pivot decided) + legal cleared + one name/domain chosen.

### Phase 1 — Make it trivially runnable (Weeks 4–6)  ·  *the F4 antidote*
**1.1 Frictionless quickstart.** `npx cherenkov init` / one-command path that works on a clean machine in <5 min, including the Ollama/model bootstrap. Test on a fresh VM.
**1.2 Reproducible demo asset.** A scripted, recorded 2-min demo against one of the G0 APIs (asciinema + a short screen capture). This is the artifact every channel reuses.
**1.3 Honest README finish.** Complete the rebrand (remove residual "CHERENKOV QA"/MIT references, fix clone URLs after repo rename), add the Schemathesis-differentiation line from G0, link the demo. Keep claims to what G0 proved.
**1.4 Logo export.** Export the Figma mark to SVG/PNG + favicon; drop into README and repo `.github`.
**Exit gate:** a stranger can install and reproduce a real divergence in <10 min following only the README.

### Phase 2 — Distribution & credibility (Weeks 7–12)  ·  *career-capital engine*
**2.1 Divergence Challenge #1.** Write up the best G0 finding (the upstream PR/issue + the head-to-head vs Schemathesis). Honest, technical, no hype. Publish on a blog + dev.to + LinkedIn (as Moayed Badawy).
**2.2 Landing page.** Apply the brand identity to a one-page site at the chosen domain (reuse `docs/landing/index.html`; match the Figma hero). CTA = GitHub + quickstart.
**2.3 Show HN / Product Hunt.** Only after 1.x is solid and 2.1 is published. Use the existing `docs/marketing/product_hunt_kit.md`. Be present to answer the Schemathesis question with evidence.
**2.4 GitHub Actions.** Publish the CI action so teams can adopt in-pipeline.
**Exit gate:** real inbound (issues/stars from strangers), ≥1 external person ran it unprompted, ≥1 published write-up with traction.

### Phase 3 — Monetization validation (Weeks 13–20)  ·  *only if §4.0 cleared*
**3.1 Services soft-launch.** Finalize [SERVICES.md](SERVICES.md) (real pricing), offer **one paid Conformance Audit** to a warm contact from your network. Goal: prove willingness-to-pay, not scale.
**3.2 Design-partner #1.** Convert an audit or an engaged OSS user into a design partner for the Team tier; learn what they'd actually pay for.
**3.3 Define the paid/free line concretely** based on partner feedback (not the doc's guess). Scope the smallest Team-tier feature that someone would pay for (likely hosted history + CI orchestration).
**Exit gate:** one paid engagement *or* one committed design partner. If neither after honest effort → revisit the wealth thesis (lifestyle-OSS + employment may be the right answer; that's a fine outcome, decided on data).

### Phase 4 — Decide the shape (Week 20+)
From a position of traction + revenue signal, choose: lifestyle open-core + services · bootstrap a product · or raise. **Do not pick this now** — earn the right to pick it.

> **Parked until post-traction (do NOT touch sooner):** mobile, K8s operator polish, desktop app, VLM/visual, chat agent, the full "Reality Engine" surface. They're real, but they are scope risk (F8) until the wedge has pull.

---

## 5. What's needed — readiness checklist

**Decisions (yours, this week)**
- [ ] One public name (rec: Moayed Badawy) — used everywhere
- [ ] Primary domain (rec: buy `cherenkov.io` — `cherenkov.dev` is taken; optional `cherenkov.sh` CLI alias; `cherenkov-security.com` → enterprise/redirect)
- [ ] Go/no-go on paid services pending §4.0 legal check

**Accounts/assets to secure**
- [ ] Domain(s); GitHub org `cherenkov`; npm + PyPI names; rename repo from `moaidmoatasem/cherenkov-qa`
- [ ] Logo SVG/PNG + favicon exported from Figma (note: your Figma seat is "View" — may need an editor seat to export/edit)
- [ ] asciinema account; a blog/dev.to; LinkedIn set to founder/maintainer framing

**Proof (the gate)**
- [ ] 3 target public APIs chosen
- [ ] G0 run + recorded; ≥2/3 real divergences; Schemathesis head-to-head documented
- [ ] 3 external QA practitioners validated the quickstart

**Product readiness**
- [ ] `<5 min` clean-machine install verified on a fresh VM
- [ ] README rebrand finished; residual "CHERENKOV QA"/MIT/old-URL references removed
- [ ] Every public claim personally reproduced; unverifiable claims cut

**Legal/integrity**
- [ ] Celfocus contract reviewed (moonlighting/IP/non-compete)
- [ ] Claims policy added; fabricated-doc debt swept

---

## 6. Risk register (top 8, live)

| Risk | Owner action | Trigger to act |
|---|---|---|
| Demo unproven (F1) | Gate G0 before launch | now |
| Time stall (F2) | 8 hrs/wk, one phase at a time | weekly review |
| Employer CoI (F3) | §4.0 legal check | before services |
| Brand-over-proof (F4) | brand frozen; proof-first | enforced by this doc |
| Schemathesis (F5/pos.) | head-to-head in G0; honest diff line | in G0 |
| Findability (F6) | one name/domain/org | Phase 0 |
| Integrity (F7) | reproduce or cut every claim | Phase 0 |
| Scope sprawl (F8) | park everything off-wedge | ongoing |

---

## 7. Definitions

**Definition of Ready (to launch publicly):** G0 passed · install <10 min for a stranger · README honest & rebranded · one divergence write-up live · name/domain consistent · no unverifiable public claims · legal clear (for any commercial framing).

**Definition of Done (a phase):** its exit gate is met and recorded. No phase is "mostly done."

**Definition of Success (12 mo):** a tool real strangers run and cite + a globally legible founder/maintainer brand for Moayed Badawy + at least one validated revenue signal (paid audit or committed design partner) — *or* a data-driven decision that lifestyle-OSS-plus-employment is the right call.
