import sys
import click


@click.group(invoke_without_command=True, context_settings=dict(ignore_unknown_options=True))
@click.pass_context
def cli(ctx):
    """CHERENKOV E2E Suite Command Line Interface"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# All commands ported to Click. The legacy argparse CLI (legacy_cli.py) has been
# deleted — these are the only entry points.
_CLICK_COMMANDS = [
    "validate", "synthetic",
    "diff", "report", "eject", "self-test", "completion", "init", "doctor",
    "visual", "perf", "hitl", "review", "mcp",
    "dashboard", "map", "daemon", "explore", "author",
    "tokens", "governance", "certify", "profile",
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
    from cherenkov.cli.commands.epoch import (
        dashboard_cmd, map_cmd, daemon_cmd, explore_cmd, author_cmd,
        tokens_cmd, governance_cmd, certify_cmd, profile_cmd,
    )
    for cmd, name in [
        (validate_cmd, "validate"), (synthetic_cmd, "synthetic"),
        (diff_cmd, "diff"), (report_cmd, "report"), (eject_cmd, "eject"),
        (self_test_cmd, "self-test"), (completion_cmd, "completion"),
        (init_cmd, "init"), (doctor_cmd, "doctor"),
        (visual_cmd, "visual"), (perf_cmd, "perf"),
        (hitl_cmd, "hitl"), (review_cmd, "review"), (mcp_cmd, "mcp"),
        (dashboard_cmd, "dashboard"), (map_cmd, "map"), (daemon_cmd, "daemon"),
        (explore_cmd, "explore"), (author_cmd, "author"),
        (tokens_cmd, "tokens"), (governance_cmd, "governance"),
        (certify_cmd, "certify"), (profile_cmd, "profile"),
    ]:
        cli.add_command(cmd, name=name)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in _CLICK_COMMANDS:
        _register_commands()
        cli()
    else:
        _register_commands()
        with click.Context(cli) as ctx:
            click.echo(ctx.get_help())


if __name__ == '__main__':
    main()
