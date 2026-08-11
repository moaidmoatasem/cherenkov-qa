"""Simple CLI commands — each delegates to a single module function."""
from __future__ import annotations

import sys

import click


@click.command("diff")
@click.option("--before", required=True, type=click.Path(exists=True), help="Path to the original spec")
@click.option("--after", required=True, type=click.Path(exists=True), help="Path to the modified spec")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format")
def diff_cmd(before: str, after: str, fmt: str) -> None:
    """Compare two OpenAPI specs for breaking changes.

Args:
    before (str): Parameter before.
    after (str): Parameter after.
    fmt (str): Parameter fmt.

Returns:
    None: Command execution result.
    """
    from cherenkov.diff.spec_differ import SpecDiffer, print_diff_report

    report = SpecDiffer().diff(before, after)
    print_diff_report(report, fmt=fmt)
    sys.exit(1 if report.has_breaking_changes else 0)


# report_cmd is implemented in cherenkov.cli.commands.report (divergence JSON reports + diff)
from cherenkov.cli.commands.report import report_cmd

__all__ = ["report_cmd"]


@click.command("eject")
@click.option("--output", "-o", required=True, type=click.Path(), help="Target output directory for the standalone suite")
@click.option(
    "--tests-dir",
    "-t",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help=(
        "Directory containing the generated .spec.ts test files to eject. "
        "Defaults to stub/generated_tests. Pass this when you ran "
        "`cherenkov generate --output-dir <dir>` with a custom directory — "
        "eject does not otherwise know where generate wrote its output."
    ),
)
def eject_cmd(output: str, tests_dir: str | None) -> None:
    """Eject generated tests to a standalone Playwright suite.

Args:
    output (str): Parameter output.
    tests_dir (str | None): Parameter tests_dir.

Returns:
    None: Command execution result.
    """
    from cherenkov.execution.eject import EjectorEngine

    ejector = EjectorEngine("cli_eject", tests_src_dir=tests_dir)
    click.echo(f"Reading generated tests from: {ejector.tests_src_dir}")
    if ejector.eject_suite(output):
        click.echo(f"\nCHERENKOV E2E suite ejected successfully to: {output}")
        click.echo("All CHERENKOV metadata and hooks stripped successfully.")
        click.echo("Ejected folder is 100% standard and runs standalone.\n")
        sys.exit(0)
    else:
        click.echo("\nError: Standalone test suite ejection failed.\n", err=True)
        sys.exit(1)


@click.command("self-test")
def self_test_cmd() -> None:
    """Live smoke test of the core pipeline: real Ollama generation + tsc compile.

Requires a reachable Ollama daemon and npx/tsc; exits 1 on the first
failing step. For environment diagnostics without Ollama, use `doctor`;
for an offline demonstration, use `demo`.

Returns:
    None: Command execution result.
    """
    from cherenkov.stages.self_test_cmd import run_self_test

    sys.exit(run_self_test())


@click.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion_cmd(shell: str) -> None:
    """Generate shell completion scripts.

Args:
    shell (str): Parameter shell.

Returns:
    None: Command execution result.
    """
    if shell in ("bash", "zsh"):
        click.echo('eval "$(register-python-argcomplete cherenkov)"')
    else:
        click.echo("register-python-argcomplete --shell fish cherenkov | source")


@click.command("init")
@click.option("--profile", "-p", default=None,
              type=click.Choice(["laptop", "ci", "enterprise-vpc", "frontier-cloud"]),
              help="Configuration profile (default: autodetect)")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing cherenkov.toml")
def init_cmd(profile: str | None, force: bool) -> None:
    """Zero-config project setup.

Args:
    profile (str | None): Parameter profile.
    force (bool): Parameter force.

Returns:
    None: Command execution result.
    """
    from cherenkov.stages.init_cmd import run_init

    sys.exit(run_init(profile=profile, force=force))


@click.command("doctor")
@click.option("--desktop", is_flag=True, help="Include Track C (Desktop/Tauri) checks")
def doctor_cmd(desktop: bool) -> None:
    """System health check.

Args:
    desktop (bool): Parameter desktop.

Returns:
    None: Command execution result.
    """
    from cherenkov.stages.doctor_cmd import run_doctor

    sys.exit(run_doctor(desktop=desktop))
