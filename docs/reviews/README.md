# External / Teammate-Agent Reviews — index + caveats

This folder archives reviews produced by other agents. They contain useful signal **and**
material errors. Read them through the project's honest baseline ([HANDOVER.md](../HANDOVER.md),
[SCOPE_LEDGER.md](../SCOPE_LEDGER.md)) — not the other way around.

## Archived

- `2026-06-04_mistral_comprehensive_review.md` — broad technical+business review. **Caveat: treat its
  status claims as UNRELIABLE.** It repeats the **fabricated** "Track A SHIPPED / 4/5 QA gates passed /
  ready to ship" (see [HANDOVER.md §5](../HANDOVER.md)), and contains factual errors: it lists the 6
  Review gates as implemented (Gate 4 Novelty and Gate 6 LLM-quality do **not** exist — see
  [GAP_REPORT.md](../GAP_REPORT.md)), and references files that do not exist (`ai/strip_think.py`,
  `core/progress.py` — both are inline). Its concrete code/security/doc items are useful; its scoring
  (B+ 88.5) and "ready to ship / monetize / un-quarantine now" verdicts are not.

## How recommendations were triaged

All actionable recommendations from the teammate reviews were triaged into
[../ROADMAP_NEXT.md §9](../ROADMAP_NEXT.md). The rule applied: **anything predicated on the gate having
passed (ship now, un-quarantine Track B/C, pricing/SaaS) is deferred until the real validation gate
passes** (validation-first). Genuinely useful items were adopted as tickets or roadmap backlog.
