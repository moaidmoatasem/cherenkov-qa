"""Simple CLI commands — each delegates to a single module function."""

from __future__ import annotations

import sys
import click


@click.command("diff")
@click.option(
    "--before",
    required=True,
    type=click.Path(exists=True),
    help="Path to the original spec",
)
@click.option(
    "--after",
    required=True,
    type=click.Path(exists=True),
    help="Path to the modified spec",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
def diff_cmd(before: str, after: str, fmt: str) -> None:
    """Compare two OpenAPI specs for breaking changes."""
    from cherenkov.diff.spec_differ import SpecDiffer, print_diff_report

    report = SpecDiffer().diff(before, after)
    print_diff_report(report, fmt=fmt)
    sys.exit(1 if report.has_breaking_changes else 0)


@click.command("report")
@click.option(
    "--output", "-o", default=None, help="JSON output file path (e.g. report.json)"
)
@click.option(
    "--diff",
    "-d",
    "diff_path",
    default=None,
    help="Path to previous report.json for diff comparison",
)
def report_cmd(output: str | None, diff_path: str | None) -> None:
    """Generate test coverage and diff reports from run logs."""
    from cherenkov.stages.report_cmd import run_report

    sys.exit(run_report(output=output, diff=diff_path))


@click.command("eject")
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(),
    help="Target output directory for the standalone suite",
)
def eject_cmd(output: str) -> None:
    """Eject generated tests to a standalone Playwright suite."""
    from cherenkov.execution.eject import EjectorEngine

    ejector = EjectorEngine("cli_eject")
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
    """Run a deterministic dry-run of the pipeline (mocking Ollama and the server)."""
    from cherenkov.stages.self_test_cmd import run_self_test

    sys.exit(run_self_test())


@click.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion_cmd(shell: str) -> None:
    """Generate shell completion scripts."""
    if shell in ("bash", "zsh"):
        click.echo('eval "$(register-python-argcomplete cherenkov)"')
    else:
        click.echo("register-python-argcomplete --shell fish cherenkov | source")


@click.command("init")
@click.option(
    "--profile",
    "-p",
    default=None,
    type=click.Choice(["laptop", "ci", "enterprise-vpc", "frontier-cloud"]),
    help="Configuration profile (default: autodetect)",
)
@click.option("--force", "-f", is_flag=True, help="Overwrite existing cherenkov.toml")
def init_cmd(profile: str | None, force: bool) -> None:
    """Zero-config project setup."""
    from cherenkov.stages.init_cmd import run_init

    sys.exit(run_init(profile=profile, force=force))


@click.command("doctor")
@click.option("--desktop", is_flag=True, help="Include Track C (Desktop/Tauri) checks")
def doctor_cmd(desktop: bool) -> None:
    """System health check."""
    from cherenkov.stages.doctor_cmd import run_doctor

    sys.exit(run_doctor(desktop=desktop))
