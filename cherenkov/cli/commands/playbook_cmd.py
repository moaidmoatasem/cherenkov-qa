"""cherenkov playbook — list, inspect, and run playbooks against a live API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


@click.group("playbook")
def playbook_cmd():
    """Manage and run validation playbooks (auto-triggering skill rules)."""


@playbook_cmd.command("list")
@click.option(
    "--dir",
    "search_dirs",
    multiple=True,
    help="Extra directories to scan for playbook YAML files.",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_cmd(search_dirs: tuple[str, ...], as_json: bool) -> None:
    """List all loaded playbooks."""
    from cherenkov.playbooks.registry import PlaybookRegistry

    dirs = list(search_dirs) if search_dirs else None
    registry = PlaybookRegistry(search_dirs=dirs)

    if not registry.playbooks:
        click.echo("No playbooks found.")
        return

    if as_json:
        click.echo(json.dumps([pb.to_dict() for pb in registry.playbooks], indent=2))
        return

    click.echo(f"{'NAME':<30} {'SEVERITY':<10} {'SOURCE'}")
    click.echo("-" * 70)
    for pb in registry.playbooks:
        src = Path(pb.source_path).name if pb.source_path else "—"
        click.echo(f"{pb.name:<30} {pb.severity:<10} {src}")
        if pb.description:
            desc = pb.description.strip().replace("\n", " ")[:60]
            click.echo(f"  {desc}")


@playbook_cmd.command("show")
@click.argument("name")
@click.option("--dir", "search_dirs", multiple=True)
def show_cmd(name: str, search_dirs: tuple[str, ...]) -> None:
    """Show full details of a named playbook."""
    from cherenkov.playbooks.registry import PlaybookRegistry

    dirs = list(search_dirs) if search_dirs else None
    registry = PlaybookRegistry(search_dirs=dirs)
    pb = registry.get(name)
    if pb is None:
        click.echo(f"Playbook '{name}' not found.", err=True)
        sys.exit(1)
    click.echo(json.dumps(pb.to_dict(), indent=2))


@playbook_cmd.command("run")
@click.option("--url", required=True, help="Base URL of the API under test.")
@click.option("--path", "endpoint_path", required=True, help="Endpoint path, e.g. /health.")
@click.option("--method", default="GET", show_default=True)
@click.option("--header", "extra_headers", multiple=True, help="KEY:VALUE request header.")
@click.option("--dir", "search_dirs", multiple=True)
@click.option("--json", "as_json", is_flag=True)
def run_cmd(
    url: str,
    endpoint_path: str,
    method: str,
    extra_headers: tuple[str, ...],
    search_dirs: tuple[str, ...],
    as_json: bool,
) -> None:
    """Fire matching playbooks against a single live endpoint."""
    import requests

    from cherenkov.playbooks.matcher import PlaybookMatcher
    from cherenkov.playbooks.registry import PlaybookRegistry
    from cherenkov.playbooks.runner import PlaybookRunner

    dirs = list(search_dirs) if search_dirs else None
    registry = PlaybookRegistry(search_dirs=dirs)
    matcher = PlaybookMatcher(registry.playbooks)
    runner = PlaybookRunner()

    req_headers: dict[str, str] = {}
    for h in extra_headers:
        if ":" in h:
            k, _, v = h.partition(":")
            req_headers[k.strip()] = v.strip()

    full_url = url.rstrip("/") + endpoint_path
    try:
        resp = requests.request(method.upper(), full_url, headers=req_headers, timeout=15)
        try:
            body = resp.json() if resp.content else None
        except ValueError:
            body = None
        status = resp.status_code
        resp_headers = dict(resp.headers)
    except requests.RequestException as exc:
        click.echo(f"Request failed: {exc}", err=True)
        sys.exit(1)

    matched = matcher.match(endpoint_path, method)
    if not matched:
        click.echo(f"No playbooks matched {method.upper()} {endpoint_path}")
        return

    all_findings = []
    for pb in matched:
        findings = runner.run(
            pb,
            endpoint=endpoint_path,
            method=method,
            status_code=status,
            response_headers=resp_headers,
            response_body=body,
            request_headers=req_headers,
        )
        all_findings.extend(findings)

    if as_json:
        click.echo(json.dumps([f.to_dict() for f in all_findings], indent=2))
        return

    click.echo(f"\nPlaybook results for {method.upper()} {endpoint_path} (HTTP {status})")
    click.echo(f"Matched {len(matched)} playbook(s), {len(all_findings)} finding(s)\n")
    for f in all_findings:
        icon = {"error": "✗", "warn": "!", "info": "i"}.get(f.level, "?")
        click.echo(f"  [{icon}] [{f.level.upper()}] {f.playbook_name}: {f.message}")

    if any(f.level == "error" for f in all_findings):
        sys.exit(1)


@playbook_cmd.command("new")
@click.argument("name")
@click.option(
    "--out-dir",
    default=".cherenkov/playbooks",
    show_default=True,
    help="Directory to write the new playbook file.",
)
def new_cmd(name: str, out_dir: str) -> None:
    """Scaffold a new playbook YAML file."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{name}.yaml"
    if dest.exists():
        click.echo(f"{dest} already exists.", err=True)
        sys.exit(1)

    slug = name.replace(" ", "-").lower()
    template = f"""\
name: {slug}
description: >
  Describe what this playbook enforces and why.
trigger:
  # path_prefix: /api/v1
  # path_contains: /users
  # methods: [GET, POST]
  # tags: [auth]
required_headers: []
  # - Authorization
expected_status: []
  # - 200
  # - 201
forbidden_response_fields: []
  # - password
  # - secret
required_response_fields: []
  # - id
severity: warn  # info | warn | error
"""
    dest.write_text(template)
    click.echo(f"Created {dest}")
