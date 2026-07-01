"""Advanced CLI commands — visual, perf, hitl, review, mcp."""
from __future__ import annotations

import sys
import click


@click.command("visual")
@click.option("--target", "-t", required=True, help="Absolute URL of the page to snapshot")
@click.option("--baseline-dir", default="stub/visual_baselines",
              help="Baseline directory (default: stub/visual_baselines)")
def visual_cmd(target: str, baseline_dir: str) -> None:
    """Run optional visual-regression checks against a rendered URL (Track B)."""
    from cherenkov.core.orchestrator import OrchestrationEngine
    from cherenkov.core.contracts import VisualSlice
    from cherenkov.cli.legacy_reports import print_visual_report

    slices = [VisualSlice(name="cli_default", url=target)]
    engine = OrchestrationEngine(run_id="cli_visual")
    reports = engine.run_visual_stage(slices, baseline_dir=baseline_dir)
    print_visual_report(target, reports)
    sys.exit(0 if (reports and all(r.status == "ok" for r in reports)) else 1)


@click.command("perf")
@click.option("--target", "-t", required=True, help="Base URL of the API to load test")
@click.option("--endpoint", default="/", help="Endpoint path (default: /)")
@click.option("--method", default="GET", help="HTTP method (default: GET)")
@click.option("--vus", type=int, default=5, help="Virtual users (default: 5)")
@click.option("--duration", type=int, default=5, help="Duration in seconds (default: 5)")
def perf_cmd(target: str, endpoint: str, method: str, vus: int, duration: int) -> None:
    """Run optional performance baseline checks (Track B)."""
    from cherenkov.core.orchestrator import OrchestrationEngine
    from cherenkov.core.contracts import PerfSlice
    from cherenkov.cli.legacy_reports import print_perf_report

    slices = [PerfSlice(
        name="cli_default",
        target_url=target,
        endpoint=endpoint,
        method=method,
        vus=vus,
        duration_sec=duration,
    )]
    engine = OrchestrationEngine(run_id="cli_perf")
    reports = engine.run_perf_stage(slices)
    print_perf_report(target, reports)
    sys.exit(1 if any(r.status != "ok" for r in reports) else 0)


@click.group("hitl")
def hitl_cmd() -> None:
    """Manage the Human-in-the-Loop review queue."""


@hitl_cmd.command("list")
@click.option("--status", type=click.Choice(["pending", "approved", "rejected", "ignored"]),
              default="pending", help="Filter by status (default: pending)")
@click.option("--all", "-a", "list_all", is_flag=True, help="Show all statuses")
@click.option("--json", "json_out", is_flag=True, help="Emit JSON envelope")
def hitl_list(status: str, list_all: bool, json_out: bool) -> None:
    """List HITL queue items."""
    from cherenkov.hitl.cmd import run_list

    sys.exit(run_list(status=None if list_all else status, json_out=json_out))


@hitl_cmd.command("show")
@click.argument("item_id")
@click.option("--json", "json_out", is_flag=True, help="Emit JSON envelope")
def hitl_show(item_id: str, json_out: bool) -> None:
    """Show details of a single HITL item."""
    from cherenkov.hitl.cmd import run_show

    sys.exit(run_show(item_id=item_id, json_out=json_out))


@hitl_cmd.command("approve")
@click.argument("item_id")
@click.option("--actor", default=None, help="Reviewer identity (default: $USER)")
@click.option("--json", "json_out", is_flag=True, help="Emit JSON envelope")
def hitl_approve(item_id: str, actor: str | None, json_out: bool) -> None:
    """Approve a pending HITL item."""
    from cherenkov.hitl.cmd import run_approve

    sys.exit(run_approve(item_id=item_id, actor=actor, json_out=json_out))


@hitl_cmd.command("reject")
@click.argument("item_id")
@click.option("--reason", "-r", required=True, help="Rejection reason")
@click.option("--actor", default=None, help="Reviewer identity (default: $USER)")
@click.option("--json", "json_out", is_flag=True, help="Emit JSON envelope")
def hitl_reject(item_id: str, reason: str, actor: str | None, json_out: bool) -> None:
    """Reject a HITL item."""
    from cherenkov.hitl.cmd import run_reject

    sys.exit(run_reject(item_id=item_id, reason=reason, actor=actor, json_out=json_out))


@hitl_cmd.command("classify")
@click.argument("item_id")
@click.option("--classification", "-c", required=True,
              type=click.Choice(["regression", "intended", "ignore"]),
              help="Classification label")
@click.option("--actor", default=None, help="Reviewer identity (default: $USER)")
@click.option("--detail", "-d", default="", help="Free-text detail")
@click.option("--json", "json_out", is_flag=True, help="Emit JSON envelope")
def hitl_classify(item_id: str, classification: str, actor: str | None,
                  detail: str, json_out: bool) -> None:
    """Classify a HITL item (Tier-2)."""
    from cherenkov.hitl.cmd import run_classify

    sys.exit(run_classify(item_id=item_id, classification=classification,
                          actor=actor, detail=detail, json_out=json_out))


@hitl_cmd.command("explain")
@click.argument("item_id")
@click.option("--json", "json_out", is_flag=True, help="Emit JSON envelope")
def hitl_explain(item_id: str, json_out: bool) -> None:
    """Get an AI explanation for why a HITL item was flagged (Tier-3)."""
    from cherenkov.hitl.cmd import run_explain

    sys.exit(run_explain(item_id=item_id, json_out=json_out))


@click.command("review")
@click.option("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
@click.option("--port", "-p", type=int, default=8000, help="Port to bind (default: 8000)")
@click.option("--demo", is_flag=True, help="Load demo fixture data into HITL queue on startup")
def review_cmd(host: str, port: int, demo: bool) -> None:
    """Start the review dashboard web UI (FastAPI + prebuilt frontend)."""
    import os
    import uvicorn
    from cherenkov.web.api import app

    if demo or os.environ.get("DEMO_MODE") == "1":
        from cherenkov.execution.demo_mode import generate_demo_findings

        click.echo("Loading demo findings into HITL queue...")
        generate_demo_findings()

    click.echo(f"\nCHERENKOV review dashboard starting on http://{host}:{port}")
    click.echo("Hit Ctrl+C to stop.\n")
    uvicorn.run(app, host=host, port=port, log_level="info")


@click.group("mcp")
def mcp_cmd() -> None:
    """Expose CHERENKOV over Model Context Protocol."""


@mcp_cmd.command("serve")
def mcp_serve() -> None:
    """Start the MCP server over stdio."""
    from cherenkov.mcp.server import run_mcp_server

    run_mcp_server()


@mcp_cmd.command("publish")
@click.option("--name", required=True, help="Server name")
@click.option("--url", required=True, help="Server URL")
@click.option("--tools", default="[]", help="JSON list of tool definitions")
@click.option("--resources", default="[]", help="JSON list of resource definitions")
@click.option("--version", default="1.0.0", help="Server version")
@click.option("--attestation", default="", help="Optional attestation token")
def mcp_publish(name: str, url: str, tools: str, resources: str,
                version: str, attestation: str) -> None:
    """Register an external MCP server with the mesh registry."""
    import json
    from cherenkov.mcp.mesh_router import get_registry

    registry = get_registry()
    reg_id = registry.register_server(
        name=name, url=url,
        tools=json.loads(tools), resources=json.loads(resources),
        version=version, attestation=attestation,
    )
    click.echo(json.dumps({"status": "ok", "registration_id": reg_id}))


@mcp_cmd.command("install")
@click.option("--platform", type=click.Choice(["claude", "cursor", "windsurf", "all"]),
              default="all", help="Target platform (default: all)")
@click.option("--write", is_flag=True, help="Write config file directly")
def mcp_install(platform: str, write: bool) -> None:
    """Generate MCP configuration for Claude Desktop, Cursor, Windsurf."""
    from cherenkov.mcp.install import MCPConfigGenerator

    if write and platform == "all":
        raise click.UsageError("--write requires a specific --platform (claude, cursor)")

    gen = MCPConfigGenerator()
    if write and platform == "claude":
        click.echo(f"Claude Desktop config written to {gen.write_claude_config()}")
    elif write and platform == "cursor":
        click.echo(f"Cursor config written to {gen.write_cursor_config()}")
    else:
        gen.print_configs()


@mcp_cmd.command("discover")
def mcp_discover() -> None:
    """Discover available tools in the MCP Marketplace."""
    from cherenkov.mcp.marketplace.registry import MarketplaceRegistry

    registry = MarketplaceRegistry()
    tools = registry.discover_tools()
    if not tools:
        click.echo("No tools found in the marketplace.")
        return

    click.echo(f"Found {len(tools)} tools in the marketplace:")
    for t in tools:
        click.echo(f"- {t.id} (v{t.version}): {t.description}")


@mcp_cmd.command("install-tool")
@click.argument("tool_id")
def mcp_install_tool(tool_id: str) -> None:
    """Install a tool from the MCP Marketplace."""
    from cherenkov.mcp.install import install_marketplace_tool

    success = install_marketplace_tool(tool_id)
    if not success:
        raise click.ClickException(f"Failed to install {tool_id}")


@mcp_cmd.command("remove")
@click.argument("tool_id")
def mcp_remove(tool_id: str) -> None:
    """Remove a marketplace tool."""
    import subprocess
    click.echo(f"Removing {tool_id}...")
    try:
        # In a real scenario, map tool_id to package name
        package_name = f"cherenkov-mcp-{tool_id.split('-')[0]}"
        subprocess.run(["pip", "uninstall", "-y", package_name], check=True)
        click.echo("Successfully removed tool.")
    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Removal failed: {e}")
