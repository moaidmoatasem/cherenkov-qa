from typing import Any, Dict
from datetime import datetime, timezone


class SARIFEmitter:
    """Emits DivergenceReports into the SARIF format for GitHub Advanced Security."""

    def emit(self, report, spec_path: str) -> Dict[str, Any]:
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
                            "executionSuccessful": len(results) == 0,
                            "endTimeUtc": datetime.now(timezone.utc).isoformat() + "Z",
                        }
                    ],
                    "results": results,
                }
            ],
        }
