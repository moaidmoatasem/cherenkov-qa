"""Command tiers: what a new user sees (Core), what helps (Assist), what is experimental (Labs).

Cherenkov is the integrity gate for AI-written tests. Only a handful of commands
are that product; the rest stay callable but are not advertised in `--help`.
Anything not listed here is Labs, so a new command is Labs until someone
promotes it on purpose (tests/unit/test_cli_tiers.py pins the Core set).
"""
from __future__ import annotations

import click

CORE: tuple[str, ...] = ("check", "demo", "init", "doctor", "validate", "verify")
ASSIST: tuple[str, ...] = (
    "check-suite", "audit", "certify", "generate", "eject", "author", "agent", "docs", "review",
)
META: tuple[str, ...] = ("labs",)  # shown in the footer, never in a section


def labs_names(group: click.Group) -> list[str]:
    shown = set(CORE) | set(ASSIST) | set(META)
    return sorted(n for n in group.list_commands(click.Context(group)) if n not in shown)


class TieredGroup(click.Group):
    """Root group whose `--help` lists Core and Assist commands and points at Labs."""

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        def rows(names: tuple[str, ...]) -> list[tuple[str, str]]:
            out = []
            for name in names:
                cmd = self.get_command(ctx, name)
                if cmd is not None and not cmd.hidden:
                    out.append((name, cmd.get_short_help_str(limit=max(30, formatter.width - 22))))
            return out

        for title, names in (("Core commands", CORE), ("Assist commands", ASSIST)):
            items = rows(names)
            if items:
                with formatter.section(title):
                    formatter.write_dl(items)
        n = len(labs_names(self))
        with formatter.section("More"):
            formatter.write_text(
                f"{n} experimental commands (desktop, mobile, federation, enterprise, ...) "
                "are still available. Run `cherenkov labs` to list them."
            )
