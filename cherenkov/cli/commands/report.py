"""
cherenkov/cli/commands/report.py — `cherenkov report`.

Reads a saved divergence JSON (written by `cherenkov verify --output`) and
formats it as human-readable text, Markdown, or machine-readable JSON.
Supports `--diff <baseline>` to compare two runs and show what is new vs
resolved — the CI-diffing flow described in docs/ROADMAP_NEXT.md §9b.

Examples:
  # Summarise a saved report:
  cherenkov report run-2026-06-27.json

  # Compare against a baseline:
  cherenkov report run-today.json --diff run-yesterday.json

  # CI gate: exit 1 if new divergences appeared:
  cherenkov report run-today.json --diff run-yesterday.json --fail-on-new

  # Write structured JSON for downstream tooling:
  cherenkov report run-today.json --format json --output summary.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from cherenkov.divergence.report_diff import ReportDiff, diff_reports

_SEV_COLOUR = {
    "HIGH": "red", "CRITICAL": "red",
    "MEDIUM": "yellow",
    "LOW": "cyan",
}


@click.command("report")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--diff", "baseline_file", default=None,
    help="Baseline divergence JSON to compare against (shows new vs resolved).",
)
@click.option(
    "--format", "fmt", default="text",
    type=click.Choice(["text", "json", "markdown"], case_sensitive=False),
    help="Output format.  Default: text.",
)
@click.option(
    "--output", "-o", default=None,
    help="Write the formatted report to this file instead of stdout.",
)
@click.option(
    "--fail-on-new", is_flag=True, default=False,
    help="Exit with code 1 if any new divergences appear vs --diff baseline (CI gate).",
)
def report_cmd(
    input_file: str,
    baseline_file: str | None,
    fmt: str,
    output: str | None,
    fail_on_new: bool,
) -> None:
    """Summarise and diff saved divergence reports.

    \b
    INPUT_FILE is a JSON file written by `cherenkov verify --output`.

    \b
    Without --diff, prints a formatted summary of all divergences.
    With --diff <baseline>, shows new / resolved / unchanged counts and lists.

    \b
    Exit codes:
      0 — report processed (or no new divergences when --fail-on-new)
      1 — new divergences found (only with --fail-on-new)
      2 — file read/parse error
    """
    current = _load_report(input_file)
    if current is None:
        sys.exit(2)

    if baseline_file:
        baseline = _load_report(baseline_file)
        if baseline is None:
            sys.exit(2)
        diff = diff_reports(baseline, current)
        text = _format_diff(diff, fmt, input_file, baseline_file)
    else:
        diff = None
        text = _format_summary(current, fmt, input_file)

    if output:
        Path(output).write_text(text)
        click.echo(f"Report written to {output}")
    else:
        click.echo(text)

    if fail_on_new and diff and diff.has_new:
        sys.exit(1)


# ── loaders ───────────────────────────────────────────────────────────────────

def _load_report(path: str) -> list[dict] | None:
    try:
        data = json.loads(Path(path).read_text())
        if isinstance(data, list):
            return data
        # Accept a single dict (cert-style wrapping) — not our format but handle gracefully
        if isinstance(data, dict) and "divergences_json" in data:
            return data["divergences_json"]
        click.echo(f"[ERROR] {path}: expected a JSON array of divergences.", err=True)
        return None
    except FileNotFoundError:
        click.echo(f"[ERROR] File not found: {path}", err=True)
        return None
    except json.JSONDecodeError as exc:
        click.echo(f"[ERROR] Could not parse {path}: {exc}", err=True)
        return None


# ── formatters ────────────────────────────────────────────────────────────────

def _sev(div: dict) -> str:
    raw = div.get("severity", "MEDIUM")
    if isinstance(raw, dict):
        raw = raw.get("value", "MEDIUM")
    return str(raw).upper()


def _format_summary(divs: list[dict], fmt: str, label: str) -> str:
    if fmt == "json":
        return json.dumps(
            {"source": label, "total": len(divs), "divergences": divs},
            indent=2, default=str,
        )
    if fmt == "markdown":
        return _md_summary(divs, label)
    return _text_summary(divs, label)


def _format_diff(diff: ReportDiff, fmt: str, current_label: str, baseline_label: str) -> str:
    if fmt == "json":
        return json.dumps(
            {
                "current": current_label,
                "baseline": baseline_label,
                "summary": diff.summary_line,
                "new_count": len(diff.new),
                "resolved_count": len(diff.resolved),
                "unchanged_count": len(diff.unchanged),
                "new": diff.new,
                "resolved": diff.resolved,
                "unchanged": diff.unchanged,
            },
            indent=2, default=str,
        )
    if fmt == "markdown":
        return _md_diff(diff, current_label, baseline_label)
    return _text_diff(diff, current_label, baseline_label)


# ── text format ───────────────────────────────────────────────────────────────

def _text_summary(divs: list[dict], label: str) -> str:
    lines: list[str] = []
    width = 68
    lines.append("=" * width)
    lines.append(f"  CHERENKOV Report — {label}")
    lines.append(f"  {len(divs)} divergence(s) total")
    lines.append("=" * width)
    for i, d in enumerate(divs, 1):
        sev = _sev(d)
        ep = d.get("endpoint", "")
        dc = d.get("divergence_class", "")
        if isinstance(dc, dict):
            dc = dc.get("value", dc)
        lines.append(f"\n{i}. [{sev}] {dc}  {ep}")
        lines.append(f"   Spec says : {str(d.get('claim_a', ''))[:100]}")
        lines.append(f"   Actual    : {str(d.get('claim_b', ''))[:100]}")
    lines.append("")
    return "\n".join(lines)


def _text_diff(diff: ReportDiff, current: str, baseline: str) -> str:
    lines: list[str] = []
    width = 68
    lines.append("=" * width)
    lines.append(f"  CHERENKOV Diff — {current}")
    lines.append(f"  Baseline    : {baseline}")
    lines.append(f"  Result      : {diff.summary_line}")
    lines.append("=" * width)

    if diff.new:
        lines.append(f"\n  NEW ({len(diff.new)}) — divergences not in baseline:")
        for d in diff.new:
            sev = _sev(d)
            lines.append(f"    + [{sev}] {d.get('endpoint', '')}  {d.get('claim_a', '')[:60]}")

    if diff.resolved:
        lines.append(f"\n  RESOLVED ({len(diff.resolved)}) — divergences fixed since baseline:")
        for d in diff.resolved:
            sev = _sev(d)
            lines.append(f"    - [{sev}] {d.get('endpoint', '')}  {d.get('claim_a', '')[:60]}")

    if diff.unchanged:
        lines.append(f"\n  UNCHANGED ({len(diff.unchanged)}) — still present:")
        for d in diff.unchanged:
            sev = _sev(d)
            lines.append(f"    = [{sev}] {d.get('endpoint', '')}  {d.get('claim_a', '')[:60]}")

    lines.append("")
    return "\n".join(lines)


# ── markdown format ───────────────────────────────────────────────────────────

def _md_summary(divs: list[dict], label: str) -> str:
    lines = [f"# CHERENKOV Report — `{label}`\n", f"**Total:** {len(divs)} divergence(s)\n"]
    if divs:
        lines.append("| # | Severity | Endpoint | Spec says | Actual |")
        lines.append("|---|----------|----------|-----------|--------|")
        for i, d in enumerate(divs, 1):
            sev = _sev(d)
            ep = d.get("endpoint", "")
            ca = str(d.get("claim_a", ""))[:60]
            cb = str(d.get("claim_b", ""))[:60]
            lines.append(f"| {i} | {sev} | `{ep}` | {ca} | {cb} |")
    return "\n".join(lines) + "\n"


def _md_diff(diff: ReportDiff, current: str, baseline: str) -> str:
    lines = [
        "# CHERENKOV Diff\n",
        f"**Current:** `{current}`  \n**Baseline:** `{baseline}`\n",
        f"**Result:** {diff.summary_line}\n",
    ]
    if diff.new:
        lines.append(f"## New ({len(diff.new)})\n")
        for d in diff.new:
            lines.append(f"- **[{_sev(d)}]** `{d.get('endpoint', '')}` — {str(d.get('claim_a',''))[:80]}")
        lines.append("")
    if diff.resolved:
        lines.append(f"## Resolved ({len(diff.resolved)})\n")
        for d in diff.resolved:
            lines.append(f"- **[{_sev(d)}]** `{d.get('endpoint', '')}` — {str(d.get('claim_a',''))[:80]}")
        lines.append("")
    if diff.unchanged:
        lines.append(f"## Unchanged ({len(diff.unchanged)})\n")
        for d in diff.unchanged:
            lines.append(f"- **[{_sev(d)}]** `{d.get('endpoint', '')}` — {str(d.get('claim_a',''))[:80]}")
        lines.append("")
    return "\n".join(lines)
