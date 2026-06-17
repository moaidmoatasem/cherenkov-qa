# Demo — "Catch the AI Cheating"

**Gate G0 / E0.2** · Runtime: ~5 seconds (static gates) or ~30s with Docker (all 6 gates)

> "We let an AI write the tests. Then we let it cheat. Watch CHERENKOV catch it."

## What this proves

When an AI agent generates a test suite and gets a red CI result, it has three common escape routes:

| Cheat | What the agent does | Suite looks like |
|-------|---------------------|-----------------|
| Weakened assertion | `toBe(201)` → `toBeLessThan(500)` | Green. Passes even on 400/500. |
| Deleted check | Removes `toHaveProperty('id')` | Green. Body could be `{}`. |
| Hallucinated oracle | Asserts `auth_token` field that's not in spec | Green locally. Fails on real server. |

CHERENKOV catches all three without trusting the suite's own claims — it re-derives expected behavior from the OpenAPI spec.

## Quick start

```bash
# From the repo root:
python demos/catch-the-ai-cheating/run_demo.py
```

No cloud. No setup. Gates 1–4 run instantly (static analysis).  
Gate 6 (Prism mock dry-run) requires Docker — gracefully skipped if absent.

## What you'll see

```
Beat 1 — Baseline: what a correct spec-derived test looks like
  Gate [syntax            ]  ✓ PASS
  Gate [structure         ]  ✓ PASS
  Gate [ast               ]  ✓ PASS
  Gate [assertion         ]  ✓ PASS
  Gate [tsc               ]  ✓ PASS
  Gate [prism-dryrun      ]  ✓ PASS   (or ○ SKIP if no Docker)
  Verdict : PASS ✓

Beat 2+3 — The cheats

  Cheat 1: Weakened assertion
  Gate [assertion         ]  ✗ FAIL
             ↳ Missing expectation asserting specific status code (toBe(code)).
  Verdict : FAIL ✗

  Cheat 2: Deleted check
  Gate [assertion         ]  ✗ FAIL
             ↳ Missing expectation asserting response body property structure (toHaveProperty).
  Verdict : FAIL ✗

  Cheat 3: Hallucinated oracle
  Gate [assertion         ]  ✓ PASS   ← passes static analysis
  Gate [prism-dryrun      ]  ✗ FAIL   ← caught by dynamic execution against spec mock
             ↳ toHaveProperty('auth_token') — field absent from spec-derived Prism response
  Verdict : FAIL ✗
```

## Fixtures

| File | Cheat pattern | Caught by |
|------|--------------|-----------|
| `fixtures/correct_test.spec.ts` | None — spec-derived baseline | — |
| `fixtures/cheat_weakened_assertion.spec.ts` | `toBeLessThan(500)` instead of `toBe(201)` | Gate 4 (static) |
| `fixtures/cheat_deleted_check.spec.ts` | Body assertions deleted | Gate 4 (static) |
| `fixtures/cheat_hallucinated_oracle.spec.ts` | `auth_token` field not in spec | Gate 6 (Prism, requires Docker) |

## How CHERENKOV catches it

The 6-gate REVIEW stage re-derives truth from the spec — it does **not** trust the suite's own assertions:

1. **Syntax** — no empty code, no markdown leakage
2. **Structure** — correct Playwright + openapi-fetch client imports
3. **AST** — uses the openapi-fetch client (no raw fetch/axios bypass)
4. **Assertion** — every test must assert `.toBe(<3-digit-status>)` AND `toHaveProperty()`/`typeof`
5. **TypeScript compilation** — type-safe against the spec-generated types
6. **Prism dry-run** — executes test against a spec-derived Prism mock; hallucinated fields fail here

This is the **integrity catch** — different from test generation tools that only show you what was produced.

## Gate G0 / E0.2 evidence

When this demo runs and catches all three cheats:
1. Screenshot or record the terminal output (`asciinema rec demo.cast`)
2. Save the output to `demos/catch-the-ai-cheating/evidence/run_$(date +%Y%m%d).txt`
3. That output **is** the Gate G0 / E0.2 artifact — keep it

See `docs/ROADMAP_AQE.md` (E0.2) and `docs/demos/CATCH_THE_AI_CHEATING.md` for context.
