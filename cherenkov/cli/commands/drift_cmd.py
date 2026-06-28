"""cherenkov/cli/commands/drift_cmd.py — `cherenkov drift` command.

Three invocation tiers (spec §7):

  Interactive  (default):  cherenkov drift --spec openapi.yaml --suite suite.json
                            Discovers latest baseline in ledger, runs reconcile.

  CI-fast:                  cherenkov drift --spec ... --suite ... --baseline-id 2026-06-25T14:03:11Z
                            Uses a specific snapshot by ID — no DB discovery cost.

  CI-fastest:               cherenkov drift --spec ... --suite ... --baseline-file baseline.json
                            Loads the baseline from a downloaded artifact — no DB roundtrip.

  Seed:                     cherenkov drift seed --spec openapi.yaml --suite suite.json
                            Writes a new baseline snapshot to the ledger.
"""

from __future__ import annotations

import sys
import json
import click
from pathlib import Path


# ── helpers ────────────────────────────────────────────────────────────────────

def _load_json(path: str, label: str) -> dict:
    p = Path(path)
    if not p.exists():
        click.echo(click.style(f"[ERROR] {label} not found: {path}", fg="red"), err=True)
        sys.exit(1)
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        click.echo(click.style(f"[ERROR] {label} is not valid JSON: {e}", fg="red"), err=True)
        sys.exit(1)


def _load_yaml_or_json(path: str, label: str) -> dict:
    p = Path(path)
    if not p.exists():
        click.echo(click.style(f"[ERROR] {label} not found: {path}", fg="red"), err=True)
        sys.exit(1)
    text = p.read_text()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
            return yaml.safe_load(text)
        except Exception as e:
            click.echo(click.style(f"[ERROR] {label} YAML parse error: {e}", fg="red"), err=True)
            sys.exit(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        click.echo(click.style(f"[ERROR] {label} JSON parse error: {e}", fg="red"), err=True)
        sys.exit(1)


def _ledger(ledger_path: str | None):
    from cherenkov.drift.ledger import DriftLedger
    return DriftLedger(path=Path(ledger_path) if ledger_path else None)


# ── `cherenkov drift` group ───────────────────────────────────────────────────

@click.group("drift")
def drift_cmd():
    """Detect and report drift between spec, suite, and live API.

    Run `cherenkov drift --help` for reconcile options, or
    `cherenkov drift seed --help` to write a new baseline.

    \b
    Examples:
        # Seed a baseline
        cherenkov drift seed --spec openapi.yaml --suite suite.json

        # Daily reconcile (discovers latest baseline)
        cherenkov drift reconcile --spec openapi.yaml --suite suite.json

        # CI-fast (explicit baseline id)
        cherenkov drift reconcile --spec openapi.yaml --suite suite.json \\
            --baseline-id 2026-06-25T14:03:11Z

        # CI-fastest (downloaded artifact)
        cherenkov drift reconcile --spec openapi.yaml --suite suite.json \\
            --baseline-file baseline.json --fail-on-drift
    """


# ── `cherenkov drift seed` ────────────────────────────────────────────────────

@drift_cmd.command("seed")
@click.option("--spec",  required=True, help="Path to OpenAPI spec (YAML or JSON).")
@click.option("--suite", required=True, help="Path to suite manifest JSON.")
@click.option("--profile", default="default", show_default=True,
              help="Generation profile label (model/prompt variant).")
@click.option("--ledger", "ledger_path", default=None,
              help="Ledger file path [default: .cherenkov/drift-ledger.jsonl].")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON.")
def seed_cmd(spec, suite, profile, ledger_path, as_json):
    """Seed a new drift baseline from a spec + suite pair.

    Writes an immutable SpecSuiteSnapshot to the ledger.
    Idempotent — running twice with identical inputs writes only one record.

    \b
    Example:
        cherenkov drift seed --spec openapi.yaml --suite suite.json
    """
    spec_dict = _load_yaml_or_json(spec, "spec")
    suite_dict = _load_json(suite, "suite")
    ledger = _ledger(ledger_path)

    snapshot = ledger.seed_baseline(spec_dict, suite_dict, generation_profile=profile)

    if as_json:
        click.echo(json.dumps({
            "snapshot_id": snapshot.snapshot_id,
            "spec_hash": snapshot.spec_hash[:12],
            "suite_hash": snapshot.suite_hash[:12],
            "generation_profile": snapshot.generation_profile,
        }, indent=2))
    else:
        click.echo(click.style("[SEEDED] ", fg="green", bold=True) +
                   f"Baseline snapshot_id={snapshot.snapshot_id}")
        click.echo(f"  spec_hash:  {snapshot.spec_hash[:16]}…")
        click.echo(f"  suite_hash: {snapshot.suite_hash[:16]}…")
        click.echo(f"  profile:    {snapshot.generation_profile}")
        click.echo(f"  ledger:     {ledger.path}")


# ── `cherenkov drift list` ────────────────────────────────────────────────────

@drift_cmd.command("list")
@click.option("--since", default=None, help="Show snapshots after this snapshot_id.")
@click.option("--limit", default=10, show_default=True, help="Max results.")
@click.option("--ledger", "ledger_path", default=None,
              help="Ledger file path [default: .cherenkov/drift-ledger.jsonl].")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON.")
def list_cmd(since, limit, ledger_path, as_json):
    """List drift baseline snapshots (newest first).

    \b
    Example:
        cherenkov drift list --limit 5
    """
    ledger = _ledger(ledger_path)
    snapshots = ledger.list_snapshots(since=since, limit=limit)

    if as_json:
        click.echo(json.dumps([
            {
                "snapshot_id": s.snapshot_id,
                "spec_hash": s.spec_hash[:12],
                "suite_hash": s.suite_hash[:12],
                "generation_profile": s.generation_profile,
                "created_at": s.created_at,
            }
            for s in snapshots
        ], indent=2))
        return

    if not snapshots:
        click.echo(click.style("No baselines found.", fg="yellow"))
        click.echo("Run `cherenkov drift seed` to create one.")
        return

    click.echo(click.style(f"{'SNAPSHOT ID':<26} {'SPEC HASH':>14} {'PROFILE'}", bold=True))
    click.echo("─" * 60)
    for s in snapshots:
        click.echo(f"{s.snapshot_id:<26}  {s.spec_hash[:12]}…  {s.generation_profile}")


# ── `cherenkov drift export` ──────────────────────────────────────────────────

@drift_cmd.command("export")
@click.option("--snapshot-id", default=None, help="Export a specific snapshot (default: latest).")
@click.option("--output", "-o", default=None, help="Output file path [default: drift-baseline-<id>.json].")
@click.option("--ledger", "ledger_path", default=None,
              help="Ledger file path [default: .cherenkov/drift-ledger.jsonl].")
def export_cmd(snapshot_id, output, ledger_path):
    """Export a baseline snapshot to a standalone JSON file (CI artifact).

    Use the exported file with --baseline-file for zero-DB-latency CI checks.

    \b
    Example:
        cherenkov drift export -o baseline.json
    """
    ledger = _ledger(ledger_path)
    out_path = ledger.export_snapshot(
        snapshot_id=snapshot_id,
        path=Path(output) if output else None,
    )
    click.echo(click.style("[EXPORTED] ", fg="green", bold=True) + str(out_path))


# ── `cherenkov drift reconcile` ───────────────────────────────────────────────

@drift_cmd.command("reconcile")
@click.option("--spec",  required=True, help="Path to current OpenAPI spec (YAML or JSON).")
@click.option("--suite", required=True, help="Path to current suite manifest JSON.")
@click.option("--baseline-id", default=None,
              help="Snapshot ID to diff against (CI-fast tier). Default: latest in ledger.")
@click.option("--baseline-file", default=None,
              help="Path to exported baseline JSON (CI-fastest tier, no ledger needed).")
@click.option("--ledger", "ledger_path", default=None,
              help="Ledger file path [default: .cherenkov/drift-ledger.jsonl].")
@click.option("--fail-on-drift", is_flag=True, default=False,
              help="Exit 1 if any blocking drift is found (for CI gates).")
@click.option("--fail-on-warn", is_flag=True, default=False,
              help="Exit 1 on WARN findings too (stricter gate).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON report.")
@click.option(
    "--level",
    type=click.Choice(["L1", "L2"], case_sensitive=False),
    default="L1",
    show_default=True,
    help=(
        "Autonomy level. L1=report-only (default). "
        "L2=propose+check+human-approve for WARN findings."
    ),
)
@click.option(
    "--auto-approve",
    is_flag=True,
    default=False,
    help="L2 only: skip interactive confirmation and auto-approve all verified proposals.",
)
@click.option(
    "--suite-out",
    default=None,
    help="L2 only: write updated suite to this path (default: overwrite --suite).",
)
def reconcile_cmd(spec, suite, baseline_id, baseline_file, ledger_path,
                  fail_on_drift, fail_on_warn, as_json, level, auto_approve, suite_out):
    """Detect drift between a baseline and the current spec+suite.

    Compares the baseline snapshot against the current state using the three
    drift axes: spec drift (A), suite staleness (B), and optionally contract
    drift (C, wired in via --violations if available).

    Detection is deterministic — no LLM is called during detection.
    At L2, the maker generates test skeletons from the spec (schema-driven).

    \b
    Examples:
        # Interactive (auto-discovers latest baseline)
        cherenkov drift reconcile --spec openapi.yaml --suite suite.json

        # CI gate — block on any FAIL finding
        cherenkov drift reconcile --spec openapi.yaml --suite suite.json \\
            --baseline-file baseline.json --fail-on-drift

        # L2: propose + approve new tests for untested operations
        cherenkov drift reconcile --spec openapi.yaml --suite suite.json \\
            --level L2 --suite-out suite-updated.json
    """
    from cherenkov.drift.reconcile import DriftVerdict, MagnitudeVerdict, SEVERITY
    from cherenkov.drift.detect import DriftKind
    from cherenkov.drift.loop import DriftLoop, AutonomyLevel

    spec_dict = _load_yaml_or_json(spec, "spec")
    suite_dict = _load_json(suite, "suite")
    ledger = _ledger(ledger_path)

    try:
        report = ledger.reconcile_from(
            baseline_id=baseline_id,
            baseline_file=Path(baseline_file) if baseline_file else None,
            current_spec=spec_dict,
            current_suite=suite_dict,
        )
    except (KeyError, RuntimeError) as e:
        click.echo(click.style(f"[ERROR] {e}", fg="red"), err=True)
        click.echo("Run `cherenkov drift seed --spec ... --suite ...` to create a baseline.", err=True)
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        _print_report(report)

    # L2 autonomy gate — propose + check + (optionally) commit
    loop_result = None
    if level.upper() == "L2" and report.has_drift:
        out_path = Path(suite_out) if suite_out else Path(suite)
        loop = DriftLoop.l2_interactive(
            spec=spec_dict,
            suite_path=out_path,
            auto_approve=auto_approve,
        )
        loop_result = loop.run(report)
        if not as_json:
            _print_loop_result(loop_result)

    # Exit codes
    if fail_on_drift and report.blocked:
        sys.exit(1)
    if fail_on_warn and report.gate_verdict in (DriftVerdict.WARN, DriftVerdict.FAIL):
        sys.exit(1)


def _print_report(report) -> None:
    from cherenkov.drift.reconcile import DriftVerdict, MagnitudeVerdict, SEVERITY

    # Header
    mag_color = {
        MagnitudeVerdict.NEAR_IDENTICAL: "green",
        MagnitudeVerdict.MINOR_DRIFT:    "yellow",
        MagnitudeVerdict.MODERATE_DRIFT: "yellow",
        MagnitudeVerdict.MAJOR_DRIFT:    "red",
    }.get(report.magnitude_label, "white")

    gate_color = {
        DriftVerdict.PASS: "green",
        DriftVerdict.WARN: "yellow",
        DriftVerdict.FAIL: "red",
    }.get(report.gate_verdict, "white")

    click.echo()
    click.echo(click.style("── Drift Report ──────────────────────────────────────", bold=True))
    click.echo(
        f"  magnitude  : "
        + click.style(f"{report.magnitude:.3f} ({report.magnitude_label.value})", fg=mag_color)
    )
    click.echo(
        f"  gate       : "
        + click.style(report.gate_verdict.value.upper(), fg=gate_color, bold=True)
    )
    click.echo(f"  findings   : {len(report.findings)}")
    click.echo(
        f"  blocked    : "
        + click.style(str(report.blocked), fg="red" if report.blocked else "green")
    )
    click.echo()

    if not report.findings:
        click.echo(click.style("  No drift detected — suite is current.", fg="green"))
        return

    # Group by severity
    severity_order = [DriftVerdict.FAIL, DriftVerdict.WARN, DriftVerdict.PASS]
    severity_label = {DriftVerdict.FAIL: "FAIL", DriftVerdict.WARN: "WARN", DriftVerdict.PASS: "INFO"}
    severity_color = {DriftVerdict.FAIL: "red", DriftVerdict.WARN: "yellow", DriftVerdict.PASS: "white"}

    for sev in severity_order:
        group = [f for f in report.findings if SEVERITY[f.kind] == sev]
        if not group:
            continue
        color = severity_color[sev]
        label = severity_label[sev]
        click.echo(click.style(f"  [{label}] {len(group)} finding(s):", fg=color, bold=True))
        for finding in group:
            click.echo(f"    • {finding.kind.value:<30}  {finding.operation_id}")
            click.echo(f"      {finding.detail}")
        click.echo()

    if report.blocked:
        click.echo(click.style(
            "  ✖  Drift is blocking — resolve FAIL findings or update the baseline.",
            fg="red", bold=True,
        ))
        click.echo("     Run `cherenkov drift seed` after fixing to advance the baseline.")
    else:
        click.echo(click.style(
            "  ✔  Drift is non-blocking — review WARN/INFO findings at your discretion.",
            fg="yellow",
        ))


def _print_loop_result(result) -> None:
    from cherenkov.drift.loop import AutonomyLevel

    click.echo()
    click.echo(click.style("── L2 Reconciliation ─────────────────────────────────", bold=True))
    click.echo(f"  proposals  : {len(result.proposals)}")
    click.echo(f"  escalations: {len(result.escalations)}")
    click.echo(
        f"  committed  : "
        + click.style(str(result.committed), fg="green" if result.committed else "yellow")
    )

    if result.proposals:
        click.echo()
        click.echo(click.style("  Proposals:", bold=True))
        for p in result.proposals:
            status = click.style("✔ committed", fg="green") if result.committed else click.style("pending", fg="yellow")
            click.echo(f"    • [{status}] {p.operation_id}")
            click.echo(f"      {p.action}")

    if result.escalations:
        click.echo()
        click.echo(click.style("  Escalations (require manual review):", fg="yellow", bold=True))
        for f in result.escalations:
            click.echo(f"    • {f.kind.value:<30}  {f.operation_id}")
            click.echo(f"      {f.detail}")

    if result.audit_trail:
        click.echo()
        click.echo(click.style("  Audit trail:", bold=True))
        for entry in result.audit_trail:
            click.echo(f"    {entry}")
