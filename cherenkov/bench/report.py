"""cherenkov/bench/report.py — Rich-formatted bench report output."""

from __future__ import annotations

import json
from typing import Any

from cherenkov.bench.metrics import BenchReport, SpecBenchResult

try:
    from rich.console import Console
    from rich.table import Table  # noqa: F401
    from rich import box as rich_box  # noqa: F401

    _RICH = True
except ImportError:
    _RICH = False


def _rate_str(rate: float | None) -> str:
    if rate is None:
        return "N/A"
    pct = rate * 100
    if pct >= 90:
        return f"[green]{pct:.1f}%[/green]"
    if pct >= 70:
        return f"[yellow]{pct:.1f}%[/yellow]"
    return f"[red]{pct:.1f}%[/red]"


def _verdict_str(dist: dict[str, int]) -> str:
    total = sum(dist.values())
    if total == 0:
        return "—"
    approve = dist.get("auto_approve", 0)
    hitl = dist.get("hitl", 0)
    regen = dist.get("regenerate", 0)
    parts = []
    if approve:
        parts.append(f"[green]✓{approve}[/green]")
    if hitl:
        parts.append(f"[yellow]↑{hitl}[/yellow]")
    if regen:
        parts.append(f"[red]✗{regen}[/red]")
    return " ".join(parts)


def print_report(report: BenchReport, verbose: bool = False) -> None:
    """Print a Rich-formatted bench report to stdout."""
    if not _RICH:
        _print_plain(report)
        return

    console = Console()
    console.print()
    console.rule("[bold]CHERENKOV bench report[/bold]")
    console.print()

    for result in report.results:
        _print_spec_result(console, result, verbose=verbose)

    console.print()
    console.rule("[bold]Summary[/bold]")
    _print_summary(console, report)
    console.print()


def _print_spec_result(
    console: Any, result: SpecBenchResult, verbose: bool = False
) -> None:
    from rich.table import Table
    import rich.box as rich_box

    # label = result.spec_path.split("/")[-1]
    console.print(f"  [dim]spec:[/dim] {result.spec_path}")
    console.print(
        f"  [dim]tests:[/dim] {result.scenario_count}  "
        f"[dim]elapsed:[/dim] {result.elapsed_s:.1f}s"
    )
    console.print()

    tbl = Table(box=rich_box.SIMPLE, show_header=True, header_style="bold")
    tbl.add_column("Gate", style="dim")
    tbl.add_column("Pass", justify="right")
    tbl.add_column("Fail", justify="right")
    tbl.add_column("Skip", justify="right")
    tbl.add_column("Rate", justify="right")

    for name, summary in result.gate_summaries.items():
        rate = summary.pass_rate
        rate_s = _rate_str(rate)
        tbl.add_row(
            name,
            str(summary.pass_count),
            str(summary.fail_count),
            str(summary.skip_count),
            rate_s,
        )
    console.print(tbl)

    console.print(
        f"  [bold]Avg quality score:[/bold] {_rate_str(result.avg_quality_score)}"
    )
    console.print(
        f"  [bold]Verdicts:[/bold] {_verdict_str(result.verdict_distribution)}"
    )

    if verbose and result.errors:
        console.print()
        console.print(f"  [red]Errors ({len(result.errors)}):[/red]")
        for e in result.errors:
            console.print(f"    [red]• {e}[/red]")

    console.print()


def _print_summary(console: Any, report: BenchReport) -> None:
    cr = report.overall_compile_rate
    qs = report.overall_quality_score
    passed = report.passed()

    thr_c = report.thresholds.get("compile_rate", 0.9)
    thr_q = report.thresholds.get("quality_score", 0.85)

    console.print(f"  Total tests      : {report.total_scenarios}")
    console.print(
        f"  Compile rate     : {_rate_str(cr)}  [dim](threshold ≥ {thr_c:.0%})[/dim]"
    )
    console.print(
        f"  Avg quality score: {_rate_str(qs)}  [dim](threshold ≥ {thr_q:.0%})[/dim]"
    )
    console.print()

    if passed:
        console.print("  [bold green]✓ BENCH PASSED[/bold green]  — quality bar met")
    else:
        console.print(
            "  [bold red]✗ BENCH FAILED[/bold red]  — below threshold; do not market yet"
        )

    console.print()
    console.print(
        "  [dim]Thresholds from: Yuan et al. FSE 2024 (compile ≥ 90%, pass ≥ 85%)[/dim]"
    )
    console.print("  [dim]Run with --output bench_report.json to persist results[/dim]")


def _print_plain(report: BenchReport) -> None:
    """Fallback when Rich is not installed."""
    print("\n=== CHERENKOV bench report ===\n")
    for result in report.results:
        print(f"Spec: {result.spec_path}")
        print(f"Tests: {result.scenario_count}  Elapsed: {result.elapsed_s:.1f}s")
        for name, summary in result.gate_summaries.items():
            rate = summary.pass_rate
            rate_s = f"{rate * 100:.1f}%" if rate is not None else "N/A"
            print(
                f"  [{name}] pass={summary.pass_count} fail={summary.fail_count} skip={summary.skip_count} rate={rate_s}"
            )
        print(f"  Avg quality: {result.avg_quality_score:.1%}")
        dist = result.verdict_distribution
        print(
            f"  Verdicts: approve={dist.get('auto_approve',0)} hitl={dist.get('hitl',0)} regenerate={dist.get('regenerate',0)}"
        )
        print()

    cr = report.overall_compile_rate
    print(f"Overall compile rate : {f'{cr:.1%}' if cr is not None else 'N/A'}")
    print(f"Overall quality score: {report.overall_quality_score:.1%}")
    print(f"BENCH {'PASSED' if report.passed() else 'FAILED'}")


def write_json(report: BenchReport, path: str) -> None:
    """Write JSON report to disk."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2)
