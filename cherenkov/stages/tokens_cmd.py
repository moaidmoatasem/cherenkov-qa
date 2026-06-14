"""
cherenkov tokens — token consumption monitor CLI.

Usage:
    cherenkov tokens report [--days N] [--json]
    cherenkov tokens breakdown [--stage] [--days N]
"""

from __future__ import annotations

import json


def run_tokens_report(days: int = 30, as_json: bool = False) -> None:
    from cherenkov.observability.token_monitor import get_monitor

    monitor = get_monitor()
    report = monitor.get_report(days=days)

    if as_json:
        print(json.dumps(monitor.get_dashboard_data(days=days), indent=2))
        return

    # Human-readable output
    print(f"\n{'─'*60}")
    print(f"  CHERENKOV Token Consumption Report — last {days} days")
    print(f"{'─'*60}")
    print(f"  Total requests : {report.total_requests:,}")
    print(f"  Total tokens   : {report.total_tokens:,}")
    print(f"  Total cost     : ${report.total_cost_usd:.6f}")
    print(f"  Cache hit rate : {report.cache_hit_rate*100:.1f}%")
    print(f"  Reprompt rate  : {report.reprompt_rate*100:.1f}%")
    print(f"  Avg prompt tok : {report.avg_prompt_tokens:.0f}")
    print(f"  Avg output tok : {report.avg_completion_tokens:.0f}")

    if report.by_provider:
        print(f"\n  {'Provider/Model':<32} {'Requests':>9} {'Tokens':>10} {'Cost':>12}")
        print(f"  {'─'*32} {'─'*9} {'─'*10} {'─'*12}")
        for row in report.by_provider:
            label = f"{row['provider']}/{row['model']}"[:32]
            print(
                f"  {label:<32} {row['requests']:>9,} "
                f"{row['total_tokens']:>10,} ${row['cost_usd']:>11.6f}"
            )

    if report.by_stage:
        print(f"\n  {'Stage':<20} {'Requests':>9} {'Tokens':>10} {'Cost':>12}")
        print(f"  {'─'*20} {'─'*9} {'─'*10} {'─'*12}")
        for row in report.by_stage:
            print(
                f"  {row['stage']:<20} {row['requests']:>9,} "
                f"{row['total_tokens']:>10,} ${row['cost_usd']:>11.6f}"
            )

    if report.recommendations:
        print("\n  Recommendations")
        print(f"  {'─'*56}")
        for rec in report.recommendations:
            sev = rec["severity"].upper()
            icon = {"OK": "✓", "INFO": "ℹ", "WARNING": "⚠", "ERROR": "✗"}.get(sev, "·")
            print(f"\n  {icon} [{sev}] {rec['title']}")
            print(f"    {rec['detail']}")
            if rec.get("action"):
                print(f"    → {rec['action']}")

    print(f"\n{'─'*60}\n")


def run_tokens_breakdown(by_stage: bool = False, days: int = 30) -> None:
    from cherenkov.observability.token_monitor import get_monitor

    monitor = get_monitor()
    report = monitor.get_report(days=days)

    if by_stage:
        print(json.dumps(report.by_stage, indent=2))
    else:
        print(json.dumps(report.by_provider, indent=2))
