# CHERENKOV E2E Suite — Demo Script

This script provides a reproducible 4-segment demonstration of the CHERENKOV E2E Suite in action, highlighting system health checks, drift detection, test ejection, and the human-in-the-loop (HITL) review dashboard.

## Prerequisites
- A running target application (e.g. `python target/app.py` returning 400 for `password_too_short`).
- The `stub/openapi.yaml` should expect 422 for `password_too_short` (intentional drift).

## Segment 1: System Health Check
Verify the environment and egress policies are ready.

```bash
# Run the doctor command to check capabilities
python cherenkov.py doctor
```
*Expected Output*: Displays configuration, ollama daemon status, node/playwright versions, and egress policy consistency.

## Segment 2: Detect Conformance Drift
Run the test suite against the target and observe the intentional failure.

```bash
# Execute validation (uses incremental cache if unchanged)
python cherenkov.py validate --target http://localhost:8000
```
*Expected Output*: Fails with a mismatch on the `/auth/register` endpoint (expected 422, got 400). A tightening report is printed to the console, and `.cherenkov/report.html` is generated.

## Segment 3: Eject the Suite
Demonstrate the "No Lock-in" invariant by ejecting the generated tests to a standalone Playwright suite.

```bash
# Eject tests
python cherenkov.py eject --output /tmp/standalone_suite

# Run the standalone suite
cd /tmp/standalone_suite
npm install
npx playwright test
```
*Expected Output*: The suite runs using native Playwright without any CHERENKOV dependencies, failing at the exact same drift point.

## Segment 4: Review Dashboard
Launch the web UI to inspect the divergence.

```bash
# Launch review dashboard in demo mode
python cherenkov.py review --web --demo
```
*Expected Output*: A FastAPI server starts on port 8000. Navigating to `http://localhost:8000` shows the prebuilt frontend with demo findings loaded into the HITL queue.
