"""
CHERENKOV security/snyk_bridge.py — import Snyk scan results into agent-accessible format.
Parses `snyk test --json` output, writes structured findings to agent_memory/,
and surfaces issues for agent-driven remediation.
"""

from __future__ import annotations

import json
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel, Field


class SnykVulnerability(BaseModel):
    vuln_id: str = Field(alias="id")
    title: str
    severity: str  # critical, high, medium, low
    package_name: str = Field(alias="packageName")
    package_manager: str = Field(alias="packageManager")
    version: str
    fixed_in: List[str] = Field(alias="fixedIn", default_factory=list)
    description: str = ""
    from_path: List[str] = Field(alias="from", default_factory=list)
    exploit_maturity: str = Field(alias="exploitMaturity", default="")


class SnykIaCIssue(BaseModel):
    issue_id: str = Field(alias="id")
    title: str
    severity: str
    resource: str
    path: str
    description: str = ""
    remediation: str = ""


class SnykCodeIssue(BaseModel):
    vuln_id: str = Field(alias="id")
    title: str
    severity: str
    file_path: str = Field(alias="filePath")
    line_start: int = Field(alias="lineStart")
    line_end: int = Field(alias="lineEnd")
    description: str = ""
    remediation: str = ""


class SnykReport(BaseModel):
    vulnerabilities: List[SnykVulnerability] = []
    infrastructure_as_code: List[SnykIaCIssue] = Field(
        default_factory=list, alias="infrastructureAsCode"
    )
    code_issues: List[SnykCodeIssue] = Field(default_factory=list, alias="code")


AGENT_MEMORY_PATH = Path(__file__).resolve().parent.parent.parent / "agent_memory"
FINDINGS_FILE = AGENT_MEMORY_PATH / "snyk-findings.md"


def run_snyk_scan(target_dir: str | None = None) -> dict[str, Any]:
    """Execute `snyk test --json` and return parsed output."""
    try:
        cmd = ["snyk", "test", "--json"]
        if target_dir:
            cmd.extend(["--file", target_dir])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        print(
            "error: `snyk` binary not found. Install from https://snyk.io/download",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("error: snyk scan timed out after 300s", file=sys.stderr)
        sys.exit(1)
    if result.returncode not in (0, 1):
        print(
            f"snyk scan failed (rc={result.returncode}): {result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    return json.loads(result.stdout)


def parse_report(raw: dict[str, Any]) -> SnykReport:
    """Parse raw Snyk JSON into structured models."""
    return SnykReport(**raw)


def reset_findings() -> None:
    """Reset snyk-findings.md to a clean no-vulnerabilities state."""
    AGENT_MEMORY_PATH.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Snyk Vulnerability Findings",
        "",
        f"Last scan: {now}",
        "",
        "## Summary",
        "",
        "| Severity | Open Source | IaC | Code | Total |",
        "|----------|-------------|-----|------|-------|",
        "| Critical | 0 | 0 | 0 | 0 |",
        "| High | 0 | 0 | 0 | 0 |",
        "| Medium | 0 | 0 | 0 | 0 |",
        "| Low | 0 | 0 | 0 | 0 |",
        "| **Total** | **0** | **0** | **0** | **0** |",
        "",
        "## Remediation Log",
        "",
        "| Date | Vuln ID | Package | Fix Applied | Agent |",
        "|------|---------|---------|-------------|-------|",
        "",
    ]
    FINDINGS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_findings(report: SnykReport) -> None:
    """Write structured findings to agent_memory/snyk-findings.md."""
    AGENT_MEMORY_PATH.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Snyk Vulnerability Findings",
        "",
        f"Last scan: {now}",
        "",
        "## Summary",
        "",
        "| Severity | Open Source | IaC | Code | Total |",
        "|----------|-------------|-----|------|-------|",
    ]

    def sev_count(items, sev):
        return sum(1 for i in items if i.severity.lower() == sev.lower())

    for sev in ("critical", "high", "medium", "low"):
        os_count = sev_count(report.vulnerabilities, sev)
        iac_count = sev_count(report.infrastructure_as_code, sev)
        code_count = sev_count(report.code_issues, sev)
        total = os_count + iac_count + code_count
        lines.append(
            f"| {sev.title()} | {os_count} | {iac_count} | {code_count} | {total} |"
        )

    total_all = (
        len(report.vulnerabilities)
        + len(report.infrastructure_as_code)
        + len(report.code_issues)
    )
    lines.append(
        f"| **Total** | **{len(report.vulnerabilities)}** | **{len(report.infrastructure_as_code)}** | **{len(report.code_issues)}** | **{total_all}** |"
    )
    lines.append("")

    if report.vulnerabilities:
        lines.append("## Open Source Vulnerabilities")
        lines.append("")
        lines.append("| ID | Package | Version | Severity | Fix | Exploit |")
        lines.append("|----|---------|---------|----------|-----|---------|")
        for v in report.vulnerabilities:
            fix = ", ".join(v.fixed_in) if v.fixed_in else "no fix"
            em = v.exploit_maturity or "none"
            lines.append(
                f"| {v.vuln_id} | {v.package_name} | {v.version} | {v.severity} | {fix} | {em} |"
            )
        lines.append("")

    if report.infrastructure_as_code:
        lines.append("## IaC Misconfigurations")
        lines.append("")
        lines.append("| ID | Resource | Severity | Path |")
        lines.append("|----|----------|----------|------|")
        for i in report.infrastructure_as_code:
            lines.append(f"| {i.issue_id} | {i.resource} | {i.severity} | {i.path} |")
        lines.append("")

    if report.code_issues:
        lines.append("## Snyk Code Issues")
        lines.append("")
        lines.append("| ID | Title | Severity | File | Lines |")
        lines.append("|----|-------|----------|------|-------|")
        for c in report.code_issues:
            lines.append(
                f"| {c.vuln_id} | {c.title} | {c.severity} | {c.file_path} | {c.line_start}-{c.line_end} |"
            )
        lines.append("")

    lines.append("## Remediation Log")
    lines.append("")
    lines.append("| Date | Vuln ID | Package | Fix Applied | Agent |")
    lines.append("|------|---------|---------|-------------|-------|")
    lines.append("")

    content = "\n".join(lines) + "\n"
    FINDINGS_FILE.write_text(content, encoding="utf-8")
    print(f"wrote findings to {FINDINGS_FILE}")


def print_summary(report: SnykReport) -> None:
    """Print a human-readable summary to stdout."""
    total = (
        len(report.vulnerabilities)
        + len(report.infrastructure_as_code)
        + len(report.code_issues)
    )
    print(f"\nSnyk Scan Results - {total} total issues")
    print(f"  Open Source: {len(report.vulnerabilities)}")
    print(f"  IaC:         {len(report.infrastructure_as_code)}")
    print(f"  Code:        {len(report.code_issues)}")
    for v in report.vulnerabilities:
        fix = v.fixed_in[0] if v.fixed_in else "?"
        print(f"  [{v.severity:>7}] {v.package_name}@{v.version} -> {fix}")


def main() -> None:
    """CLI entry point: parse Snyk JSON and write agent memory."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Import Snyk scan results for agent remediation"
    )
    parser.add_argument(
        "input", nargs="?", help="Path to snyk JSON file (reads stdin if omitted)"
    )
    parser.add_argument(
        "--run", action="store_true", help="Run snyk test --json directly"
    )
    parser.add_argument("--dir", help="Target directory for --run")
    parser.add_argument(
        "--reset", action="store_true", help="Reset findings to clean state"
    )
    args = parser.parse_args()

    if args.reset:
        reset_findings()
        print(f"reset findings to clean state -> {FINDINGS_FILE}")
        return

    if args.run:
        raw = run_snyk_scan(args.dir)
    elif args.input:
        try:
            raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"error: file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"error: invalid JSON in {args.input}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(
                "error: no input provided (pipe JSON or pass a file path)",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            raw = json.loads(raw_input)
        except json.JSONDecodeError as e:
            print(f"error: invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)

    report = parse_report(raw)
    print_summary(report)
    write_findings(report)


if __name__ == "__main__":
    main()
