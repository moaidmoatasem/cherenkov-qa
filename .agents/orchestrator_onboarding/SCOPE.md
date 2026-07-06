# Scope: CHERENKOV QA Onboarding & KT Package

## Architecture
This project produces the onboarding and knowledge transfer package for CHERENKOV QA at `/home/moaid/teamwork_projects/cherenkov_onboarding`.
The package includes:
- `sessions/` containing three markdown session scripts (Session A, B, and C).
- `casts/` containing two executable shell scripts for asciinema terminal recording simulations.
- `run_demo.sh` at the root of the package, which launches the target FastAPI server, runs validation, injects a regression bug, re-validates (detecting the bug), and cleans up.
- `PITCH_DECK.md` containing a 10-slide outline.
- `FAQ_OBJECTIONS.md` containing >=20 questions and answers.
- An updated `docs/INDEX.md` in `/home/moaid/cherenkov-qa` integrating these files.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Directory & Session Scripts | Set up folders, create Session A, B, C scripts under `sessions/` | none | DONE |
| 2 | Demo Harness & Cast Scripts | Create `run_demo.sh` and `casts/cast_session_a.sh` & `cast_session_b.sh` | M1 | DONE |
| 3 | Pitch Deck & FAQ | Create `PITCH_DECK.md` and `FAQ_OBJECTIONS.md` | M1 | DONE |
| 4 | Docs Integration & Verification | Update `/home/moaid/cherenkov-qa/docs/INDEX.md`, run verification on demo harness | M2, M3 | DONE |

## Interface Contracts
- `run_demo.sh` must execute `cherenkov validate` using `bin/cherenkov` relative to `/home/moaid/cherenkov-qa` or system path.
- The controllable FastAPI app is running in `/home/moaid/cherenkov-qa/target/target_api.py`.
- No background processes from target API (uvicorn) or validation must be left running after `run_demo.sh` exits.
- Return exit code 0 on successful verification.
