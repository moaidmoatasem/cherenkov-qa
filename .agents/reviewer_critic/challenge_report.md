# Adversarial Challenge Report

## Challenge Summary

**Overall risk assessment**: LOW

## Challenges

### [Low] Challenge 1: Hardcoded sleep delays in cast scripts
- Assumption challenged: The user will record these casts interactively or review them.
- Attack scenario: When run without the mock `sleep` bypass (`sleep() { :; }`), these scripts take upwards of 10-12 minutes to run, which could cause terminal session timeouts or excessive developer friction.
- Blast radius: Mild developer friction during manual walkthrough.
- Mitigation: Add a command-line argument to the cast scripts (e.g. `./cast_session_a.sh --no-sleep`) that conditionally bypasses sleep, rather than forcing the user to manually export a shell function override.

### [Low] Challenge 2: CLI argument discrepancy in simulated command outputs
- Assumption challenged: The commands typed on the screen in the casts match the actual commands run under the hood.
- Attack scenario: The scripts output `$ cherenkov generate --spec openapi.json --out tests/` but then run `cherenkov generate --spec ... --out ...` which fails due to the CLI lacking the `--out` parameter (it actually uses `--output`).
- Blast radius: Mild confusion if a developer tries to copy the echoed command verbatim and encounters an option parsing error.
- Mitigation: Update the `echo` commands and the actual invocations to use `--output` instead of `--out`.

## Stress Test Results

- **Port 8000 Conflict Resolution** -> verified running another process on port 8000 before executing `run_demo.sh` -> PASS (`fuser -k 8000/tcp` kills the conflicting process cleanly and restarts uvicorn).
- **Graceful Termination** -> verified sending SIGINT/Ctrl+C to `run_demo.sh` during execution -> PASS (The trap on EXIT triggers immediately, killing uvicorn and removing the Docker container).

## Unchallenged Areas

- **Docker Registry Connectivity** -> The script assumes the `stoplight/prism:5` image is pre-cached or that the network is available to download it. If Docker is offline and the image isn't local, it will print a warning and skip Phase 3, which degrades gracefully.
