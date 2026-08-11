"""cherenkov/cli/commands/template_cmd.py — `cherenkov template` command."""

from pathlib import Path
import click
from cherenkov.marketplace.templates import MarketplaceTemplate, TemplateRegistry


@click.group("template")
def template_cmd() -> None:
    """Manage and install test templates from the marketplace.

Returns:
    None: Command execution result.
    """
    pass


@template_cmd.command("search")
def template_search_cmd() -> None:
    """List available templates from the marketplace.

Returns:
    None: Command execution result.
    """
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
    """List locally installed templates.

Returns:
    None: Command execution result.
    """
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
    """Download and install a specific template.

Args:
    template_id (str): Parameter template_id.

Returns:
    None: Command execution result.
    """
    registry = TemplateRegistry()
    success = registry.install_template(template_id)
    if success:
        click.echo(click.style(f"\nSuccessfully installed template '{template_id}'", fg="green"))
    else:
        click.echo(click.style(f"\nFailed to install template '{template_id}'", fg="red"), err=True)


@template_cmd.command("publish")
@click.option("--id", "template_id", required=True, help="Unique identifier for the template.")
@click.option("--name", required=True, help="Human readable name.")
@click.option("--description", default="", help="Description of the template.")
@click.option("--version", default="1.0.0", help="Template version.")
@click.option("--tags", default="", help="Comma separated tags.")
@click.option("--file", "file_path", default=None, help="Path to custom suite.yaml template file.")
def template_publish_cmd(
    template_id: str,
    name: str,
    description: str,
    version: str,
    tags: str,
    file_path: str | None,
) -> None:
    """Publish a custom test template to the marketplace.

Args:
    template_id (str): Parameter template_id.
    name (str): Parameter name.
    description (str): Parameter description.
    version (str): Parameter version.
    tags (str): Parameter tags.
    file_path (str | None): Parameter file_path.

Returns:
    None: Command execution result.
    """
    registry = TemplateRegistry()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    template = MarketplaceTemplate(
        id=template_id,
        name=name,
        description=description,
        version=version,
        tags=tag_list,
        download_url=f"local://{template_id}",
    )
    success = registry.publish_template(template, file_path=file_path)
    if success:
        click.echo(click.style(f"Successfully published template '{template_id}'", fg="green"))
    else:
        click.echo(click.style(f"Failed to publish template '{template_id}'", fg="red"), err=True)
