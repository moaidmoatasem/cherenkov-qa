"""CLI commands for Routines (CC-4)."""
from __future__ import annotations

import click
import json
from cherenkov.scheduling.adapters.apscheduler_adapter import APSchedulerAdapter
from cherenkov.scheduling.use_cases.manage_routines import create_routine, toggle_routine

@click.group("routine")
def routine_cmd() -> None:
    """Manage automated scheduling routines."""
    pass


@routine_cmd.command("list")
def list_routines() -> None:
    """List all registered routines."""
    scheduler = APSchedulerAdapter()
    routines = scheduler.list_routines()
    if not routines:
        click.echo("No routines found.")
        return
    for r in routines:
        status = "ENABLED" if r.enabled else "DISABLED"
        click.echo(f"[{status}] {r.id}: {r.name} ({r.trigger.type} -> {r.trigger.value})")


@routine_cmd.command("create")
@click.option("--name", required=True)
@click.option("--description", default="")
@click.option("--trigger", required=True, type=click.Choice(["cron", "interval"]))
@click.option("--value", required=True, help="Cron expression or interval seconds")
@click.option("--target", required=True, help="Module path e.g. 'cherenkov.scheduling.templates.health:run'")
def create_routine_cli(name: str, description: str, trigger: str, value: str, target: str) -> None:
    """Create a new routine."""
    scheduler = APSchedulerAdapter()
    r = create_routine(scheduler, name, description, trigger, value, target, {})
    click.echo(f"Created routine {r.id}")


@routine_cmd.command("toggle")
@click.argument("routine_id")
@click.argument("enabled", type=bool)
def toggle_routine_cli(routine_id: str, enabled: bool) -> None:
    """Enable or disable a routine."""
    scheduler = APSchedulerAdapter()
    toggle_routine(scheduler, routine_id, enabled)
    click.echo(f"Toggled routine {routine_id} to {enabled}")


@routine_cmd.command("trigger")
@click.argument("routine_id")
def trigger_routine_cli(routine_id: str) -> None:
    """Trigger a routine immediately."""
    scheduler = APSchedulerAdapter()
    scheduler.trigger_routine_now(routine_id)
    click.echo(f"Triggered routine {routine_id}")
