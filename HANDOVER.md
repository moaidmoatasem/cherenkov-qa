# CHERENKOV -- Session Handover

**Date:** 2026-06-20
**HEAD:** `588d9d4` on `main`
**Tests:** 728 unit tests passing; G0 integrity suite 10/10; E11 60/60
**Branch:** `main` -- working tree clean (generated-test CRLF noise is cosmetic)

---

## Gate G0 status (EPIC #535)

G0 requires E0.1 AND E0.2 AND E0.3 AND E0.4.

| Exit criterion | Status | Evidence |
|---|---|---|
| E0.1 -- real divergences on 3rd-party APIs | **DONE** | `docs/evidence/e0.1_divergences.md` -- 6 divergences across 3 APIs |
| E0.2 -- integrity catch (catch the AI cheating) | DONE | `demos/catch-the-ai-cheating/`; CI-gated; 10/10 pass |
| E0.3 -- 3 practitioners complete quickstart unaided | NOT YET | User-research activity (can't code our way out) |
| E0.4 -- honest differentiation sentence vs Schemathesis | DONE | `docs/NORTH_STAR.md` section 8 |

**Gate G0: 3/4. Only E0.3 (human recruitment) remains.**

---

## AQE Phase 1 status (Rung 1 -- "the Tool people love")

All code-deliverable Phase 1 items are DONE:

| Item | Status | Where |
|---|---|---|
| E1.1 -- `cherenkov verify` UX | **DONE** | `cherenkov/cli/commands/verify.py`; 8 unit tests |
| E1.2 -- meaningful-assertion gate | **DONE** | `cherenkov/sdet/`; 60 tests (E11 landed via #92) |
| E1.3 -- guardrails-can't-be-weakened proof | **DONE** | `demos/catch-the-ai-cheating/`; CI-gated |
| E1.4 -- eject command hardening | **DONE** | `cherenkov/execution/eject.py`; 10 unit tests |
| E1.5 -- install friction to near-zero | **DONE** | `install.sh` (git+pip/pipx one-liner); Dockerfile fixed (3.12, `pip install .`, `cherenkov` entrypoint); `dist/cherenkov-1.0.0.whl` built and verified |

---

## Phase 2 status (Rung 2 -- "the Platform")

| Item | Status | Where |
|---|---|---|
| E2.1 -- `verify_system` MCP tool | **DONE** | `cherenkov/mcp/handlers.py`; 11 unit tests; `cherenkov mcp install` |
| E2.5 -- `cherenkov check-suite` | **DONE** | `cherenkov/cli/commands/check_suite.py`; 13 unit tests |
| E2.2 -- MCP context consumer | PENDING | Four open seams in `cherenkov/mcp/` |
| E2.3 -- Continuous engine | PENDING | Watch spec/code/traffic changes |
| E2.4 -- Source adapters (gRPC/GraphQL) | PENDING | `cherenkov/truth/sources/` |

## What landed this session

| SHA | What |
|---|---|
| `588d9d4` | feat(e2.5): `cherenkov check-suite` — catch AI cheating (13 tests) |
| `8b50b9d` | feat(e2.1): `verify_system` MCP tool — system conformance over MCP (11 tests) |
| `f66a4da` | feat(e1.1): `cherenkov verify` command (E1.1, 8 tests) |
| `3075235` | feat(g0): E0.1 DONE -- 6 real divergences across 3 public APIs |
| `1ca48e4` | feat(reflector): offline idiom replay + Skeptic/Generate injection (--learn) |

---

## Next code actions (ordered by impact)

1. **E2.2 -- MCP context consumer** -- consume MCP for richer system context (four open seams in `cherenkov/mcp/`; spec: `docs/specs/MCP_VERIFICATION_SERVER.md §4.2`).
2. **E2.3 -- Continuous engine** -- watch spec/code/traffic/schema changes and surface divergence on change; `daemon_cmd.py` exists, needs divergence integration.
3. **E2.4 -- Source adapters (gRPC/GraphQL)** -- add to `cherenkov/truth/sources/`; OpenAPI/AsyncAPI/Postman already exist.
4. **E0.3 -- Human validation gate** -- recruit ≥3 QA practitioners to complete quickstart unaided. `install.sh` now reduces their install burden. Cannot be automated.
5. **PyPI publish** -- `twine upload dist/*` once PyPI credentials are available; `dist/cherenkov-1.0.0.whl` is already built.
6. **Tauri updater signing key** -- `desktop/src-tauri/tauri.conf.json` `pubkey` is empty; needs `cargo tauri signer generate` (`cargo install tauri-cli` first).

---

## Environment hazards

- **Shared working tree**: `~/cherenkov-qa` shared across concurrent agent sessions. Always check `git branch` before committing.
- **CRLF noise**: `stub/generated_tests/*.spec.ts` and `npm-package/` show as modified constantly -- cosmetic, do not commit.
- **GitHub CLI**: not authenticated in this agent environment -- PRs must be created manually.
- **Note on E1.2 warning in ROADMAP_AQE.md**: the "do NOT merge the stale branch" caveat is outdated -- `cherenkov/sdet/` is already on `main` via #92. E1.2 is done.
