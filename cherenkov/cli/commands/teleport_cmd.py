"""Teleport CLI Command Group (CC-5)."""
from __future__ import annotations

import json
import sys

import click

from cherenkov.continuity.sessions.adapters.sqlite_sessions import SQLiteSessionStore
from cherenkov.continuity.sessions.use_cases.resume import ResumeSessionUseCase
from cherenkov.continuity.sessions.use_cases.snapshot import SnapshotSessionUseCase

store = SQLiteSessionStore()
snapshot_uc = SnapshotSessionUseCase(store)
resume_uc = ResumeSessionUseCase(store)


@click.group(name="teleport")
def teleport_cmd():
    """Manage cross-device session teleportation (CC-5)."""
    pass


@teleport_cmd.command()
@click.argument("session_id")
@click.argument("state_data_json", required=False, default="{}")
def push(session_id: str, state_data_json: str):
    """Push a session state and generate a teleport token."""
    try:
        state_data = json.loads(state_data_json)
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON for state_data.", err=True)
        sys.exit(1)

    snapshot = snapshot_uc.execute(session_id, state_data)
    if snapshot.token:
        click.echo(f"Session '{session_id}' pushed successfully.")
        click.echo(f"Teleport Token: {snapshot.token.token}")
    else:
        click.echo("Failed to generate teleport token.", err=True)
        sys.exit(1)


@teleport_cmd.command()
@click.argument("token")
def pull(token: str):
    """Pull a session state using a teleport token."""
    snapshot = resume_uc.execute_by_token(token)
    if snapshot:
        click.echo(f"Resumed session '{snapshot.id}'.")
        click.echo("State Data:")
        click.echo(json.dumps(snapshot.state_data, indent=2))
    else:
        click.echo("Error: Invalid or expired token.", err=True)
        sys.exit(1)


@teleport_cmd.command()
def list():
    """List all available session snapshots."""
    sessions = store.list_sessions()
    if not sessions:
        click.echo("No sessions found.")
        return

    for s in sessions:
        token_str = s.token.token if s.token else "None"
        click.echo(f"- ID: {s.id} | Token: {token_str} | Updated: {s.updated_at.isoformat()}")


@teleport_cmd.command()
@click.argument("session_id")
def status(session_id: str):
    """Get the status of a specific session by ID."""
    snapshot = store.load(session_id)
    if not snapshot:
        click.echo(f"Session '{session_id}' not found.", err=True)
        sys.exit(1)

    click.echo(f"Session ID: {snapshot.id}")
    token_str = snapshot.token.token if snapshot.token else "None"
    click.echo(f"Teleport Token: {token_str}")
    click.echo(f"Created At: {snapshot.created_at.isoformat()}")
    click.echo(f"Updated At: {snapshot.updated_at.isoformat()}")
    click.echo("State Data:")
    click.echo(json.dumps(snapshot.state_data, indent=2))
