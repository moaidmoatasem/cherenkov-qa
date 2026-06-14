# CHERENKOV FE — Experience Design Spec (journeys, motion, states, notifications)

**Companion to** [`FE_REDESIGN.md`](FE_REDESIGN.md) (IA + agent build prompts). This doc adds the **experiential layer**: user journeys, flows, transitions/animations, edge cases, loading, error handling, notifications, and added FE features. It is **Figma-ready** — every frame/state to draw is enumerated in §10.
**Design language:** the existing Cherenkov-glow system (dark `#020617`, cyan `#22d3ee`, Inter/Poppins/JetBrains Mono, `.cherenkov-card`, glassmorphism). **All motion honors `prefers-reduced-motion`.**

---

## 1. Personas & their primary journey
| Persona | Goal | Flagship journey |
|---|---|---|
| **Maya — manual QA (non-coder)** | "Test this without writing code." | J1 · Author by Intent |
| **Sam — QA lead** | "Am I safe to ship? What's lying?" | J2 · Triage a divergence |
| **Jordan — junior SDET** | "What would a senior check here?" | J3 · Learn via pairing |

---

## 2. Journey J1 — Author by Intent (the manual-QA heart)

**Entry:** Sidebar → *Author by Intent* (or ⌘K → "author").
**Happy path (7 beats):**
1. **Blank canvas, inviting.** Big focused input ("Describe what to test…"), 3 example chips, Mentor idiom hints fade in (`160ms`). *State: empty.*
2. **Typing.** Live affordance: a subtle character-stream glow on the submit button (`beam-flow`); "Assisted" autonomy pill visible.
3. **Submit → Planning.** Input collapses up (`220ms ease-out`), a **step list** scaffolds in with skeleton rows (`shimmer`). *State: loading-plan.*
4. **Pilot executes step-by-step.** Each step row animates from `pending → running (cyan pulse) → done (success check)`; on **Assisted**, a "Confirm step" inline button gates each action. Live screenshot thumbnail updates per step.
5. **Result.** A result `Card` slides up (`260ms`): pass/fail `StatusDot`, evidence disclosure (request/response + screenshot), and the diverging claim if any.
6. **Save & Eject.** Primary button → toast "Test ejected to `tests/checkout.spec.ts` — runs standalone."
7. **Reflector microcopy.** "CHERENKOV learned this flow" chip — reinforces compounding value.

**Branches & edge cases:**
- *Ambiguous intent* → inline clarifying chips ("Which checkout — guest or member?") instead of guessing.
- *Step fails* → row turns `warning`; offer **Retry**, **Self-heal** (vision re-locate), or **Skip & flag**. Never hard-crash the run.
- *Pilot can't find element* → vision fallback banner: "Couldn't locate 'Confirm' — showing 3 candidates" with click-to-pick.
- *Backend/model offline* → see §6 offline handling; the run pauses, not dies.

---

## 3. Journey J2 — Triage a divergence (the lead's money path)

**Entry:** Overview "Top Divergences" card → or Divergences screen.
**Flow:** filter (D1–D5 / severity / status) → scan severity-sorted rows → open row → **Drawer** slides from right (`240ms cubic-bezier(.2,.8,.2,1)`) showing **Claim A vs Claim B**, evidence diff, repro steps → choose:
- **Close with test** → hands to J1's Pilot with intent pre-filled → on success, divergence row collapses with a `success` ripple.
- **Mark intended** → row greys (`rejected` dot), writes a Reflector verdict ("this is expected here").
- **Reject (noise)** → reason prompt → Reflector learns to stop surfacing it; toast "Won't show this again."

**Edge cases:** 500+ findings → virtualized list + "showing 50 of 1,240" with progressive load; evidence too large → lazy-load diff on disclosure; reproduction flaky → show confidence ("reproduced 4/5 runs").

---

## 4. Journey J3 — Pairing (junior ↔ senior)
Junior opens *Memory & Pairing* → picks a context (e.g. "new list endpoint") → Mentor panel explains *why* a senior checks tenant isolation here, with the source idiom + confirm-count. Inline CTA "Author this check" → J1. Transition between idiom cards: cross-fade `160ms`.

---

## 5. Motion system (transitions & animations)

| Token | Duration | Easing | Use |
|---|---|---|---|
| `motion-instant` | 80ms | ease-out | hover, focus ring |
| `motion-fast` | 160ms | ease-out | chips, tooltips, cross-fade |
| `motion-base` | 240ms | `cubic-bezier(.2,.8,.2,1)` | drawers, panels, tab change |
| `motion-slow` | 320ms | ease-in-out | screen transitions, onboarding |
| `glow-pulse` | 2s loop | — | live/running state only |
| `beam-flow` | 1.5s loop | linear | active stream/run only |

**Rules:** (1) screen change = fade-through (`base`), never slide-the-whole-app. (2) Drawers/modals slide + backdrop blur fade. (3) Looping glows **only** on genuinely live elements (running step, LIVE status) — never decorative on idle. (4) **Reduced-motion:** disable all loops + replace slide/fade with instant; keep a 1-frame opacity for orientation. (5) List reorder uses FLIP (`base`); respect reduced-motion by snapping.

---

## 6. Edge cases & failure handling (the "way of handling")

| Situation | Handling |
|---|---|
| **Backend down** | Global amber banner "Backend offline — showing last known data"; screens fall back to last cache/mock; actions disabled with tooltip, not hidden. (Matches existing `lib/api.ts` graceful-fallback.) |
| **Model/inference timeout** | Run pauses at current step; "Inference slow/over budget — retry, switch tier, or pause"; never silent-fail. |
| **Long-running run** | Run continues in a **dismissible drawer**; user navigates away freely; a TopBar `LIVE` chip + progress ring persists; completion → toast. |
| **Partial data** | Render what's present; mark missing sections with inline "couldn't load — retry"; never block whole screen on one failed card. |
| **Large lists (1k+)** | Virtualize; "showing N of M"; server-side filter; never dump all. |
| **Stale data** | "Updated 3m ago • refresh" affordance; soft-refresh without full reload. |
| **Permission/seat limits** | If an action needs a capability the user lacks, explain + link, don't dead-end. |
| **Destructive/expensive action** | Confirm dialog with blast-radius + cost estimate (e.g. "load test ~$0.40, 2 min"). |
| **Empty (first run)** | Teaching empty state + "Try the Petstore demo" everywhere. |
| **Sovereign mode** (`egress:none`) | Persistent "🔒 Local-only" badge; any cloud-tier action is disabled with explanation. |

---

## 7. Loading strategy
- **Skeletons, not spinners** — shimmer placeholders matching final layout (cards, rows, charts).
- **Optimistic UI** for approve/reject/close — update instantly, reconcile on response, rollback + toast on failure.
- **Streaming** for runs — step rows appear as they execute (no "wait then dump").
- **Progressive** for heavy detail — list loads first, evidence/diff lazy-loads on disclosure.
- **Perceived-speed budget:** first meaningful paint < 1s from mock/cache; never a blank panel.

---

## 8. Notification & feedback system

| Channel | When | Spec |
|---|---|---|
| **Toast** (bottom-right) | async result (eject done, verdict saved, run complete) | auto-dismiss 4s, pause-on-hover, `success/warning/danger` token, max 3 stacked, action link ("View") |
| **Inline** | field/step-level (validation, step fail) | next to the element, non-blocking |
| **Banner** (top) | global/persistent (backend offline, sovereign mode, gate status) | dismissible unless system-critical |
| **Badge** | counts (open criticals, learned idioms, live runs) | on nav items + TopBar; pulse once on increment |
| **Drawer/Modal** | needs decision (confirm destructive, clarify intent) | focus-trapped, ESC-closable (unless critical) |

**Rules:** one toast per action; never toast + banner for the same event; errors always offer a next step (retry/learn-more); respect reduced-motion (no slide, just fade).

---

## 9. Added FE features (beyond screens)
1. **⌘K Command Palette** — fuzzy nav + verbs ("author a test", "open divergences", "new run", "switch project"). Recent + suggested.
2. **Autonomy ladder** (TopBar segmented: Assisted/Augmented/Agentic) — changes how much runs unattended; persists to `[copilot] autonomy`; Maya defaults Assisted.
3. **Keyboard map** — `?` opens shortcuts; `j/k` list nav, `Enter` open, `a/r` approve/reject, `g d` go-to-divergences, `/` focus filter.
4. **Onboarding** — 3-step coachmark ending at "your first reproduced divergence" (the <10-min promise); skippable; once-only.
5. **Cost & budget meter** (existing) — live token/cost vs `[substrate.budgets]`; warns before exceeding.
6. **Sovereign badge** — `🔒 Local-only` when `egress:none`.
7. **Density toggle** (comfortable/compact) for senior SDETs.
8. **Provenance everywhere** — `[spec|code|traffic|db]` chips on any claim/finding/test → trust at a glance.
9. **Run drawer** — any long run is backgroundable and resumable.

---

## 10. Figma handoff — frames to create (when on an edit/Full seat)

> The connected account is **View-only (starter)** — generation needs an edit/Dev seat. Once upgraded, build these pages/frames; this spec + `FE_REDESIGN.md` define every one.

**Page A — Foundations:** color/type/elevation tokens; component states for `SeverityPill`, `StatusDot`, `ProvenanceChip`, `Button`, `Card`, `EmptyState`, `Skeleton`, `Toast`, `Tabs`, `Drawer`, `KpiRing` (default/hover/focus/active/disabled/loading).
**Page B — Shell:** Sidebar (grouped, collapsed icon-rail), TopBar (autonomy + cost + LIVE), Command Palette.
**Page C — Screens (each with empty/loading/error/populated):** Overview, Truth Map, **Divergences + Drawer**, Explore, **Author by Intent** (7 beats), Review Queue, Signals (Perf/Visual/Coverage), Memory & Pairing, Governance, Settings.
**Page D — Journeys (prototype flows with transitions):** J1 Author, J2 Triage, J3 Pairing — wired with the §5 motion tokens.
**Page E — Edge cases:** the §6 matrix as visual states (offline banner, sovereign mode, large-list truncation, failed step, confirm-cost dialog).

---

### How to actually produce it in Figma
1. Upgrade the Figma seat to **Full/Dev** (or share an edit-seat file), then re-run the design generation — the `use_figma` / `generate_figma_design` tools need write access.
2. Alternatively hand this spec + `FE_REDESIGN.md` to a designer; both are complete enough to execute without further Q&A.
