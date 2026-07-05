# CHERENKOV — Strategic & Technical Review

> **Date:** 2026-07-05 · **Scope:** business positioning, market check, technical implementation, AI-era fit, recommended route.
> **Method:** full codebase survey (verified by reading code, file:line refs throughout), repo strategy docs (`NORTH_STAR.md`, `VISION_AQE_2026.md`, `EXECUTION_PLAN.md`), internal QA reports (`PROJECT_REVIEW.md`, `usability_report.md`, `5_QA_REPORT.md`), and a fresh external market check (July 2026, sources at the bottom).
> **Claims policy:** every technical claim below was verified against the code this session; every market claim carries a source.

---

## 1. Verdict summary

| Question | Answer |
|---|---|
| **Should we proceed?** | **Yes, conditionally.** The core engine is real, the moat thesis is sound, and Gate G0 is 3/4. The condition: stop building surfaces, fix one critical product gap (§5.1), and ship distribution. |
| **Is it unique?** | **Partially — and the unique half is under-sold.** Spec↔implementation drift detection (`verify`) is now a crowded, commoditizing space. Test-suite **integrity auditing** (`check-suite`: weakened / deleted / hallucinated assertion detection) still has **no visible direct competitor** as of July 2026. |
| **Do we need to make it different?** | Not different — **re-led.** The differentiated capability is already shipped. It needs to become the headline instead of the footnote. |
| **What should the tool be used for?** | A CI gate + MCP tool that (a) audits AI-generated test suites for integrity violations and (b) proves API↔spec conformance with reproducible HTTP evidence, issuing a signed certificate. |
| **What development is needed?** | One P0 (spec-derived probes, §5.1), a positioning fix (§4), and distribution (§6). Not more features. |

---

## 2. Market check — what changed since the June strategy docs

The June 2026 strategy docs (`VISION_AQE_2026.md`) made two bets. A fresh check shows one has eroded and one has strengthened:

**Bet 1 — conformance/drift as the wedge: ERODED.** The spec↔reality drift space has filled in fast. PactFlow ships "Drift" (deterministic spec-vs-implementation conformance checks); FlareCanary polls live endpoints against spec or learned baseline with severity-classified drift; Speakeasy publishes drift-detection tooling and content; Schemathesis remains the free, deterministic, academically-benchmarked default (1.4x–4.5x more defects found than other fuzzers in published comparisons). "AI-first shift-left" platforms now market self-healing on schema drift as table stakes. A tool whose headline is "catches spec drift" enters a melee, exactly as `VISION_AQE_2026.md` §2 warned about generation.

**Bet 2 — test-suite integrity as the moat: HOLDING.** Searches for tools that audit AI-generated test suites for assertion weakening, test deletion, or hallucinated oracles return **nothing comparable** — the term "assertion weakening" surfaces academic work and hiring-assessment products, not developer tooling. The research-backed problem (agents cheat to look successful; ~88% of devs distrust AI-generated code) is getting *worse* as agentic coding scales, and nobody owns the audit layer. CHERENKOV's `check-suite` is, as far as this review could find, still the only shipped tool that treats the test suite itself as an attack surface.

**Implication:** the strategy docs' conclusion was right; the market moved to confirm it. Conformance is the *proof engine*; integrity is the *product*.

---

## 3. Expected users — a revision

The original framing (QA practitioners running a CLI) is one release cycle behind where the market moved. Revised user model:

1. **Primary (new): coding agents, via MCP.** The buyer is the platform/DevEx team that deploys Claude Code / Cursor / internal agents and needs a gate the agent cannot argue with. The agent calls `verify_suite` / `verify_system` before claiming "done." This user has infinite patience, zero onboarding cost, and is growing exponentially. The MCP server already exists with ~35 tools (`cherenkov/mcp/handlers.py:128-585`) — it is the most under-leveraged asset in the repo.
2. **Secondary: the reviewing human.** Tech leads and QA leads (the "AI orchestrator" role) who need to approve agent-produced PRs and want `cherenkov check-suite` in CI as a merge gate.
3. **Tertiary: regulated orgs** (finance, health, automotive) where the certificate + local-first + auditability story lands. Important for revenue later; wrong to optimize for first (they demand SOC2, contracts, support — unservable solo, per `EXECUTION_PLAN.md` §1.6).

**Approach change this implies:** design and document every feature MCP-first and CI-first. The human CLI is the demo surface; the agent/CI interface is the product surface.

---

## 4. Positioning — the shop window sells the wrong product

`README.md:11` leads with: *"uses a local LLM to generate a fully typed Playwright test suite."* That is the commoditized generator pitch — the exact positioning `VISION_AQE_2026.md` §2 says gets CHERENKOV "commoditized to zero as #30 in a melee." The trust-layer story (`NORTH_STAR.md` §0, the honest differentiation sentence in §8) lives only in `docs/`, which no stranger reads.

**Fix (R0):** rewrite the README top to lead with the integrity wedge:

> *Your AI writes the tests. CHERENKOV catches it cheating.* — detects weakened assertions, deleted checks, and hallucinated oracles in AI-generated test suites, then proves your API honors its spec with reproducible HTTP evidence and a signed certificate. Local-first, no lock-in, eject anytime.

Generation stays in the README as a supporting feature ("and yes, it can generate the suite too"), not the identity.

---

## 5. Technical findings

### 5.1 P0 — the flagship probes are hardcoded to Petstore

`run_proof()` (`cherenkov/divergence/proof_run.py:287`) iterates `PROOF_RUN_PROBES` (`proof_run.py:217`) — five hardcoded Petstore endpoints — **regardless of the spec passed in** (the loop at `proof_run.py:318` never consults the `spec` argument for probe selection). Offline hypotheses (`_offline_hypotheses`, `proof_run.py:355`) encode *known Petstore divergences*. Both `verify` code paths route through this: the simple path (`cherenkov/cli/commands/verify.py:189`) and the default rich-verdict path (`cherenkov/verdict/engine.py:162-166`, and again at `engine.py:352` for the mutation oracle).

**Consequence:** `cherenkov verify --url X --spec Y` probes Petstore paths against server X. The magic moment — "point it at any running system" (`NORTH_STAR.md` §2) — currently only exists for Petstore. This is almost certainly why E0.1 evidence required separate effort per target, and it is the single biggest gap between the pitch and the product. It is also exactly the failure mode `EXECUTION_PLAN.md` F1 warned about ("demo didn't hold up").

**Fix (R1):** a spec-derived probe planner. For each endpoint/method in the *loaded* spec, synthesize offline hypotheses from the spec itself — the checks are mechanical and need no LLM:
- enum parameter sent with out-of-enum value → expect 4xx (spec `enum`)
- required field omitted in request body → expect 4xx (spec `required`)
- documented error-status contract (e.g. invalid path param) → expect the documented code
- response schema conformance: required response fields present, types match
- documented response headers present

The Witness (`cherenkov/divergence/witness.py`) already makes real HTTP calls and reproduces hypotheses generically — only the hypothesis *source* is hardcoded. Keep `PROOF_RUN_PROBES` as the zero-config Petstore demo default; use the planner whenever `--spec` is supplied.

### 5.2 What is genuinely strong (verified)

- **`check-suite`** (`cherenkov/cli/commands/check_suite.py`): pure-stdlib AST/regex analysis catching WEAKENED / DELETED / HALLUCINATED assertions. No LLM, no server needed. This is the moat, already shipped.
- **The Skeptic→Witness divergence loop**: real HTTP reproduction with recorded evidence (`witness.py`), fed into reports and certificates. The value mechanism is real, not demo-ware — it's only the probe *selection* that's hardcoded.
- **Certificate** (`cherenkov/core/certificate.py:58-96`): canonical SHA-256 fingerprint + HMAC seal, compliance profile mapping (EU AI Act / SOC 2 / ISO 25010). Spec promoted to STABLE v1.0.
- **MCP server** (`cherenkov/mcp/handlers.py`): ~35 tools including `verify_suite`, `verify_system`, `validate_run_gate`, HITL queue, conformance check. Richer than HANDOVER implies.
- **Hallucination resistance by construction**: LLM writes test structure; oracles come strictly from the spec.
- Test breadth is real: ~238 test files / ~2,400 test functions.

### 5.3 Health debt (from internal reports, spot-verified)

- **Scope sprawl is the plan's own F8 risk, realized.** `EXECUTION_PLAN.md` §4 parks desktop, K8s polish, VSCode, and the full Reality Engine surface "until post-traction" — yet the repo contains a Tauri desktop app, VSCode extension, Backstage plugin, Go operator, K8s HA manifests, and a default-template landing page. Meanwhile the built PyPI wheel (`dist/cherenkov-1.0.0.whl`) is unpublished.
- Legacy 65KB `cherenkov.py` argparse entry point duplicates the Click CLI — dead weight, confusing to contributors.
- Root-dir committed run artifacts: `soc2_report.json`, `pr.json`, `qwen.json`, `issues.txt`, `test-junit.xml`, `test-sarif.json`, `mut_spec.json`, `audit.json` — this is exactly the "documentation integrity debt" class `EXECUTION_PLAN.md` §1.2 flags.
- Web security headers FAIL (no CSP/HSTS/X-Frame-Options/X-Content-Type-Options — `5_QA_REPORT.md`); no `data-testid` hooks; dashboard offline overlay can block indefinitely (`usability_report.md`).

---

## 6. Recommended route (ordered; each gate blocks the next)

**R0 — Truth alignment (days).**
Reposition the README per §4. Delete or `.gitignore` the root artifact clutter. Remove the legacy `cherenkov.py` entry point. Declare a formal surface freeze: no new commits to desktop/, vscode/, cherenkov-backstage-plugin/, operator/, landing-page/ until R3 passes. Cheap, and it removes the two credibility risks (F4 brand-over-proof, F7 integrity) before anything public.

**R1 — Make `verify` real for arbitrary specs (the one big code item).**
The spec-derived probe planner (§5.1). Exit test: on a spec-first OSS API the project does not own (RealWorld/Conduit, Gitea — the `EXECUTION_PLAN.md` §3 targets), offline `cherenkov verify --spec <their spec>` probes *their* endpoints and reproduces at least one real divergence, recorded end-to-end.

**R2 — Distribution (ship what's built).**
Publish to PyPI (wheel exists — `twine upload`). Publish the MCP server to MCP registries so agents can discover it. Write up the "Catch the AI cheating" demo (`demos/catch-the-ai-cheating/` is CI-gated and passing) as the signature public artifact. Publish the GitHub Action.

**R3 — E0.3, the last G0 gate (human, not code).**
Recruit ≥3 external QA practitioners to run the quickstart cold. R1 must land first — otherwise practitioners pointing `verify` at their own APIs hit the Petstore gap, which is the F1 failure mode in the wild.

**Parked (reaffirmed, per the plan's own rules):** desktop app, VSCode extension, Backstage plugin, K8s operator polish, landing page, VLM/visual, chat agent. They are real work, and they are launch liabilities until the wedge has pull.

**Do not change:** local-first/air-gapped defaults, eject-to-vanilla-Playwright, Apache-2.0, spec-derived oracles, the certificate spec, model-agnostic substrate. These are the moat's structural components (`NORTH_STAR.md` §5) — neutrality is the product.

---

## 7. AI-future fit

The thesis holds and is strengthening: as generation goes to zero cost, verification is the scarce complement, and a model vendor structurally cannot own it (self-verification isn't credible). Three concrete moves keep CHERENKOV aligned with where this goes:

1. **Agents as first-class users** (§3) — MCP-native both ways, already 80% built.
2. **The certificate as a machine-verifiable artifact** — position it for agent-to-agent trust (one agent requires another's cherenkov certificate before consuming its output), not just human compliance.
3. **The integrity corpus** — every caught cheat is training signal for better detection; local-first means it compounds per-customer without data leaving. Start recording anonymized detection patterns now.

Regulatory tailwind (EU AI Act, FCA/PRA, ISO 26262/21434) continues to favor auditable, local, constrained-autonomy QA — the trust layer *is* the compliance layer.

---

## 8. Part 2 — Market-research synthesis (addendum, 2026-07-05)

> Source: three market-research reports supplied 2026-07-05 (2026 AI macro trends & investment; agentic AI frameworks & the QA transformation; LLM-evaluation stack; Egypt/MENA sovereign-AI ecosystem). Figures below are from that research; primary organizations it draws on include Gartner, McKinsey, Stanford AI Index, OWASP, NIST, ISO, and Egypt's ITIDA/SECC.

### 8.1 The thesis, now with harder numbers

The research independently confirms Part 1's central call — and quantifies the demand:

- ~**40% of newly written enterprise code is AI-generated**; **88% of developers lack confidence** deploying it; **29% have rolled back releases** due to AI errors.
- **95% of AI pilots fail without guardrails**, with 60% of those failures linked to compliance/security. Gartner: **40%+ of agentic-AI projects will be canceled by 2027**; Forrester: 75% of DIY agentic architectures will fail. Verification is the failure-prevention layer.
- QA's role is formally shifting from "executor" to **"orchestrator / risk intelligence"**, spawning the exact roles CHERENKOV serves: *AI Output Reviewer, LLM Response Auditor, Model Safety Tester*.
- Market: software testing $55.8B (2024) → $112.5B (2034); generative testing $48.9M → $351.4M; 77.7% of orgs already use AI in QA; MCP is described as the "USB-C for QA agents" — validating the MCP-first user model in §3.

### 8.2 Sharper category map — where CHERENKOV sits

The research clarifies two adjacent stacks that could be confused with CHERENKOV, and neither overlaps its lane:

| Stack | Examples | What it judges | What it does *not* do |
|---|---|---|---|
| LLM-evaluation | DeepEval, Promptfoo, Ragas, TruLens, LangSmith, Arize Phoenix, Confident AI, Giskard | The *model's outputs* (relevancy, hallucination, RAG faithfulness) | Audit generated *test code* for integrity |
| Agentic QA platforms | Tricentis, Virtuoso GENerator, mabl, QA Wolf, Functionize | Nothing — they *generate/maintain* tests (the commoditizing melee) | Independently verify their own output |

Positioning line vs the eval stack, to use alongside the Schemathesis line: **"Eval frameworks judge the LLM's answers; CHERENKOV audits the tests the LLM wrote — and proves the API honors its contract."**

### 8.3 Standards hook (R2-adjacent backlog)

The **OWASP AI Testing Guide v1** (Nov 2025) is the first community standard for AI trustworthiness testing, alongside NIST AI RMF and **ISO/IEC 42001** (certifiable AI-management standard). CHERENKOV's `compliance_profile()` (`cherenkov/core/certificate.py:161`) already maps to EU AI Act / SOC 2 / ISO 25010; extending the mapping to OWASP-ATG and ISO/IEC 42001 would let the certificate ride the standards wave. Backlog item, not new scope.

### 8.4 New GTM channel: Egypt / MENA sovereign AI — and a concrete E0.3 path

Egypt's national AI strategy (2025–2030) targets 7.7% of GDP from AI and formalizes QA as an export discipline: the **ESTB/SECC has certified 9,000+ professionals (13,600+ ISTQB certificates)** and now offers the **ISTQB CT-GenAI** certification; SECC runs **Software Testing Day**, and **Ai Everything MEA Egypt 2026** convenes the ecosystem. Three implications:

1. **E0.3 execution path (the last G0 gate):** recruit the 3 quickstart practitioners from the ESTB/ISTQB CT-GenAI community — a warm, credentialed pool aligned with exactly this problem space — instead of cold outreach.
2. **Sovereignty fit:** local-first/air-gapped operation is not just a privacy feature here; it is the *procurement requirement* of sovereign-AI programs. The repo already ships `scan_mena_compliance` MCP tools.
3. **Distribution:** SECC events and the AUC Venture Lab network are low-cost, high-credibility venues for the "Catch the AI cheating" demo (R2).

### 8.5 What does NOT change

The R0→R3 route, priorities, and park list from Part 1 stand unchanged. Pricing-model trends (hybrid subscription+usage, outcome-based) are noted for the post-traction monetization phase only. The research's enthusiasm for building more agentic surface area is explicitly *not* adopted — it is the same scope-sprawl temptation §5.3 warns about; CHERENKOV's job is to be the layer that makes everyone else's agents trustworthy.

---

## 9. Sources (external market check, 2026-07-05)

- PactFlow — "Schemas Can Be Contracts | Introducing Drift": https://pactflow.io/blog/schemas-can-be-contracts/
- "API Schema Drift Detection Tools Compared (2026)": https://dev.to/flarecanary/api-schema-drift-detection-tools-compared-2026-1ib4
- Speakeasy — "OpenAPI Spec Drift Detection": https://www.speakeasy.com/blog/openapi-spec-drift-detection
- Schemathesis: https://schemathesis.io/ · https://github.com/schemathesis/schemathesis
- "Top OpenAPI Testing Tools Compared: Best Tools for 2026": https://totalshiftleft.ai/blog/top-openapi-testing-tools-compared-2026
- Absence-of-competitor check for AI-test-integrity auditing: July 2026 web searches for assertion-weakening / test-integrity verification tooling returned academic and hiring-assessment results only; no developer tool comparable to `check-suite` was found.
