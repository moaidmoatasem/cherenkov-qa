"""CLI entrypoints for Enterprise features."""

import json
from typing import Optional
from cherenkov.enterprise import (
    get_org_manager,
    get_audit_log,
    get_soc2_generator,
)


def run_enterprise_org(action: str, name: Optional[str] = None, owner: Optional[str] = None):
    manager = get_org_manager()
    if action == "create":
        if not name or not owner:
            print("Error: --name and --owner required for org create")
            return 1
        org = manager.create_org(name, owner)
        print(f"Created Org: {org.name} (ID: {org.id})")
        return 0
    elif action == "list":
        orgs = manager.list_orgs()
        if not orgs:
            print("No organizations found.")
        for o in orgs:
            print(f"- {o.name} [{o.id}] (Owner: {o.owner_id}, Members: {len(o.members)})")
        return 0
    return 1


def run_enterprise_audit(action: str, output: str, export_format: str):
    log = get_audit_log()
    if action == "export":
        if export_format == "json":
            log.export_json(output)
        else:
            log.export_csv(output)
        print(f"Audit log exported to {output}")
        return 0
    return 1


def run_enterprise_compliance(action: str, output: str):
    generator = get_soc2_generator()
    if action == "generate":
        report = generator.generate_report("DefaultOrg")
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report.__dict__, f, indent=2, default=str)
        print(f"SOC2 Compliance report generated: {output}")
        return 0
    return 1
