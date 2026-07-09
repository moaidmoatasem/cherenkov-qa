# Black-Box Functional Assessment — CHERENKOV `verify` / `certify`

**Date:** 2026-07-08
**HEAD:** `aac3c17`
**Method:** Black-box functional testing against a **real, live API** — no `--demo`, no stubs, no mocks, no `SUBSTRATE_PROVIDER=mock`.
**Target under test:** CHERENKOV's own FastAPI backend (`cherenkov review`), a genuine live service exposing a real `/openapi.json` (81 paths, "CHERENKOV QA Observability Dashboard Server 1.3.0"). Self-dogfooding, exactly as `.github/workflows/self-dogfood.yml` does.

> Network policy in this environment blocks all external egress (petstore3.swagger.io, httpbin.org → 403 policy denial), so a real *local* server is the only honest non-mock target available. It is a real uvicorn process serving real handlers over real HTTP.

---

## TL;DR

The headline capability — *"verify a live API against its OpenAPI spec — find spec↔implementation divergences"* — **does not detect real divergences in its default offline mode.** Three independently confirmed spec-vs-implementation divergences were injected into the spec; `verify`, `verify --fail-on-divergence`, and `certify` all reported **0 divergences and exited 0**, and `certify` issued a **signed [PASS] certificate** for the divergent API.

Root cause observed at the wire level: the only requests the target actually receives during a "verify" are **hardcoded Swagger-Petstore probes** (`GET /pet/0`, `POST /pet`, `GET /store/inventory`, …), not the target's own 81 endpoints. The verdict's own `spec_coverage` dimension admits *"Only 0% of spec endpoints probed."*

Input validation on the **spec file** is honest (missing → exit 2, malformed → exit 2). Offline `generate` produces structurally valid, non-vacuous Playwright tests. Those are the bright spots.

---

## What was tested (real inputs, real server)

| # | Command | Input | Result |
|---|---------|-------|--------|
| 1 | `verify --url … --spec real-openapi.json` (rich, offline) | Real 81-path spec, conformant server | Grade D / SUSPECT, 81/81 pass, 0 divergences, **exit 0**. `Offline: 0 hypothesis(es)` for **every** endpoint. |
| 2 | `verify … --simple` | same | `No divergences found.` exit 0 |
| 3 | `verify … --spec divergent-spec.json --fail-on-divergence` | Spec with **3 confirmed real divergences** | **0 divergences, 82/82 pass, exit 0** ❌ |
| 4 | `certify --url … --spec divergent-spec.json` | same divergent spec | **Signed certificate `[PASS]`, Divergences: 0, exit 0** ❌ |
| 5 | `verify --spec /no/such/file` | missing spec file | `[ERROR] Spec file not found` exit 2 ✅ |
| 6 | `verify --spec malformed.json` | invalid JSON | `[ERROR] Could not parse spec` exit 2 ✅ |
| 7 | `verify --url http://127.0.0.1:59999` | **dead server (nothing listening)** | Grade D / SUSPECT, **exit 0** ❌ |
| 8 | `generate --spec real-openapi.json --output-dir … --no-repair` | real spec, no LLM available | 2 valid `.spec.ts` files emitted, then **hung ~2 min on unreachable LLM** ⚠️ |

### The injected divergences (ground truth confirmed by direct `curl`)

| Divergence | Spec claims | Server actually returns |
|---|---|---|
| A — documented-but-missing | `GET /api/v1/totally-fake-endpoint` → 200 | **404** |
| B — missing required fields | `/health` 200 body requires `status`,`version`,`uptime_seconds` | `{"status":"ok"}` only |
| C — status mismatch | `/healthz` → **201** only | **200** |

A tool that "finds spec↔implementation divergences" must catch at least B and C. It caught **none**.

---

## Findings

### F1 — CRITICAL: Offline `verify` does not detect real spec↔implementation divergences
Against a spec with 3 confirmed divergences, `divergent-report.json` shows `total: 82, passed: 82, pass_rate: 1.0, divergences: []`. The `rich_verdict.dimensions` entry for `divergence_probe` reads `"score": 1.0, "detail": "0 divergence(s) confirmed", "duration_ms": 0` — i.e. it did zero work and declared a pass. The offline hypothesis engine emits `Offline: 0 hypothesis(es)` for every non-Petstore endpoint, so there is nothing to validate responses against.

### F2 — CRITICAL: `--fail-on-divergence` CI gate is unsound
The gate exited **0** on a demonstrably divergent API. A gate that cannot fail provides false assurance; wiring it into CI (as the README and `certify-gate.yml` intend) would green-light non-conformant deployments.

### F3 — CRITICAL: `certify` issues a signed PASS certificate for a divergent API
`certify` printed `CHERENKOV Certificate [PASS] … Divergences: 0` and exited 0 for the same 3-divergence spec. The entire Certificate/Authority proposition (Rung 3) rests on the offline divergence detector, which does not work — so the certificate attests to conformance that was never checked.

### F4 — HIGH: Verify's real network probes are hardcoded Petstore paths (R1, confirmed live)
The target's uvicorn access log during a verify run shows the only non-`/health` requests it received were:
```
  GET /pet/0                                  -> 404
  GET /pet/findByStatus?status=INVALID_VALUE_XYZ    -> 404
  GET /pet/findByStatus?status=MUTATION_INJECTED_VALUE -> 404
  POST /pet                                   -> 404
  GET /store/inventory                        -> 404
```
None of the target's 81 real endpoints were probed for divergences. The verdict corroborates this: `spec_coverage` → *"Only 0% of spec endpoints probed", "0.0% coverage"*. Consequently the `mutation_oracle` (0.75) and `divergence_probe` sub-scores are computed against Swagger-Petstore, not the API under test. This is the `run_proof()` hardcoded-`PROOF_RUN_PROBES` issue (HANDOVER "R1") observed end-to-end.

### F5 — HIGH: Verify against an unreachable server returns exit 0
Pointing verify at a dead port (nothing listening) still produced a verdict (`Grade D / SUSPECT`, `Est. fix time: none needed`) and **exited 0** — no connection error surfaced. A target that is completely down should hard-fail, not pass.

### F6 — MEDIUM: Misleading console output overstates work done
For every endpoint the console prints `── Probing GET /api/v1/… ──`, implying the endpoint is being exercised. The access log proves the server never receives those requests — only inert offline hypothesis generation runs (`0 hypothesis(es)`). The output misrepresents what the tool actually did.

### F7 — MEDIUM: Incoherent verdict semantics
Every run reports `Grade D / Overall SUSPECT` **and** `Est. fix time: none needed` **and** `0 divergences` simultaneously. "SUSPECT" is driven solely by the `spec_coverage` FAIL, which is itself an artifact of F4 (probing the wrong paths). The grade is not a function of the target's actual conformance.

### F8 — LOW: Offline `generate` hangs instead of failing fast
`generate … --no-repair` emitted 2 valid test files then blocked ~2 min on an unreachable LLM (`localhost:11434` → connection refused) before being killed. With no LLM backend it should degrade or fail fast, not hang. Coverage was 2 of 81 endpoints.

---

## What works (honest positives)

- **Server / CLI plumbing is real and solid.** `cherenkov review` boots a real uvicorn server (`/health` 200 in ~3 s); the full CLI surface loads; `doctor` reports effective config.
- **Spec-file input validation is honest.** Missing file → `exit 2`; malformed JSON → `exit 2` with a clear parse error. No false success on bad spec input.
- **Offline `generate` output is non-vacuous.** The two emitted Playwright tests use real spec paths, schema-derived request bodies, and meaningful assertions (`expect(response.status).toBe(201)`, `expect(data).toHaveProperty('status')`) — not `expect(true).toBe(true)` filler. This is consistent with the "meaningful-assertion gate" claim, at least for the happy-path/auth templates.

---

## Assessment

The **integrity wedge the product markets — "catch the divergence / catch the AI cheating"** — is not exercised by the default offline path against a real, arbitrary API. Offline `verify`/`certify` structurally cannot observe target responses against the spec (0 hypotheses, 0% coverage, Petstore-only probes), yet they emit **PASS verdicts, green CI exit codes, and signed certificates**. For a *truth/integrity* tool, a confident false-negative is worse than an error: it launders "we never checked" into "we checked and it's fine."

The richer LLM path (`--llm`, Ollama) was unavailable in this environment and may generate real hypotheses — but the tool should not report PASS/`[PASS]`/exit 0 when it is running in a mode that cannot verify. It should surface *"cannot verify offline — coverage 0%"* as a hard, non-passing outcome.

## Recommended fixes (ordered)

1. **Make offline `verify` actually validate observed responses against the spec** (status codes, required response fields, declared error codes, documented-but-missing/undocumented endpoints). This is deterministic and needs no LLM — the 3 injected divergences are all statically checkable.
2. **Fail closed on zero real coverage.** If `spec_coverage == 0%` (no target endpoint was actually probed), `verify` must not return a PASS grade, `--fail-on-divergence` must exit non-zero, and `certify` must refuse to issue a certificate.
3. **Fix R1 (F4):** drive probes from the loaded `--spec`, not hardcoded `PROOF_RUN_PROBES`. Remove Petstore fallback whenever a spec is supplied.
4. **Fail fast on unreachable target (F5)** and on unavailable LLM backend in `generate` (F8) instead of passing / hanging.
5. **Stop printing `── Probing … ──` for endpoints that are not sent (F6);** make the verdict grade a function of measured conformance (F7).

## Reproduction

```bash
# 1. Real live target
CHERENKOV_ENV=ci cherenkov review --host 127.0.0.1 --port 8765 &
curl -sf http://127.0.0.1:8765/openapi.json > real-openapi.json     # 81 paths

# 2. Inject 3 real divergences (fake endpoint / missing required health fields / 201-vs-200)
#    -> divergent-spec.json  (see table above)

# 3. Divergence detector has no teeth offline:
cherenkov verify --url http://127.0.0.1:8765 --spec divergent-spec.json --fail-on-divergence
#   -> 0 divergences, 82/82 pass, EXIT 0

# 4. False attestation:
cherenkov certify --url http://127.0.0.1:8765 --spec divergent-spec.json
#   -> Certificate [PASS], Divergences: 0, EXIT 0

# 5. Proof of R1 — inspect the target's access log: only /pet, /store/inventory probes arrive.
```
