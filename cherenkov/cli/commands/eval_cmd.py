"""cherenkov/cli/commands/eval_cmd.py — `cherenkov eval` command group.

Four-stage pipeline inspired by google/agents-cli:
  run      — execute suite against a live API, emit JSONL trace
  grade    — static quality analysis (assertion density, schema conformance, coverage)
  compare  — diff two grade files (before/after)
  optimize — suggest generation profile improvements from grade data
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


def _load_json(path: str, label: str) -> dict:
    p = Path(path)
    if not p.exists():
        click.echo(click.style(f"[ERROR] {label} not found: {path}", fg="red"), err=True)
        sys.exit(1)
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        click.echo(click.style(f"[ERROR] {label} is not valid JSON: {e}", fg="red"), err=True)
        sys.exit(1)


def _load_yaml_or_json(path: str, label: str) -> dict:
    p = Path(path)
    if not p.exists():
        click.echo(click.style(f"[ERROR] {label} not found: {path}", fg="red"), err=True)
        sys.exit(1)
    text = p.read_text()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
            return yaml.safe_load(text)
        except Exception as e:
            click.echo(click.style(f"[ERROR] {label} YAML parse error: {e}", fg="red"), err=True)
            sys.exit(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        click.echo(click.style(f"[ERROR] {label} JSON parse error: {e}", fg="red"), err=True)
        sys.exit(1)


# ── `cherenkov eval` group ─────────────────────────────────────────────────────

@click.group("eval")
def eval_cmd():
    """Evaluate, grade, and optimize your test suite quality.

    Implements a STORM-inspired generate → grade → compare → optimize
    lifecycle for continuous suite improvement.

    \b
    Examples:
        # Generate a suite from an OpenAPI spec using 5 tester personas
        cherenkov eval generate --spec openapi.yaml --output suite.json

        # Grade a suite against a spec (no live API needed)
        cherenkov eval grade --spec openapi.yaml --suite suite.json

        # Run suite against a live API and emit a trace
        cherenkov eval run --suite suite.json --target http://localhost:8080

        # Compare two grade reports
        cherenkov eval compare --before grade-v1.json --after grade-v2.json

        # Get improvement suggestions
        cherenkov eval optimize --grade grade.json
    """


# ── `cherenkov eval grade` ─────────────────────────────────────────────────────

@eval_cmd.command("grade")
@click.option("--spec",  required=True, help="Path to OpenAPI spec (YAML or JSON).")
@click.option("--suite", required=True, help="Path to suite manifest JSON.")
@click.option("--output", "-o", default=None,
              help="Write grade report JSON to this file [default: grade-<timestamp>.json].")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON.")
@click.option("--fail-on", type=click.Choice(["F", "D", "C", "B", "A"]), default=None,
              help="Exit 1 if overall grade is at or below this threshold.")
def grade_cmd(spec, suite, output, as_json, fail_on):
    """Score test suite quality against the OpenAPI spec.

    Measures assertion density, schema conformance, and meaningful assertion
    ratio — no live API required.

    \b
    Example:
        cherenkov eval grade --spec openapi.yaml --suite suite.json --output grade.json
    """
    from cherenkov.eval.grader import SuiteGrader

    spec_dict  = _load_yaml_or_json(spec, "spec")
    suite_dict = _load_json(suite, "suite")

    grader = SuiteGrader(spec_dict)
    report = grader.grade(suite_dict)

    if output:
        report.save(Path(output))

    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        _print_grade_report(report)

    if fail_on:
        _GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
        if _GRADE_ORDER.get(report.grade, 0) <= _GRADE_ORDER.get(fail_on, 0):
            sys.exit(1)


def _print_grade_report(report) -> None:
    grade_color = {
        "A": "green", "B": "green", "C": "yellow", "D": "yellow", "F": "red",
    }.get(report.grade, "white")

    click.echo()
    click.echo(click.style("── Suite Grade Report ────────────────────────────────", bold=True))
    click.echo(
        f"  grade      : "
        + click.style(report.grade, fg=grade_color, bold=True)
        + f"  (score {report.overall_score:.3f})"
    )
    click.echo(f"  coverage   : {report.coverage:.1%}  ({report.suite_op_count}/{report.spec_op_count} ops)")
    click.echo(f"  density    : {report.overall_assertion_density:.1f} assertions/test")
    click.echo(f"  meaningful : {report.overall_meaningful_ratio:.1%} of assertions pass quality check")
    click.echo()

    if report.operations:
        click.echo(click.style(f"  {'OPERATION':<32} {'GRADE':>5} {'SCORE':>6} {'DENSITY':>8} {'CONFORM':>8}", bold=True))
        click.echo("  " + "─" * 65)
        for op in report.operations:
            color = {"A": "green", "B": "green", "C": "yellow", "D": "yellow", "F": "red"}.get(op.grade, "white")
            conform_str = click.style("✔" if op.schema_conformance >= 1.0 else "✘", fg="green" if op.schema_conformance >= 1.0 else "red")
            click.echo(
                f"  {op.operation_id[:32]:<32} "
                + click.style(f"{op.grade:>5}", fg=color)
                + f" {op.overall_score:>6.3f} {op.assertion_density:>8.1f}       {conform_str}"
            )
    click.echo()


# ── `cherenkov eval run` ───────────────────────────────────────────────────────

@eval_cmd.command("run")
@click.option("--suite", required=True, help="Path to suite manifest JSON.")
@click.option("--spec",  default=None, help="Path to OpenAPI spec (for spec/suite hashing).")
@click.option("--target", default=None,
              help="Base URL of the API under test [default: dry-run mode].")
@click.option("--output", "-o", default=None,
              help="Output JSONL file [default: eval-run-<timestamp>.jsonl].")
@click.option("--timeout", default=10.0, show_default=True, help="Per-request timeout (seconds).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON summary.")
@click.option("--fail-on-failure", is_flag=True, default=False,
              help="Exit 1 if any test fails.")
def run_cmd(suite, spec, target, output, timeout, as_json, fail_on_failure):
    """Execute suite against a live API and emit a JSONL trace.

    Without --target, runs in dry-run mode (no HTTP requests, records metadata only).
    The JSONL trace is consumed by `cherenkov eval grade` and `eval compare`.

    \b
    Example:
        cherenkov eval run --suite suite.json --target http://localhost:8080 -o run.jsonl
    """
    from cherenkov.eval.runner import EvalRunner
    from cherenkov.drift.snapshot import spec_hash as _spec_hash, suite_manifest_hash

    suite_dict = _load_json(suite, "suite")
    spec_dict  = _load_yaml_or_json(spec, "spec") if spec else {}

    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(output) if output else Path(f"eval-run-{ts}.jsonl")

    runner = EvalRunner(
        target_url=target,
        timeout_s=timeout,
        spec_hash=_spec_hash(spec_dict) if spec_dict else "",
        suite_hash=suite_manifest_hash(suite_dict),
    )
    trace = runner.run(suite_dict)
    trace.to_jsonl(out_path)

    if as_json:
        click.echo(json.dumps({
            "total": trace.total,
            "passed": trace.passed,
            "failed": trace.failed,
            "pass_rate": round(trace.pass_rate, 4),
            "output": str(out_path),
        }, indent=2))
    else:
        _print_run_summary(trace, out_path, target)

    if fail_on_failure and trace.failed > 0:
        sys.exit(1)


def _print_run_summary(trace, out_path: Path, target: str | None) -> None:
    mode = target or "dry-run"
    pass_color = "green" if trace.pass_rate >= 0.9 else ("yellow" if trace.pass_rate >= 0.6 else "red")

    click.echo()
    click.echo(click.style("── Eval Run Summary ──────────────────────────────────", bold=True))
    click.echo(f"  target     : {mode}")
    click.echo(f"  tests      : {trace.total}")
    click.echo(
        f"  pass rate  : "
        + click.style(f"{trace.pass_rate:.1%}  ({trace.passed}/{trace.total})", fg=pass_color, bold=True)
    )
    click.echo(f"  trace      : {out_path}")
    click.echo()

    failed = [r for r in trace.results if not r.passed]
    if failed:
        click.echo(click.style(f"  [{len(failed)} failure(s)]:", fg="red", bold=True))
        for r in failed[:10]:
            click.echo(f"    • {r.operation_id} / {r.test_name}  status={r.response_status}")
            if r.error:
                click.echo(f"      {r.error[:80]}")
        if len(failed) > 10:
            click.echo(f"    … and {len(failed) - 10} more")
    else:
        click.echo(click.style("  All tests passed.", fg="green"))
    click.echo()


# ── `cherenkov eval compare` ──────────────────────────────────────────────────

@eval_cmd.command("compare")
@click.option("--before", required=True, help="Path to baseline grade JSON (before).")
@click.option("--after",  required=True, help="Path to new grade JSON (after).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON.")
@click.option("--fail-on-regression", is_flag=True, default=False,
              help="Exit 1 if any operation regressed in grade.")
def compare_cmd(before, after, as_json, fail_on_regression):
    """Compare two grade reports to detect regressions and improvements.

    \b
    Example:
        cherenkov eval compare --before grade-v1.json --after grade-v2.json
    """
    from cherenkov.eval.grader import GradeReport
    from cherenkov.eval.compare import compare_grades

    before_report = GradeReport.load(Path(before))
    after_report  = GradeReport.load(Path(after))
    cmp = compare_grades(before_report, after_report)

    if as_json:
        click.echo(json.dumps(cmp.to_dict(), indent=2))
    else:
        _print_compare_report(cmp)

    if fail_on_regression and cmp.has_regressions:
        sys.exit(1)


def _print_compare_report(cmp) -> None:
    direction_color = "green" if cmp.delta_score >= 0 else "red"

    click.echo()
    click.echo(click.style("── Eval Compare Report ───────────────────────────────", bold=True))
    click.echo(
        f"  grade      : {cmp.before_grade} → "
        + click.style(cmp.after_grade, fg=direction_color, bold=True)
        + f"  (Δ{cmp.delta_score:+.3f})"
    )
    click.echo(f"  coverage Δ : {cmp.delta_coverage:+.1%}")
    click.echo(f"  density Δ  : {cmp.delta_assertion_density:+.2f} assertions/test")
    click.echo(f"  meaningful Δ: {cmp.delta_meaningful_ratio:+.1%}")
    click.echo()

    if cmp.improved:
        click.echo(click.style(f"  Improved ({len(cmp.improved)}):", fg="green", bold=True))
        for d in cmp.improved:
            click.echo(f"    ✔  {d.operation_id:<30} {d.before_grade} → {d.after_grade}  (Δ{d.delta_score:+.3f})")
        click.echo()

    if cmp.regressed:
        click.echo(click.style(f"  Regressed ({len(cmp.regressed)}):", fg="red", bold=True))
        for d in cmp.regressed:
            click.echo(f"    ✘  {d.operation_id:<30} {d.before_grade} → {d.after_grade}  (Δ{d.delta_score:+.3f})")
        click.echo()

    if cmp.added:
        click.echo(click.style(f"  Added ({len(cmp.added)}):", fg="cyan", bold=True))
        for d in cmp.added:
            click.echo(f"    +  {d.operation_id} (grade {d.after_grade})")
        click.echo()

    if cmp.removed:
        click.echo(click.style(f"  Removed ({len(cmp.removed)}):", fg="yellow", bold=True))
        for d in cmp.removed:
            click.echo(f"    -  {d.operation_id}")
        click.echo()

    if not cmp.has_regressions:
        click.echo(click.style("  ✔  No regressions detected.", fg="green"))
    else:
        click.echo(click.style(
            "  ✖  Regressions detected — review failing operations above.",
            fg="red", bold=True,
        ))


# ── `cherenkov eval optimize` ─────────────────────────────────────────────────

@eval_cmd.command("optimize")
@click.option("--grade", "grade_path", required=True, help="Path to grade report JSON.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON.")
def optimize_cmd(grade_path, as_json):
    """Suggest generation profile improvements from a grade report.

    Analyzes weak areas and outputs actionable recommendations that can be
    fed back into `cherenkov synthetic` or the drift L2 maker.

    \b
    Example:
        cherenkov eval optimize --grade grade.json
    """
    from cherenkov.eval.grader import GradeReport
    from cherenkov.eval.optimizer import optimize_profile

    report = GradeReport.load(Path(grade_path))
    suggestion = optimize_profile(report)

    if as_json:
        click.echo(json.dumps(suggestion.to_dict(), indent=2))
    else:
        _print_optimize_suggestion(suggestion)


def _print_optimize_suggestion(suggestion) -> None:
    grade_color = {
        "A": "green", "B": "green", "C": "yellow", "D": "yellow", "F": "red",
    }.get(suggestion.current_grade, "white")

    click.echo()
    click.echo(click.style("── Eval Optimize ─────────────────────────────────────", bold=True))
    click.echo(
        f"  current grade : "
        + click.style(suggestion.current_grade, fg=grade_color, bold=True)
    )
    click.echo()
    click.echo(click.style("  Suggestions:", bold=True))
    for s in suggestion.suggestions:
        click.echo(f"    • {s}")

    if suggestion.weakest_operations:
        click.echo()
        click.echo(click.style("  Weakest operations (prioritize these):", bold=True))
        for op in suggestion.weakest_operations:
            click.echo(f"    • {op}")

    if suggestion.suggested_profile:
        click.echo()
        click.echo(click.style("  Suggested generation profile:", bold=True))
        for k, v in suggestion.suggested_profile.items():
            click.echo(f"    {k}: {v}")
    click.echo()


# ── `cherenkov eval generate` ─────────────────────────────────────────────────

@eval_cmd.command("generate")
@click.option("--spec", required=True, help="Path to OpenAPI spec (YAML or JSON).")
@click.option("--output", "-o", default=None,
              help="Write suite JSON to this file [default: suite-<timestamp>.json].")
@click.option("--personas", default="all",
              help=(
                  "Comma-separated persona names or 'all'. "
                  "Available: HappyPath, ErrorPath, SecurityProber, SchemaPedant, BoundarySeeker"
              ))
@click.option("--no-enrich", "no_enrich", is_flag=True, default=False,
              help="Skip the assertion-enrichment polish pass.")
@click.option("--no-grade", "no_grade", is_flag=True, default=False,
              help="Skip grading after generation.")
@click.option("--sequential", is_flag=True, default=False,
              help="Run personas sequentially instead of in parallel.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON summary.")
def generate_cmd(spec, output, personas, no_enrich, no_grade, sequential, as_json):
    """Generate a multi-persona test suite from an OpenAPI spec.

    Inspired by STORM's perspective-guided questioning: five built-in tester
    personas (HappyPath, ErrorPath, SecurityProber, SchemaPedant, BoundarySeeker)
    each generate tests from their viewpoint in parallel, then the results are
    merged, deduplicated, and enriched with a polish pass.

    The output is a suite.json compatible with `cherenkov eval grade` and
    `cherenkov eval run`.

    \b
    Examples:
        cherenkov eval generate --spec openapi.yaml --output suite.json
        cherenkov eval generate --spec openapi.yaml --personas HappyPath,SchemaPedant
        cherenkov eval generate --spec openapi.yaml | cherenkov eval grade --spec openapi.yaml
    """
    from cherenkov.synthetic.suite_engine import SuiteEngine
    from cherenkov.synthetic.personas import DEFAULT_PERSONAS, PERSONA_BY_NAME
    from datetime import datetime, timezone

    spec_dict = _load_yaml_or_json(spec, "spec")

    if personas.lower() == "all":
        selected = list(DEFAULT_PERSONAS)
    else:
        selected = []
        for name in [n.strip() for n in personas.split(",")]:
            p = PERSONA_BY_NAME.get(name)
            if p is None:
                click.echo(
                    click.style(f"[ERROR] Unknown persona: {name!r}", fg="red"), err=True
                )
                click.echo(
                    f"  Available: {', '.join(PERSONA_BY_NAME)}", err=True
                )
                sys.exit(1)
            selected.append(p)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(output) if output else Path(f"suite-{ts}.json")

    engine = SuiteEngine(
        spec=spec_dict,
        personas=selected,
        run_grader=not no_grade,
        parallel=not sequential,
        enricher=not no_enrich,
    )
    result = engine.run()

    out_path.write_text(json.dumps(result.suite, indent=2))

    if as_json:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _print_generate_result(result, out_path, selected)


def _print_generate_result(result, out_path: Path, personas) -> None:
    grade_str = ""
    if result.grade_report is not None:
        g = result.grade_report.grade
        color = {"A": "green", "B": "green", "C": "yellow", "D": "yellow", "F": "red"}.get(g, "white")
        grade_str = "  grade      : " + click.style(g, fg=color, bold=True) + "\n"

    click.echo()
    click.echo(click.style("── Eval Generate ─────────────────────────────────────", bold=True))
    click.echo(f"  personas   : {', '.join(p.name for p in personas)}")
    click.echo(f"  ops covered: {result.operations_covered}")
    click.echo(f"  tests      : {result.total_tests}")
    if grade_str:
        click.echo(grade_str, nl=False)
    click.echo(f"  duration   : {result.duration_ms}ms")
    click.echo(f"  output     : {out_path}")
    click.echo()

    if result.persona_runs:
        click.echo(click.style(
            f"  {'PERSONA':<20} {'OPS':>4} {'TESTS':>6} {'MS':>6}", bold=True
        ))
        click.echo("  " + "─" * 40)
        for r in sorted(result.persona_runs, key=lambda x: x.persona_name):
            click.echo(
                f"  {r.persona_name:<20} {r.op_count:>4} {r.test_count:>6} {r.duration_ms:>6}"
            )
    click.echo()
