# CHERENKOV QA Dashboard — Full Interactive Audit (Evidence)

Method: Playwright drove **31 real interactions** through the live UI (`:3000`) against the
live backend (`:8000`), with every `/api/v1` request intercepted per action. This is
behavioral proof of what hits the backend vs what is client-only — not inspection of code.

Reproduce: `npx playwright test tests/full_audit.spec.ts` → `scratch/audit/report.json`.

Result: **31 actions · 7+ hit backend · 14 no backend · 2 defects found · 0 crashes.**

## 🟢 Flows proven LIVE (hit the real backend)

| Flow / button | Backend call | Verified |
|---|---|---|
| New Spec Run → preset `petstore-v2.yaml` | `POST /ingest` | ✅ 200 |
| New Spec Run → paste URL + **FETCH** | `POST /ingest` | ✅ fired (returned 400 on non-spec URL — see Bug 2) |
| Divergences → navigate | `GET /divergences` | ✅ 200, real corpus |
| Divergences → act (close/mark) | `POST /divergences/act` | ✅ 200 |
| Review Queue → navigate | `GET /tests` | ✅ 200 |
| Review Queue → **APPROVE SPEC TEST** | `POST /review/approve` | ✅ 200 |
| Eject → **EJECT AND WRITE DIRECTORIES** | `POST /eject` | ✅ 200, 10 files |
| (verified via API earlier) review/edit, review/reject, validate | respective routes | ✅ |

**The spec→generate→review→eject golden path is genuinely functional end-to-end.**

## 🔴 Flows proven FAKE (zero backend, despite looking active)

| Flow / button | Observed | Impact |
|---|---|---|
| **Author by Intent → INITIALIZE PILOT RUN** | **no API call** — runs a `setTimeout` replay of `MOCK_PILOT_STEPS`, then toasts "completed" | Flagship NL→test feature generates nothing, while `runPipeline()` already works |
| **Healing → APPLY HEALING SUGGESTION** | no API call | Apply is a no-op; `validateSuite()` exists but isn't wired to this button |
| **Overview → RUN DISCOVERY SCAN** | no API call | Decorative |
| Overview / Truth Map / Signals / Governance / Memory (navigate) | no API call | All render `MOCK_*`; no `/overview /signals /governance /truthmap /memory` routes exist (all 404) |
| **Workspace switcher** (→ Swagger Petstore v2) | no API call, **data unchanged** | Cosmetic; 3 workspaces share one dataset |
| Settings → toggle + **APPLY PARAMETERS** | no API call | localStorage only; nothing persisted server-side |
| Truth Map → **HUNT DIVERGENCES** | only triggers the Divergences page's own `GET /divergences` | Button just navigates |

## 🐞 Defects found

**Bug 1 — React setState-in-render in `ReviewScreen`** (correctness)
```
Console error: Cannot update a component (App) while rendering a different
component (ReviewScreen). ... setState() call inside ReviewScreen
```
`ReviewScreen.tsx` updates parent `App` state during its own render (approve/toast path,
~L60/L136). Real React anti-pattern — can cause dropped updates / double-render. Fix: move
the parent update into an effect or event handler, not render.

**Bug 2 — Ingest FETCH surfaces raw 400 to console** (UX)
Pasting a non-OpenAPI URL into FETCH posts to `/ingest`, backend correctly returns
`400 Parsing error`, but it lands as an unhandled `Failed to load resource: 400` console
error. The request path is live and correct; the error presentation is noisy. Confirm the
on-screen error toast renders (handler exists in `SetupScreen`).

## Cross-cutting

- **Header telemetry is client-side fiction:** `$0.11` cost, `48%` token pool,
  `Cloud equiv $0.370` come from local `useState` (`totalSpentEstimated`,
  `tokenUsagePercent`); no `/cost` or `/metrics` route exists. Identical on every screen.
- **Silent-failure pattern:** `actOnDivergence` (and eject/divergence fallbacks) swallow
  backend errors and update the UI optimistically — a failed write can read as success.
- **No crashes, no broken navigation.** All 13 screens render; all nav works; 0 page errors
  beyond the two defects above.

## Bottom line

The **engine half is real and shippable** (ingest → live-LLM generate → HITL review → eject).
The **observability half is a presentation layer** (Overview, Signals, Governance, Truth Map,
Memory) plus a **fake flagship** (Author Pilot Run) and a **no-op Healing apply**. Priority
fixes: wire Author→`runPipeline`, wire Healing apply→`validateSuite`, fix the ReviewScreen
render bug, and either back the 5 mock screens with real run artifacts or label them clearly.
