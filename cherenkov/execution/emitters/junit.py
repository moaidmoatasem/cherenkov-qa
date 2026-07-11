from __future__ import annotations

import xml.etree.ElementTree as ET  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from typing import Any


class JUnitEmitter:
    """Emits DivergenceReports into the JUnit XML format for native import into Xray, Zephyr, and TestRail."""

    def emit(self, report: Any, spec_path: str) -> str:
        """Convert a DivergenceReport into a valid JUnit XML string."""
        testsuites = ET.Element("testsuites", name="Cherenkov API Conformance")
        testsuite = ET.SubElement(
            testsuites,
            "testsuite",
            name="conformance-drift",
            tests=str(len(getattr(report, "findings", []))),
            failures="0",
            errors="0",
            skipped="0",
            time="0",
        )

        failures_count = 0

        for finding in getattr(report, "findings", []):
            testcase = ET.SubElement(
                testsuite,
                "testcase",
                name=getattr(finding, "summary", "Response drift detected"),
                classname=getattr(finding, "endpoint", "unknown").replace("/", "."),
                time="0",
            )

            # Since these are all findings from a DivergenceReport, they are considered failures/drifts
            failure = ET.SubElement(
                testcase,
                "failure",
                message=getattr(finding, "description", ""),
                type=getattr(finding, "violation_type", "conformance-drift")
            )

            actual = getattr(finding, "actual", "")
            expected = getattr(finding, "expected", "")
            method = getattr(finding, "http_method", "ANY")

            details = (
                f"Endpoint: {getattr(finding, 'endpoint', 'unknown')}\n"
                f"Method: {method}\n"
                f"Expected: {expected}\n"
                f"Actual: {actual}\n"
                f"Remediation: {getattr(finding, 'remediation', '')}"
            )
            failure.text = details
            failures_count += 1

        testsuite.set("failures", str(failures_count))

        ET.indent(testsuites, space="  ")
        return '<?xml version="1.0" ?>\n' + ET.tostring(testsuites, encoding="unicode")
