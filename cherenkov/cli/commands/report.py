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
import os
import sys
from pathlib import Path

import click

from cherenkov.divergence.report_diff import ReportDiff, diff_reports


def _find_latest_run() -> tuple[str | None, str | None]:
    """Scan .cherenkov/runs/ and return (path_to_events_jsonl, error_msg)."""
    runs_dir = os.path.join(os.getcwd(), ".cherenkov", "runs")
    if not os.path.isdir(runs_dir):
        return None, None
    subdirs = sorted(
        (d for d in os.listdir(runs_dir)
         if os.path.isdir(os.path.join(runs_dir, d))),
        reverse=True,
    )
    for sub in subdirs:
        events = os.path.join(runs_dir, sub, "events.jsonl")
        if os.path.isfile(events):
            return events, None
        return None, f"events.jsonl not found in {sub}"
    return None, None


def _summarise_events(events: list[dict]) -> dict:
    """Compute summary statistics from an events list."""
    total = len(events)
    passed = sum(
        1 for e in events
        if e.get("verdict") == "AUTO_APPROVE" and e.get("stage") == "REVIEW"
    )
    skipped = sum(1 for e in events if "skipping low richness" in e.get("msg", ""))
    return {
        "total_scenarios": total,
        "passed_scenarios": passed,
        "success_rate": passed / total if total else 0.0,
        "skipped": [e for e in events if "skipping low richness" in e.get("msg", "")],
    }


def _format_run_summary(events: list[dict], fmt: str) -> str:
    """Format an events.jsonl run summary."""
    stats = _summarise_events(events)
    if fmt != "text":
        return json.dumps(stats, indent=2, default=str)
    lines = [f"{stats['passed_scenarios']}/{stats['total_scenarios']} passed"]
    if stats["skipped"]:
        lines.append(f"Skipped low-richness endpoints: {len(stats['skipped'])}")
        for e in stats["skipped"]:
            method = e.get("method", "")
            path = e.get("path", "")
            if path:
                lines.append(f"  {method} {path}")
    return "\n".join(lines)

_SEV_COLOUR = {
    "HIGH": "red", "CRITICAL": "red",
    "MEDIUM": "yellow",
    "LOW": "cyan",
}


@click.command("report")
@click.argument("input_file", type=click.Path(exists=True), required=False)
@click.option(
    "-d", "--diff", "baseline_file", default=None,
    help="Baseline divergence JSON to compare against (shows new vs resolved).",
)
@click.option(
    "--format", "fmt", default=None,
    type=click.Choice(["text", "json", "markdown"], case_sensitive=False),
    help="Output format.  Default: text or auto-detected from --output extension.",
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
    input_file: str | None,
    baseline_file: str | None,
    fmt: str | None,
    output: str | None,
    fail_on_new: bool,
) -> None:
    """Summarise and diff saved divergence reports.

    \b
    INPUT_FILE is a JSON file written by `cherenkov verify --output`.
    If omitted, CHERENKOV scans .cherenkov/runs/ for the latest run's events.jsonl.

    \b
    Without --diff, prints a formatted summary of all divergences.
    With --diff <baseline>, shows new / resolved / unchanged counts and lists.

    \b
    Exit codes:
      0 — report processed (or no new divergences when --fail-on-new)
      1 — new divergences found (only with --fail-on-new)
      2 — file read/parse error
    """
    if fmt is None:
        fmt = "json" if output and output.endswith(".json") else "text"
    if input_file is None:
        input_file, err = _find_latest_run()
        if input_file is None:
            click.echo(err or "No runs found", err=True)
            sys.exit(1)
    is_run_report = "events.jsonl" in input_file
    current = _load_report(input_file)
    if current is None:
        sys.exit(2)

    if is_run_report and not baseline_file:
        text = _format_run_summary(current, fmt)
    elif baseline_file:
        baseline = _load_report(baseline_file)
        if baseline is None:
            sys.exit(1)
        # Rate comparison when baseline has success_rate
        if baseline and isinstance(baseline[0], dict) and "success_rate" in baseline[0]:
            prev_rate = baseline[0]["success_rate"]
            stats = _summarise_events(current)
            text = _format_rate_diff(prev_rate, stats, baseline_file, fmt)
        else:
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
        raw = Path(path).read_text()
    except FileNotFoundError:
        click.echo(f"[ERROR] File not found: {path}", err=True)
        return None

    # Empty file = no events
    if not raw.strip():
        return []

    # Try plain JSON parse first for single objects/arrays
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "divergences_json" in data:
            return data["divergences_json"]
    except json.JSONDecodeError:
        pass

    # Try JSON Lines format (one JSON object per line, e.g. events.jsonl)
    try:
        lines = [json.loads(line) for line in raw.strip().splitlines() if line.strip()]
        if lines and all(isinstance(l, dict) for l in lines):
            return lines
    except json.JSONDecodeError:
        pass

    click.echo(f"[ERROR] Could not parse {path}: expected a JSON array of divergences.", err=True)
    return None


# ── formatters ────────────────────────────────────────────────────────────────

def _sev(div: dict) -> str:
    raw = div.get("severity", "MEDIUM")
    if isinstance(raw, dict):
        raw = raw.get("value", "MEDIUM")
    return str(raw).upper()


def _format_rate_diff(prev_rate: float, stats: dict, baseline_file: str, fmt: str) -> str:
    """Format a success-rate comparison between previous and current run."""
    cur_rate = stats["success_rate"]
    if fmt == "json":
        return json.dumps({
            "baseline": baseline_file,
            "previous_success_rate": prev_rate,
            "current_success_rate": cur_rate,
            "total_scenarios": stats["total_scenarios"],
            "passed_scenarios": stats["passed_scenarios"],
        }, indent=2, default=str)
    lines = [
        "=" * 50,
        "  DIFF REPORT — Success Rate Comparison",
        f"  Baseline: {baseline_file}",
        f"  Previous Success Rate: {prev_rate:.0%}",
        f"  Current  Success Rate: {cur_rate:.0%}",
        "=" * 50,
    ]
    return "\n".join(lines) + "\n"


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
