# Demo — "Catch the AI Cheating"

**Gate G0 / E0.2** · Demonstrates CHERENKOV catching AI cheat patterns.

> "We let an AI write the tests. Then we let it cheat. Watch CHERENKOV catch it."

## What this proves

When an AI agent generates a test suite and gets a red CI result, it has common escape routes to fake a green result. This demonstrator shows each cheat being **caught**, with reproducible, dependency-light harnesses.

| Cheat | What the agent does | Suite looks like |
|-------|---------------------|-----------------|
| **Weakened assertion** | `toBe(201)` → `toBeLessThan(500)` or `==` → `< 500` | Green. Passes even on broken responses. |
| **Deleted check** | Removes `toHaveProperty('id')` or drops failing tests | Green. Important checks are missing. |
| **Hallucinated oracle** | Asserts `auth_token` field that's not in spec | Green locally. Fails on real server. |

We provide two versions of the demo:
1. **TypeScript / Playwright (Review Stage)** - Uses the production ReviewStage against spec-derived Playwright tests.
2. **Python / Meaningful Assertion Gate** - A pure Phase-0 standalone proof using Python `ast`.

---

## 1. TypeScript / Playwright Demo (Review Stage)

```bash
# From the repo root:
python demos/catch-the-ai-cheating/run_demo_ts.py
```

No cloud. No setup. Gates 1–4 run instantly (static analysis).  
Gate 6 (Prism mock dry-run) requires Docker — gracefully skipped if absent.

### Fixtures
| File | Cheat pattern | Caught by |
|------|--------------|-----------|
| `fixtures/correct_test.spec.ts` | None — spec-derived baseline | — |
| `fixtures/cheat_weakened_assertion.spec.ts` | `toBeLessThan(500)` instead of `toBe(201)` | Gate 4 (static) |
| `fixtures/cheat_deleted_check.spec.ts` | Body assertions deleted | Gate 4 (static) |
| `fixtures/cheat_hallucinated_oracle.spec.ts` | `auth_token` field not in spec | Gate 6 (Prism, requires Docker) |

The 6-gate REVIEW stage re-derives truth from the spec — it does **not** trust the suite's own assertions.

---

## 2. Python Demo (Meaningful Assertion Gate)

```bash
# narrative demo (control passes, 3 cheats caught)
PYTHON=python3 ./run_demo.sh

# or one candidate at a time
python3 integrity_check.py --spec openapi.yaml --baseline suite_good.py --candidate suite_cheat_weakened.py

# the MeaningfulAssertionGate demo
python demos/catch-the-ai-cheating/run_demo_py.py
```

Expected: control → `PASS`; each cheat → `FAIL` with a `[CAUGHT]` line naming the exact subject and how it was weakened/deleted/hallucinated.

### How it works
Pure `ast` static analysis (no execution, stdlib + optional PyYAML):
- **Weakened** — a subject checked with `==` in the baseline now uses only weak comparators.
- **Deleted** — a baseline test is gone, or a baseline assertion's subject is no longer checked.
- **Hallucinated** — a candidate asserts on a `body[...]` field absent from every `properties` block in the spec.

## Gate G0 / E0.2 evidence

When either demo runs and catches all three cheats:
1. Screenshot or record the terminal output (`asciinema rec demo.cast`)
2. Save the output to `demos/catch-the-ai-cheating/evidence/run_$(date +%Y%m%d).txt`
3. That output **is** the Gate G0 / E0.2 artifact — keep it.
