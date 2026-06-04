#!/usr/bin/env python3
"""
cherenkov.py — Unified CLI for CHERENKOV E2E Suite operations.
Authority: v3.1 + delta. Track A surface + optional B1 visual capability.
"""
import sys
import argparse
import subprocess

from cherenkov.execution.validate import ValidationEngine
from cherenkov.execution.eject import EjectorEngine

def print_tightening_report(results: dict):
    target_url = results.get('target_url', 'N/A')
    reports = results.get('reports', [])

    print('\n' + '=' * 80)
    print('CHERENKOV VALUE ASSERTION TIGHTENING REPORT')
    print('=' * 80)
    print(f'Target Server URL: {target_url}')
    print(f'Scenarios Verified: {len(reports)}')
    print('=' * 80)

    for r in reports:
        scenario = r['scenario_id']
        status_str = 'PASSED' if r['passed'] else 'FAILED'
        print(f'\nScenario: {scenario} [{status_str}]')
        print('-' * 80)
        if not r['passed']:
            print(f'Failure Error: {r["error"]}')
            continue
        print('Captured HTTP Exchange:')
        print(f'  Sent Payload:     {r["request_body"]}')
        print(f'  Received Response: {r["response_body"]}')
        suggestions = r.get('suggestions', [])
        if suggestions:
            print('\nSuggested Assertion Tightening (Suggest-only):')
            for sug in list(set(suggestions)):
                print(f'  consider -> {sug}')
        else:
            print('\nNo value matching suggestions detected.')

    print('\n' + '=' * 80)
    print('Git status verification:')
    git_status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    test_files_modified = any('generated_tests' in line for line in git_status.stdout.splitlines())
    if test_files_modified:
        print('WARNING: Git status reports test files were modified! (Trust rule violated)')
    else:
        print('Git status is clean — zero test files were auto-modified by validation. Suggest-only constraint honored.')
    print('=' * 80 + '\n')


def print_visual_report(target_url: str, reports):
    print('\n' + '=' * 80)
    print('CHERENKOV VISUAL REGRESSION REPORT (B1 — optional Track B layer)')
    print('=' * 80)
    print(f'Target URL: {target_url}')
    print(f'Slices Verified: {len(reports)}')
    print('=' * 80)
    for r in reports:
        status_str = 'OK' if r.status == 'ok' else 'FAILED'
        verdict_str = r.verdict.upper() if hasattr(r.verdict, 'upper') else str(r.verdict).upper()
        print(f'\nSlice: {r.scenario_id} [{status_str}]  Verdict: {verdict_str}')
        print('-' * 80)
        if r.errors:
            for err in r.errors:
                print(f'  Error [{err.code}]: {err.detail}')
        if not r.gates:
            print('  (no gates evaluated)')
            continue
        for g in r.gates:
            pass_str = 'PASS' if g.passed else 'FAIL'
            print(f'  Gate {g.gate}: [{pass_str}]  diff_pixels={g.diff_pixels}')
            if g.baseline_path:
                print(f'    baseline: {g.baseline_path}')
            if g.actual_path:
                print(f'    actual:   {g.actual_path}')
    print('\n' + '=' * 80 + '\n')




def print_perf_report(target_url, reports):
    print(chr(10) + "=" * 80)
    print("CHERENKOV PERFORMANCE BASELINE REPORT (B2 - optional Track B layer)")
    print("=" * 80)
    print("Target URL:", target_url)
    print("Slices Verified:", len(reports))
    print("=" * 80)
    for r in reports:
        status_str = "OK" if r.status == "ok" else "FAILED"
        verdict_str = r.verdict.upper() if hasattr(r.verdict, "upper") else str(r.verdict).upper()
        print(chr(10) + "Slice:", r.scenario_id, "[" + status_str + "]  Verdict:", verdict_str)
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
            print("    latency_ms=" + str(g.latency_ms) + "  k6_available=" + str(g.k6_available))
            print("    baseline: count=" + str(g.baseline_count) + " mean=" + str(g.baseline_mean_ms) + "ms stddev=" + str(g.baseline_stddev_ms) + "ms")
            if g.threshold_limit_ms:
                print("    threshold_limit_ms=" + str(g.threshold_limit_ms) + "  anomaly_detected=" + str(g.anomaly_detected))
    print(chr(10) + "=" * 80 + chr(10))

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='CHERENKOV E2E Suite Command Line Interface')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress all output (including JSONL from stderr)')
    subparsers = parser.add_subparsers(dest='command', required=True, help='Subcommands to execute')

    validate_parser = subparsers.add_parser('validate', help='Validate E2E test suite against a real server')
    validate_parser.add_argument('--target', '-t', required=True, help='The real server target base URL')

    self_test_parser = subparsers.add_parser('self-test', help='Run a deterministic dry-run of the pipeline (mocking Ollama and the server)')


    report_parser = subparsers.add_parser('report', help='Generate test coverage and diff reports from run logs')
    report_parser.add_argument('--output', '-o', help='JSON output file path (e.g. report.json)')
    report_parser.add_argument('--diff', '-d', help='Path to previous report.json for diff comparison')

    eject_parser = subparsers.add_parser("eject", help='Eject generated tests to a standalone Playwright suite')
    eject_parser.add_argument('--output', '-o', required=True, help='Target output directory for the standalone suite')

    visual_parser = subparsers.add_parser('visual', help='Run optional visual-regression checks against a rendered URL (Track B layer)')
    visual_parser.add_argument('--target', '-t', required=True, help='Absolute URL of the page to snapshot')
    visual_parser.add_argument('--baseline-dir', default='stub/visual_baselines', help='Baseline directory label (default: stub/visual_baselines)')

    perf_parser = subparsers.add_parser("perf", help="Run optional performance baseline checks against an API endpoint (Track B layer)")
    perf_parser.add_argument("--target", "-t", required=True, help="Base URL of the API to load test")
    perf_parser.add_argument("--endpoint", default="/", help="Endpoint path appended to --target (default: /)")
    perf_parser.add_argument("--method", default="GET", help="HTTP method (default: GET)")
    perf_parser.add_argument("--vus", type=int, default=5, help="Virtual users (default: 5)")
    perf_parser.add_argument("--duration", type=int, default=5, help="Test duration in seconds (default: 5)")

    # ── Epoch 5: Experience + Configuration ────────────────────────────────
    init_parser = subparsers.add_parser('init', help='Zero-config project setup (E5-1)')
    init_parser.add_argument('--profile', '-p', default=None,
                            choices=['laptop', 'ci', 'enterprise-vpc', 'frontier-cloud'],
                            help='Configuration profile (default: autodetect)')
    init_parser.add_argument('--force', '-f', action='store_true',
                            help='Overwrite existing cherenkov.toml')

    doctor_parser = subparsers.add_parser('doctor', help='System health check (E5-3)')

    dashboard_parser = subparsers.add_parser('dashboard', help='Visualise Truth Model + divergences (E5-4, defer-first)')

    # ── Epoch 2: Truth Model ───────────────────────────────────────────────
    map_parser = subparsers.add_parser('map', help='Build + inspect the Truth Model from configured sources (E2-6)')
    map_parser.add_argument('--detailed', '-d', action='store_true', help='Show full claim details')

    # ── Epoch 4: Continuity ────────────────────────────────────────────────
    daemon_parser = subparsers.add_parser('daemon', help='Continuously watch sources and rebuild Truth Model (E4-4)')
    daemon_parser.add_argument('--interval', '-i', type=int, default=60, help='Poll interval in seconds (default: 60)')
    daemon_parser.add_argument('--max-loops', '-n', type=int, default=0, help='Max rebuild iterations (0=infinite)')

    # ── Epoch 10: Explorer + Copilot (manual-QA pillar) ────────────────────
    explore_parser = subparsers.add_parser('explore', help="Crawl a live surface and print a 'second pair of eyes' risk digest (E10)")
    explore_parser.add_argument('--target', '-t', required=True, help='Base URL of the app/API to crawl')
    explore_parser.add_argument('--path', '-p', action='append', dest='paths', help='Route to probe (repeatable); default: /')
    explore_parser.add_argument('--method', '-m', default='GET', help='HTTP method to probe with (default: GET)')

    author_parser = subparsers.add_parser('author', help='Turn plain-language intent into an ejectable Playwright test (E10)')
    author_parser.add_argument('intent', help='Plain-language test intent, e.g. "check guest checkout with a discount"')
    author_parser.add_argument('--output', '-o', required=True, help='Directory to write the .spec.ts test into')
    author_parser.add_argument('--target', '-t', default='', help='Base URL the flow runs against')

    # ── Epoch 12: Governance KPI panel (C12 #127) ─────────────────────────
    governance_parser = subparsers.add_parser('governance', help='E12 Governance KPI panel (escape/FP/coverage/maintenance)')
    governance_parser.add_argument('--json', dest='json_out', action='store_true',
                                   help='Emit machine-readable JSON report')
    governance_parser.add_argument('--trend', '-t', metavar='METRIC', default=None,
                                   help='Show trend for a metric (health_score, escape_rate, coverage, etc.)')

    # ── Epoch 12: Certification gate (C11 #126) ────────────────────────────
    certify_parser = subparsers.add_parser('certify', help='E12 Gold-Set + RAG-Triad model tier certification')
    certify_parser.add_argument('--tier', '-T', default='small', choices=['small', 'deep', 'vision'],
                                help='Capability tier to certify (default: small)')
    certify_parser.add_argument('--rag-report', '-r', action='store_true',
                                help='Show per-item RAG-Triad metrics')

    # ── E13: Autonomy profile (C14 #129) & Mentor (C13 #128) ──────────────
    profile_parser = subparsers.add_parser('profile', help='E13 Autonomy-ladder profile (assisted/augmented/agentic/predictive)')
    profile_parser.add_argument('action', nargs='?', default='show',
                                choices=['show', 'set'],
                                help='Show current profile or set a new one (default: show)')
    profile_parser.add_argument('--level', '-l', default=None,
                                choices=['assisted', 'augmented', 'agentic', 'predictive'],
                                help='Autonomy level to set')

    # ── HITL terminal queue (A1 #109) ─────────────────────────────────────────
    hitl_parser = subparsers.add_parser('hitl', help='Human-in-the-loop review queue (list/show/approve/reject)')
    hitl_sub = hitl_parser.add_subparsers(dest='hitl_command', required=True)

    hitl_list = hitl_sub.add_parser('list', help='List HITL queue items (default: pending)')
    hitl_list.add_argument('--status', '-s', default='pending',
                           choices=['pending', 'approved', 'rejected', 'ignored'],
                           help='Filter by status (default: pending)')
    hitl_list.add_argument('--all', '-a', dest='list_all', action='store_true',
                           help='Show all statuses (overrides --status)')
    hitl_list.add_argument('--json', dest='json_out', action='store_true',
                           help='Emit machine-readable hitl/v1 JSON envelope')

    hitl_show = hitl_sub.add_parser('show', help='Show details of a single HITL item')
    hitl_show.add_argument('item_id', help='The HITL item ID to show')
    hitl_show.add_argument('--json', dest='json_out', action='store_true',
                           help='Emit machine-readable hitl/v1 JSON envelope')

    hitl_approve = hitl_sub.add_parser('approve', help='Approve a pending HITL item')
    hitl_approve.add_argument('item_id', help='The HITL item ID to approve')
    hitl_approve.add_argument('--actor', default=None,
                              help='Reviewer identity (default: $USER env var)')
    hitl_approve.add_argument('--json', dest='json_out', action='store_true',
                              help='Emit machine-readable hitl/v1 JSON envelope')

    hitl_reject = hitl_sub.add_parser('reject', help='Reject a pending HITL item')
    hitl_reject.add_argument('item_id', help='The HITL item ID to reject')
    hitl_reject.add_argument('--reason', '-r', required=True,
                             help='Rejection reason (required)')
    hitl_reject.add_argument('--actor', default=None,
                             help='Reviewer identity (default: $USER env var)')
    hitl_reject.add_argument('--json', dest='json_out', action='store_true',
                             help='Emit machine-readable hitl/v1 JSON envelope')

    # ── Tier-2: classify (#150) ───────────────────────────────────────────────
    hitl_classify = hitl_sub.add_parser('classify', help='Classify a HITL item as regression, intended, or ignore (Tier-2)')
    hitl_classify.add_argument('item_id', help='The HITL item ID to classify')
    hitl_classify.add_argument('--classification', '-c', required=True,
                               choices=['regression', 'intended', 'ignore'],
                               help='Classification label')
    hitl_classify.add_argument('--actor', default=None,
                               help='Reviewer identity (default: $USER env var)')
    hitl_classify.add_argument('--detail', '-d', default='',
                               help='Free-text detail (not used in LLM prompts)')
    hitl_classify.add_argument('--json', dest='json_out', action='store_true',
                               help='Emit machine-readable hitl/v1 JSON envelope')

    # ── Tier-3: explain (#151) ────────────────────────────────────────────────
    hitl_explain = hitl_sub.add_parser('explain', help='Get an AI explanation for why the HITL item was flagged (Tier-3)')
    hitl_explain.add_argument('item_id', help='The HITL item ID to explain')
    hitl_explain.add_argument('--json', dest='json_out', action='store_true',
                              help='Emit machine-readable hitl/v1 JSON envelope')

    # ── Horizon V: Review dashboard web UI (Issues 175-176) ─────────────────
    review_parser = subparsers.add_parser('review', help='Start the review dashboard web UI (launches FastAPI + prebuilt FE)')
    review_parser.add_argument('--web', '-w', action='store_true', default=True,
                               help='Serve the prebuilt web UI (default: True)')
    review_parser.add_argument('--port', '-p', type=int, default=8000,
                               help='Port to bind (default: 8000)')

    # ── X4: MCP server (#133) — post-gate, treat peers as untrusted ──────────
    mcp_parser = subparsers.add_parser(
        'mcp',
        help='Expose CHERENKOV over Model Context Protocol (stdio, mcp/v1)',
    )
    mcp_sub = mcp_parser.add_subparsers(dest='mcp_command', required=True)
    mcp_sub.add_parser(
        'serve',
        help='Start the MCP server over stdio (connect Claude Desktop, Cursor, etc.)',
    )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    from cherenkov.core.errors import LoggerConfig
    if args.quiet:
        LoggerConfig.suppress_stderr = True
        
    # Setup for verbose (e.g. if we want to change standard output logic)
    # The JSONL logs always go to events.jsonl now via OrchestrationEngine
    # If not quiet, they also go to stderr.

    if args.command == 'validate':
        engine = ValidationEngine('cli_validate')
        results = engine.validate_suite(args.target)
        if results.get('status') == 'empty':
            print(f'\nError: {results.get("message")}\n')
            sys.exit(1)
        print_tightening_report(results)
        sys.exit(0)

    elif args.command == 'self-test':
        from cherenkov.stages.self_test_cmd import run_self_test
        sys.exit(run_self_test())

    elif args.command == 'report':
        from cherenkov.stages.report_cmd import run_report
        sys.exit(run_report(output=args.output, diff=args.diff))

    elif args.command == 'eject':
        ejector = EjectorEngine('cli_eject')
        success = ejector.eject_suite(args.output)
        if success:
            print(f'\nCHERENKOV E2E suite ejected successfully to: {args.output}')
            print('All CHERENKOV metadata and hooks stripped successfully.')
            print('Ejected folder is 100% standard and runs standalone.\n')
            sys.exit(0)
        else:
            print('\nError: Standalone test suite ejection failed.\n')
            sys.exit(1)

    elif args.command == 'visual':
        from cherenkov.core.orchestrator import OrchestrationEngine
        from cherenkov.core.contracts import VisualSlice
        slices = [VisualSlice(name='cli_default', url=args.target)]
        engine = OrchestrationEngine(run_id='cli_visual')
        reports = engine.run_visual_stage(slices, baseline_dir=args.baseline_dir)
        print_visual_report(args.target, reports)
        all_ok = all(r.status == 'ok' for r in reports) if reports else False
        sys.exit(0 if all_ok else 1)


    elif args.command == "perf":
        from cherenkov.core.orchestrator import OrchestrationEngine
        from cherenkov.core.contracts import PerfSlice
        slices = [PerfSlice(name="cli_default", target_url=args.target,
                            endpoint=args.endpoint, method=args.method,
                            vus=args.vus, duration_sec=args.duration)]
        engine = OrchestrationEngine(run_id="cli_perf")
        reports = engine.run_perf_stage(slices)
        print_perf_report(args.target, reports)
        any_failed = any(r.status != "ok" for r in reports)
        sys.exit(1 if any_failed else 0)

    # ── Epoch 5 subcommands ────────────────────────────────────────────────
    elif args.command == 'init':
        from cherenkov.stages.init_cmd import run_init
        sys.exit(run_init(profile=args.profile, force=args.force))

    elif args.command == 'doctor':
        from cherenkov.stages.doctor_cmd import run_doctor
        sys.exit(run_doctor())

    elif args.command == 'dashboard':
        from cherenkov.dashboard.render import run_dashboard
        sys.exit(run_dashboard())

    # ── Epoch 2 subcommands ────────────────────────────────────────────────
    elif args.command == 'map':
        from cherenkov.stages.map_cmd import run_map
        sys.exit(run_map(detailed=args.detailed))

    elif args.command == 'daemon':
        from cherenkov.stages.daemon_cmd import run_daemon
        sys.exit(run_daemon(interval_seconds=args.interval, max_loops=args.max_loops))

    # ── Epoch 10 subcommands ───────────────────────────────────────────────
    elif args.command == 'explore':
        from cherenkov.stages.copilot_cmd import run_explore
        sys.exit(run_explore(args.target, paths=args.paths, method=args.method))

    elif args.command == 'author':
        from cherenkov.stages.copilot_cmd import run_author
        sys.exit(run_author(args.intent, output=args.output, target=args.target))

    # ── Epoch 12 subcommands ────────────────────────────────────────────────
    elif args.command == 'governance':
        from cherenkov.stages.governance_cmd import run_governance
        sys.exit(run_governance(json_out=args.json_out, trend=args.trend))

    elif args.command == 'certify':
        from cherenkov.stages.certify_cmd import run_certify
        sys.exit(run_certify(tier=args.tier, rag_report=args.rag_report))

    # ── E13 subcommands ────────────────────────────────────────────────────
    elif args.command == 'profile':
        from cherenkov.stages.profile_cmd import run_profile
        sys.exit(run_profile(action=args.action, level=args.level))

    # ── HITL terminal queue (A1 #109) ─────────────────────────────────────────
    elif args.command == 'hitl':
        from cherenkov.hitl.cmd import run_list, run_show, run_approve, run_reject
        if args.hitl_command == 'list':
            status_filter = None if getattr(args, 'list_all', False) else args.status
            sys.exit(run_list(status=status_filter, json_out=args.json_out))
        elif args.hitl_command == 'show':
            sys.exit(run_show(item_id=args.item_id, json_out=args.json_out))
        elif args.hitl_command == 'approve':
            sys.exit(run_approve(item_id=args.item_id, actor=args.actor, json_out=args.json_out))
        elif args.hitl_command == 'reject':
            sys.exit(run_reject(item_id=args.item_id, reason=args.reason,
                                actor=args.actor, json_out=args.json_out))
        elif args.hitl_command == 'classify':
            from cherenkov.hitl.cmd import run_classify
            sys.exit(run_classify(item_id=args.item_id, classification=args.classification,
                                  actor=args.actor, detail=args.detail,
                                  json_out=args.json_out))
        elif args.hitl_command == 'explain':
            from cherenkov.hitl.cmd import run_explain
            sys.exit(run_explain(item_id=args.item_id, json_out=args.json_out))


    # ── Horizon V: review dashboard web UI (Issues 175-176) ─────────────────
    elif args.command == 'review':
        import uvicorn
        from cherenkov.web.api import app
        print(f"\nCHERENKOV review dashboard starting on http://127.0.0.1:{args.port}")
        print("Hit Ctrl+C to stop.\n")
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")

    # ── X4: MCP server (issue #133) ─────────────────────────────────────────
    elif args.command == 'mcp':
        from cherenkov.mcp.server import run_mcp_server
        if args.mcp_command == 'serve':
            run_mcp_server()
            sys.exit(0)


if __name__ == "__main__":
    main()
