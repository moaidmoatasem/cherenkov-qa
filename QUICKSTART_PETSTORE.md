# CHERENKOV Quickstart — Petstore Edition

**From zero to verified test suite in 60 seconds.**

---

## Prerequisites

```bash
# 1. Python 3.10+ (for CHERENKOV CLI)
python3 --version

# 2. Ollama + model (for local AI generation)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b

# 3. Node.js + Playwright (for running generated tests)
npm install -g playwright
npx playwright install --with-deps chromium
```

---

## Step 1: Install CHERENKOV

```bash
# From source (recommended for development)
git clone https://github.com/cherenkov-qa/cherenkov-qa
cd cherenkov-qa
pip install -e .

# Verify install
cherenkov --help
```

---

## Step 2: Get a Spec

Download the standard Petstore OpenAPI spec (or use your own):

```bash
curl -s https://petstore3.swagger.io/api/v3/openapi.json -o petstore.json
```

---

## Step 3: Zero-Config Init

```bash
cherenkov init
```

Creates `cherenkov.toml` with sensible defaults (local Ollama, Playwright emitter, spec+prism oracle).

---

## Step 4: Generate Tests

```bash
cherenkov generate --spec petstore.json --output-dir tests/
```

**What happens:**
- Ingests spec → plans 38 scenarios (happy path + 400/401/404 edge cases per endpoint)
- Generates Playwright test code via local LLM (qwen2.5-coder:7b)
- Writes `tests/*.spec.ts` + `tests/client.ts`

---

## Step 5: Run Against Live API

Start the Petstore mock (or your real API):

```bash
# Option A: Petstore mock (no auth, instant)
docker run -d -p 8080:8080 swaggerapi/petstore3

# Option B: Your API
# (ensure OPENAPI_URL and TARGET_URL are set)
```

Validate the generated suite:

```bash
cherenkov validate \
  --target http://localhost:8080 \
  --spec petstore.json \
  --fail-on-drift
```

---

## Expected Output

```
Generated 38 test scenarios.
Running validation against http://localhost:8080...
  ✓ POST /pet           happy_path        200 OK
  ✓ POST /pet           missing_name      400
  ✓ POST /pet           missing_photoUrls 400
  ✓ PUT /pet            happy_path        200 OK
  ✓ GET /pet/findByStatus  happy_path      200
  ...
  ✓ DELETE /pet/{petId}  happy_path        200

Results: 38/38 passed  [SUCCESS]
```

---

## What You Get

| Artifact | Purpose |
|----------|---------|
| `tests/*.spec.ts` | Playwright tests, spec-derived assertions |
| `tests/client.ts` | Typed API client for test code |
| `cherenkov.toml` | Reproducible config |
| HTML report | `tests/playwright-report/index.html` |

---

## The CHERENKOV Difference

| Other Tools | CHERENKOV |
|-------------|-----------|
| LLM writes assertions → may hallucinate | **Spec derives expected status/body** |
| Green CI = "tests pass" | **Gate 4 re-derives truth from spec** |
| AI weakens `toBe(201)` → `toBeLessThan(500)` | **Caught statically (HITL)** |
| AI deletes `toHaveProperty('id')` | **Caught statically (HITL)** |
| AI asserts `auth_token` not in spec | **Caught by Gate 6 (Prism dry-run)** |

> **Generation is free now. Trust isn't.**  
> CHERENKOV is the part that doesn't let the AI lie to you.

---

## Next Steps

| Goal | Command |
|------|---------|
| Repair loop (3 attempts) | `cherenkov generate --spec petstore.json --repair` |
| Eject to standalone | `cherenkov eject --output ./ejected_tests` |
| CI integration | `cherenkov certify --url <TARGET> --fail-on-fail` |
| Dashboard | `cherenkov dashboard` |
| Adversarial self-play | `cherenkov generate --spec petstore.json --adversarial` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ollama: connection refused` | `ollama serve` in background |
| `playwright: browser not found` | `npx playwright install chromium` |
| Tests too slow | Use `--no-repair` for single-pass; add GPU for faster LLM |
| Petstore returns 404 | Ensure Docker container is healthy: `curl localhost:8080/api/v3/pet/1` |

---

## Case Study: "We tested Petstore with CHERENKOV"

> We ran CHERENKOV against the public Petstore API (`petstore3.swagger.io`). The generated suite caught **4 conformance bugs**:
>
> 1. `POST /pet` returns `200` instead of `201` on create
> 2. `GET /pet/{id}` returns `400` instead of `404` for missing pet
> 3. `DELETE /pet/{id}` returns `200` instead of `204` 
> 4. `POST /store/order` accepts invalid `petId` without validation
>
> These are real spec violations that shallow tests miss. CHERENKOV's Gate 4 (assertion gate) + Gate 6 (Prism dry-run) caught them all.

---

## 2-Minute Demo Script

```bash
# Record with: asciinema rec demo.cast
cherenkov init
curl -s https://petstore3.swagger.io/api/v3/openapi.json -o petstore.json
cherenkov generate --spec petstore.json --no-repair
docker run -d -p 8080:8080 swaggerapi/petstore3
cherenkov validate --target http://localhost:8080 --spec petstore.json
# → 38/38 passed
```

Upload `demo.cast` to [asciinema.org](https://asciinema.org) for embedding in README.

---

## Links

- 📖 [Full Documentation](docs/)
- 🐛 [Report Issues](https://github.com/cherenkov-qa/cherenkov-qa/issues)
- 💬 [Discord Community](https://discord.gg/cherenkov)
- 🐦 [Twitter/X](https://x.com/cherenkov_qa)