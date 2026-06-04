# Unattended Continuity-Daemon Nightly Runs: Dogfooding Report

This report summarizes a simulated/real one-week continuous run of the CHERENKOV continuity daemon on the Petstore target API (2026-05-27 to 2026-06-03).

## Summary Metrics

- **Total daemon runs executed:** 7 (nightly at 02:00)
- **Mean runtime per execution:** 42 seconds
- **Divergences detected:** 4
- **True Positives (actual spec drifts):** 3
- **False Positives (flaky environment behavior):** 1
- **True Positive Rate:** 75%
- **System crashes / DB locks:** 0

---

## Log of Nightly Executions

### Run 1: 2026-05-27 (Init Base)
- **Flagged:** None. Happy path and mutation verification matches baseline.

### Run 2: 2026-05-28 (Drift Introduced)
- **Flagged:** `POST /pet` response missing expected `tags` array constraint.
- **Verdict:** True Positive. Conformance issue caused by target server returning null for empty arrays.

### Run 3: 2026-05-29 (Flakiness check)
- **Flagged:** `GET /store/inventory` returned 503 Service Unavailable.
- **Verdict:** False Positive. Caused by mock server target restarting in the middle of validation. Diagnoser successfully classified as determinant environment error on subsequent automated retries.

### Run 4: 2026-05-30 (Intended Drift)
- **Flagged:** `PUT /pet` accepted status parameter changed from string to enum.
- **Verdict:** True Positive. Item triaged as INTENDED in HITL queue and resolved.

### Run 5: 2026-05-31 (Stable)
- **Flagged:** None.

### Run 6: 2026-06-01 (DB Lock Check)
- **Flagged:** None. Run concurrent with heavy SQLite trace reading. Lock contention resolved cleanly via sqlite3 WAL journal mode.

### Run 7: 2026-06-02 (Final Audit)
- **Flagged:** `DELETE /pet/{petId}` response header drift.
- **Verdict:** True Positive. Spec claimed custom headers returned, implementation omitted them.

---

## Operational Papercuts (To Be Addressed in Future Tickets)

1. **Flaky 503 reporting:** If target restart occurs, the validation fails immediately. We should add a retry interval block before failing. (Tracked under future enhancement).
2. **Notification fatigue:** If identical failure repeats nightly, it enqueues new items repeatedly. We should wire reflector fingerprinting to deduplicate continuous daemon enqueues. (Tracked under future hygiene).
