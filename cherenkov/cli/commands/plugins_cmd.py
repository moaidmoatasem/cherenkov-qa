"""cherenkov/cli/commands/plugins_cmd.py — `cherenkov plugins` command."""

import click
from cherenkov.plugins.manager import PluginManager

@click.group("plugins")
def plugins_cmd() -> None:
    """Manage and inspect CHERENKOV plugins."""
    pass

@plugins_cmd.command("list")
def plugins_list_cmd() -> None:
    """List all loaded plugins."""
    manager = PluginManager()
    plugins = manager.list_plugins()
    if not plugins:
        click.echo("No plugins currently loaded via entry points.")
    else:
        click.echo(f"Loaded plugins ({len(plugins)}):")
        for p in plugins:
            click.echo(f"  - {p}")
