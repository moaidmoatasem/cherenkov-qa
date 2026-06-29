"""
cherenkov/cli/commands/report.py — `cherenkov report`.

Two operating modes:

  FILE MODE (existing behaviour, unchanged):
    cherenkov report run.json
    cherenkov report run.json --diff baseline.json --fail-on-new

  STORE MODE (reads directly from RunStore):
    cherenkov report                          # latest run
    cherenkov report --run <id>              # specific run
    cherenkov report --run <id> --diff <id>  # grade+verdict delta between two runs
    cherenkov report --list                  # recent 20 runs

All modes support --format text|json|markdown and --output <file>.
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

_GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}


@click.command("report")
@click.argument("input_file", type=click.Path(), required=False, default=None)
@click.option(
    "--run", "run_id", default=None,
    help="Run ID from RunStore (or 'latest').  Bypasses INPUT_FILE.",
)
@click.option(
    "--list", "list_runs", is_flag=True, default=False,
    help="List the 20 most recent runs from RunStore.",
)
@click.option(
    "--diff", "baseline_ref", default=None,
    help="Baseline to compare against: a run ID (store mode) or a JSON file path (file mode).",
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
    input_file: str | None,
    run_id: str | None,
    list_runs: bool,
    baseline_ref: str | None,
    fmt: str,
    output: str | None,
    fail_on_new: bool,
) -> None:
    """Summarise and diff cherenkov run reports.

    \b
    Without arguments, shows the latest run from RunStore.
    With INPUT_FILE, reads a divergence JSON written by `cherenkov verify --output`.

    \b
    Exit codes:
      0 — report processed (or no new divergences when --fail-on-new)
      1 — new divergences found (only with --fail-on-new)
      2 — file read/parse error or run not found
    """
    if list_runs:
        text = _handle_list(fmt)
        _emit(text, output)
        return

    if run_id or (input_file is None):
        # Store mode
        target_id = run_id or "latest"
        text, has_new = _handle_run(target_id, baseline_ref, fmt)
        _emit(text, output)
        if fail_on_new and has_new:
            sys.exit(1)
        return

    # File mode (existing behaviour)
    if not Path(input_file).exists():
        click.echo(f"[ERROR] File not found: {input_file}", err=True)
        sys.exit(2)

    current = _load_report(input_file)
    if current is None:
        sys.exit(2)

    if baseline_ref and not Path(baseline_ref).exists():
        # Might be a run ID — try store mode diff against the file
        click.echo(
            f"[WARN] --diff value {baseline_ref!r} is not a file; "
            "try --run <id> --diff <id> for store-mode diff.",
            err=True,
        )
        baseline_ref = None

    if baseline_ref:
        baseline = _load_report(baseline_ref)
        if baseline is None:
            sys.exit(2)
        diff = diff_reports(baseline, current)
        text = _format_diff(diff, fmt, input_file, baseline_ref)
        _emit(text, output)
        if fail_on_new and diff.has_new:
            sys.exit(1)
    else:
        text = _format_summary(current, fmt, input_file)
        _emit(text, output)


# ── store mode ────────────────────────────────────────────────────────────────

def _resolve_run(run_id: str):
    """Return RunRecord or None. Accepts 'latest' as alias."""
    from cherenkov.persistence.run_store import get_run_store
    store = get_run_store()
    if run_id == "latest":
        records = store.list(limit=1)
        return records[0] if records else None
    return store.get(run_id)


def _rich(record) -> dict | None:
    try:
        meta = json.loads(record.meta_json or "{}")
        return meta.get("rich_verdict")
    except Exception:
        return None


def _handle_list(fmt: str) -> str:
    from cherenkov.persistence.run_store import get_run_store
    records = get_run_store().list(limit=20)
    if not records:
        return "No runs found. Run `cherenkov verify --url <url>` to populate history.\n"

    rows = []
    for r in records:
        rv = _rich(r)
        rows.append({
            "run_id": r.run_id,
            "timestamp": r.timestamp,
            "command": r.command,
            "verdict": r.verdict,
            "grade": rv["grade"] if rv else None,
            "divergence_count": r.divergence_count,
            "coverage_pct": r.coverage_pct,
            "duration_ms": r.duration_ms,
            "target_url": r.target_url,
        })

    if fmt == "json":
        return json.dumps(rows, indent=2, default=str)

    if fmt == "markdown":
        lines = ["# Run History\n", "| Run ID | Time | Verdict | Grade | Div | Cov% | URL |",
                 "|--------|------|---------|-------|-----|------|-----|"]
        for r in rows:
            cov = f"{r['coverage_pct']:.0f}" if r['coverage_pct'] is not None else "—"
            grade = r["grade"] or "—"
            lines.append(
                f"| `{r['run_id'][:8]}` | {r['timestamp']} | {r['verdict']} | "
                f"{grade} | {r['divergence_count']} | {cov} | {r['target_url']} |"
            )
        return "\n".join(lines) + "\n"

    # text
    lines = [f"  {'RUN ID':36}  {'TIME':20}  {'VRD':12}  GR  DIV  COV%"]
    lines.append("  " + "-" * 80)
    for r in rows:
        cov = f"{r['coverage_pct']:.0f}%" if r['coverage_pct'] is not None else "  —"
        grade = r["grade"] or "—"
        lines.append(
            f"  {r['run_id']:36}  {r['timestamp']:20}  {r['verdict']:12}  {grade:2}  "
            f"{r['divergence_count']:3}  {cov}"
        )
    return "\n".join(lines) + "\n"


def _handle_run(run_id: str, baseline_ref: str | None, fmt: str) -> tuple[str, bool]:
    """Return (formatted text, has_new_divergences)."""
    record = _resolve_run(run_id)
    if record is None:
        click.echo(f"[ERROR] Run not found: {run_id!r}", err=True)
        sys.exit(2)

    rv = _rich(record)

    if baseline_ref:
        from cherenkov.persistence.run_store import get_run_store
        store = get_run_store()
        try:
            base_delta = store.diff(baseline_ref, record.run_id)
        except ValueError as exc:
            click.echo(f"[ERROR] {exc}", err=True)
            sys.exit(2)

        base_record = store.get(baseline_ref)
        base_rv = _rich(base_record) if base_record else None

        grade_a = base_rv["grade"] if base_rv else None
        grade_b = rv["grade"] if rv else None
        grade_delta = (
            (_GRADE_ORDER.get(grade_b, 0) - _GRADE_ORDER.get(grade_a, 0))
            if grade_a and grade_b else None
        )

        diff_dict = {
            **base_delta,
            "grade_a": grade_a,
            "grade_b": grade_b,
            "grade_delta": grade_delta,
            "overall_a": base_rv["overall"] if base_rv else None,
            "overall_b": rv["overall"] if rv else None,
        }
        text = _format_run_diff(diff_dict, record, base_record, fmt)
        has_new = (base_delta.get("divergence_delta") or 0) > 0
        return text, has_new

    text = _format_run_summary(record, rv, fmt)
    return text, False


def _format_run_summary(record, rv: dict | None, fmt: str) -> str:
    d: dict = {
        "run_id": record.run_id,
        "timestamp": record.timestamp,
        "command": record.command,
        "target_url": record.target_url,
        "verdict": record.verdict,
        "divergence_count": record.divergence_count,
        "coverage_pct": record.coverage_pct,
        "duration_ms": record.duration_ms,
    }
    if rv:
        d["grade"] = rv.get("grade")
        d["overall"] = rv.get("overall")
        d["confidence"] = rv.get("confidence")
        d["risk_flags"] = rv.get("risk_flags", [])
        d["top_findings"] = rv.get("top_findings", [])
        d["dimensions"] = [
            {"name": dim["name"], "score": dim["score"], "grade": dim["grade"], "passed": dim["passed"]}
            for dim in rv.get("dimensions", [])
        ]

    if fmt == "json":
        return json.dumps(d, indent=2, default=str)

    if fmt == "markdown":
        return _md_run_summary(d, rv)

    return _text_run_summary(d, rv)


def _text_run_summary(d: dict, rv: dict | None) -> str:
    w = 68
    lines = ["=" * w]
    grade = d.get("grade", "")
    overall = d.get("overall", d["verdict"])
    cov = f"{d['coverage_pct']:.1f}%" if d['coverage_pct'] is not None else "—"
    lines.append(f"  CHERENKOV Run — {d['run_id']}")
    lines.append(f"  {d['timestamp']}  {d['target_url']}")
    lines.append(f"  Grade: {grade or '—'}  |  {overall}  |  Divergences: {d['divergence_count']}  |  Coverage: {cov}")
    lines.append("=" * w)

    if rv and rv.get("dimensions"):
        lines.append("\n  DIMENSIONS")
        for dim in rv["dimensions"]:
            bar_w = int(dim["score"] * 20)
            bar = "█" * bar_w + "░" * (20 - bar_w)
            status = "✓" if dim["passed"] else "✗"
            lines.append(f"  {status} {dim['name']:20} {bar} {dim['score']*100:.0f}%  {dim['grade']}")

    if rv and rv.get("risk_flags"):
        lines.append(f"\n  RISK FLAGS: {' '.join(f'[{f}]' for f in rv['risk_flags'])}")

    if rv and rv.get("top_findings"):
        lines.append(f"\n  TOP FINDINGS  (fix est: {rv.get('time_to_fix_estimate', '—')})")
        for f in rv["top_findings"][:5]:
            lines.append(f"  {f['rank']}. [{f['severity'].upper()[:4]}]  {f['endpoint']:30}  {f['summary'][:50]}")

    lines.append("")
    return "\n".join(lines)


def _md_run_summary(d: dict, rv: dict | None) -> str:
    grade = d.get("grade", "—")
    overall = d.get("overall", d["verdict"])
    lines = [
        f"# CHERENKOV Run Report\n",
        f"**Run:** `{d['run_id']}`  \n**Time:** {d['timestamp']}  \n**URL:** {d['target_url']}\n",
        f"## Grade: {grade} — {overall}\n",
        f"- Divergences: **{d['divergence_count']}**",
        f"- Coverage: **{'{:.1f}%'.format(d['coverage_pct']) if d['coverage_pct'] is not None else '—'}**",
        f"- Duration: **{d['duration_ms']}ms**\n",
    ]
    if rv and rv.get("dimensions"):
        lines.append("## Dimensions\n")
        lines.append("| Dimension | Score | Grade | Pass |")
        lines.append("|-----------|-------|-------|------|")
        for dim in rv["dimensions"]:
            lines.append(f"| {dim['name']} | {dim['score']*100:.0f}% | {dim['grade']} | {'✓' if dim['passed'] else '✗'} |")
        lines.append("")
    if rv and rv.get("risk_flags"):
        lines.append(f"## Risk Flags\n{', '.join(f'`{f}`' for f in rv['risk_flags'])}\n")
    if rv and rv.get("top_findings"):
        lines.append("## Top Findings\n")
        lines.append("| # | Severity | Endpoint | Summary |")
        lines.append("|---|----------|----------|---------|")
        for f in rv["top_findings"][:5]:
            lines.append(f"| {f['rank']} | {f['severity']} | `{f['endpoint']}` | {f['summary']} |")
        lines.append("")
    return "\n".join(lines)


def _format_run_diff(diff: dict, record, base_record, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(diff, indent=2, default=str)

    w = 68
    delta = diff.get("divergence_delta", 0)
    delta_str = f"+{delta}" if delta > 0 else str(delta)
    grade_a = diff.get("grade_a") or "—"
    grade_b = diff.get("grade_b") or "—"
    gd = diff.get("grade_delta")
    grade_arrow = ("↑" if gd and gd > 0 else "↓" if gd and gd < 0 else "→") if gd is not None else "—"

    if fmt == "markdown":
        return "\n".join([
            "# CHERENKOV Run Diff\n",
            f"**Run A (baseline):** `{diff['run_a']}`  ({diff.get('timestamp_a', '')})",
            f"**Run B (current):**  `{diff['run_b']}`  ({diff.get('timestamp_b', '')})\n",
            f"| | Baseline | Current | Delta |",
            f"|---|---|---|---|",
            f"| Verdict | {diff.get('verdict_a', '—')} | {diff.get('verdict_b', '—')} | {'changed' if diff.get('verdict_changed') else 'same'} |",
            f"| Grade | {grade_a} | {grade_b} | {grade_arrow} |",
            f"| Divergences | — | — | {delta_str} |",
            f"| Coverage | — | — | {diff.get('coverage_delta', '—')} |",
            "",
        ])

    lines = ["=" * w]
    lines.append(f"  CHERENKOV Diff")
    lines.append(f"  Baseline : {diff['run_a']}  ({diff.get('timestamp_a', '')})")
    lines.append(f"  Current  : {diff['run_b']}  ({diff.get('timestamp_b', '')})")
    lines.append("=" * w)
    lines.append(f"  Verdict  : {diff.get('verdict_a', '—')} → {diff.get('verdict_b', '—')}"
                 + ("  (CHANGED)" if diff.get("verdict_changed") else ""))
    lines.append(f"  Grade    : {grade_a} → {grade_b}  {grade_arrow}")
    lines.append(f"  Diverg.  : {delta_str}")
    cov_d = diff.get("coverage_delta")
    if cov_d is not None:
        lines.append(f"  Coverage : {'+' if cov_d >= 0 else ''}{cov_d:.1f}%")
    lines.append("")
    return "\n".join(lines)


# ── file mode helpers (unchanged) ─────────────────────────────────────────────

def _load_report(path: str) -> list[dict] | None:
    try:
        data = json.loads(Path(path).read_text())
        if isinstance(data, list):
            return data
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


def _emit(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text)
        click.echo(f"Report written to {output}")
    else:
        click.echo(text)
