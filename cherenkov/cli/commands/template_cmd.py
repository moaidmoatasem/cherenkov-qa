"""cherenkov/cli/commands/template_cmd.py — `cherenkov template` command."""

import click
from cherenkov.marketplace.templates import TemplateRegistry


@click.group("template")
def template_cmd() -> None:
    """Manage and install test templates from the marketplace."""
    pass


@template_cmd.command("search")
def template_search_cmd() -> None:
    """List available templates from the marketplace."""
    registry = TemplateRegistry()
    templates = registry.discover_templates()
    if not templates:
        click.echo("No templates found in the marketplace.")
        return

    click.echo(f"Found {len(templates)} templates in the marketplace:")
    for t in templates:
        click.echo(f"  - {t.id} (v{t.version}): {t.name}")
        click.echo(f"    {t.description}")
        click.echo(f"    Tags: {', '.join(t.tags)}")
        click.echo("")


@template_cmd.command("list")
def template_list_cmd() -> None:
    """List locally installed templates."""
    registry = TemplateRegistry()
    installed = registry.list_installed_templates()
    if not installed:
        click.echo("No templates are currently installed in .cherenkov/templates.")
        return

    click.echo(f"Installed templates ({len(installed)}):")
    for t in installed:
        click.echo(f"  - {t}")


@template_cmd.command("install")
@click.argument("template_id")
def template_install_cmd(template_id: str) -> None:
    """Download and install a specific template."""
    registry = TemplateRegistry()
    success = registry.install_template(template_id)
    if success:
        click.echo(click.style(f"\nSuccessfully installed template '{template_id}'", fg="green"))
    else:
        click.echo(click.style(f"\nFailed to install template '{template_id}'", fg="red"), err=True)
