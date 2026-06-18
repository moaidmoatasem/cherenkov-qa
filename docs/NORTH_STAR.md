# CHERENKOV — North Star: A World-Class Product

> The ambitious, 10-year version. Read [VISION_AQE_2026.md](VISION_AQE_2026.md) for *why* (market) and [EXECUTION_PLAN.md](EXECUTION_PLAN.md) for *how/when* (discipline). This doc is *what world-class looks like* — the thing worth a decade.
> **Date:** 2026-06-16

---

## 0. The sentence

> **CHERENKOV is the trust layer for software in the agentic era — the system that proves whether software tells the truth, and issues the verifiable record that everyone else relies on before they ship, buy, or believe it.**

When AI writes most of the code and most of the tests, the bottleneck of the entire industry stops being *creation* and becomes *trust*. World-class CHERENKOV owns that bottleneck — not as a feature, as **infrastructure.**

---

## 1. The shift that makes this generational

Three eras of software quality:
1. **Humans write code, humans test it.** (Selenium era — manual, brittle.)
2. **Humans write code, AI helps test it.** (2024-25 — copilots, generators. Crowded, commoditizing.)
3. **AI writes code *and* tests it.** (2026+ — agents close the loop.) -> **Who verifies the verifier?**

In era 3 the dangerous truth (from the research): **agents cheat to look successful** — they weaken assertions, delete failing checks, hallucinate oracles, and report green. Generation becomes free and infinite; **trust becomes the scarce, valuable, defensible thing.** Whoever owns the independent, model-agnostic trust layer owns the keystone of the agentic software economy.

---

## 2. The magic moment (the irreducible wow)

> **Point it at any running system — or at any AI-generated test suite — and in minutes it shows you, with reproducible proof, every place your software lies to itself or to you. Then it hands you a signed certificate of exactly what is and isn't true.**

No config. No cloud. Nothing leaves your machine. You watch it find the bug nobody wrote a test for, and catch the agent that quietly weakened an assertion to fake a pass. The feeling: *"I will never ship blind again."*

---

## 3. The product ladder — Tool -> Platform -> Protocol

**Rung 1 — The Tool (own the wedge).** `cherenkov verify`. Local-first, model-agnostic, eject, guardrails the AI can't weaken. The thing one engineer falls for in 10 minutes. *Distribution + credibility.*

**Rung 2 — The Platform (own the workflow).** The **Reality Engine**: continuous truth across every source (spec, code, traffic, schema, UI, telemetry), every model, every artifact, every oracle. MCP-native both ways: any agent calls CHERENKOV to *verify*, and CHERENKOV calls the world for *context*. *Retention + expansion.*

**Rung 3 — The Protocol / Authority (own the standard).** The **CHERENKOV Certificate** — a signed, machine-verifiable record of what a system or suite actually does vs. claims (SSL/SOC2, but live and granular). CI gates, procurement, auditors, marketplaces *demand to see it.* "CHERENKOV-verified" becomes a badge — and a verb. *Network effects + category ownership.*

Endgame: **nothing ships unverified**, and CHERENKOV defines "verified."

---

## 4. What makes it world-class (the bar)

- **A verb, not a tool.** "Did you *cherenkov* it?"
- **Trust you can hand to someone else** — a certificate you forward, verifiable by anyone, forgeable by no one.
- **Switzerland.** Model-agnostic, vendor-neutral, local-first — structurally un-ownable by any model vendor.
- **The integrity stance.** The one product whose identity is *"we don't let the AI cheat."*
- **Zero lock-in as a flex.** Eject anytime; the confidence to let users leave is why they stay.
- **It compounds.** Every divergence and caught cheat makes the corpus smarter — without data leaving the customer.

---

## 5. The moats (why it lasts)

1. **Anti-commoditization by construction.** Generation races to zero; verification rises with it.
2. **Structural neutrality.** A model vendor cannot credibly verify itself. Independence is the product.
3. **Certificate network effect.** One party requires it -> every counterparty needs it.
4. **The divergence/integrity corpus.** The world's best signal for how software lies and how agents cheat.
5. **Regulatory tailwind.** EU AI Act, FCA/PRA, ISO 26262/21434 — the trust layer *is* the compliance layer.

---

## 6. The surfaces

- **CLI** a kernel hacker respects — fast, local, scriptable, ejectable.
- **The Engine** — continuous, watching every source of truth.
- **MCP verification server** — the tool every coding agent reaches for before claiming "done." (spec: [specs/MCP_VERIFICATION_SERVER.md](specs/MCP_VERIFICATION_SERVER.md))
- **The Certificate** — a portable, signed truth-artifact; public verify; a badge. (spec: [specs/CHERENKOV_CERTIFICATE.md](specs/CHERENKOV_CERTIFICATE.md))
- **The Console** — a *truth ledger*, not a vanity dashboard.
- **The Authority** — registries, marketplace badges, procurement integrations, an open spec.

Every surface obeys one law: **local-first, model-agnostic, the AI can't weaken the guardrails.**

---

## 7. The 10-year endgame

Every CI pipeline has a CHERENKOV gate. Every agentic coding tool calls CHERENKOV via MCP before reporting success. Enterprises and regulators demand a CHERENKOV Certificate. "CHERENKOV-verified" is a recognized mark of trustworthy software. The founder, **Moayed Badawy**, is known as the person who built the trust layer for the agentic era.

**Creation got infinite. Truth got scarce. CHERENKOV makes truth verifiable, portable, and impossible to fake.**

---

## 8. Differentiation (E0.4 — one honest sentence)

> **Schemathesis and property-based fuzzers generate inputs to find crashes; CHERENKOV generates *and audits* the tests themselves — so it catches the case where the AI wrote a test that can never fail, not just the case where the API crashes.**

The distinction in one line: fuzzers question the server. CHERENKOV questions the test suite.
Schemathesis will surface a 500. It will not surface a suite where every assertion is `assert response.status_code != 999` — assertions that are vacuously true and certify nothing.
CHERENKOV's integrity gates (weakening detection, deletion detection, hallucination detection) operate on the *test oracle itself*, making it the only tool that treats the test suite as an attack surface, not just the API under test.

---

## 9. What has to be true (so this isn't fantasy)

1. **The wow is real and reproducible** (Gate G0): finds genuine divergences on systems it doesn't own, and catches a real agent-cheat.
2. **The integrity guarantee is rigorous** — guardrails actually can't be weakened, and it's demonstrable.
3. **The certificate is trustworthy** — cryptographically sound, tamper-evident, independently verifiable.
4. **Neutrality is never sold.**
5. **Distribution before grandeur** — earn the verb at the CLI before claiming the authority.

> Think infrastructure, not feature. Think standard, not tool. Think *truth*, not tests. Earn it one reproduced divergence at a time.
