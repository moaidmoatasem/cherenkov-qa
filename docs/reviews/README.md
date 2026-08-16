# External / Teammate-Agent Reviews — index + caveats

This folder archives reviews produced by other agents. They contain useful signal **and**
material errors. Read them through the project's honest baseline ([HANDOVER.md](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/HANDOVER.md),
[SCOPE_LEDGER.md](../SCOPE_LEDGER.md)) — not the other way around.

## Current

- `TESTERARMY_TEARDOWN_2026-08.md` — competitive teardown of TesterArmy (`testerarmy@0.9.0`)
  plus a phased plan for the gaps it exposes. **Caveat on method:** the docs site was
  egress-blocked from the session that wrote it, so the product was reconstructed from the
  published npm artifact and the public CLI repo, not from vendor documentation — §1 states
  exactly what was and wasn't reachable. CHERENKOV-side claims are grep-verified against the
  tree at `de2974a` and cited inline. Its plan (§6) maps onto existing milestones; it does
  **not** supersede [ROADMAP_2026H2.md](../ROADMAP.md) or [HANDOVER.md](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/HANDOVER.md).

## Archived

- `2026-06-04_mistral_comprehensive_review.md` — broad technical+business review. **Caveat: treat its
  status claims as UNRELIABLE.** It repeats the **fabricated** "Track A SHIPPED / 4/5 QA gates passed /
  ready to ship" (see [HANDOVER.md §5](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/HANDOVER.md)), and contains factual errors: it lists the 6
  Review gates as implemented (Gate 4 Novelty and Gate 6 LLM-quality do **not** exist — see
  [GAP_REPORT.md](../GAP_REPORT.md)), and references files that do not exist (`ai/strip_think.py`,
  `core/progress.py` — both are inline). Its concrete code/security/doc items are useful; its scoring
  (B+ 88.5) and "ready to ship / monetize / un-quarantine now" verdicts are not.

## How recommendations were triaged

All actionable recommendations from the teammate reviews were triaged into
[../_archive/ROADMAP_NEXT.md §9](../_archive/ROADMAP_NEXT.md). The rule applied: **anything predicated on the gate having
passed (ship now, un-quarantine Track B/C, pricing/SaaS) is deferred until the real validation gate
passes** (validation-first). Genuinely useful items were adopted as tickets or roadmap backlog.
