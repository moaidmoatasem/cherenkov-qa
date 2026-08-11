"""CLI commands for federation operations.

Provides:
- ``cherenkov federation join <url>`` – stores remote URL and optional token.
- ``cherenkov federation query <topic>`` – queries the remote mesh.
- ``cherenkov federation push <topic> <json>`` – pushes local payload.
"""

import json
import click
from pathlib import Path
from cherenkov.federation.mesh import FederationClient

CONFIG_PATH = Path(".cherenkov/federation_config.json")


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


@click.group("federation")
def federation_cmd() -> None:
    """Manage federation with remote CHERENKOV instances.

Returns:
    None: Command execution result.
    """
    pass


@federation_cmd.command("join")
@click.argument("url")
@click.option("--token", default=None, help="Bearer token for auth.")
def federation_join_cmd(url: str, token: str) -> None:
    """Store a remote federation endpoint.

Args:
    url (str): Parameter url.
    token (str): Parameter token.

Returns:
    None: Command execution result.
    """
    cfg = _load_config()
    cfg["remote_url"] = url.rstrip("/")
    cfg["token"] = token
    _save_config(cfg)
    click.echo(f"Federation endpoint set to {url}")


@federation_cmd.command("query")
@click.argument("topic")
def federation_query_cmd(topic: str) -> None:
    """Query the remote mesh for a topic and display results.

Args:
    topic (str): Parameter topic.

Returns:
    None: Command execution result.
    """
    cfg = _load_config()
    if "remote_url" not in cfg:
        click.echo("No federation endpoint configured. Use 'cherenkov federation join' first.", err=True)
        return
    client = FederationClient(cfg["remote_url"], cfg.get("token"))
    results = client.query_topic(topic)
    click.echo(json.dumps(results, indent=2))


@federation_cmd.command("push")
@click.argument("topic")
@click.argument("payload", type=click.File("r"))
def federation_push_cmd(topic: str, payload) -> None:
    """Push a JSON payload to the remote mesh under a topic.

Args:
    topic (str): Parameter topic.
    payload: Parameter payload.

Returns:
    None: Command execution result.
    """
    cfg = _load_config()
    if "remote_url" not in cfg:
        click.echo("No federation endpoint configured. Use 'cherenkov federation join' first.", err=True)
        return
    try:
        data = json.load(payload)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON payload: {e}", err=True)
        return
    client = FederationClient(cfg["remote_url"], cfg.get("token"))
    success = client.push_local(topic, data)
    if success:
        click.echo("Push successful.")
    else:
        click.echo("Push failed.", err=True)
