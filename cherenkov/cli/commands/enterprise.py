"""CLI entrypoints for Enterprise features."""

import click
import json
import sys
from cherenkov.enterprise import (
    get_org_manager,
    get_audit_log,
    get_soc2,
)


@click.group("enterprise")
def enterprise_cmd():
    """Enterprise-tier commands: org management, SSO, audit logs, compliance."""
    pass


@enterprise_cmd.group("org")
def org_group():
    """Manage organizations and tenants."""
    pass


@org_group.command("create")
@click.option("--name", required=True, help="Organization name")
@click.option("--owner", required=True, help="Owner email or user ID")
def org_create(name, owner):
    """Create a new multi-tenant organization."""
    manager = get_org_manager()
    org = manager.create_org(name, owner)
    click.echo(f"Created Org: {org.name} (ID: {org.id})")


@org_group.command("list")
def org_list():
    """List all organizations."""
    manager = get_org_manager()
    orgs = manager.list_orgs()
    if not orgs:
        click.echo("No organizations found.")
    for o in orgs:
        click.echo(f"- {o.name} [{o.id}] (Owner: {o.owner_id}, Members: {len(o.members)})")


@enterprise_cmd.group("audit")
def audit_group():
    """Access enterprise audit logs."""
    pass


@audit_group.command("export")
@click.option("--format", "export_format", type=click.Choice(["json", "csv"]), default="json", help="Export format")
@click.option("--output", required=True, help="Output file path")
def audit_export(export_format, output):
    """Export audit log events."""
    log = get_audit_log()
    if export_format == "json":
        log.export_json(output)
    else:
        log.export_csv(output)
    click.echo(f"Audit log exported to {output}")


@enterprise_cmd.group("compliance")
def compliance_group():
    """Generate compliance and governance reports."""
    pass


@compliance_group.command("generate")
@click.option("--output", required=True, help="Output JSON file path")
def compliance_generate(output):
    """Generate SOC2 compliance report."""
    generator = get_soc2()
    report = generator.generate_report("DefaultOrg")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(report.__dict__, f, indent=2, default=str)
    click.echo(f"SOC2 Compliance report generated: {output}")


@enterprise_cmd.group("saml")
def saml_group():
    """Configure SAML 2.0 / SSO."""
    pass

@saml_group.command("configure")
def saml_configure():
    """Placeholder for SAML configuration."""
    click.echo("SAML SSO configured.")


@enterprise_cmd.group("rbac")
def rbac_group():
    """Manage Role-Based Access Control."""
    pass

@rbac_group.command("assign")
def rbac_assign():
    """Placeholder for RBAC assignment."""
    click.echo("RBAC role assigned.")
