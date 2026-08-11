"""
CLI command groups (consolidation).

Organizes the flat top-level command list into logical groups while keeping
every legacy top-level command name registered as an alias, so existing
invocations keep working unchanged.
"""

from __future__ import annotations

import click

# Group name -> layout. ``commands`` lists the top-level command names that
# belong in the group; the same command objects stay registered at the top
# level for backwards compatibility.
GROUP_LAYOUT: dict[str, dict] = {
    "pipeline": {
        "help": "Core API conformance pipeline: validate, verify, audit, generate, bench.",
        "commands": [
            "validate",
            "verify",
            "audit",
            "check-suite",
            "check-stale",
            "synthetic",
            "generate",
            "bench",
            "eval",
            "drift",
        ],
    },
    "review": {
        "help": "Human-in-the-loop review workflows: hitl, review, ocr.",
        "commands": ["hitl", "review", "ocr"],
    },
    "model": {
        "help": "Model / VLM substrate commands: visual, perf, mcp, examples.",
        "commands": ["visual", "perf", "mcp", "examples"],
    },
    "operate": {
        "help": "Long-running operations and observability: daemon, dashboard, teleport.",
        "commands": [
            "daemon",
            "dashboard",
            "explore",
            "map",
            "author",
            "record",
            "tokens",
            "governance",
            "profile",
            "teleport",
        ],
    },
    "admin": {
        "help": "Setup, maintenance, and self-service: init, doctor, self-test, report.",
        "commands": [
            "init",
            "doctor",
            "self-test",
            "eject",
            "completion",
            "report",
            "diff",
            "demo",
        ],
    },
    "enterprise": {
        "help": "Enterprise integrations and certification: enterprise, certify, playbook, guardian.",
        "commands": ["enterprise", "certify", "playbook", "guardian"],
    },
    "routine": {
        "help": "Scheduled routines: routine.",
        "commands": ["routine"],
    },
}


def build_groups(commands: dict[str, click.Command]) -> list[click.Group]:
    """Build the nested command groups from the registered command map.

    Args:
        commands: Dictionary mapping command names to click.Command instances.

    Returns:
        list[click.Group]: List of configured Click command groups.
    """
    groups: list[click.Group] = []
    for name, layout in GROUP_LAYOUT.items():
        group = click.Group(name=name, help=layout["help"])
        group.no_args_is_help = True
        for cmd_name in layout["commands"]:
            cmd = commands.get(cmd_name)
            if cmd is not None:
                group.add_command(cmd)
        groups.append(group)
    return groups

