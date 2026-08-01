"""cherenkov/cli/commands/guardian_cmd.py — `cherenkov guardian` command.

CLI entrypoint for the Spec Guardian daemon (issue #811).

  Start:  cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080
            Polls the live API against the OpenAPI spec, persisting drift
            events and reports until interrupted (SIGINT/SIGTERM).

  Endpoints default to every path+method declared in the spec; override
  with repeatable --endpoint METHOD:PATH flags.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml


def _load_spec(spec_path: str) -> dict:
    """Load an OpenAPI spec from YAML or JSON."""
    p = Path(spec_path)
    if not p.exists():
        click.echo(click.style(f"[ERROR] spec not found: {spec_path}", fg="red"), err=True)
        sys.exit(1)
    text = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    return json.loads(text)


def _spec_endpoints(spec: dict) -> list[dict]:
    """Derive endpoint configs from every path/method declared in the spec."""
    configs = []
    for path, ops in (spec.get("paths") or {}).items():
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            if isinstance(ops, dict) and method in ops:
                configs.append({"method": method.upper(), "path": path})
    return configs


@click.group("guardian")
def guardian_cmd():
    """Continuously monitor API endpoints for OpenAPI spec drift.

    \b
    Examples:
        # Start the drift-monitoring daemon (all spec paths, 60s interval)
        cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080

        # Watch one endpoint every 10s, store history elsewhere
        cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080 \\
            --endpoint "GET:/health" --interval 10 --db .cherenkov/guardian.db
    """


@guardian_cmd.command("start")
@click.option("--spec", required=True, help="Path to the OpenAPI spec (YAML or JSON).")
@click.option("--base-url", required=True, help="Base URL of the API to monitor.")
@click.option("--interval", default=60, show_default=True, type=int,
              help="Seconds between drift checks.")
@click.option("--endpoint", "endpoints", multiple=True,
              help="Endpoint to check as METHOD:PATH (repeatable; default: all spec paths).")
@click.option("--db", "db_path", default=None,
              help="Path to the drift SQLite DB [default: .cherenkov/drift.db].")
def guardian_start_cmd(spec, base_url, interval, endpoints, db_path):
    """Start the Spec Guardian daemon.

    Polls each endpoint against the spec and persists drift events and
    reports to the drift store until interrupted (SIGINT/SIGTERM).

    \b
    Example:
        cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080
    """
    from cherenkov.spec_guardian.daemon import SpecGuardianDaemon

    endpoint_configs = []
    for ep in endpoints:
        if ":" not in ep:
            click.echo(click.style(
                f"[ERROR] --endpoint must be METHOD:PATH, got: {ep}", fg="red"), err=True)
            sys.exit(2)
        method, path = ep.split(":", 1)
        endpoint_configs.append({"method": method.upper(), "path": path})

    if not endpoint_configs:
        endpoint_configs = _spec_endpoints(_load_spec(spec))

    daemon = SpecGuardianDaemon(
        spec_path=spec,
        base_url=base_url,
        check_interval=interval,
        endpoints=endpoint_configs,
        db_path=Path(db_path) if db_path else None,
    )
    daemon.start()
