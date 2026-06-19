# CHERENKOV -- Session Handover

**Date:** 2026-06-20
**HEAD:** `f66a4da` on `main`
**Tests:** 696 unit tests passing; G0 integrity suite 10/10; E11 60/60
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
| E1.5 -- install friction to near-zero | PENDING | Needs PyPI publish or Docker image (packaging epic #200-#207) |

---

## What landed this session

| SHA | What |
|---|---|
| `f66a4da` | feat(e1.1): `cherenkov verify` command (E1.1) -- 8 tests |
| `3075235` | feat(g0): E0.1 DONE -- 6 real divergences across 3 public APIs |
| `1ca48e4` | feat(reflector): offline idiom replay + Skeptic/Generate injection (--learn) |

---

## Next code actions (ordered by impact)

1. **E1.5 -- one-line install** -- publish to PyPI (`python3 -m build && twine upload`) or build the Docker image (Packaging EPIC #200-#207, ticket P-1). This is the last E1 gate item.
2. **Phase 2 -- MCP verification server (E2.1)** -- publish `cherenkov mcp` as an installable MCP server so any agent can call CHERENKOV to verify a suite. Spec: `docs/specs/MCP_VERIFICATION_SERVER.md`.
3. **Tauri updater signing key** -- `desktop/src-tauri/tauri.conf.json` `pubkey` is empty; needs `cargo tauri signer generate` from a terminal with the Tauri CLI installed (`cargo install tauri-cli`).

---

## Environment hazards

- **Shared working tree**: `~/cherenkov-qa` shared across concurrent agent sessions. Always check `git branch` before committing.
- **CRLF noise**: `stub/generated_tests/*.spec.ts` and `npm-package/` show as modified constantly -- cosmetic, do not commit.
- **GitHub CLI**: not authenticated in this agent environment -- PRs must be created manually.
- **Note on E1.2 warning in ROADMAP_AQE.md**: the "do NOT merge the stale branch" caveat is outdated -- `cherenkov/sdet/` is already on `main` via #92. E1.2 is done.
