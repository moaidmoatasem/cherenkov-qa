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


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='CHERENKOV E2E Suite Command Line Interface')
    subparsers = parser.add_subparsers(dest='command', required=True, help='Subcommands to execute')

    validate_parser = subparsers.add_parser('validate', help='Validate E2E test suite against a real server')
    validate_parser.add_argument('--target', '-t', required=True, help='The real server target base URL')

    eject_parser = subparsers.add_parser("eject", help='Eject generated tests to a standalone Playwright suite')
    eject_parser.add_argument('--output', '-o', required=True, help='Target output directory for the standalone suite')

    visual_parser = subparsers.add_parser('visual', help='Run optional visual-regression checks against a rendered URL (Track B layer)')
    visual_parser.add_argument('--target', '-t', required=True, help='Absolute URL of the page to snapshot')
    visual_parser.add_argument('--baseline-dir', default='stub/visual_baselines', help='Baseline directory label (default: stub/visual_baselines)')

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if args.command == 'validate':
        engine = ValidationEngine('cli_validate')
        results = engine.validate_suite(args.target)
        if results.get('status') == 'empty':
            print(f'\nError: {results.get("message")}\n')
            sys.exit(1)
        print_tightening_report(results)
        sys.exit(0)

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


if __name__ == '__main__':
    main()
