"""cherenkov/cli/commands/guardian_cmd.py — `cherenkov guardian` command.

CLI entrypoint for the Spec Guardian daemon (issue #811).

  Start:  cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080
            Polls the live API against the OpenAPI spec, persisting drift
            events and reports until interrupted (SIGINT/SIGTERM).

  Endpoints default to every concrete GET path declared in the spec; override
  with repeatable --endpoint METHOD:PATH flags.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
import yaml


def _load_spec(spec_path: str) -> dict[str, Any]:
    """Load an OpenAPI spec from YAML or JSON."""
    p = Path(spec_path)
    if not p.exists():
        click.echo(click.style(f"[ERROR] spec not found: {spec_path}", fg="red"), err=True)
        sys.exit(1)
    text = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    return json.loads(text)


def _default_endpoints(spec_path: str) -> list[dict[str, Any]]:
    """Derive a safe, read-only default endpoint list from an OpenAPI spec.

    Only concrete GET paths are included — path parameters (`{id}`) have no
    safe guessable value, and non-GET methods would mutate the target on
    every poll cycle.
    """
    spec = _load_spec(spec_path)
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

    \b
    Examples:
        # Start the drift-monitoring daemon (all concrete GET paths, 60s interval)
        cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080

        # Watch one endpoint every 10s, store history elsewhere
        cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080 \\
            --endpoint "GET:/health" --interval 10 --db .cherenkov/guardian.db
    """


@guardian_cmd.command("start")
@click.option("--spec", required=True, help="Path to the OpenAPI spec (YAML or JSON).")
@click.option("--base-url", required=True, help="Base URL of the live API to monitor.")
@click.option(
    "--interval", "-i", type=int, default=60, show_default=True,
    help="Seconds between check cycles.",
)
@click.option(
    "--endpoint", "raw_endpoints", multiple=True,
    help="METHOD:PATH to check (repeatable). Default: every concrete GET "
         "path in the spec (no {param} placeholders).",
)
@click.option(
    "--max-loops", "-n", type=int, default=0,
    help="Stop after N check cycles (0 = run until interrupted).",
)
@click.option(
    "--db", "db_path", default=None,
    help="SQLite drift database path [default: .cherenkov/drift.db].",
)
def guardian_start_cmd(
    spec: str,
    base_url: str,
    interval: int,
    raw_endpoints: tuple[str, ...],
    max_loops: int,
    db_path: str | None,
) -> None:
    """Start the Spec Guardian daemon.

    Polls each endpoint against the spec and persists drift events and
    reports to the drift store until interrupted (SIGINT/SIGTERM) or
    until --max-loops is reached.

    \b
    Example:
        cherenkov guardian start --spec openapi.yaml --base-url https://api.example.com
        cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8000 \\
            --endpoint GET:/health --max-loops 1
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

    daemon = SpecGuardianDaemon(
        spec_path=spec,
        base_url=base_url,
        check_interval=interval,
        endpoints=endpoints,
        db_path=Path(db_path) if db_path else None,
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
