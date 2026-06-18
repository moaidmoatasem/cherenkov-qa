# CHERENKOV -- Session Handover

**Date:** 2026-06-18
**HEAD:** `b98cbdfd` on `main` -- synced with `origin/main`
**Tests:** unit tests passing (clean); G0 integrity suite 5/5
**Branch:** `main` -- working tree clean (generated-test CRLF noise is cosmetic)

---

## Gate G0 status (EPIC #535 -- the shipping blocker)

G0 requires E0.1 AND E0.2 AND E0.3 AND E0.4.

| Exit criterion | Status | Evidence |
|---|---|---|
| E0.1 -- real divergences on 3rd-party APIs | NOT YET | Needs a live run against real APIs |
| E0.2 -- integrity catch (catch the AI cheating) | DONE | `demos/catch-the-ai-cheating/`; CI-gated; 4/4 scenarios pass |
| E0.3 -- 3 practitioners complete quickstart unaided | NOT YET | User-research activity |
| E0.4 -- honest differentiation sentence vs Schemathesis | DONE | `docs/NORTH_STAR.md` section 8 |

**Gate G0 is 2/4. E0.1 is the only purely-code blocker remaining.**

---

## What landed this session

| SHA | What |
|---|---|
| `b98cbdfd` | docs(g0): E0.4 differentiation statement (EPIC #535) |
| `7a93fd81` | ci: gate-g0 + unit-test jobs added to cherenkov-ci.yml |
| `5c6b500c` | docs: previous handover |
| `837e19c4` | fix(api): auth on /knowledge/query + _validate_spec_url async |
| `d5fda086` | merge: QA-18 fix + security hardening + HITL ignore |

Security fixes on `origin/main` (all done, not to revisit):
settings.py timeouts, ollama_client None-guard, playwright_invoke timeouts+shlex,
prism_mock timeouts+FileNotFoundError, mcp/handlers URL scheme check,
api.py eject auth + SSRF blocklist + settings protection,
review.py TSC timeout from settings + silent-exception logging,
.gitignore secrets, requirements.txt upper bounds.

---

## Next action: E0.1 (the remaining code-side G0 blocker)

Run CHERENKOV against at least 3 real public APIs and capture at least 2 genuine divergences.

Suggested targets (all have public OpenAPI specs, no auth for basic endpoints):
1. **JSONPlaceholder** -- `https://jsonplaceholder.typicode.com` (fake REST; no real divergences likely, but validates the runner)
2. **PetStore** -- `https://petstore3.swagger.io/api/v3` (the canonical demo spec, will likely show real divergences)
3. **dog.ceo** or **open-meteo.com** -- small public APIs with published specs

Steps:
```bash
# Install the CLI
pip install -e .

# Run against PetStore (or replace with a real local target)
cherenkov run --spec https://petstore3.swagger.io/api/v3/openapi.json \
              --url https://petstore3.swagger.io/api/v3

# Capture any divergences to docs/evidence/e0.1_divergences.md
```
Record the run output (divergences found, gates passed/failed) as evidence in `docs/evidence/` so E0.1 is anchored to a real artefact, not a claim.

---

## Remaining backlog (post-G0)

1. **Tauri updater signing key** -- `desktop/src-tauri/tauri.conf.json` `pubkey` is empty; needs `cargo tauri signer generate` from a terminal with the Tauri CLI installed.
2. **E1.2 -- meaningful-assertion gate** -- port the `feat/92-coverage-sdet` concept cleanly onto main (do NOT merge the stale branch -- it has 542k-line deletions). This is the product version of E0.2.
3. **E0.3** -- 3 practitioners complete quickstart unaided (user-research, not a code task).

---

## Environment hazards

- **Shared working tree**: `~/cherenkov-qa` shared across concurrent agent sessions. Always `git branch` before committing; commit each file immediately after editing.
- **CRLF noise**: `stub/generated_tests/*.spec.ts` and `npm-package/` show as modified constantly -- cosmetic, do not commit.
- **GitHub CLI**: not authenticated in this agent environment -- PRs must be created manually.
