# CHERENKOV — Brand, Strategy & Go-to-Market

> **Status:** Canonical brand + strategy source of truth · **Owner:** Moaid Moatasem
> **Decisions locked (2026-06-16):** One master brand · Open-core (career capital **and** wealth) · Apache-2.0 core
> Supersedes the branding fragments in `PRODUCT_STRATEGY_ROADMAP.md`, `docs/vision/00_VISION.md` (now the *vision layer* only), and the `cherenkov-security.com` "Sovereign AI Security" shell (to be folded in).

---

## 0. TL;DR

CHERENKOV is **one** brand with a **three-layer message**:

1. **Sell today (the wedge):** *Local-first AI that finds where your API and its spec disagree — and proves it.*
2. **Why it wins (the moat):** model-agnostic · zero lock-in (eject) · nothing leaves your machine.
3. **Where it's going (the vision):** **the Reality Engine** — continuous truth across every source (spec, code, traffic, schema, UI).

Business model: **open-core**. Apache-2.0 CLI = distribution + career capital. Commercial tier (cloud/CI orchestration, K8s operator, RBAC/audit, the divergence corpus) = wealth. `cherenkov-security.com` is retired as a separate brand; "sovereign/local-first" becomes CHERENKOV's **trust pillar**, not a separate company.

---

## 1. Why we had a branding problem

Three identities were competing for the same scarce founder attention:

| Identity | What it claimed | Problem |
|---|---|---|
| **CHERENKOV QA** | OpenAPI → Playwright conformance tool | Real & shippable, but framed as "#3 in a crowded category." |
| **Reality Engine** (`00_VISION.md`) | Model-agnostic truth/divergence engine | Brilliant vision, but too abstract to *sell* or *get hired on* today. |
| **cherenkov-security.com** | "Sovereign AI Security" | A tagline with no product behind it; overclaims (the product tests conformance, not security). |

A solo founder cannot run three brands and two GTMs. The fix is **one master brand with a layered narrative** — lead with the provable wedge, let the vision pull.

---

## 2. The name (keep it — it's an asset)

**CHERENKOV** stays. Cherenkov radiation is the faint blue glow emitted when a particle travels *faster than light through a medium* — **the visible evidence of something moving where it shouldn't.** That is *exactly* the product: making invisible divergence visible, and proving it. The metaphor is ownable, technical, and credible to the developer audience. Blue glow → visual identity (§7).

Wordmark: **CHERENKOV** (all caps). Product descriptor: **"the conformance engine"** today, **"the Reality Engine"** as the vision matures.

---

## 3. Positioning

**Category (own this phrase):** *AI-native API conformance & drift detection — local-first.*

**Positioning statement:**
> For backend and platform engineers who ship API-first software, **CHERENKOV** is the local-first AI tool that **finds where your running service and its spec disagree — and proves each gap with a reproducible test.** Unlike Postman, Schemathesis, or GPT-wrapper test generators, CHERENKOV needs no cloud, no API keys, and no lock-in: your code never leaves your machine, and you can eject to vanilla Playwright at any time.

**Three message layers (use everywhere — site, README, deck, talks):**

| Layer | Line | Where it leads |
|---|---|---|
| **What** | "Catch where your software lies — before your users do." | Homepage H1, README hero |
| **Why** | "Model-agnostic. Zero lock-in. Nothing leaves your machine." | Feature trio, trust section |
| **Where** | "Building the Reality Engine — continuous truth across every source of truth." | Manifesto, vision page, investor/recruiter narrative |

**What we are NOT (anti-positioning):** not a SaaS-only cloud tool; not a generic "AI writes your tests" wrapper; not a security scanner (yet — that's an earned expansion, not the headline).

---

## 4. The "sovereign / security" question — resolved

The instinct behind `cherenkov-security.com` was right; the framing was premature. **Local-first IS a security and data-sovereignty property** — your specs, code, and traffic never touch a third party. So:

- **Retire** "Sovereign AI Security" as a standalone brand. Redirect `cherenkov-security.com` → main site (or use it as the enterprise/landing domain).
- **Promote** sovereignty to CHERENKOV's **trust pillar**: *"Air-gapped by default. Your IP stays yours."* This is the wedge into regulated/enterprise buyers later.
- **Sequence** an actual security product (conformance → contract security → DAST) as a roadmap *expansion*, only once the conformance wedge has traction. Don't claim it before it ships.

---

## 5. Business model — open-core (decided)

**Why open-core is strictly dominant for your goals (career capital + wealth):**

- A widely-adopted **OSS tool is the single highest-leverage career asset** for an engineer outside the US hiring network. It's globally legible proof of staff-level skill → remote senior/staff offers, conference talks, inbound. This is the **career engine**.
- The **commercial layer** (orchestration, hosted intelligence, compliance) is where enterprises pay. Local-first/privacy is exactly what they pay *for*. This is the **wealth engine**.
- This is the proven **GitLab / Sentry / n8n** pattern. The `eject` feature is a genuine adoption masterstroke — it removes lock-in fear; enterprise value lives in what ejected tests *can't* replicate (CI orchestration, the cross-customer divergence corpus, RBAC/audit, the dashboard).

**License:** **Apache-2.0** for the core (switch from MIT) — explicit patent grant + enterprise-trusted, still permissive. Keep the option to put the **orchestration/cloud layer under BSL** later (Sentry/HashiCorp style) so a hyperscaler can't resell your managed product.

### The line between free and paid

| Tier | What's in it | Who | Price |
|---|---|---|---|
| **Core (Apache-2.0, free)** | CLI, OpenAPI→Playwright generator, 6-gate review, local LLM routing, conformance run, **eject**, single-repo use | Individual devs, OSS | $0 |
| **Team (commercial)** | Hosted dashboard, CI/GitHub Action orchestration, history/trends, multi-repo, Slack/PR reporting | 50–500-eng companies | per-seat / per-repo |
| **Enterprise (commercial)** | K8s operator + `ConformanceCheck` CRD, RBAC, audit trails, SSO, air-gapped support, the cross-customer divergence corpus, SLAs | 500+ eng, regulated | annual contract |

---

## 6. Go-to-market

**Motion:** bottom-up, developer-led. OSS tool = top of funnel → Team → Enterprise (land-and-expand on local-first/compliance).

**The signature growth loop — the "30-Minute Divergence Challenge":**
1. Point CHERENKOV at a popular OSS API (its spec + a live instance).
2. It surfaces *real, reproducible* "your system is lying to itself" findings.
3. Each finding → (a) a write-up/blog, (b) a PR to a famous repo, (c) a backlink + credibility.
4. This **doubles as your career proof** — every divergence found in a known project is a public artifact of staff-level skill.

**Channels & sequence (P0 → P1):**
- **P0:** Landing page (`cherenkov.io` — note `cherenkov.dev` is taken), 2-min demo video, `npx cherenkov init` frictionless quickstart, GitHub Actions in marketplace, docs site. (Most already scoped in `PRODUCT_STRATEGY_ROADMAP.md §2.3`.)
- **P0 content:** Show HN + Product Hunt (kit exists at `docs/marketing/product_hunt_kit.md`) + 3 divergence-challenge write-ups.
- **P1:** VS Code extension, hosted no-install demo, dev.to/blog cadence, the divergence corpus as recurring content.

**Metrics that matter:** GitHub stars → installs → activated runs (found ≥1 real divergence) → Team conversions. Vanity metric to ignore: "tests generated." North-star: **real divergences found & reproduced.**

---

## 7. Visual identity

**Concept:** the Cherenkov glow — evidence emerging from the dark. High-contrast, technical, trustworthy.

**Color (the "Cherenkov blue" story):**

| Token | Hex | Use |
|---|---|---|
| `--void` | `#0A0E1A` | Background (near-black, deep cobalt undertone) |
| `--cherenkov` | `#22D3EE` | Primary — the glow (cyan) |
| `--cherenkov-deep` | `#2563EB` | Secondary cobalt, gradients |
| `--pass` | `#22C55E` | Pass states |
| `--drift` | `#F59E0B` | Drift / warning |
| `--fail` | `#EF4444` | Fail / divergence |
| `--ink` | `#E5E9F0` | Primary text on void |
| `--muted` | `#7C89A3` | Secondary text |

Gradient signature: `--cherenkov-deep → --cherenkov` (cobalt-to-cyan glow).

**Logo:** a Cherenkov radiation cone / particle-trail mark — a sharp glyph emitting a blue cone, doubling as a "C" and a beam of light revealing what's hidden. Pairs with the **CHERENKOV** wordmark.

**Type:** geometric/grotesk for wordmark & headings (e.g. Space Grotesk / Geist), monospace for product/code (e.g. JetBrains Mono / Geist Mono).

**Voice:** precise, confident, evidence-driven. Short declaratives. No hype words ("revolutionary"). Show the failing test, not adjectives. The README's existing tone ("nobody wrote that test, CHERENKOV found it") is the target voice — keep it.

**Shift from current:** README leads with ⚡ + green MIT badges. Move to the **blue glow** identity (more ownable, bridges the trust/sovereign feel) and Apache-2.0.

---

## 8. Career & wealth alignment (your profile)

**Founder:** Moayed Badawy — **QA Lead** (currently Celfocus; prev. Lead/Senior QA at Nomo Fintech [London], Capiter, Eventtus, Eye ADV). 8 years, test engineer → QA Lead. ISTQB CTFL + ICAgile. BSc Computer Science (El Shorouk Academy). Built & led a 13-person QA team; cut manual testing 40% via Selenium/Java/JMeter/Appium; **API testing (Postman, REST) is a through-line across every role.**

This profile makes CHERENKOV unusually authentic — and it shifts the strategy in four concrete ways:

1. **You are the buyer you're selling to.** You're not an IC dev who'd *use* a CLI — you're a QA *Lead* who sets automation strategy, builds QMS, and reports quality to stakeholders. So CHERENKOV's voice should speak to **QA leads / SDETs / heads of quality** (the economic buyer) as much as to developers. Your credibility line: *"I led QA automation at fintech and telecom — CHERENKOV is the tool I wished existed."*

2. **API conformance is literally your career, productized.** Postman at Eye ADV → REST APIs at Capiter → automation strategy at Nomo. You have unimpeachable authority to define the "AI-native API conformance" category. Lead with that lived expertise in every write-up and talk.

3. **The local-first / sovereign trust pillar is validated by your résumé.** Fintech (Nomo, regulated) + telecom consultancy (Celfocus/Vodafone-sphere) + UK delivery = you've lived *why* regulated buyers reject SaaS and demand air-gapped tooling. That's not a marketing guess; it's your buyer context. Sell it from experience.

4. **Your leadership profile unlocks a faster wealth path than pure product.** You've recruited and led teams and sold quality strategy to stakeholders — so an **open-core + expert-services wedge** is viable *now*: offer "QA automation strategy / AI-in-testing" consulting under the CHERENKOV brand while the OSS builds adoption. Services fund the runway and generate design-partner accounts that convert to the Team/Enterprise tier. This de-risks wealth vs. waiting on product MRR alone.

**Plays:**
- **Career:** be the visible maintainer (commits, talks, divergence write-ups under *Moayed Badawy*). Target (12 mo): a tool with real adoption that makes you a globally legible "Head of Quality Engineering / founder," not a regional QA Lead.
- **Wealth:** open-core gives optionality — services revenue now → Team-tier MRR → fundable startup or acquihire. Apache-2.0 + future-BSL keeps every door open.
- **Sequencing:** ship the wedge → publish Divergence Challenges (your expertise on display) → land 2–3 services/design-partner accounts → introduce Team tier once you have weekly-active installs → decide raise-vs-bootstrap from traction.

> **Name note:** professional brand name is **Moayed Badawy** (GitHub/handle `MoayedBadawy`); the repo currently lives under `moaidmoatasem`. Pick one public identity and use it consistently across GitHub org, site, and talks.

---

## 9. Immediate next actions

- [ ] Adopt this doc as canonical; demote `00_VISION.md` to "vision layer."
- [ ] Relicense core MIT → Apache-2.0; update README badges + hero to the blue identity & three-layer message.
- [ ] Decide `cherenkov.dev` (primary) vs `cherenkov-security.com` (enterprise/redirect).
- [ ] Build the visual identity in Figma (see `docs/brand/` once generated).
- [ ] Ship P0 GTM list (§6).
- [ ] First "30-Minute Divergence Challenge" write-up.
