#!/usr/bin/env python3
"""
cherenkov.py — Unified CLI for CHERENKOV E2E Suite operations.
"""

import json
import os
import sys
import argparse
import subprocess
import argcomplete

from cherenkov.execution.validate import ValidationEngine
from cherenkov.execution.eject import EjectorEngine


def print_tightening_report(results: dict):
    target_url = results.get("target_url", "N/A")
    reports = results.get("reports", [])

    print("\n" + "=" * 80)
    print("CHERENKOV VALUE ASSERTION TIGHTENING REPORT")
    print("=" * 80)
    print(f"Target Server URL: {target_url}")
    print(f"Scenarios Verified: {len(reports)}")
    print("=" * 80)

    for r in reports:
        scenario = r["scenario_id"]
        status_str = "PASSED" if r["passed"] else "FAILED"
        print(f"\nScenario: {scenario} [{status_str}]")
        print("-" * 80)
        if not r["passed"]:
            print(f'Failure Error: {r["error"]}')
            continue
        print("Captured HTTP Exchange:")
        print(f'  Sent Payload:     {r["request_body"]}')
        print(f'  Received Response: {r["response_body"]}')
        suggestions = r.get("suggestions", [])
        if suggestions:
            print("\nSuggested Assertion Tightening (Suggest-only):")
            for sug in list(set(suggestions)):
                print(f"  consider -> {sug}")
        else:
            print("\nNo value matching suggestions detected.")

    print("\n" + "=" * 80)
    print("Git status verification:")
    git_status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    )
    test_files_modified = any(
        "generated_tests" in line for line in git_status.stdout.splitlines()
    )
    if test_files_modified:
        print(
            "WARNING: Git status reports test files were modified! (Trust rule violated)"
        )
    else:
        print(
            "Git status is clean — zero test files were auto-modified by validation. Suggest-only constraint honored."
        )
    print("=" * 80 + "\n")


def print_visual_report(target_url: str, reports):
    print("\n" + "=" * 80)
    print("CHERENKOV VISUAL REGRESSION REPORT (B1 — optional Track B layer)")
    print("=" * 80)
    print(f"Target URL: {target_url}")
    print(f"Slices Verified: {len(reports)}")
    print("=" * 80)
    for r in reports:
        status_str = "OK" if r.status == "ok" else "FAILED"
        verdict_str = (
            r.verdict.upper() if hasattr(r.verdict, "upper") else str(r.verdict).upper()
        )
        print(f"\nSlice: {r.scenario_id} [{status_str}]  Verdict: {verdict_str}")
        print("-" * 80)
        if r.errors:
            for err in r.errors:
                print(f"  Error [{err.code}]: {err.detail}")
        if not r.gates:
            print("  (no gates evaluated)")
            continue
        for g in r.gates:
            pass_str = "PASS" if g.passed else "FAIL"
            print(f"  Gate {g.gate}: [{pass_str}]  diff_pixels={g.diff_pixels}")
            if g.baseline_path:
                print(f"    baseline: {g.baseline_path}")
            if g.actual_path:
                print(f"    actual:   {g.actual_path}")
    print("\n" + "=" * 80 + "\n")


def print_perf_report(target_url, reports):
    print(chr(10) + "=" * 80)
    print("CHERENKOV PERFORMANCE BASELINE REPORT (B2 - optional Track B layer)")
    print("=" * 80)
    print("Target URL:", target_url)
    print("Slices Verified:", len(reports))
    print("=" * 80)
    for r in reports:
        status_str = "OK" if r.status == "ok" else "FAILED"
        verdict_str = (
            r.verdict.upper() if hasattr(r.verdict, "upper") else str(r.verdict).upper()
        )
        print(
            chr(10) + "Slice:",
            r.scenario_id,
            "[" + status_str + "]  Verdict:",
            verdict_str,
        )
        print("-" * 80)
        if r.errors:
            for err in r.errors:
                print("  Error [" + err.code + "]:", err.detail)
        if not r.gates:
            print("  (no gates evaluated)")
            continue
        for g in r.gates:
            pass_str = "PASS" if g.passed else "FAIL"
            print("  Gate " + g.gate + ": [" + pass_str + "]")
            print(
                "    latency_ms="
                + str(g.latency_ms)
                + "  k6_available="
                + str(g.k6_available)
            )
            print(
                "    baseline: count="
                + str(g.baseline_count)
                + " mean="
                + str(g.baseline_mean_ms)
                + "ms stddev="
                + str(g.baseline_stddev_ms)
                + "ms"
            )
            if g.threshold_limit_ms:
                print(
                    "    threshold_limit_ms="
                    + str(g.threshold_limit_ms)
                    + "  anomaly_detected="
                    + str(g.anomaly_detected)
                )
    print(chr(10) + "=" * 80 + chr(10))


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CHERENKOV E2E Suite Command Line Interface"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all output (including JSONL from stderr)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommands to execute")

    validate_parser = subparsers.add_parser(
        "validate", help="Validate E2E test suite against a real server"
    )
    validate_parser.add_argument(
        "--target", "-t", default=None,
        help="The real server target base URL (default: http://localhost:8000 in --demo mode)",
    )
    validate_parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo mode: use bundled pre-generated fixtures and auto-start the target API; no Ollama required",
    )
    validate_parser.add_argument(
        "--headed", action="store_true", help="Run Playwright in headed (visible browser) mode"
    )
    validate_parser.add_argument(
        "--source",
        choices=["openapi", "graphql", "grpc", "accessibility"],
        default="openapi",
        help="Source type for ingestion",
    )
    validate_parser.add_argument(
        "--format",
        choices=["json", "text", "sarif", "html", "junit", "allure"],
        default=None,
        help="Output report format",
    )
    validate_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for Playwright tests",
    )
    validate_parser.add_argument(
        "--no-html",
        action="store_true",
        help="Disable automatic HTML report generation",
    )
    validate_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable incremental test generation cache",
    )
    validate_parser.add_argument(
        "--json-summary",
        help="Output path for a machine-readable JSON summary of the run",
    ).completer = argcomplete.completers.FilesCompleter()
    validate_parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit with code 1 if any API drift is detected",
    )
    validate_parser.add_argument(
        "--spec",
        default=None,
        help="Path to OpenAPI spec (JSON/YAML); auto-discovered if omitted",
    ).completer = argcomplete.completers.FilesCompleter()

    diff_parser = subparsers.add_parser(
        "diff", help="Compare two OpenAPI specs for breaking changes"
    )
    diff_parser.add_argument(
        "--before", required=True, help="Path to the original spec"
    ).completer = argcomplete.completers.FilesCompleter()
    diff_parser.add_argument(
        "--after", required=True, help="Path to the modified spec"
    ).completer = argcomplete.completers.FilesCompleter()
    diff_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    completion_parser = subparsers.add_parser(
        "completion", help="Generate shell completion scripts"
    )
    completion_parser.add_argument(
        "shell", choices=["bash", "zsh", "fish"], help="Target shell"
    )

    subparsers.add_parser(
        "self-test",
        help="Run a deterministic dry-run of the pipeline (mocking Ollama and the server)",
    )

    report_parser = subparsers.add_parser(
        "report", help="Generate test coverage and diff reports from run logs"
    )
    report_parser.add_argument(
        "--output", "-o", help="JSON output file path (e.g. report.json)"
    )
    report_parser.add_argument(
        "--diff", "-d", help="Path to previous report.json for diff comparison"
    )
    report_parser.add_argument(
        "--format", choices=["json", "junit", "sarif"], default="json", help="Output format for the report"
    )

    eject_parser = subparsers.add_parser(
        "eject", help="Eject generated tests to a standalone Playwright suite"
    )
    eject_parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Target output directory for the standalone suite",
    )

    visual_parser = subparsers.add_parser(
        "visual",
        help="Run optional visual-regression checks against a rendered URL (Track B layer)",
    )
    visual_parser.add_argument(
        "--target", "-t", required=True, help="Absolute URL of the page to snapshot"
    )
    visual_parser.add_argument(
        "--baseline-dir",
        default="stub/visual_baselines",
        help="Baseline directory label (default: stub/visual_baselines)",
    )

    perf_parser = subparsers.add_parser(
        "perf",
        help="Run optional performance baseline checks against an API endpoint (Track B layer)",
    )
    perf_parser.add_argument(
        "--target", "-t", required=True, help="Base URL of the API to load test"
    )
    perf_parser.add_argument(
        "--endpoint",
        default="/",
        help="Endpoint path appended to --target (default: /)",
    )
    perf_parser.add_argument(
        "--method", default="GET", help="HTTP method (default: GET)"
    )
    perf_parser.add_argument(
        "--vus", type=int, default=5, help="Virtual users (default: 5)"
    )
    perf_parser.add_argument(
        "--duration", type=int, default=5, help="Test duration in seconds (default: 5)"
    )

    # ── Epoch 5: Experience + Configuration ────────────────────────────────
    init_parser = subparsers.add_parser("init", help="Zero-config project setup (E5-1)")
    init_parser.add_argument(
        "--profile",
        "-p",
        default=None,
        choices=["laptop", "ci", "enterprise-vpc", "frontier-cloud"],
        help="Configuration profile (default: autodetect)",
    )
    init_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing cherenkov.toml"
    )

    doctor_parser = subparsers.add_parser("doctor", help="System health check (E5-3)")
    doctor_parser.add_argument(
        "--desktop", action="store_true", help="Include Track C (Desktop/Tauri) checks"
    )

    subparsers.add_parser(
        "dashboard", help="Visualise Truth Model + divergences (E5-4, defer-first)"
    )

    # ── Epoch 2: Truth Model ───────────────────────────────────────────────
    map_parser = subparsers.add_parser(
        "map", help="Build + inspect the Truth Model from configured sources (E2-6)"
    )
    map_parser.add_argument(
        "--detailed", "-d", action="store_true", help="Show full claim details"
    )

    # ── Epoch 4: Continuity ────────────────────────────────────────────────
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Continuously watch sources and rebuild Truth Model (E4-4) or run Spec Guardian",
    )
    daemon_parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60)",
    )
    daemon_parser.add_argument(
        "--max-loops",
        "-n",
        type=int,
        default=0,
        help="Max rebuild iterations (0=infinite)",
    )
    daemon_parser.add_argument(
        "--guardian",
        action="store_true",
        help="Run in Spec Guardian mode (continuous validation)",
    )
    daemon_parser.add_argument("--spec", help="Path to spec (required for guardian)")
    daemon_parser.add_argument("--target", help="Target URL (required for guardian)")
    daemon_parser.add_argument(
        "--source",
        choices=["openapi", "graphql", "grpc", "accessibility"],
        default="openapi",
        help="Source type (guardian)",
    )

    # ── Epoch 10: Explorer + Copilot (manual-QA pillar) ────────────────────
    explore_parser = subparsers.add_parser(
        "explore",
        help="Crawl a live surface and print a 'second pair of eyes' risk digest (E10)",
    )
    explore_parser.add_argument(
        "--target", "-t", required=True, help="Base URL of the app/API to crawl"
    )
    explore_parser.add_argument(
        "--path",
        "-p",
        action="append",
        dest="paths",
        help="Route to probe (repeatable); default: /",
    )
    explore_parser.add_argument(
        "--method", "-m", default="GET", help="HTTP method to probe with (default: GET)"
    )

    author_parser = subparsers.add_parser(
        "author",
        help="Turn plain-language intent into an ejectable Playwright test (E10)",
    )
    author_parser.add_argument(
        "intent",
        help='Plain-language test intent, e.g. "check guest checkout with a discount"',
    )
    author_parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Directory to write the .spec.ts test into",
    )
    author_parser.add_argument(
        "--target", "-t", default="", help="Base URL the flow runs against"
    )

    # ── Epoch 12: Governance KPI panel (C12 #127) ─────────────────────────
    governance_parser = subparsers.add_parser(
        "governance", help="E12 Governance KPI panel (escape/FP/coverage/maintenance)"
    )
    governance_parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit machine-readable JSON report",
    )
    governance_parser.add_argument(
        "--trend",
        "-t",
        metavar="METRIC",
        default=None,
        help="Show trend for a metric (health_score, escape_rate, coverage, etc.)",
    )

    # ── Token consumption monitor ─────────────────────────────────────────
    tokens_parser = subparsers.add_parser(
        "tokens", help="Token consumption monitor — usage, cost, recommendations"
    )
    tokens_sub = tokens_parser.add_subparsers(dest="tokens_command", required=True)

    tok_report = tokens_sub.add_parser(
        "report", help="Full usage report with recommendations"
    )
    tok_report.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Lookback window in days (default: 30)",
    )
    tok_report.add_argument(
        "--json", dest="json_out", action="store_true", help="Output as JSON"
    )

    tok_breakdown = tokens_sub.add_parser(
        "breakdown", help="Per-provider or per-stage breakdown"
    )
    tok_breakdown.add_argument(
        "--stage", action="store_true", help="Break down by stage instead of provider"
    )
    tok_breakdown.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Lookback window in days (default: 30)",
    )

    # ── Epoch 12: Certification gate (C11 #126) ────────────────────────────
    certify_parser = subparsers.add_parser(
        "certify", help="E12 Gold-Set + RAG-Triad model tier certification"
    )
    certify_parser.add_argument(
        "--tier",
        "-T",
        default="small",
        choices=["small", "deep", "vision"],
        help="Capability tier to certify (default: small)",
    )
    certify_parser.add_argument(
        "--rag-report",
        "-r",
        action="store_true",
        help="Show per-item RAG-Triad metrics",
    )

    # ── E13: Autonomy profile (C14 #129) & Mentor (C13 #128) ──────────────
    profile_parser = subparsers.add_parser(
        "profile",
        help="E13 Autonomy-ladder profile (assisted/augmented/agentic/predictive)",
    )
    profile_parser.add_argument(
        "action",
        nargs="?",
        default="show",
        choices=["show", "set"],
        help="Show current profile or set a new one (default: show)",
    )
    profile_parser.add_argument(
        "--level",
        "-l",
        default=None,
        choices=["assisted", "augmented", "agentic", "predictive"],
        help="Autonomy level to set",
    )

    # ── HITL terminal queue (A1 #109) ─────────────────────────────────────────
    hitl_parser = subparsers.add_parser(
        "hitl", help="Human-in-the-loop review queue (list/show/approve/reject)"
    )
    hitl_sub = hitl_parser.add_subparsers(dest="hitl_command", required=True)

    hitl_list = hitl_sub.add_parser(
        "list", help="List HITL queue items (default: pending)"
    )
    hitl_list.add_argument(
        "--status",
        "-s",
        default="pending",
        choices=["pending", "approved", "rejected", "ignored"],
        help="Filter by status (default: pending)",
    )
    hitl_list.add_argument(
        "--all",
        "-a",
        dest="list_all",
        action="store_true",
        help="Show all statuses (overrides --status)",
    )
    hitl_list.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit machine-readable hitl/v1 JSON envelope",
    )

    hitl_show = hitl_sub.add_parser("show", help="Show details of a single HITL item")
    hitl_show.add_argument("item_id", help="The HITL item ID to show")
    hitl_show.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit machine-readable hitl/v1 JSON envelope",
    )

    hitl_approve = hitl_sub.add_parser("approve", help="Approve a pending HITL item")
    hitl_approve.add_argument("item_id", help="The HITL item ID to approve")
    hitl_approve.add_argument(
        "--actor", default=None, help="Reviewer identity (default: $USER env var)"
    )
    hitl_approve.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit machine-readable hitl/v1 JSON envelope",
    )

    hitl_reject = hitl_sub.add_parser("reject", help="Reject a pending HITL item")
    hitl_reject.add_argument("item_id", help="The HITL item ID to reject")
    hitl_reject.add_argument(
        "--reason", "-r", required=True, help="Rejection reason (required)"
    )
    hitl_reject.add_argument(
        "--actor", default=None, help="Reviewer identity (default: $USER env var)"
    )
    hitl_reject.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit machine-readable hitl/v1 JSON envelope",
    )

    # ── Tier-2: classify (#150) ───────────────────────────────────────────────
    hitl_classify = hitl_sub.add_parser(
        "classify",
        help="Classify a HITL item as regression, intended, or ignore (Tier-2)",
    )
    hitl_classify.add_argument("item_id", help="The HITL item ID to classify")
    hitl_classify.add_argument(
        "--classification",
        "-c",
        required=True,
        choices=["regression", "intended", "ignore"],
        help="Classification label",
    )
    hitl_classify.add_argument(
        "--actor", default=None, help="Reviewer identity (default: $USER env var)"
    )
    hitl_classify.add_argument(
        "--detail", "-d", default="", help="Free-text detail (not used in LLM prompts)"
    )
    hitl_classify.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit machine-readable hitl/v1 JSON envelope",
    )

    # ── Tier-3: explain (#151) ────────────────────────────────────────────────
    hitl_explain = hitl_sub.add_parser(
        "explain",
        help="Get an AI explanation for why the HITL item was flagged (Tier-3)",
    )
    hitl_explain.add_argument("item_id", help="The HITL item ID to explain")
    hitl_explain.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit machine-readable hitl/v1 JSON envelope",
    )

    # ── Horizon V: Review dashboard web UI (Issues 175-176) ─────────────────
    review_parser = subparsers.add_parser(
        "review",
        help="Start the review dashboard web UI (launches FastAPI + prebuilt FE)",
    )
    review_parser.add_argument(
        "--web",
        "-w",
        action="store_true",
        default=True,
        help="Serve the prebuilt web UI (default: True)",
    )
    review_parser.add_argument(
        "--port", "-p", type=int, default=8000, help="Port to bind (default: 8000)"
    )
    review_parser.add_argument(
        "--demo",
        action="store_true",
        help="Load demo fixture data into HITL queue on startup",
    )

    # ── X4: MCP server (#133) — post-gate, treat peers as untrusted ──────────
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Expose CHERENKOV over Model Context Protocol (stdio, mcp/v1)",
    )
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_command", required=True)
    mcp_sub.add_parser(
        "serve",
        help="Start the MCP server over stdio (connect Claude Desktop, Cursor, etc.)",
    )
    pub_parser = mcp_sub.add_parser(
        "publish",
        help="Register an external MCP server with the mesh registry",
    )
    pub_parser.add_argument("--name", required=True, help="Server name")
    pub_parser.add_argument("--url", required=True, help="Server URL")
    pub_parser.add_argument(
        "--tools",
        default="[]",
        help="JSON list of tool definitions this server provides",
    )
    pub_parser.add_argument(
        "--resources",
        default="[]",
        help="JSON list of resource definitions this server provides",
    )
    pub_parser.add_argument(
        "--version", default="1.0.0", help="Server version"
    )
    pub_parser.add_argument(
        "--attestation", default="", help="Optional attestation token"
    )
    # ── Phase 13: Enterprise Tier ──────────────────────────────────────────
    enterprise_parser = subparsers.add_parser("enterprise", help="Manage enterprise features (org, audit, compliance)")
    ent_sub = enterprise_parser.add_subparsers(dest="enterprise_command", required=True)
    
    ent_org = ent_sub.add_parser("org", help="Manage multi-tenant organizations")
    ent_org.add_argument("action", choices=["create", "list"], help="Action to perform")
    ent_org.add_argument("--name", help="Organization name")
    ent_org.add_argument("--owner", help="Owner ID")

    ent_audit = ent_sub.add_parser("audit", help="Manage enterprise audit logs")
    ent_audit.add_argument("action", choices=["export"], help="Action to perform")
    ent_audit.add_argument("--format", choices=["json", "csv"], default="csv", dest="export_format", help="Export format")
    ent_audit.add_argument("--output", "-o", default="audit_export.csv", help="Output file path")

    ent_comp = ent_sub.add_parser("compliance", help="Generate compliance reports")
    ent_comp.add_argument("action", choices=["generate"], help="Action to perform")
    ent_comp.add_argument("--output", "-o", default="soc2_report.json", help="Output file path")

    playbook_parser = subparsers.add_parser(
        "playbook", help="Manage and run validation playbooks (auto-triggering skill rules)"
    )
    playbook_sub = playbook_parser.add_subparsers(dest="playbook_command", required=True)

    pb_list = playbook_sub.add_parser("list", help="List all loaded playbooks")
    pb_list.add_argument(
        "--dir", dest="search_dirs", action="append", default=[],
        help="Extra directories to scan for playbook YAML files (repeatable).",
    )
    pb_list.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON.")

    pb_show = playbook_sub.add_parser("show", help="Show full details of a named playbook")
    pb_show.add_argument("name", help="Playbook name to display")
    pb_show.add_argument("--dir", dest="search_dirs", action="append", default=[])

    pb_run = playbook_sub.add_parser(
        "run", help="Fire matching playbooks against a single live endpoint"
    )
    pb_run.add_argument("--url", required=True, help="Base URL of the API under test.")
    pb_run.add_argument("--path", dest="endpoint_path", required=True, help="Endpoint path, e.g. /health.")
    pb_run.add_argument("--method", default="GET", help="HTTP method (default: GET).")
    pb_run.add_argument(
        "--header", dest="extra_headers", action="append", default=[],
        help="KEY:VALUE request header (repeatable).",
    )
    pb_run.add_argument("--dir", dest="search_dirs", action="append", default=[])
    pb_run.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON.")

    pb_new = playbook_sub.add_parser("new", help="Scaffold a new playbook YAML file")
    pb_new.add_argument("name", help="Playbook name (becomes the file slug).")
    pb_new.add_argument(
        "--out-dir", default=".cherenkov/playbooks",
        help="Directory to write the new playbook (default: .cherenkov/playbooks).",
    )

    return parser


def main():
    parser = get_parser()
    argcomplete.autocomplete(parser)
    # Default to 'validate' when called with legacy engine args (--spec)
    if "--spec" in sys.argv[1:] and not any(
        a in sys.argv[1:]
        for a in [
            "validate",
            "self-test",
            "report",
            "eject",
            "visual",
            "perf",
            "init",
            "doctor",
            "dashboard",
            "map",
            "daemon",
            "explore",
            "author",
            "governance",
            "certify",
            "profile",
            "hitl",
            "review",
            "mcp",
            "tokens",
            "diff",
            "completion",
        ]
    ):
        sys.argv.insert(1, "validate")
    args = parser.parse_args()

    from cherenkov.core.errors import LoggerConfig

    if args.quiet:
        LoggerConfig.suppress_stderr = True

    # Setup for verbose (e.g. if we want to change standard output logic)
    # The JSONL logs always go to events.jsonl now via OrchestrationEngine
    # If not quiet, they also go to stderr.

    if args.command == "validate":
        _demo_proc = None
        if getattr(args, "demo", False):
            print("\n" + "=" * 80)
            print("[DEMO MODE] Using pre-generated tests — no Ollama or GPU required.")
            print("Run without --demo for live generation against your own API spec.")
            print("=" * 80 + "\n")
            if not args.target:
                args.target = "http://localhost:8000"
            # Auto-start the bundled target API if it is not already reachable.
            import urllib.request, urllib.error as _ue
            _target_live = False
            try:
                urllib.request.urlopen(f"{args.target}/health", timeout=2)
                _target_live = True
            except Exception:
                pass
            if not _target_live:
                import subprocess as _sp, time as _t, atexit as _atexit
                _target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target")
                _venv_uvicorn = os.path.join(_target_dir, ".venv", "bin", "uvicorn")
                _uvicorn_cmd = _venv_uvicorn if os.path.exists(_venv_uvicorn) else "uvicorn"
                print(f"  Starting bundled target API at {args.target} …")
                _demo_proc = _sp.Popen(
                    [_uvicorn_cmd, "target_api:app", "--host", "127.0.0.1", "--port", "8000"],
                    cwd=_target_dir, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                )
                _atexit.register(lambda p=_demo_proc: p.poll() is None and p.terminate())
                for _ in range(15):
                    _t.sleep(0.5)
                    try:
                        urllib.request.urlopen(f"{args.target}/health", timeout=1)
                        print("  Target API ready.\n")
                        break
                    except Exception:
                        pass
        elif not args.target:
            parser.error("cherenkov validate: --target is required (or use --demo to run against the bundled target API)")

        if getattr(args, "no_cache", False):
            from cherenkov.cache.endpoint_cache import EndpointCache

            EndpointCache().clear()

        if hasattr(args, "spec") and args.spec:
            # We don't automatically fail the validate on breaking change here,
            # we just run the tests. Spec differs are explicit.
            pass

        if getattr(args, "source", "openapi") == "graphql":
            from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
            from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
            from cherenkov.stages.generate import GenerateStage

            source = GraphQLSourceAdapter(args.spec)
            planner = GraphQLScenarioPlanner()
            scenarios = planner.plan(source)
            for sc in scenarios:
                GenerateStage("cli_validate").run(scenario=sc, source_type="graphql")
        elif getattr(args, "source", "openapi") == "grpc":
            from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
            from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
            from cherenkov.stages.generate import GenerateStage

            source = gRPCSourceAdapter(args.spec)
            planner = gRPCScenarioPlanner()
            scenarios = planner.plan(source)
            for sc in scenarios:
                GenerateStage("cli_validate").run(scenario=sc, source_type="grpc")
        elif getattr(args, "source", "openapi") == "accessibility":
            from cherenkov.sources.accessibility.adapter import (
                AccessibilitySourceAdapter,
            )
            from cherenkov.stages.plan_accessibility import AccessibilityScenarioPlanner
            from cherenkov.stages.generate import GenerateStage

            source = AccessibilitySourceAdapter(args.spec)
            planner = AccessibilityScenarioPlanner()
            scenarios = planner.plan(source)
            for sc in scenarios:
                GenerateStage("cli_validate").run(
                    scenario=sc, source_type="accessibility"
                )

        engine = ValidationEngine("cli_validate")
        results = engine.validate_suite(
            args.target,
            workers=getattr(args, "workers", 1),
            headed=getattr(args, "headed", False),
            spec_path=getattr(args, "spec", None),
        )

        if getattr(args, "format", None) == "sarif":
            from cherenkov.execution.emitters.sarif import SARIFEmitter

            os.makedirs(".cherenkov", exist_ok=True)
            emitter = SARIFEmitter()
            from cherenkov.core.contracts import DivergenceReport

            # Mapping reports dict to DivergenceReport finding format dynamically.
            report_obj = DivergenceReport(findings=[])
            for r in results.get("reports", []):
                from cherenkov.core.contracts import DivergenceFinding

                if not r.get("passed", False):
                    report_obj.findings.append(
                        DivergenceFinding(
                            violation_type="conformance-drift",
                            endpoint=r.get("scenario_id", "unknown"),
                            http_method="ANY",
                            expected="Valid response",
                            actual=r.get("error", ""),
                            summary="Response drift detected",
                            description=f"Error: {r.get('error', '')}",
                            severity="high",
                            remediation="Update API or spec",
                        )
                    )
            sarif_data = emitter.emit(report_obj, args.spec or "openapi.yaml")
            out_path = (
                args.output
                if getattr(args, "output", "").endswith(".sarif")
                else getattr(args, "output", ".cherenkov/report") + ".sarif"
            )
            with open(out_path, "w") as f:
                json.dump(sarif_data, f, indent=2)
            print(f"SARIF report written to {out_path}")
            sys.exit(
                0
                if results.get("status") != "empty"
                and all(r.get("passed", False) for r in results.get("reports", []))
                else 1
            )

        if getattr(args, "format", None) == "allure":
            from cherenkov.execution.emitters.allure import AllureEmitter
            from types import SimpleNamespace

            emitter = AllureEmitter()
            from cherenkov.core.contracts import DivergenceFinding

            report_obj = SimpleNamespace(findings=[])
            total_tests = 0
            for r in results.get("reports", []):
                total_tests += 1
                if not r.get("passed", False):
                    report_obj.findings.append(
                        DivergenceFinding(
                            violation_type="conformance-drift",
                            endpoint=r.get("scenario_id", "unknown"),
                            http_method="ANY",
                            expected="Valid response",
                            actual=r.get("error", ""),
                            summary="Response drift detected",
                            description=f"Error: {r.get('error', '')}",
                            severity="high",
                            remediation="Update API or spec",
                        )
                    )
            setattr(report_obj, "_total_tests", total_tests)
            allure_data = emitter.emit(report_obj, args.spec or "openapi.yaml")
            
            out_dir = getattr(args, "output", ".cherenkov/allure-results")
            if out_dir.endswith(".json") or out_dir.endswith(".xml"):
                out_dir = ".cherenkov/allure-results"
            os.makedirs(out_dir, exist_ok=True)
            
            for item in allure_data:
                file_path = os.path.join(out_dir, f"{item['uuid']}-result.json")
                with open(file_path, "w") as f:
                    json.dump(item, f, indent=2)
            
            print(f"Allure results written to {out_dir}")
            sys.exit(
                0
                if results.get("status") != "empty"
                and all(r.get("passed", False) for r in results.get("reports", []))
                else 1
            )

        if results.get("status") == "empty":
            msg = results.get("message", "Unknown error")
            if getattr(args, "format", None) == "json":
                print(json.dumps({"passed": False, "divergences": [msg], "summary": msg, "checks": []}))
            else:
                print(f"\nError: {msg}\n")
            sys.exit(1)

        reports = results.get("reports", [])
        passed_count = sum(1 for r in reports if r.get("passed", False))
        total = len(reports)
        failed = [r for r in reports if not r.get("passed", False)]

        if getattr(args, "format", None) == "json":
            checks = [
                {"passed": r.get("passed", False), "scenario_id": r.get("scenario_id", "?"),
                 "error": r.get("error", "") if not r.get("passed", False) else ""}
                for r in reports
            ]
            divergences = [r.get("error", "failed") for r in failed]
            print(json.dumps({
                "passed": passed_count == total,
                "divergences": divergences,
                "summary": f"{passed_count}/{total} scenarios passed",
                "checks": checks,
            }))
            sys.exit(0 if passed_count == total else 1)

        # Human-readable summary
        width = 80
        print("\n" + "=" * width)
        print("CHERENKOV CONFORMANCE REPORT")
        print("=" * width)
        print(f"Target: {args.target}")
        print(f"Scenarios: {total}  |  Passed: {passed_count}  |  Failed: {len(failed)}")
        print("=" * width)
        for r in reports:
            status = "PASS" if r.get("passed") else "FAIL"
            sid = r.get("scenario_id", "?")
            print(f"  [{status}]  {sid}")
            if not r.get("passed") and r.get("error"):
                # Show first line of error only
                first_line = str(r["error"]).split("\n")[0][:120]
                print(f"         {first_line}")
        print("=" * width)
        if failed:
            print(f"\n  {len(failed)} conformance drift(s) detected\n")
        else:
            print("\n  All scenarios passed — no drift detected\n")

        print_tightening_report(results)

        if not getattr(args, "no_html", False):
            from cherenkov.execution.emitters.html_report import HTMLReportEmitter
            from pathlib import Path

            html_path = Path(".cherenkov") / "report.html"
            HTMLReportEmitter().emit(results, html_path)
            print(f"HTML report generated: {html_path}")

        from cherenkov.cache.endpoint_cache import EndpointCache

        stats = EndpointCache().stats()
        print(f"Cache Stats: {stats}")

        if getattr(args, "fail_on_drift", False) and failed:
            sys.exit(1)
        sys.exit(0)

    elif args.command == "diff":
        from cherenkov.diff.spec_differ import SpecDiffer, print_diff_report

        differ = SpecDiffer()
        report = differ.diff(args.before, args.after)
        print_diff_report(report, fmt=args.format)
        sys.exit(1 if report.has_breaking_changes else 0)

    elif args.command == "completion":
        # Generate the argcomplete activation script for the specified shell
        if args.shell == "bash":
            print('eval "$(register-python-argcomplete cherenkov)"')
        elif args.shell == "zsh":
            print('eval "$(register-python-argcomplete cherenkov)"')
        elif args.shell == "fish":
            print("register-python-argcomplete --shell fish cherenkov | source")
        sys.exit(0)

    elif args.command == "self-test":
        from cherenkov.stages.self_test_cmd import run_self_test

        sys.exit(run_self_test())

    elif args.command == "report":
        from cherenkov.stages.report_cmd import run_report

        sys.exit(run_report(output=args.output, diff=args.diff))

    elif args.command == "eject":
        ejector = EjectorEngine("cli_eject")
        success = ejector.eject_suite(args.output)
        if success:
            print(f"\nCHERENKOV E2E suite ejected successfully to: {args.output}")
            print("All CHERENKOV metadata and hooks stripped successfully.")
            print("Ejected folder is 100% standard and runs standalone.\n")
            sys.exit(0)
        else:
            print("\nError: Standalone test suite ejection failed.\n")
            sys.exit(1)

    elif args.command == "visual":
        from cherenkov.core.orchestrator import OrchestrationEngine
        from cherenkov.core.contracts import VisualSlice

        slices = [VisualSlice(name="cli_default", url=args.target)]
        engine = OrchestrationEngine(run_id="cli_visual")
        reports = engine.run_visual_stage(slices, baseline_dir=args.baseline_dir)
        print_visual_report(args.target, reports)
        all_ok = all(r.status == "ok" for r in reports) if reports else False
        sys.exit(0 if all_ok else 1)

    elif args.command == "perf":
        from cherenkov.core.orchestrator import OrchestrationEngine
        from cherenkov.core.contracts import PerfSlice

        slices = [
            PerfSlice(
                name="cli_default",
                target_url=args.target,
                endpoint=args.endpoint,
                method=args.method,
                vus=args.vus,
                duration_sec=args.duration,
            )
        ]
        engine = OrchestrationEngine(run_id="cli_perf")
        reports = engine.run_perf_stage(slices)
        print_perf_report(args.target, reports)
        any_failed = any(r.status != "ok" for r in reports)
        sys.exit(1 if any_failed else 0)

    # ── Epoch 5 subcommands ────────────────────────────────────────────────
    elif args.command == "init":
        from cherenkov.stages.init_cmd import run_init

        sys.exit(run_init(profile=args.profile, force=args.force))

    elif args.command == "doctor":
        from cherenkov.stages.doctor_cmd import run_doctor

        sys.exit(run_doctor(desktop=getattr(args, "desktop", False)))

    elif args.command == "dashboard":
        from cherenkov.dashboard.render import run_dashboard

        sys.exit(run_dashboard())

    # ── Epoch 2 subcommands ────────────────────────────────────────────────
    elif args.command == "map":
        from cherenkov.stages.map_cmd import run_map

        sys.exit(run_map(detailed=args.detailed))

    elif args.command == "daemon":
        from cherenkov.stages.daemon_cmd import run_daemon, run_guardian_daemon

        if getattr(args, "guardian", False):
            if not args.spec or not args.target:
                print("Error: --spec and --target are required for --guardian mode")
                sys.exit(1)
            sys.exit(
                run_guardian_daemon(
                    target_url=args.target,
                    spec_path=args.spec,
                    source_type=args.source,
                    interval_seconds=args.interval,
                )
            )
        else:
            sys.exit(
                run_daemon(interval_seconds=args.interval, max_loops=args.max_loops)
            )

    # ── Epoch 10 subcommands ───────────────────────────────────────────────
    elif args.command == "explore":
        from cherenkov.stages.copilot_cmd import run_explore

        sys.exit(run_explore(args.target, paths=args.paths, method=args.method))

    elif args.command == "author":
        from cherenkov.stages.copilot_cmd import run_author

        sys.exit(run_author(args.intent, output=args.output, target=args.target))

    # ── Epoch 12 subcommands ────────────────────────────────────────────────
    elif args.command == "tokens":
        from cherenkov.stages.tokens_cmd import run_tokens_report, run_tokens_breakdown

        if args.tokens_command == "report":
            run_tokens_report(days=args.days, as_json=args.json_out)
        elif args.tokens_command == "breakdown":
            run_tokens_breakdown(by_stage=args.stage, days=args.days)

    elif args.command == "governance":
        from cherenkov.stages.governance_cmd import run_governance

        sys.exit(run_governance(json_out=args.json_out, trend=args.trend))

    elif args.command == "certify":
        from cherenkov.stages.certify_cmd import run_certify

        sys.exit(run_certify(tier=args.tier, rag_report=args.rag_report))

    # ── E13 subcommands ────────────────────────────────────────────────────
    elif args.command == "profile":
        from cherenkov.stages.profile_cmd import run_profile

        sys.exit(run_profile(action=args.action, level=args.level))

    # ── HITL terminal queue (A1 #109) ─────────────────────────────────────────
    elif args.command == "hitl":
        from cherenkov.hitl.cmd import run_list, run_show, run_approve, run_reject

        if args.hitl_command == "list":
            status_filter = None if getattr(args, "list_all", False) else args.status
            sys.exit(run_list(status=status_filter, json_out=args.json_out))
        elif args.hitl_command == "show":
            sys.exit(run_show(item_id=args.item_id, json_out=args.json_out))
        elif args.hitl_command == "approve":
            sys.exit(
                run_approve(
                    item_id=args.item_id, actor=args.actor, json_out=args.json_out
                )
            )
        elif args.hitl_command == "reject":
            sys.exit(
                run_reject(
                    item_id=args.item_id,
                    reason=args.reason,
                    actor=args.actor,
                    json_out=args.json_out,
                )
            )
        elif args.hitl_command == "classify":
            from cherenkov.hitl.cmd import run_classify

            sys.exit(
                run_classify(
                    item_id=args.item_id,
                    classification=args.classification,
                    actor=args.actor,
                    detail=args.detail,
                    json_out=args.json_out,
                )
            )
        elif args.hitl_command == "explain":
            from cherenkov.hitl.cmd import run_explain

            sys.exit(run_explain(item_id=args.item_id, json_out=args.json_out))

    # ── Horizon V: review dashboard web UI (Issues 175-176) ─────────────────
    elif args.command == "review":
        if getattr(args, "demo", False) or os.environ.get("DEMO_MODE") == "1":
            from cherenkov.execution.demo_mode import generate_demo_findings

            print("Loading demo findings into HITL queue...")
            generate_demo_findings()

        import uvicorn
        from cherenkov.web.api import app

        print(f"\nCHERENKOV review dashboard starting on http://0.0.0.0:{args.port}")
        print("Hit Ctrl+C to stop.\n")
        uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")

    # ── X4: MCP server (issue #133) ─────────────────────────────────────────
    elif args.command == "mcp":
        from cherenkov.mcp.server import run_mcp_server

        if args.mcp_command == "serve":
            run_mcp_server()
            sys.exit(0)
        elif args.mcp_command == "publish":
            from cherenkov.mcp.mesh_router import get_registry

            registry = get_registry()
            tools = json.loads(args.tools)
            resources = json.loads(args.resources)
            reg_id = registry.register_server(
                name=args.name,
                url=args.url,
                tools=tools,
                resources=resources,
                version=args.version,
                attestation=args.attestation,
            )
            print(json.dumps({"status": "ok", "registration_id": reg_id}))
            sys.exit(0)

    elif args.command == "playbook":
        from cherenkov.cli.commands.playbook_cmd import list_cmd, show_cmd, run_cmd, new_cmd

        sub = args.playbook_command
        if sub == "list":
            list_cmd.callback(search_dirs=tuple(args.search_dirs), as_json=args.as_json)
        elif sub == "show":
            show_cmd.callback(name=args.name, search_dirs=tuple(args.search_dirs))
        elif sub == "run":
            run_cmd.callback(
                url=args.url,
                endpoint_path=args.endpoint_path,
                method=args.method,
                extra_headers=tuple(args.extra_headers),
                search_dirs=tuple(args.search_dirs),
                as_json=args.as_json,
            )
        elif sub == "new":
            new_cmd.callback(name=args.name, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
