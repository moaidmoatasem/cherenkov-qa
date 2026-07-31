from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SARIFEmitter:
    """Emits DivergenceReports into the SARIF format for GitHub Advanced Security."""

    def emit(self, report, spec_path: str) -> dict[str, Any]:
        """Convert a DivergenceReport into a valid SARIF v2.1.0 JSON dictionary."""
        results = []
        for finding in getattr(report, "findings", []):
            severity = getattr(finding, "severity", "medium")
            level = "error" if severity in ("high", "critical") else "warning"

            result = {
                "ruleId": getattr(finding, "violation_type", "conformance-drift"),
                "level": level,
                "message": {
                    "text": getattr(finding, "summary", "Response drift detected")
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": spec_path},
                            "region": {"startLine": 1},
                        }
                    }
                ],
                "properties": {
                    "endpoint": getattr(finding, "endpoint", "unknown"),
                    "method": getattr(finding, "http_method", "ANY"),
                    "expected": getattr(finding, "expected", ""),
                    "actual": getattr(finding, "actual", ""),
                    "description": getattr(finding, "description", ""),
                    "remediation": getattr(finding, "remediation", ""),
                },
            }
            results.append(result)

        return {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Cherenkov QA",
                            "informationUri": "https://github.com/moaidmoatasem/cherenkov-qa",
                            "rules": [
                                {
                                    "id": "conformance-drift",
                                    "shortDescription": {
                                        "text": "API Conformance Drift Detected"
                                    },
                                    "fullDescription": {
                                        "text": "The API response drifted from the defined specification."
                                    },
                                }
                            ],
                        }
                    },
                    "invocations": [
                        {
                            # `executionSuccessful` means "the analysis ran",
                            # not "the analysis found nothing". It was `not
                            # results`, so every run that actually detected
                            # drift reported its own invocation as failed —
                            # which is how GitHub decides whether to trust the
                            # upload at all. Finding results IS a successful run.
                            "executionSuccessful": True,
                            # `.isoformat()` on an aware datetime already ends
                            # in "+00:00"; appending "Z" produced "+00:00Z",
                            # two designators, and an invalid SARIF timestamp.
                            "endTimeUtc": datetime.now(timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                            + "Z",
                        }
                    ],
                    "results": results,
                }
            ],
        }
