"""cherenkov bench — quality benchmark for the REVIEW stage.

Runs the 6-gate REVIEW stage against a corpus of .spec.ts files and
reports per-gate pass rates, average quality score, and verdict distribution.

Thresholds (from Yuan et al. FSE 2024 baseline):
  compile rate  ≥ 90%   (tsc gate; N/A when node/tsc not on PATH)
  quality score ≥ 85%   (weighted gate pass rate)

Exit codes:
  0 — bench passed (all thresholds met)
  1 — bench failed (below threshold or errors)
  2 — misconfiguration / bad arguments
"""
from __future__ import annotations

import os
import sys

import click


_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
_GOLDEN_DIR = os.path.join(_REPO_ROOT, "bench", "fixtures", "golden_tests")
_DEFAULT_SPEC = os.path.join(_REPO_ROOT, "stub", "openapi_3_1.yaml")


@click.command("bench")
@click.option(
    "--dir", "test_dirs", multiple=True, type=click.Path(exists=True),
    help="Directory of .spec.ts files to review. Repeatable.",
)
@click.option(
    "--spec", "spec_path", type=click.Path(exists=True),
    help="OpenAPI spec for Prism gate (default: stub/openapi_3_1.yaml).",
)
@click.option(
    "--golden/--no-golden", default=True, show_default=True,
    help="Include bundled golden fixtures from bench/fixtures/golden_tests/.",
)
@click.option(
    "--threshold-compile", default=0.9, show_default=True, type=float,
    help="Min tsc gate pass rate (0–1). Bench fails below this.",
)
@click.option(
    "--threshold-quality", default=0.85, show_default=True, type=float,
    help="Min average quality score (0–1). Bench fails below this.",
)
@click.option(
    "--output", "-o", type=click.Path(),
    help="Write full JSON report to file.",
)
@click.option(
    "--verbose", "-v", is_flag=True,
    help="Show per-file errors and extra detail.",
)
def bench_cmd(
    test_dirs: tuple[str, ...],
    spec_path: str | None,
    golden: bool,
    threshold_compile: float,
    threshold_quality: float,
    output: str | None,
    verbose: bool,
) -> None:
    """Benchmark the REVIEW stage against a corpus of generated tests.

    By default runs against the bundled golden fixtures
    (bench/fixtures/golden_tests/). Pass --dir to include additional
    directories of .spec.ts files.

    \b
    Example:
      cherenkov bench
      cherenkov bench --dir stub/generated_tests --no-golden
      cherenkov bench --threshold-quality 0.90 --output bench_report.json
    """
    from cherenkov.bench.runner import run_bench
    from cherenkov.bench.report import print_report, write_json

    dirs: list[str] = list(test_dirs)
    if golden:
        if os.path.isdir(_GOLDEN_DIR):
            dirs.insert(0, _GOLDEN_DIR)
        else:
            click.echo(
                f"[warn] Golden fixtures directory not found: {_GOLDEN_DIR}", err=True
            )

    if not dirs:
        click.echo(
            "No test directories to benchmark. Pass --dir or use --golden (default).",
            err=True,
        )
        sys.exit(2)

    effective_spec = spec_path or (_DEFAULT_SPEC if os.path.exists(_DEFAULT_SPEC) else None)

    thresholds = {
        "compile_rate": threshold_compile,
        "quality_score": threshold_quality,
    }

    report = run_bench(dirs, spec_path=effective_spec, thresholds=thresholds)
    print_report(report, verbose=verbose)

    if output:
        write_json(report, output)
        click.echo(f"  JSON report written to: {output}")

    sys.exit(0 if report.passed() else 1)
