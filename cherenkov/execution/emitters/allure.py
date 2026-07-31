from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any


def _history_id(full_name: str) -> str:
    """Stable identity for one logical test across runs.

    Allure keys its history, flakiness and trend views on `historyId`. Emitting
    a fresh uuid4 per run — as this module did until 2026-07-31 — makes every
    run look like a brand-new test and permanently empties those views.
    """
    return hashlib.sha1(full_name.encode("utf-8")).hexdigest()


class AllureEmitter:
    """Emits DivergenceReports into Allure-compatible JSON result files.

    **Only real results are emitted.** Until 2026-07-31 this emitter
    synthesized `successful_conformance_check_{i}` entries with
    `"status": "passed"` from an integer count (`_total_tests - len(findings)`),
    inventing named test cases that corresponded to nothing that ran.

    That is the exact failure mode CHERENKOV exists to catch — a report
    asserting green for work never performed — shipped inside CHERENKOV's own
    reporter. A conformance run yields *divergences*, not a roster of named
    passing tests, so there is no honest way to name the passes. The count is
    surfaced as a run-level label instead of being expanded into fictional
    cases. See `docs/evidence/e0.6_claim_verification.md`.
    """

    def emit(self, report, _spec_path: str) -> list[dict[str, Any]]:
        """Convert findings into Allure JSON test cases. One case per finding."""
        results: list[dict[str, Any]] = []
        findings = getattr(report, "findings", []) or []

        start_time = int(time.time() * 1000)
        duration_ms = int(getattr(report, "duration_ms", 0) or 0)
        stop_time = start_time + duration_ms

        # Run-level context, reported honestly as a number rather than expanded
        # into invented per-test entries.
        probes_total = getattr(report, "_total_tests", None)

        for finding in findings:
            endpoint = getattr(finding, "endpoint", "unknown_endpoint")
            full_name = f"cherenkov.conformance.{endpoint}"
            labels = [
                {"name": "framework", "value": "cherenkov"},
                {"name": "severity", "value": getattr(finding, "severity", "normal")},
                {"name": "language", "value": "python"},
            ]
            if probes_total is not None:
                labels.append({"name": "probes_total", "value": str(probes_total)})

            results.append(
                {
                    "uuid": str(uuid.uuid4()),
                    "historyId": _history_id(full_name),
                    "name": endpoint,
                    "fullName": full_name,
                    "status": "failed",
                    "statusDetails": {
                        "message": getattr(finding, "summary", "Drift detected"),
                        "trace": getattr(finding, "description", ""),
                    },
                    "stage": "finished",
                    "start": start_time,
                    "stop": stop_time,
                    "labels": labels,
                }
            )

        return results
