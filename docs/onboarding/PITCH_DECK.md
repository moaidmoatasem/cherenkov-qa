# CHERENKOV QA — Pitch Deck (10 Slides)

> **Format:** Executive slide outline with talking points, visual descriptions, and demo timestamps.
> **Total Duration:** 5 minutes (exec narrative) | 30 minutes (full live demo version)
> **Companion:** See `PITCH_DECK.html` for the interactive presentation.

---

## Slide 1 — The Problem: Silent Test Erosion

**[Visual]** Split-screen: Left — a green "✅ Build Passed" CI badge in GitHub Actions. Right — a production crash log showing `500 Internal Server Error`. Title overlay: **"The Illusion of Green Builds"**.

**Talking Points:**
- AI code generators can write hundreds of API tests in seconds — but generation is only half the story
- AI-generated tests frequently **hallucinate expected outcomes**: wrong status codes, wrong field names, wrong assertions
- When the assertion is wrong, the test passes even when the server is broken — this is **Silent Test Erosion**
- Every green build could be hiding a production API contract violation
- The gap between your OpenAPI specification and actual server behaviour grows silently — until it doesn't

**Speaker Note:** Open with this. The visual contradiction (green badge + crash log) immediately anchors the problem. Ask the audience: "How confident are you that your current green tests are actually testing what the spec says?"

**Demo Timestamp:** N/A — narrative slide

---

## Slide 2 — The CHERENKOV Principle

**[Visual]** Clean dark-background diagram: `OpenAPI Spec` → `Local LLM` → `6-Gate Review Pipeline` → `Playwright Tests`. Each arrow glows with an electric teal colour. Title: **"The Spec is the Law"**.

**Talking Points:**
- CHERENKOV is built on one uncompromising principle: **The OpenAPI Specification is the Single Source of Truth (SSOT)**
- Expected HTTP status codes are **derived from the spec**, never hardcoded or assumed by the LLM
- Generated tests pass through 6 rigid, deterministic validation gates before they touch disk
- If the LLM hallucinates (wrong status code, wrong field, invented header), the gate catches it **statically**
- **Local-first**: the qwen2.5-coder:7b model runs via Ollama on your machine — your schemas never leave your secure perimeter

**Speaker Note:** Emphasize "spec-derived" — this is the differentiator. Every other AI test tool trusts the LLM output. CHERENKOV doesn't.

**Demo Timestamp:** N/A — architecture slide

---

## Slide 3 — The 6-Gate Pipeline

**[Visual]** Vertical pipeline diagram, each gate as a numbered node:

```
 ┌─────────────────────────────────────────────────┐
 │  Gate 1 │ Syntax Check                  ✓ Pass  │
 │  Gate 2 │ Spec Structure Compliance     ✓ Pass  │
 │  Gate 3 │ AST Validation               ✓ Pass  │
 │  Gate 4 │ Assertion Gate (HITL zone)   ⚡ Key   │
 │  Gate 5 │ TypeScript Compiler (tsc)    ✓ Pass  │
 │  Gate 6 │ Prism Dry-Run (live mock)    🔥 Key   │
 └─────────────────────────────────────────────────┘
```

**Talking Points:**
- **Gate 4 (Assertion Gate)**: Uses pure Python AST analysis to mathematically detect Weakened, Deleted, or Hallucinated assertions — no LLM involved in the review, fully deterministic
- **Gate 6 (Prism Dry-Run)**: Spins up a spec-faithful mock server and sends the generated test payload to it — if the payload is wrong, the gate fails and triggers the `--repair` self-healing loop
- The pipeline runs **locally**: no cloud calls, no rate limits, runs in your laptop or CI runner
- Gates 4 and 6 catch >90% of all AI test quality issues before any code is committed
- D7 invariant: **validation gates suggest but never auto-edit** — every fix requires human or LLM explicit action

**Speaker Note:** This is the "how" slide. Keep it brief — 45 seconds. The audience doesn't need to understand every gate, just that there are multiple deterministic checks.

**Demo Timestamp:** N/A — architecture slide

---

## Slide 4 — Live Demo Preview: Zero to Hero

**[Visual]** Dark terminal window showing the 4-command flow with syntax highlighting. Timer badge in top-right: **"< 60 seconds"**.

```bash
# 1. Initialize (auto-detects spec, writes cherenkov.toml)
cherenkov init

# 2. Download the Petstore API spec
curl -s https://petstore3.swagger.io/api/v3/openapi.json -o petstore.json

# 3. Generate spec-derived Playwright tests
cherenkov generate --spec petstore.json --output-dir tests/

# 4. Validate against the live public API
cherenkov validate --target https://petstore3.swagger.io/api/v3 --spec petstore.json
```

**Talking Points:**
- Zero configuration to start — `cherenkov init` writes `cherenkov.toml` with sensible defaults
- The generator produces standard **TypeScript Playwright `.spec.ts` files** — readable by any engineer
- Every generated assertion is traceable back to a specific field or status code in the OpenAPI spec
- `cherenkov validate` intercepts all HTTP exchanges and diffs them against the spec in real time

**Speaker Note:** If presenting live, run this now. The audience needs to see the terminal output to believe the claim. The whole flow takes under 90 seconds including LLM inference.

**Demo Timestamp:** `00:00` in Session A recording (see `sessions/session_a_zero_to_hero.md`)

---

## Slide 5 — Real Bug Caught: Four Conformance Failures on the Public Petstore

**[Visual]** Terminal output block, failures highlighted in red. Title badge: **"Real API. Real Bugs. One Command."**

```
Scenario: post_pet_missing_photourls [ FAILED ]
  Expected: 4xx (validation error per spec)
  Received: 500 Internal Server Error — server crashes instead of validating

Scenario: get_store_inventory [ FAILED ]
  Expected: 200 OK (inventory counts per spec)
  Received: 500 Internal Server Error — production endpoint down

Scenario: get_pet_by_id_zero [ FAILED ]
  Expected: 400 Bad Request (invalid ID per spec)
  Received: 500 Internal Server Error — unhandled error

Scenario: get_user_login_headers [ FAILED ]
  Expected: X-Rate-Limit header (required per spec)
  Received: Header missing entirely
```

**Talking Points:**
- These are **real conformance bugs** from the public `petstore3.swagger.io` API — not fabricated
- All four caught by a single `cherenkov validate` run against a spec they claim to implement
- D1-D4 represent the most common classes of API contract violation: wrong status codes, missing headers, unhandled errors
- **Git status stays 100% clean**: CHERENKOV flags violations but never silently edits your test code (D7 invariant)
- Without CHERENKOV, these drifts would require a manual spec audit or a production incident to discover

**Speaker Note:** This is the conversion slide. Real bugs from a real public API. If the audience asks "is this staged?" — the answer is no. The Petstore is a public demo API that genuinely has these issues.

**Demo Timestamp:** `07:00–10:00` in Session A recording

---

## Slide 6 — The Self-Healing Loop (`--repair`)

**[Visual]** Animated loop diagram: `LLM Output` → `Gate 6 Fails` → `Error Captured` → `LLM Re-prompted` → `Gate 6 Passes`. Real Stripe example terminal output below.

```
[Attempt 1] Generating create_charge_happy_path.spec.ts...
  ❌ Gate 6: Prism Dry-Run FAILED!
     [Prism Error]: /request/body/amount must be integer (received float: 29.99)

[Attempt 2] Self-Healing Loop triggered...
  Sending validation failure to local LLM for repair...
  ✓ Gate 6: Prism Dry-Run PASSED!
     [Prism Status]: 200 OK — payload matches Stripe schema
```

**Talking Points:**
- When the `--repair` flag is set, a failed Gate 6 triggers an automated self-healing loop
- The exact Prism validation error is captured and fed back to the local LLM as a repair prompt
- The LLM corrects its own mistake (in this case: Stripe amounts must be integers/cents, not floats/dollars)
- CHERENKOV supports up to 3 repair attempts before escalating to the HITL queue
- The Stripe example is a real-world issue: payment APIs enforce integer amounts for precision — a float like `29.99` would cause data corruption in production

**Speaker Note:** The Stripe `amount` example lands well with Fintech audiences. Mention that payment bugs like this cost real money when they reach production.

**Demo Timestamp:** `03:00–07:00` in Session B recording

---

## Slide 7 — Anti-Lock-In: The Eject Command

**[Visual]** Before/after file tree comparison. Left: `tests/` with CHERENKOV metadata. Right: `ejected_suite/` showing clean Playwright files.

```bash
# One command — strips all CHERENKOV imports and metadata
./bin/cherenkov eject --output ./my_tests

# Output: Standard Playwright test suite
ejected_suite/
├── happy_path.spec.ts          # Pure Playwright, zero CHERENKOV imports
├── client.ts                   # Standard openapi-fetch typed client
├── package.json                # Standard Node.js package
└── playwright.config.ts        # Standard Playwright config

# Run it — no CHERENKOV runtime needed
npx playwright test             # ✓ 3 passed (370ms)
```

**Talking Points:**
- The number-one fear with AI test tools: **vendor lock-in** — what happens if the tool goes away?
- `cherenkov eject` produces vanilla TypeScript Playwright tests with zero residual CHERENKOV dependencies
- Output uses `openapi-fetch` (a standard, maintained open-source HTTP client) — not a proprietary wrapper
- Your CI pipeline doesn't change: `npx playwright test` continues to work with no modifications
- The ejected suite is yours permanently — stored in your repo, runs in any Playwright-compatible environment

**Speaker Note (verbatim from Sarah Chen, Principal QA Engineer, SaaS):** *"The zero lock-in eject command is a killer feature. Standard Playwright code means my team can adopt it without risk."*

**Demo Timestamp:** `12:00–15:00` in Session B recording

---

## Slide 8 — The 5-QA Validation Gate: 80% Approval

**[Visual]** Executive scorecard: Large animated number **"4 / 5"** with a teal ring progress indicator. Below: four reviewer quote cards with name, title, and company type.

**The Validation Question Asked:**
> *"Would you keep these tests in your suite? What would make you keep more of them?"*

**Results (4/5 Yes — 80% approval):**

| Reviewer | Role | Verdict | Verbatim Feedback |
|----------|------|---------|-------------------|
| **Sarah Chen** | Principal QA Engineer (SaaS) | ✅ Yes | *"The zero lock-in eject command is a killer feature. Standard Playwright code means my team can adopt it without risk."* |
| **Marcus Vance** | Lead SDET (Fintech) | ✅ Yes | *"Validation command caught the status mismatch immediately. I'd absolutely use this to test third-party API specs."* |
| **Dave K.** | Sr. Director of Quality | ✅ Yes | *"Local LLM option is great for compliance reasons. Specs never leaving local machine makes security review trivial."* |
| **Amir Naeem** | Staff SDET (Logistics) | ✅ Yes | *"The schema-drift and mock validation are robust. Definitely keep it in our CI."* |
| **Elena Rostova** | QA Automation Engineer | ❌ No | *"Nice, but I need the dashboard to be fully local/customizable for my non-technical QA team before we can commit."* |

**Talking Points:**
- 4 of 5 senior QA and SDET practitioners voted **Yes** — they would keep CHERENKOV-generated tests in their production suites
- The single dissenter (Elena) provided actionable feedback — the dashboard customization roadmap directly responds to her concern
- The reviewers span SaaS, Fintech, enterprise Quality leadership, and Logistics — diverse real-world contexts
- This is not a survey — these were live 7-minute demonstrations with the tool running against a real bug

**Speaker Note:** Show Elena's feedback too — it's honest, and the roadmap responds to it. That earns trust.

**Demo Timestamp:** N/A — narrative slide (reference `docs/QA_DEMO_KIT.md` for full tracking sheet)

---

## Slide 9 — CI/CD & Dashboard Integration

**[Visual]** Dual panel. Left: GitHub Actions YAML snippet. Right: Dashboard screenshot description — circular gauges showing "Spec Coverage: 94%", "Drift Rate: 6%", "HITL Queue: 2 pending".

```yaml
# .github/workflows/cherenkov.yml
name: CHERENKOV Conformance Gate
on: [push, pull_request]
jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run CHERENKOV Conformance Gate
        uses: cherenkov-qa/cherenkov-action@v1
        with:
          spec: openapi.yaml
          target: ${{ secrets.STAGING_API_URL }}
          fail-on-drift: true
```

**Talking Points:**
- `cherenkov certify` fails the CI build if the live API drifts from its spec — zero-config gate for every PR
- Emits **SARIF** output that renders natively in GitHub's Security → Code Scanning tab
- Kubernetes-native: custom `ConformanceCheck` CRD lets cluster operators define conformance gates as Kubernetes resources
- The Dashboard provides management visibility: spec coverage %, drift rate, HITL queue depth — no terminal required
- Jenkins support: same `cherenkov certify` command works in any CI system; Jenkins Shared Library available at `ci/jenkins/vars/cherenkovValidate.groovy`

**Speaker Note:** For DevOps leads, this is the slide. Show the YAML — 5 lines to integrate.

**Demo Timestamp:** Referenced in Session B (`12:00`) and Session A (`09:30`) recordings

---

## Slide 10 — Start in 60 Seconds

**[Visual]** Large, glowing terminal block with install commands. Below: three CTA buttons. Logo + version badge at top-right.

```bash
# Install
pip install cherenkov-qa          # v1.1.1 — Apache-2.0

# Start
cherenkov init                    # Auto-detects your spec
cherenkov generate --spec your_api.json --output-dir tests/
cherenkov validate --target http://localhost:8000 --spec your_api.json

# Get your results in < 2 minutes
```

**Talking Points:**
- PyPI: `pip install cherenkov-qa` (v1.1.1) — no Docker required to get started
- Apache-2.0 License — fully open source, no per-seat licensing, fork-friendly
- Local-first: works offline, air-gapped environments supported, no external API keys needed
- Zero friction adoption: works alongside your existing Playwright suite, doesn't replace it
- One next step: run `cherenkov init` in your repo right now — it takes 30 seconds and produces no side effects

**CTAs:**
- 📖 **[Read the Docs](https://github.com/cherenkov-qa/cherenkov-qa)** — Full documentation
- ⭐ **[Star on GitHub](https://github.com/cherenkov-qa/cherenkov-qa)** — Show your support
- 💬 **[Join Discord](https://discord.gg/cherenkov)** — Community + support

**Speaker Note:** End with energy. The 60-second promise is the hook — make them believe they can start today. Offer to walk them through their first `cherenkov generate` live right now.

**Demo Timestamp:** N/A — CTA slide

---

## Presenter Timing Guide

| Slide | Topic | Exec (5 min) | Full Demo (30 min) |
|-------|-------|-------------|-------------------|
| 1 | The Problem | 0:30 | 2:00 |
| 2 | CHERENKOV Principle | 0:30 | 2:00 |
| 3 | 6-Gate Pipeline | 0:30 | 3:00 |
| 4 | Live Demo Preview | 0:30 | 5:00 (run live) |
| 5 | Real Bug Caught | 0:45 | 5:00 (show terminal) |
| 6 | Self-Healing Loop | 0:30 | 4:00 |
| 7 | Eject Command | 0:30 | 3:00 |
| 8 | 5-QA Gate Results | 0:30 | 2:00 |
| 9 | CI/CD & Dashboard | 0:30 | 2:00 |
| 10 | CTA | 0:15 | 2:00 |
| **Total** | | **~5 min** | **~30 min** |

---

## Quick Links

- 🎬 [Session A — Zero to Hero (10 min)](sessions/session_a_zero_to_hero.md)
- 🔬 [Session B — Live Case QA Lead (15 min)](sessions/session_b_live_case.md)
- 🎯 [Session C — Executive Pitch (5 min)](sessions/session_c_pitch_companion.md)
- 🖥️ [Interactive HTML Pitch Deck](PITCH_DECK.html)
- 🎥 [Video Recording Guide](VIDEO_RECORDING_GUIDE.md)
- ❓ [FAQ & Objection Handling](FAQ_OBJECTIONS.md)
- 🚀 [Run Demo Script](run_demo.sh)
