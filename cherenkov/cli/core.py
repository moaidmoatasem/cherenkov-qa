import sys
import click
from cherenkov.cli.legacy_cli import main as legacy_main

@click.group(invoke_without_command=True, context_settings=dict(ignore_unknown_options=True))
@click.pass_context
def cli(ctx):
    """CHERENKOV E2E Suite Command Line Interface (Modular)"""
    if ctx.invoked_subcommand is None:
        legacy_main()

# Commands fully ported to Click — no longer handled by legacy_main().
# Add names here as they are migrated; everything else falls back to legacy_main().
_CLICK_COMMANDS = [
    "validate",
    "synthetic",
    "diff",
    "report",
    "eject",
    "self-test",
    "completion",
    "init",
    "doctor",
    "visual",
    "perf",
    "hitl",
    "review",
    "mcp",
]


def _register_commands() -> None:
    from cherenkov.cli.commands.validate import validate_cmd
    from cherenkov.synthetic.cmd import synthetic_cmd
    from cherenkov.cli.commands.simple import (
        diff_cmd, report_cmd, eject_cmd,
        self_test_cmd, completion_cmd, init_cmd, doctor_cmd,
    )
    from cherenkov.cli.commands.advanced import (
        visual_cmd, perf_cmd, hitl_cmd, review_cmd, mcp_cmd,
    )
    cli.add_command(validate_cmd, name="validate")
    cli.add_command(synthetic_cmd, name="synthetic")
    cli.add_command(diff_cmd, name="diff")
    cli.add_command(report_cmd, name="report")
    cli.add_command(eject_cmd, name="eject")
    cli.add_command(self_test_cmd, name="self-test")
    cli.add_command(completion_cmd, name="completion")
    cli.add_command(init_cmd, name="init")
    cli.add_command(doctor_cmd, name="doctor")
    cli.add_command(visual_cmd, name="visual")
    cli.add_command(perf_cmd, name="perf")
    cli.add_command(hitl_cmd, name="hitl")
    cli.add_command(review_cmd, name="review")
    cli.add_command(mcp_cmd, name="mcp")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in _CLICK_COMMANDS:
        _register_commands()
        cli()
    else:
        legacy_main()


if __name__ == '__main__':
    main()
