# CHERENKOV — Week 0 Starter (runnable)

Three pieces, run in order. None of this is pipeline infrastructure — it's the
validation instrument. Building it does not break the Validate-First rule.

```
target/    the controllable API with a bug toggle      (the test range)
stub/      openapi-fetch typed client (Delta D1)        (the ammunition)
notebook/  generate + score, and the Day-4 green→red    (the trigger)
```

---

## 0. Pre-flight (30 min, do once)

```bash
# models
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b          # not used in Week 0 gen, but pull now

# V1 — is prefix caching real on your box?
#   send 2 calls with the SAME system prompt, different user text; 2nd faster?
# V2 — run openapi-typescript on your MESSIEST spec, not just a clean one.
#   garbage types? note it; scope Week 0 to clean specs.
```

## 1. Target API (the test range)

```bash
cd target
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn target_api:app --reload --port 8000
# verify: open http://localhost:8000/docs and http://localhost:8000/openapi.json
curl http://localhost:8000/openapi.json > ../stub/target_spec.json
```

## 2. Stub (the ammunition — Delta D1)

```bash
cd ../stub
npm init -y
npm i -D typescript openapi-typescript
npm i openapi-fetch @playwright/test
npx openapi-typescript ./target_spec.json -o ./generated-types.ts
# client.ts (already here) imports those types — that's the whole client. No class.
```

## 3. Generate + score (the trigger — Days 1-2)

```bash
cd ../notebook
pip install requests
python generate_and_score.py ../stub/target_spec.json --client-types ../stub/generated-types.ts --out ../stub/generated_tests
# reads the MEANINGFUL ASSERTION RATE at the end. Want > 60%.
# inspect generated_tests/*.spec.ts by hand — are the assertions real?
```

## 4. Day 4 — the whole point (green → red)

```bash
# put the generated .spec.ts files where Playwright + the client can run them,
# wire playwright.config.ts baseURL to http://localhost:8000, then:
cd notebook
bash day4_green_red.sh
# PASS = green with bug off, red with bug on. That transition IS the validation.
```

## 5. Day 5 — the human gate

Show a QA lead the generated tests + the caught bug. Ask: *"Would you keep
these in your suite? If not, what would change?"*

```
PROCEED  rate > 60% AND bug caught AND QA approves  → begin Week 1
PIVOT    shallow / missed bug / lukewarm            → maintenance or cloud gen
STOP     rate < 30%                                 → local-7B thesis is wrong
```

---

## What this scaffold deliberately omits

No `contracts.py`, no orchestrator, no FastAPI backend, no SQLite, no DAG.
All of that is Week 2-3 and only after this gate passes. If any agent suggests
building it now, that's the scope creep this whole structure exists to stop.
Anchor to **v3.1 + delta**. There is no v4.x or v6.0.
