# E0.3 Practitioner Kit — the last Gate G0 item

> **Goal:** ≥3 external QA practitioners (not the maintainer, not friends-being-nice) complete the
> quickstart **cold and unaided**, and rate it useful. This is the only remaining G0 exit criterion
> (`HANDOVER.md` — E0.1/E0.2/E0.4 are done). Nothing public launches until this passes
> (`docs/EXECUTION_PLAN.md` §3.5, F1 countermeasure).

---

## 1. Who to recruit

**Primary pool (per `docs/reviews/STRATEGY_REVIEW_2026-07-05.md` §8.4):** Egypt's ESTB/ISTQB
community — 9,000+ certified professionals, including holders of the new **CT-GenAI**
certification, i.e. people credentialed in exactly this problem space. Channels:

- SECC / Software Testing Day network and its speaker/alumni lists
- ISTQB CT-GenAI certificate-holder groups (LinkedIn)
- AUC Venture Lab founder network (QA-adjacent startups)

**Secondary pool:** QA/SDET communities on LinkedIn/dev.to who have shipped API test automation.

**Disqualifiers:** anyone who has contributed to this repo, been walked through the tool, or has a
personal relationship that would bias "is this useful?"

## 2. Recruitment message (copy-paste)

> Subject: 30 minutes to break my QA tool — no prep, no help
>
> I'm building CHERENKOV, an open-source (Apache-2.0) tool that audits AI-generated test suites
> for cheating (weakened/deleted/hallucinated assertions) and verifies APIs against their OpenAPI
> spec with reproducible HTTP evidence. Before anything public, I need practitioners to run the
> quickstart **cold** — README only, no help from me — and tell me honestly where it fails you.
>
> The ask: ~30 minutes. Install from the README, run the demo, point it at an API (yours or one I
> provide), fill in a 10-question survey. Brutal honesty explicitly requested: "I got stuck and
> gave up at step 2" is a *more valuable* result for me than polite success.
>
> Repo: https://github.com/moaidmoatasem/cherenkov-qa

## 3. Cold-run protocol

**Setup (facilitator):** send only the repo URL and the survey link. Answer no questions until the
run is over. Ask the practitioner to note the clock time at start and at "first meaningful result."

**Practitioner steps (README-only — do not paste these into the recruitment message; the README
must carry them on its own):**

1. Install from the README's quickstart (git clone + `pip install .`).
2. Run `cherenkov demo` — the no-setup 60-second demo.
3. Run `bash demos/catch-the-ai-cheating/run_demo.sh` — the integrity-catch sequence.
4. Point `cherenkov verify --url <server> --spec <spec>` at a real API: their own if they have one
   handy, else the fallback target below.
5. Stop at 30 minutes wherever they are; fill in the survey.

**Fallback verify target (if they have no API of their own):** run the bundled server locally —
`CHERENKOV_ENV=ci SUBSTRATE_PROVIDER=mock cherenkov review --port 8765`, then
`curl -s http://127.0.0.1:8765/openapi.json > /tmp/spec.json` and
`cherenkov verify --url http://127.0.0.1:8765 --spec /tmp/spec.json`.

**What the facilitator records per run:**

| Field | Value |
|---|---|
| Completed unaided (all 4 steps)? | yes / stopped at step N |
| Time to first meaningful result (demo output) | minutes |
| Time to verify against a real API | minutes / did not reach |
| Blockers, verbatim | free text |
| Environment | OS, Python version |

## 4. Survey (send immediately after the run; ≤10 questions)

1. How far did you get? (all steps / stopped at step __)
2. Minutes from `git clone` to first meaningful output?
3. Where did you get stuck or slow down? (verbatim, per step)
4. Did the demo make clear *what the tool catches that others don't*? (1–5 + why)
5. Did `verify` produce anything you'd act on for the API you pointed it at? (yes/no/what)
6. If you know Schemathesis or similar: what would you use CHERENKOV for that you wouldn't use
   them for — and vice versa?
7. Would you add `check-suite --fail-on-finding` to a CI pipeline you own? (yes/no/why)
8. What almost made you quit?
9. What's missing before you'd recommend it to a colleague? (one thing)
10. May we quote your answers anonymously? (yes/no)

## 5. Pass criteria (verbatim from the execution plan)

- **≥3 practitioners** complete the quickstart unaided, **and**
- they rate it useful (Q4 or Q5 positive), **and**
- every blocker they hit is either fixed or documented before launch.

**Kill/pivot trigger:** if practitioners consistently can't articulate what it does that
Schemathesis doesn't (Q6), the positioning — not the recruiting — is the problem. Stop and revisit
before spending more reach.

## 6. Logging results

Create `docs/e0.3/runs/<date>-<initials>.md` per practitioner with the §3 table + survey answers.
When three runs pass, flip E0.3 in `HANDOVER.md` and Gate G0 is closed.
