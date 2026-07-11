from __future__ import annotations

from html import escape
from typing import Any


def _attr(value: str) -> str:
    return escape(str(value), quote=True)


def _text(value: str) -> str:
    return escape(str(value))


class JUnitEmitter:
    """Emits DivergenceReports into the JUnit XML format for native import into Xray, Zephyr, and TestRail."""

    def emit(self, report: Any, spec_path: str) -> str:
        """Convert a DivergenceReport into a valid JUnit XML string."""
        findings = getattr(report, "findings", [])
        failures_count = 0
        testcase_lines: list[str] = []

        for finding in findings:
            name = _attr(getattr(finding, "summary", "Response drift detected"))
            classname = _attr(getattr(finding, "endpoint", "unknown").replace("/", "."))
            message = _attr(getattr(finding, "description", ""))
            ftype = _attr(getattr(finding, "violation_type", "conformance-drift"))
            details = (
                f"Endpoint: {getattr(finding, 'endpoint', 'unknown')}\n"
                f"Method: {getattr(finding, 'http_method', 'ANY')}\n"
                f"Expected: {getattr(finding, 'expected', '')}\n"
                f"Actual: {getattr(finding, 'actual', '')}\n"
                f"Remediation: {getattr(finding, 'remediation', '')}"
            )
            testcase_lines.append(
                f'    <testcase name="{name}" classname="{classname}" time="0">\n'
                f'      <failure message="{message}" type="{ftype}">{_text(details)}</failure>\n'
                f'    </testcase>'
            )
            failures_count += 1

        total = len(findings)
        inner = "\n".join(testcase_lines)
        return (
            '<?xml version="1.0" ?>\n'
            '<testsuites name="Cherenkov API Conformance">\n'
            f'  <testsuite name="conformance-drift" tests="{total}"'
            f' failures="{failures_count}" errors="0" skipped="0" time="0">\n'
            f'{inner}\n'
            f'  </testsuite>\n'
            '</testsuites>\n'
        )
