"""CLI entrypoints for Enterprise features."""
from __future__ import annotations

import json

import click

from cherenkov.enterprise import (
    SAMLConfig,
    SAMLServiceProvider,
    get_audit_log,
    get_org_manager,
    get_rbac,
    get_soc2,
)
from cherenkov.enterprise.rbac import Role, User


@click.group("enterprise")
def enterprise_cmd():
    """Enterprise feature commands: org management, SSO, RBAC, audit, compliance.

Returns:
    None: Command execution result.
    """
    pass


@enterprise_cmd.group("org")
def org_group():
    """Manage organizations and tenants.

Returns:
    None: Command execution result.
    """
    pass


@org_group.command("create")
@click.option("--name", required=True, help="Organization name")
@click.option("--owner", required=True, help="Owner email or user ID")
def org_create(name, owner):
    """Create a new multi-tenant organization.

Args:
    name: Parameter name.
    owner: Parameter owner.

Returns:
    None: Command execution result.
    """
    manager = get_org_manager()
    org = manager.create_org(name, owner)
    click.echo(f"Created Org: {org.name} (ID: {org.id})")


@org_group.command("list")
def org_list():
    """List all organizations.

Returns:
    None: Command execution result.
    """
    manager = get_org_manager()
    orgs = manager.list_orgs()
    if not orgs:
        click.echo("No organizations found.")
    for o in orgs:
        click.echo(f"- {o.name} [{o.id}] (Owner: {o.owner_id}, Members: {len(o.members)})")


@enterprise_cmd.group("audit")
def audit_group():
    """Access enterprise audit logs.

Returns:
    None: Command execution result.
    """
    pass


@audit_group.command("export")
@click.option("--format", "export_format", type=click.Choice(["json", "csv"]), default="json", help="Export format")
@click.option("--output", required=True, help="Output file path")
def audit_export(export_format, output):
    """Export audit log events.

Args:
    export_format: Parameter export_format.
    output: Parameter output.

Returns:
    None: Command execution result.
    """
    log = get_audit_log()
    if export_format == "json":
        log.export_json(output)
    else:
        log.export_csv(output)
    click.echo(f"Audit log exported to {output}")


@enterprise_cmd.group("compliance")
def compliance_group():
    """Generate compliance and governance reports.

Returns:
    None: Command execution result.
    """
    pass


@compliance_group.command("generate")
@click.option("--output", required=True, help="Output JSON file path")
def compliance_generate(output):
    """Generate SOC2 compliance report.

Args:
    output: Parameter output.

Returns:
    None: Command execution result.
    """
    generator = get_soc2()
    report = generator.generate_report("DefaultOrg")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(report.__dict__, f, indent=2, default=str)
    click.echo(f"SOC2 Compliance report generated: {output}")


@enterprise_cmd.group("saml")
def saml_group():
    """Configure SAML 2.0 / SSO.

Returns:
    None: Command execution result.
    """
    pass

@saml_group.command("configure")
@click.option("--idp-metadata-url", required=True, help="SAML IdP metadata endpoint URL")
@click.option("--entity-id", default="cherenkov-qa", help="SAML entity ID advertised to the IdP")
@click.option("--acs-url", default="/api/v1/auth/saml/callback", help="Assertion Consumer Service URL")
@click.option("--enabled/--disabled", "enabled", default=True, help="Enable or disable SAML SSO")
def saml_configure(idp_metadata_url, entity_id, acs_url, enabled):
    """Configure SAML 2.0 / SSO against an IdP metadata endpoint.

Args:
    idp_metadata_url: Parameter idp_metadata_url.
    entity_id: Parameter entity_id.
    acs_url: Parameter acs_url.
    enabled: Parameter enabled.

Returns:
    None: Command execution result.
    """
    config = SAMLConfig(
        idp_metadata_url=idp_metadata_url,
        entity_id=entity_id,
        acs_url=acs_url,
        enabled=enabled,
    )
    sp = SAMLServiceProvider(config)
    click.echo(f"SAML SSO {'enabled' if enabled else 'disabled'} for IdP {idp_metadata_url}")
    click.echo(f"Entity ID: {entity_id}  |  ACS URL: {acs_url}")
    login_url = sp.get_login_url()
    if login_url:
        click.echo(f"SP-initiated login URL: {login_url}")


@enterprise_cmd.group("rbac")
def rbac_group():
    """Manage Role-Based Access Control.

Returns:
    None: Command execution result.
    """
    pass

@rbac_group.command("assign")
@click.option("--user", required=True, help="User ID to assign the role to")
@click.option("--role", required=True, type=click.Choice([r.value for r in Role]), help="Role to assign")
def rbac_assign(user, role):
    """Assign a role to a user in the RBAC engine.

Args:
    user: Parameter user.
    role: Parameter role.

Returns:
    None: Command execution result.
    """
    engine = get_rbac()
    target_role = Role(role)
    if engine.get_user(user) is None:
        engine.register_user(User(id=user, name=user, email="", role=target_role))
        click.echo(f"Registered user '{user}' with role '{role}'")
    else:
        engine.set_role(user, target_role)
        click.echo(f"Assigned role '{role}' to user '{user}'")
