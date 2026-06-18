"""Epoch-specific CLI commands — dashboard, map, daemon, explore, author,
tokens, governance, certify, profile."""
from __future__ import annotations

import sys
import click


@click.command("dashboard")
def dashboard_cmd() -> None:
    """Visualise Truth Model + divergences."""
    from cherenkov.dashboard.render import run_dashboard

    sys.exit(run_dashboard())


@click.command("map")
@click.option("--detailed", "-d", is_flag=True, help="Show full claim details")
def map_cmd(detailed: bool) -> None:
    """Build + inspect the Truth Model from configured sources."""
    from cherenkov.stages.map_cmd import run_map

    sys.exit(run_map(detailed=detailed))


@click.command("daemon")
@click.option("--interval", "-i", type=int, default=60,
              help="Poll interval in seconds (default: 60)")
@click.option("--max-loops", "-n", "max_loops", type=int, default=0,
              help="Max rebuild iterations (0=infinite)")
@click.option("--guardian", is_flag=True, help="Run in Spec Guardian mode")
@click.option("--spec", default=None, help="Path to spec (required for --guardian)")
@click.option("--target", default=None, help="Target URL (required for --guardian)")
@click.option("--source", type=click.Choice(["openapi", "graphql", "grpc", "accessibility"]),
              default="openapi", help="Source type for guardian mode")
def daemon_cmd(interval: int, max_loops: int, guardian: bool,
               spec: str | None, target: str | None, source: str) -> None:
    """Continuously watch sources and rebuild Truth Model, or run Spec Guardian."""
    from cherenkov.stages.daemon_cmd import run_daemon, run_guardian_daemon

    if guardian:
        if not spec or not target:
            raise click.UsageError("--spec and --target are required for --guardian mode")
        sys.exit(run_guardian_daemon(
            target_url=target, spec_path=spec,
            source_type=source, interval_seconds=interval,
        ))
    else:
        sys.exit(run_daemon(interval_seconds=interval, max_loops=max_loops))


@click.command("explore")
@click.option("--target", "-t", required=True, help="Base URL of the app/API to crawl")
@click.option("--path", "-p", "paths", multiple=True,
              help="Route to probe (repeatable); default: /")
@click.option("--method", "-m", default="GET", help="HTTP method (default: GET)")
def explore_cmd(target: str, paths: tuple[str, ...], method: str) -> None:
    """Crawl a live surface and print a risk digest."""
    from cherenkov.stages.copilot_cmd import run_explore

    sys.exit(run_explore(target, paths=list(paths) or None, method=method))


@click.command("author")
@click.argument("intent")
@click.option("--output", "-o", required=True, type=click.Path(),
              help="Directory to write the .spec.ts test into")
@click.option("--target", "-t", default="", help="Base URL the flow runs against")
def author_cmd(intent: str, output: str, target: str) -> None:
    """Turn plain-language intent into an ejectable Playwright test."""
    from cherenkov.stages.copilot_cmd import run_author

    sys.exit(run_author(intent, output=output, target=target))


@click.group("tokens")
def tokens_cmd() -> None:
    """Token consumption monitor — usage, cost, recommendations."""


@tokens_cmd.command("report")
@click.option("--days", "-d", type=int, default=30, help="Lookback window in days (default: 30)")
@click.option("--json", "json_out", is_flag=True, help="Output as JSON")
def tokens_report(days: int, json_out: bool) -> None:
    """Full usage report with recommendations."""
    from cherenkov.stages.tokens_cmd import run_tokens_report

    run_tokens_report(days=days, as_json=json_out)


@tokens_cmd.command("breakdown")
@click.option("--stage", is_flag=True, help="Break down by stage instead of provider")
@click.option("--days", "-d", type=int, default=30, help="Lookback window in days (default: 30)")
def tokens_breakdown(stage: bool, days: int) -> None:
    """Per-provider or per-stage breakdown."""
    from cherenkov.stages.tokens_cmd import run_tokens_breakdown

    run_tokens_breakdown(by_stage=stage, days=days)


@click.command("governance")
@click.option("--json", "json_out", is_flag=True, help="Emit JSON report")
@click.option("--trend", "-t", metavar="METRIC", default=None,
              help="Show trend for a metric (health_score, escape_rate, …)")
def governance_cmd(json_out: bool, trend: str | None) -> None:
    """Governance KPI panel (escape/FP/coverage/maintenance)."""
    from cherenkov.stages.governance_cmd import run_governance

    sys.exit(run_governance(json_out=json_out, trend=trend))


@click.command("certify")
@click.option("--tier", "-T", type=click.Choice(["small", "deep", "vision"]),
              default="small", help="Capability tier to certify (default: small)")
@click.option("--rag-report", "-r", "rag_report", is_flag=True,
              help="Show per-item RAG-Triad metrics")
def certify_cmd(tier: str, rag_report: bool) -> None:
    """Gold-Set + RAG-Triad model tier certification."""
    from cherenkov.stages.certify_cmd import run_certify

    sys.exit(run_certify(tier=tier, rag_report=rag_report))


@click.command("profile")
@click.argument("action", type=click.Choice(["show", "set"]), default="show", required=False)
@click.option("--level", "-l",
              type=click.Choice(["assisted", "augmented", "agentic", "predictive"]),
              default=None, help="Autonomy level to set")
def profile_cmd(action: str, level: str | None) -> None:
    """Autonomy-ladder profile (assisted/augmented/agentic/predictive)."""
    from cherenkov.stages.profile_cmd import run_profile

    sys.exit(run_profile(action=action, level=level))
