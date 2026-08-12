"""``cherenkov brain`` — build, sync, export and inspect a project's brain map.

Every subcommand takes ``--root``, so the group maps any repository, not just
the one it is installed in::

    cherenkov brain build --root ../some-other-service
    cherenkov brain export --root ../some-other-service -o ~/vaults/service

Output is human-readable by default and machine-readable under ``--json``,
which is what the git hook and CI job consume.
"""

from __future__ import annotations

import json as json_lib
import sys
from pathlib import Path

import click

from cherenkov.brainmap.adapters.json_export import JsonExporter, graph_payload
from cherenkov.brainmap.adapters.obsidian_vault import ObsidianVaultExporter
from cherenkov.brainmap.use_cases.sync import BrainMapEngine, build_engine

SEVERITY_COLOR = {"error": "red", "warn": "yellow", "info": "cyan"}

HOOK_SCRIPT = """#!/bin/sh
# Installed by `cherenkov brain install-hook`.
# Keeps the brain map in step with the commit that just landed.
cherenkov brain sync --quiet || true
"""


def _engine(root: str | None, project: str | None = None, vault: str | None = None) -> BrainMapEngine:
    """Construct an engine from CLI options."""
    overrides: dict[str, object] = {}
    if project:
        overrides["project"] = project
    if vault:
        overrides["vault_path"] = vault
    return build_engine(root, overrides)


def _root_option(func):
    """Attach the ``--root`` option shared by every subcommand."""
    return click.option(
        "--root",
        type=click.Path(exists=True, file_okay=False),
        default=None,
        help="Project root to map. Defaults to the current directory.",
    )(func)


@click.group("brain")
def brain_cmd() -> None:
    """Build and query the Obsidian-compatible brain map of a codebase."""


@brain_cmd.command("build")
@_root_option
@click.option("--project", default=None, help="Override the project name used as the map namespace.")
@click.option("--json", "as_json", is_flag=True, help="Emit the sync report as JSON.")
@click.option("--quiet", is_flag=True, help="Print nothing but errors.")
def build(root: str | None, project: str | None, as_json: bool, quiet: bool) -> None:
    """Build the map from scratch, discarding any stored state."""
    engine = _engine(root, project)
    report = engine.sync(full=True, with_delta=False)
    _emit_sync(report, engine, as_json=as_json, quiet=quiet, verb="Built")


@brain_cmd.command("sync")
@_root_option
@click.option("--project", default=None, help="Override the project name used as the map namespace.")
@click.option("--delta", is_flag=True, help="Also report what changed since the last sync.")
@click.option("--json", "as_json", is_flag=True, help="Emit the sync report as JSON.")
@click.option("--quiet", is_flag=True, help="Print nothing but errors.")
def sync(root: str | None, project: str | None, delta: bool, as_json: bool, quiet: bool) -> None:
    """Update the map incrementally — only changed files are re-read."""
    engine = _engine(root, project)
    report = engine.sync(full=False, with_delta=delta)
    _emit_sync(report, engine, as_json=as_json, quiet=quiet, verb="Synced")


@brain_cmd.command("watch")
@_root_option
@click.option("--project", default=None, help="Override the project name used as the map namespace.")
@click.option("--interval", default=2.0, show_default=True, help="Seconds between passes.")
@click.option("--export", "export_vault", is_flag=True, help="Re-export the vault after every change.")
def watch(root: str | None, project: str | None, interval: float, export_vault: bool) -> None:
    """Keep the map in sync continuously until interrupted."""
    engine = _engine(root, project)

    def _on_change(report) -> None:
        click.echo(
            f"  {report.parsed} parsed, {report.removed} removed → "
            f"{report.stats['nodes']} nodes / {report.stats['edges']} edges ({report.duration_ms} ms)"
        )
        if export_vault:
            summary = ObsidianVaultExporter().export(engine.graph(), engine.profile.resolved_vault_path())
            click.echo(f"  vault: {summary['notes_written']} notes → {summary['vault']}")

    click.echo(f"Watching {engine.profile.root} every {interval}s — Ctrl-C to stop.")
    try:
        engine.watch(interval=interval, on_change=_on_change)
    except KeyboardInterrupt:
        click.echo("\nStopped.")


@brain_cmd.command("export")
@_root_option
@click.option("--project", default=None, help="Override the project name used as the map namespace.")
@click.option("-o", "--out", default=None, help="Output directory (vault) or file (json).")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["obsidian", "json"]),
    default="obsidian",
    show_default=True,
    help="Export format.",
)
@click.option("--sync/--no-sync", "do_sync", default=True, show_default=True, help="Sync before exporting.")
def export(root: str | None, project: str | None, out: str | None, fmt: str, do_sync: bool) -> None:
    """Write the map to an Obsidian vault or a JSON document."""
    engine = _engine(root, project, vault=out if fmt == "obsidian" else None)
    if do_sync:
        engine.sync()
    map_ = engine.graph()
    if fmt == "json":
        target = Path(out) if out else engine.profile.root / ".brainmap" / "brainmap.json"
        summary = JsonExporter().export(map_, target)
        click.echo(f"Wrote {summary['nodes']} nodes to {summary['path']} ({summary['bytes'] // 1024} KB)")
        return
    target = Path(out) if out else engine.profile.resolved_vault_path()
    summary = ObsidianVaultExporter().export(map_, target)
    click.echo(click.style(f"Vault written: {summary['vault']}", fg="green", bold=True))
    click.echo(f"  {summary['notes_written']} notes, {summary['index_notes']} indexes")
    if summary["stale_removed"]:
        click.echo(f"  {summary['stale_removed']} stale notes removed")
    click.echo("  Open that folder in Obsidian: File → Open folder as vault")


@brain_cmd.command("status")
@_root_option
@click.option("--project", default=None, help="Override the project name used as the map namespace.")
@click.option("--json", "as_json", is_flag=True, help="Emit the status as JSON.")
def status(root: str | None, project: str | None, as_json: bool) -> None:
    """Show what is in the stored map, without re-scanning."""
    engine = _engine(root, project)
    map_ = engine.graph()
    stats = map_.stats()
    if as_json:
        click.echo(json_lib.dumps(stats, indent=2))
        return
    if not stats["nodes"]:
        click.echo("No map stored yet. Run: cherenkov brain build")
        return
    click.echo(click.style(f"{stats['project']} — brain map", bold=True))
    click.echo(f"  built    {stats['built_at']}")
    click.echo(f"  nodes    {stats['nodes']}   edges {stats['edges']}   files {stats['files']}")
    click.echo("  by kind  " + ", ".join(f"{k}={v}" for k, v in stats["by_kind"].items()))
    severities = stats.get("by_severity", {})
    if severities:
        click.echo("  findings " + ", ".join(f"{k}={v}" for k, v in severities.items()))


@brain_cmd.command("findings")
@_root_option
@click.option("--project", default=None, help="Override the project name used as the map namespace.")
@click.option("--severity", type=click.Choice(["error", "warn", "info"]), default=None, help="Filter by severity.")
@click.option("--code", default=None, help="Filter by finding code, e.g. dangling_link.")
@click.option("--limit", default=40, show_default=True, help="Maximum findings to print.")
@click.option("--json", "as_json", is_flag=True, help="Emit findings as JSON.")
@click.option(
    "--fail-on",
    type=click.Choice(["none", "error", "warn"]),
    default="none",
    show_default=True,
    help="Exit non-zero when findings at this severity or worse exist — for CI.",
)
def findings(
    root: str | None,
    project: str | None,
    severity: str | None,
    code: str | None,
    limit: int,
    as_json: bool,
    fail_on: str,
) -> None:
    """List what reconciliation could not make sense of."""
    engine = _engine(root, project)
    map_ = engine.graph()
    selected = [
        f
        for f in map_.findings
        if (severity is None or f.severity == severity) and (code is None or f.code == code)
    ]
    if as_json:
        click.echo(json_lib.dumps([f.to_dict() for f in selected], indent=2))
    else:
        if not selected:
            click.echo("No findings.")
        for finding in selected[:limit]:
            tag = click.style(f"{finding.severity:>5}", fg=SEVERITY_COLOR.get(finding.severity, "white"))
            where = f"  ({finding.origin})" if finding.origin else ""
            click.echo(f"{tag}  {finding.code:<24} {finding.message}{where}")
        if len(selected) > limit:
            click.echo(f"… and {len(selected) - limit} more")

    if fail_on != "none":
        blocking = {"error"} if fail_on == "error" else {"error", "warn"}
        offenders = [f for f in selected if f.severity in blocking]
        if offenders:
            click.echo(click.style(f"{len(offenders)} finding(s) at or above '{fail_on}'", fg="red"), err=True)
            sys.exit(1)


@brain_cmd.command("query")
@_root_option
@click.option("--project", default=None, help="Override the project name used as the map namespace.")
@click.argument("term")
@click.option("--kind", default=None, help="Restrict to one node kind.")
@click.option("--limit", default=20, show_default=True, help="Maximum matches to print.")
@click.option("--neighbors", is_flag=True, help="Also print each match's immediate neighbours.")
@click.option("--json", "as_json", is_flag=True, help="Emit matches as JSON.")
def query(
    root: str | None,
    project: str | None,
    term: str,
    kind: str | None,
    limit: int,
    neighbors: bool,
    as_json: bool,
) -> None:
    """Search the map by title or summary."""
    engine = _engine(root, project)
    payload = graph_payload(
        engine.graph(), limit=limit, kinds=[kind] if kind else None, query=term
    )
    if as_json:
        click.echo(json_lib.dumps(payload["nodes"], indent=2))
        return
    if not payload["nodes"]:
        click.echo(f"No node matches '{term}'.")
        return
    for node in payload["nodes"]:
        degree = click.style("[{} links]".format(node["degree"]), dim=True)
        click.echo(f"{click.style(node['kind'], fg='cyan'):<18} {node['title']}  {degree}")
        if node["summary"]:
            click.echo(f"    {node['summary'][:140]}")
        if node["origin"]:
            click.echo(click.style(f"    {node['origin']}", dim=True))
        if neighbors:
            sub = engine.neighborhood(node["id"], depth=1)
            titles = [n.title for n in sub.nodes.values() if n.id != node["id"]][:12]
            if titles:
                click.echo("    → " + ", ".join(titles))


@brain_cmd.command("install-hook")
@_root_option
def install_hook(root: str | None) -> None:
    """Install a git post-commit hook that keeps the map current."""
    engine = _engine(root)
    hooks_dir = engine.profile.root / ".git" / "hooks"
    if not hooks_dir.parent.exists():
        click.echo(click.style(f"{engine.profile.root} is not a git repository.", fg="red"), err=True)
        sys.exit(1)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "post-commit"
    if hook.exists() and "cherenkov brain sync" not in hook.read_text(encoding="utf-8", errors="ignore"):
        # Never clobber an existing hook: append, so whatever the repo already
        # does on commit keeps happening.
        with hook.open("a", encoding="utf-8") as fh:
            fh.write("\n" + HOOK_SCRIPT.split("\n", 1)[1])
        click.echo(f"Appended brain sync to existing hook: {hook}")
    else:
        hook.write_text(HOOK_SCRIPT, encoding="utf-8")
        click.echo(f"Installed hook: {hook}")
    hook.chmod(0o755)


def _emit_sync(report, engine: BrainMapEngine, as_json: bool, quiet: bool, verb: str) -> None:
    """Print a sync report in whichever form the caller asked for."""
    if as_json:
        click.echo(json_lib.dumps(report.to_dict(), indent=2))
        return
    if quiet:
        return
    stats = report.stats
    click.echo(
        click.style(f"{verb} {stats['project']} brain map", fg="green", bold=True)
        + f" in {report.duration_ms} ms"
    )
    click.echo(
        f"  files    {report.scanned} scanned, {report.parsed} parsed, "
        f"{report.skipped} unchanged, {report.removed} removed"
    )
    click.echo(f"  graph    {stats['nodes']} nodes, {stats['edges']} edges")
    severities = stats.get("by_severity", {})
    if severities:
        parts = [
            click.style(f"{count} {name}", fg=SEVERITY_COLOR.get(name, "white"))
            for name, count in severities.items()
        ]
        click.echo("  findings " + ", ".join(parts) + "  (cherenkov brain findings)")
    if report.delta and not report.delta.get("empty", True):
        delta = report.delta
        click.echo(
            f"  changed  +{len(delta['added_nodes'])}/-{len(delta['removed_nodes'])} nodes, "
            f"{len(delta['changed_files'])} files"
        )
    click.echo(click.style(f"  store    {engine.profile.resolved_db_path()}", dim=True))
