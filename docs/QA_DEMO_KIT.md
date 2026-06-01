# CHERENKOV Phase 11 — QA Demo Kit

## The Goal
Show 5 QA engineers the tool catching a real conformance bug live. Ask one question. Get 3 "yes" answers. That's done.

---

## The One Question
> **"Would you keep these tests in your suite? What would make you keep more of them?"**

---

## Pre-Demo Checklist (2 minutes)

```bash
# Terminal 1: Start Target API (normal mode)
cd target && source .venv/bin/activate
uvicorn target_api:app --host 127.0.0.1 --port 8000

# Terminal 2: Verify green
cd /home/moaid/cherenkov-qa
./bin/cherenkov validate --target http://localhost:8000
# → happy_path PASSED, password_too_short FAILED (422 vs 400 — the real bug)
```

---

## The 7-Minute Live Demo Script

### Act 1: "Here's what the tool does" (2 min)
Open the spec file and show the contract:
```bash
cat stub/target_spec.json | python3 -m json.tool | head -30
```
Say: *"This is a standard OpenAPI spec. The tool reads it, generates Playwright tests, and runs them against your real server."*

Show the generated test — it's 10 lines of readable TypeScript:
```bash
cat stub/generated_tests/happy_path.spec.ts
```
Say: *"No magic. Standard Playwright, standard openapi-fetch client. You can read every line."*

### Act 2: "Watch it catch a real bug" (3 min)
Run validation against the live server:
```bash
./bin/cherenkov validate --target http://localhost:8000
```

Point out the output:
- **happy_path [PASSED]** — with tightening suggestions (`consider -> expect(data.email).toBe(body.email)`)
- **password_too_short [FAILED]** — Expected 422 (what the spec says), Got 400 (what the server actually returns)

Say: *"The spec promises 422 for validation errors. The server returns 400. That's a real conformance drift bug, and the test caught it without anyone writing it by hand."*

### Act 3: "You're never locked in" (1 min)
```bash
./bin/cherenkov eject --output /tmp/demo_eject
ls /tmp/demo_eject/
cat /tmp/demo_eject/client.ts
```
Say: *"One command strips everything. What's left is vanilla Playwright + openapi-fetch. No vendor dependency. If you stop using the tool tomorrow, your tests still run."*

### Act 4: The Question (1 min)
> **"Would you keep these tests in your suite? What would make you keep more of them?"**

Record their answer verbatim. That's the data.

---

## Tracking Sheet

| # | Name | Role | Date | "Keep these?" | Feedback (verbatim) |
|---|------|------|------|---------------|---------------------|
| 1 |      |      |      | Yes / No      |                     |
| 2 |      |      |      | Yes / No      |                     |
| 3 |      |      |      | Yes / No      |                     |
| 4 |      |      |      | Yes / No      |                     |
| 5 |      |      |      | Yes / No      |                     |

**Ship when:** 3 of 5 say "Yes."


---

## If They Ask Hard Questions

| Question | Honest Answer |
|----------|---------------|
| "Does it handle auth?" | Phase 7 detects 401s and suggests token-refresh setup. Suggest-only — it won't touch your code. |
| "What if the spec changes?" | Phase 7 contract-drift healer diffs response shapes against snapshots and flags regressions. |
| "Can I customize the tests?" | Yes. They're standard .spec.ts files. Edit them however you want. The tool won't overwrite your changes. |
| "What model does it use?" | Qwen 2.5-coder:7b running locally via Ollama. Your spec never leaves your machine. |
| "What if I want to stop using it?" | `./bin/cherenkov eject --output my_tests`. Done. Zero residual dependencies. |

---

## After All 5 Demos

If 3+ say yes: **You shipped.** The tool generates tests that QA professionals would keep. That was the whole thesis.

If fewer than 3: Read the verbatim feedback. The gap between "no" and "yes" is your Week 2 roadmap.
