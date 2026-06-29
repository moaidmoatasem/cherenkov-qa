import sys
import click


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """CHERENKOV E2E Suite Command Line Interface"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


_CLICK_COMMANDS = [
    "verify",
    "check-suite",
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
    "dashboard",
    "map",
    "daemon",
    "explore",
    "author",
    "tokens",
    "governance",
    "certify",
    "profile",
    "bench",
    "ocr",
    "drift",
    "eval",
    "routine",
    "teleport",
    "enterprise",
]


def _register_commands() -> None:
    from cherenkov.cli.commands.validate import validate_cmd
    from cherenkov.cli.commands.verify import verify_cmd
    from cherenkov.cli.commands.check_suite import check_suite_cmd
    from cherenkov.synthetic.cmd import synthetic_cmd
    from cherenkov.cli.commands.simple import (
        diff_cmd,
        report_cmd,
        eject_cmd,
        self_test_cmd,
        completion_cmd,
        init_cmd,
        doctor_cmd,
    )
    from cherenkov.cli.commands.generate_cmd import generate_cmd
    from cherenkov.cli.commands.advanced import (
        visual_cmd,
        perf_cmd,
        hitl_cmd,
        review_cmd,
        mcp_cmd,
    )
    from cherenkov.cli.commands.epoch import (
        dashboard_cmd,
        map_cmd,
        daemon_cmd,
        explore_cmd,
        author_cmd,
        tokens_cmd,
        governance_cmd,
        profile_cmd,
    )
    from cherenkov.cli.commands.certify import certify_cmd
    from cherenkov.cli.commands.bench import bench_cmd
    from cherenkov.cli.commands.ocr_cmd import ocr_cmd
    from cherenkov.cli.commands.check_stale import check_stale_cmd
    from cherenkov.cli.commands.drift_cmd import drift_cmd
    from cherenkov.cli.commands.demo_cmd import demo_cmd
    from cherenkov.cli.commands.eval_cmd import eval_cmd
    from cherenkov.cli.commands.examples_cmd import examples_cmd
    from cherenkov.cli.commands.routine_cmd import routine_cmd
    from cherenkov.cli.commands.teleport_cmd import teleport_cmd
    from cherenkov.cli.commands.enterprise import enterprise_cmd

    for cmd, name in [
        (verify_cmd, "verify"),
        (check_suite_cmd, "check-suite"),
        (validate_cmd, "validate"),
        (synthetic_cmd, "synthetic"),
        (diff_cmd, "diff"),
        (report_cmd, "report"),
        (eject_cmd, "eject"),
        (self_test_cmd, "self-test"),
        (completion_cmd, "completion"),
        (init_cmd, "init"),
        (doctor_cmd, "doctor"),
        (visual_cmd, "visual"),
        (perf_cmd, "perf"),
        (hitl_cmd, "hitl"),
        (review_cmd, "review"),
        (mcp_cmd, "mcp"),
        (generate_cmd, "generate"),
        (dashboard_cmd, "dashboard"),
        (map_cmd, "map"),
        (daemon_cmd, "daemon"),
        (explore_cmd, "explore"),
        (author_cmd, "author"),
        (tokens_cmd, "tokens"),
        (governance_cmd, "governance"),
        (certify_cmd, "certify"),
        (profile_cmd, "profile"),
        (bench_cmd, "bench"),
        (ocr_cmd, "ocr"),
        (check_stale_cmd, "check-stale"),
        (drift_cmd, "drift"),
        (demo_cmd, "demo"),
        (eval_cmd, "eval"),
        (examples_cmd, "examples"),
        (routine_cmd, "routine"),
        (teleport_cmd, "teleport"),
        (enterprise_cmd, "enterprise"),
    ]:
        cli.add_command(cmd, name=name)


def main():
    # Legacy bare invocation: `cherenkov --spec foo.yaml` → `cherenkov validate --spec foo.yaml`
    if len(sys.argv) > 1 and sys.argv[1].startswith("-") and "--spec" in sys.argv[1:]:
        sys.argv.insert(1, "validate")
    _register_commands()
    cli()


if __name__ == "__main__":
    main()
