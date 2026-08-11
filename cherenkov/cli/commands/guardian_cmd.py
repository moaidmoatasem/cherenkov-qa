"""cherenkov/cli/commands/guardian_cmd.py — `cherenkov guardian` command.

CLI entrypoint for the Spec Guardian daemon (issue #811).

  Start:  cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080
            Polls the live API against the OpenAPI spec, persisting drift
            events and reports until interrupted (SIGINT/SIGTERM).

  Endpoints default to every concrete GET path declared in the spec; override
  with repeatable --endpoint METHOD:PATH flags.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from cherenkov.cli.loaders import load_yaml_or_json


def _default_endpoints(spec_path: str) -> list[dict[str, Any]]:
    """Derive a safe, read-only default endpoint list from an OpenAPI spec.

    Only concrete GET paths are included — path parameters (`{id}`) have no
    safe guessable value, and non-GET methods would mutate the target on
    every poll cycle.
    """
    spec = load_yaml_or_json(spec_path, "spec")
    endpoints: list[dict[str, Any]] = []
    for path, item in (spec.get("paths") or {}).items():
        if "{" in path or not isinstance(item, dict):
            continue
        if "get" in item:
            endpoints.append({"method": "GET", "path": path})
    return endpoints


def _parse_endpoint_opts(raw: tuple[str, ...]) -> list[dict[str, Any]]:
    """Parse repeatable `--endpoint METHOD:PATH` options."""
    endpoints = []
    for entry in raw:
        method, sep, path = entry.partition(":")
        if not sep:
            raise click.UsageError(f"--endpoint must be METHOD:PATH, got: {entry!r}")
        endpoints.append({"method": method.strip().upper(), "path": path.strip()})
    return endpoints


@click.group("guardian")
def guardian_cmd() -> None:
    """Continuously monitor API endpoints for OpenAPI spec drift.


Examples:
    # Start the drift-monitoring daemon (all concrete GET paths, 60s interval)
    cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080

    # Watch one endpoint every 10s, store history elsewhere
    cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080 \
        --endpoint "GET:/health" --interval 10 --db .cherenkov/guardian.db

Returns:
    None: Command execution result.
    """


@guardian_cmd.command("start")
@click.option("--spec", required=True, help="Path to the OpenAPI spec (YAML or JSON).")
@click.option("--base-url", required=True, help="Base URL of the live API to monitor.")
@click.option(
    "--interval",
    "-i",
    type=int,
    default=60,
    show_default=True,
    help="Seconds between check cycles.",
)
@click.option(
    "--endpoint",
    "raw_endpoints",
    multiple=True,
    help="METHOD:PATH to check (repeatable). Default: every concrete GET "
    "path in the spec (no {param} placeholders).",
)
@click.option(
    "--max-loops",
    "-n",
    type=int,
    default=0,
    help="Stop after N check cycles (0 = run until interrupted).",
)
@click.option(
    "--db",
    "db_path",
    default=None,
    help="SQLite drift database path [default: .cherenkov/drift.db].",
)
@click.option("--pr-number", help="Pull request number")
@click.option("--pr-title", help="Pull request title")
@click.option("--pr-description", help="Pull request description")
@click.option("--commit-sha", help="Commit SHA")
@click.option("--head-branch", help="Head branch name")
@click.option("--base-branch", help="Base branch name")
@click.option("--deeplink", help="Dynamic preview environment URL")
@click.option("--artifact-url", help="Build artifact URL")
@click.option("--artifact-filename", help="Build artifact filename")
def guardian_start_cmd(
    spec: str,
    base_url: str,
    interval: int,
    raw_endpoints: tuple[str, ...],
    max_loops: int,
    db_path: str | None,
    pr_number: str | None,
    pr_title: str | None,
    pr_description: str | None,
    commit_sha: str | None,
    head_branch: str | None,
    base_branch: str | None,
    deeplink: str | None,
    artifact_url: str | None,
    artifact_filename: str | None,
) -> None:
    """Start the Spec Guardian daemon.

Polls each endpoint against the spec and persists drift events and
reports to the drift store until interrupted (SIGINT/SIGTERM) or
until --max-loops is reached.


Example:
    cherenkov guardian start --spec openapi.yaml --base-url https://api.example.com
    cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8000 \
        --endpoint GET:/health --max-loops 1

Args:
    spec (str): Parameter spec.
    base_url (str): Parameter base_url.
    interval (int): Parameter interval.
    raw_endpoints (tuple[str, ...]): Parameter raw_endpoints.
    max_loops (int): Parameter max_loops.
    db_path (str | None): Parameter db_path.
    pr_number (str | None): Parameter pr_number.
    pr_title (str | None): Parameter pr_title.
    pr_description (str | None): Parameter pr_description.
    commit_sha (str | None): Parameter commit_sha.
    head_branch (str | None): Parameter head_branch.
    base_branch (str | None): Parameter base_branch.
    deeplink (str | None): Parameter deeplink.
    artifact_url (str | None): Parameter artifact_url.
    artifact_filename (str | None): Parameter artifact_filename.

Returns:
    None: Command execution result.
    """
    from cherenkov.spec_guardian.daemon import SpecGuardianDaemon

    endpoints = _parse_endpoint_opts(raw_endpoints) or _default_endpoints(spec)
    if not endpoints:
        click.echo(
            click.style("[ERROR] ", fg="red", bold=True)
            + "No endpoints to monitor: the spec has no concrete GET paths "
            "and none were given via --endpoint.",
            err=True,
        )
        sys.exit(1)

    pr_metadata = {}
    if pr_number: pr_metadata["pr_number"] = pr_number
    if pr_title: pr_metadata["pr_title"] = pr_title
    if pr_description: pr_metadata["pr_description"] = pr_description
    if commit_sha: pr_metadata["commit_sha"] = commit_sha
    if head_branch: pr_metadata["head_branch"] = head_branch
    if base_branch: pr_metadata["base_branch"] = base_branch
    if deeplink: pr_metadata["deeplink"] = deeplink
    if artifact_url: pr_metadata["artifact_url"] = artifact_url
    if artifact_filename: pr_metadata["artifact_filename"] = artifact_filename

    daemon = SpecGuardianDaemon(
        spec_path=spec,
        base_url=base_url,
        check_interval=interval,
        endpoints=endpoints,
        db_path=Path(db_path) if db_path else None,
        pr_metadata=pr_metadata if pr_metadata else None,
    )

    click.echo(
        click.style("[GUARDIAN] ", fg="cyan", bold=True)
        + f"Watching {len(endpoints)} endpoint(s) on {base_url} every {interval}s"
    )

    if max_loops > 0:
        for i in range(max_loops):
            report = daemon.run_once()
            click.echo(
                f"  cycle {i + 1}/{max_loops}: {report.total_checks} checked, "
                f"{len(report.events)} drift event(s)"
            )
        return

    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()
