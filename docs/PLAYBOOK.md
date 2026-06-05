# CHERENKOV QA — Run & Test Playbook

A reproducible, end-to-end playbook for booting the full stack (FastAPI backend +
Vite/React dashboard + local Ollama LLM) and verifying every subsystem. Every command
below was executed and confirmed on **2026-06-05** (WSL Ubuntu-24.04, Node v20.20.2,
Python 3.12.3).

> Run everything **inside WSL** (`wsl -d Ubuntu-24.04 --cd /home/moaid/cherenkov-qa`).
> The project is Linux-native; Windows `python3`/paths will not resolve the package layout.

---

## 0. Prerequisites (one-time)

```bash
# Python backend deps (already present on this machine)
python3 -c "import fastapi, uvicorn, requests"        # must not error

# Frontend deps
cd track-b-c-deferred/dashboard && npm install
npx playwright install chromium                        # browser for E2E

# Local LLM — Ollama must be running with the generation model
curl -s http://127.0.0.1:11434/api/tags                # expect qwen2.5-coder:7b in the list
```

Generation model is `qwen2.5-coder:7b` (see `/api/v1/health` → `gen_model`).
Embedding model `nomic-embed-text` is used for the RAG schema index.
**On CPU, generation is ~10x slower (~30s/scenario).** A GPU is recommended for real runs.

---

## 1. Boot the stack

Two long-lived processes. Keep each in its own terminal (or `nohup ... &` + `disown`).

```bash
# Terminal A — Backend (FastAPI on :8000)
python3 scripts/start_dashboard_api.py --port 8000

# Terminal B — Frontend (Vite dev server on :3000, proxies /api/v1 -> :8000)
cd track-b-c-deferred/dashboard && npm run dev
```

Health check:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
# {"status":"online","device":"unknown","gen_model":"qwen2.5-coder:7b",...}

curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/    # 200
```

Open **http://localhost:3000** in a browser. WSL2 forwards `localhost`, so the Windows
browser reaches it directly.

---

## 2. Track A — core system smoke + unit tests

```bash
python3 run_tests.py        # 11 cache/accounting + provider + substrate checks  -> ALL PASS
python3 -m pytest tests/ -q # 23 tests (golden snapshot, DAST mutation, HITL auth,
                            #           mutation-validate, RAG schema index)       -> 23 passed (~6s)
```

**Note:** `tests/test_mutation_validate.py` does **not** hang (a prior report claimed it
did — not reproducible; the full suite completes in ~6s).

---

## 3. Backend API integration checks

```bash
B=http://127.0.0.1:8000/api/v1
curl -s $B/health
curl -s $B/divergences            # real divergence corpus (D-01..D-04)
curl -s $B/tests                  # generated Playwright specs on disk

# Ingest a spec (drives the IngestStage + richness/mutation engine)
curl -s -X POST $B/ingest -F "file=@/tmp/petstore.json;type=application/json"

# Error-path contracts
curl -s -o /dev/null -w "%{http_code}\n" -X POST $B/ingest                 # 400 (no file/url)
curl -s -o /dev/null -w "%{http_code}\n" -X POST $B/divergences/act \
     -H 'Content-Type: application/json' -d '{"divergence_id":"nope","action":"reject"}'  # 404
```

Endpoints verified: `health, ingest, run, tests, review/approve|reject|edit, validate,
eject, divergences, divergences/act, ws/live`.

---

## 4. Live LLM pipeline (the real generation loop)

```bash
SPEC=$(curl -s -X POST $B/ingest -F "file=@/tmp/petstore.json;type=application/json" \
       | python3 -c 'import sys,json;print(json.load(sys.stdin)["spec_path"])')
curl -s -X POST $B/run -H 'Content-Type: application/json' -d "{\"spec_path\":\"$SPEC\"}"
tail -f scratch/backend.log     # watch the staged JSON events
```

Confirmed stage flow against live Ollama:

```
INGEST  -> richness scoring, low-richness endpoints skipped
PLAN    -> scenarios_count: 2
GENERATE-> ollama qwen2.5-coder:7b  "code ok"  (~29s on CPU)
REVIEW  -> quality_score, verdict (pass | regenerate)
ORCHESTRATOR -> D2 planner feedback loop / Prism dry-run on failure
```

The loop is genuinely model-backed and self-healing (replans on TSC-compile / dry-run
failure). With the minimal petstore happy-path it exhausts alternative mutations and stops
gracefully — expected, not a crash.

---

## 5. Frontend / Dashboard E2E (real Chromium)

```bash
cd track-b-c-deferred/dashboard
npx playwright test tests/dashboard_e2e.spec.ts     # 10/10 PASS (~19s)
```

Covers all 10 screens: Sidebar shell, Overview, Truth Map, Divergences (filter + detail
drawer), Author by Intent, Signals (Performance/Visual/Coverage tabs), Memory & Pairing,
Governance, Settings (persistence), and the Ctrl+K Command Palette.

### Visual playbook (screenshots of every screen)

```bash
npx playwright test tests/capture_screens.spec.ts   # writes PNGs to scratch/playbook/
```

`scratch/playbook/` → `00-landing` … `09-command-palette`. Captured with **0 page/console
errors**. (Write screenshots **outside** `test-results/` — Playwright wipes that dir at the
start of each run.)

---

## 6. Teardown

```bash
# Ctrl+C each terminal, or:
pkill -f start_dashboard_api ; pkill -f vite
```

---

## Verified status (2026-06-05)

| Area | Result |
|------|--------|
| Track A `run_tests.py` | ✅ ALL PASS |
| Track A `pytest tests/` (23) | ✅ 23 passed ~6s (no hang) |
| Backend API + error contracts | ✅ 200/400/404 as specified |
| Live LLM pipeline (Ollama) | ✅ real generation, self-healing replan |
| Dashboard E2E (10 screens) | ✅ 10/10 PASS |
| Screenshot capture (10 screens) | ✅ 0 page/console errors |

### Known observations (not blockers)
- Ingest skips low-richness endpoints (e.g. petstore `POST /pets` at richness 0.1) — by design.
- CPU-mode generation ~10x slower; backend logs a `device status` WARN. Use GPU for real runs.
- Per `docs/HANDOVER.md`, Track B/C dashboard remains **exploratory** until the Track A
  5-QA validation gate passes — these results are evidence, not a shipping sign-off.
