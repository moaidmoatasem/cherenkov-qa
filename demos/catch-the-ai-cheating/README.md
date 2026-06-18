# Catch the AI Cheating — Gate G0 / E0.2 demonstrator

> **EPIC [#535](https://github.com/moaidmoatasem/cherenkov-qa/issues/535)** (Gate G0). Storyboard: [../../docs/demos/CATCH_THE_AI_CHEATING.md](../../docs/demos/CATCH_THE_AI_CHEATING.md). Thesis: [../../docs/NORTH_STAR.md](../../docs/NORTH_STAR.md).

## What this proves
When an AI/agent generates or edits a test suite, it can **cheat to fake green** in three canonical ways. This demonstrator shows each cheat being **caught**, with a reproducible, dependency-light harness — the nucleus of CHERENKOV's "we don't let the AI cheat" promise.

| Cheat | Fixture | What it does |
|---|---|---|
| **Weakened** | `suite_cheat_weakened.py` | loosens `==` to `< 500` / `is not None` / `in (...)` so a broken response still passes |
| **Deleted** | `suite_cheat_deleted.py` | removes a failing test and drops assertions from a kept test |
| **Hallucinated** | `suite_cheat_hallucinated.py` | asserts on `discount_code`, a field the spec never defines (a fake oracle) |

`openapi.yaml` is the **oracle** (source of truth). `suite_good.py` is the honest baseline. `integrity_check.py` statically compares a candidate suite against the baseline + spec and flags every violation.

## Run it
```bash
# narrative demo (control passes, 3 cheats caught)
PYTHON=python3 ./run_demo.sh

# or one candidate at a time
python3 integrity_check.py --spec openapi.yaml --baseline suite_good.py --candidate suite_cheat_weakened.py

# the assertions, as a test
python3 -m pytest demos/catch-the-ai-cheating/ -q
```

Expected: control → `PASS`; each cheat → `FAIL` with a `[CAUGHT]` line naming the exact subject and how it was weakened/deleted/hallucinated.

## How it works
Pure `ast` static analysis (no execution, stdlib + optional PyYAML):
- **Weakened** — a subject checked with `==` in the baseline now uses only weak comparators (`<`, `!=`, `in`, `is not`, …).
- **Deleted** — a baseline test is gone, or a baseline assertion's subject is no longer checked in a kept test.
- **Hallucinated** — a candidate asserts on a `body[...]` field absent from every `properties` block in the spec.

## Honest scope (what this is / isn't)
This is a **standalone Phase-0 proof of the thesis**, deliberately self-contained so G0 can be demonstrated before the product gate exists. It is **not yet wired into CHERENKOV's runtime gates** — that is **EPIC [#536](https://github.com/moaidmoatasem/cherenkov-qa/issues/536) / E1.2** (the meaningful-assertion gate), which will subsume this logic and run it against agent-generated suites in the real pipeline. The static rules here are intentionally simple and will have false-negatives on adversarial obfuscation; hardening is tracked under E1.3.

## Next steps toward closing E0.2
1. Drive a real agentic generator to produce a suite for a live target, then run this check on its output (turns the demo into genuine E0.2 evidence).
2. Port these three detectors into CHERENKOV's gate engine (#536/E1.2).
3. Add an adversarial fixture corpus + CI (#536/E1.3) so the guarantee is audited, not asserted.
