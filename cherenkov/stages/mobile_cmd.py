"""
CHERENKOV stages/mobile_cmd.py — click command for the mobile pipeline.

Plans flows from a real mobile source, generates Maestro YAML, gates it for
assertion strength, and then *executes* it on a connected device or emulator.
When no runner is available the flows are still written to disk and reported as
``not_executed`` — never as passing, because nothing ran.
"""

from __future__ import annotations

import json as _json
import os
import re
from pathlib import Path

import click

from cherenkov.execution.appium_runner import AppiumRunner
from cherenkov.execution.maestro_runner import MaestroRunner
from cherenkov.sources.mobile.adapter import MobileSourceAdapter
from cherenkov.stages.mobile_generate import MobileGenerateStage
from cherenkov.stages.mobile_plan import MobilePlanStage
from cherenkov.stages.mobile_review import MobileReviewStage

DEFAULT_OUT_DIR = os.path.join("stub", "generated_tests", "mobile")


def _safe_name(value: str) -> str:
    """Filesystem-safe flow filename."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value).strip("_") or "flow"


def _build_runner(runner_name: str) -> MaestroRunner | AppiumRunner:
    return AppiumRunner() if runner_name == "appium" else MaestroRunner()


@click.command(name="mobile")
@click.argument("source", type=click.Path(exists=True), required=False)
@click.option(
    "--app-id",
    default=None,
    help="Application package id to target (e.g. com.acme.app). "
    "Overrides the id derived from the source.",
)
@click.option(
    "--out",
    "out_dir",
    default=DEFAULT_OUT_DIR,
    show_default=True,
    help="Directory to write generated Maestro flows into.",
)
@click.option(
    "--runner",
    type=click.Choice(["maestro", "appium"]),
    default="maestro",
    show_default=True,
    help="Execution backend for the generated flows.",
)
@click.option(
    "--execute/--no-execute",
    default=True,
    show_default=True,
    help="Run the generated flows on a device. With --no-execute the flows are "
    "generated and gated but reported as not_executed.",
)
@click.option(
    "--strict/--no-strict",
    default=True,
    show_default=True,
    help="Fail a flow that carries no assertion at all.",
)
@click.option(
    "--demo",
    is_flag=True,
    help="Use the built-in demo scenarios instead of a real source. "
    "Demo flows are never executed against a device.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option(
    "--fail-on-finding",
    is_flag=True,
    help="Exit non-zero when any flow fails review or execution.",
)
@click.option("--run-id", default=None, help="Run identifier for logging")
def mobile(
    source: str | None,
    app_id: str | None,
    out_dir: str,
    runner: str,
    execute: bool,
    strict: bool,
    demo: bool,
    as_json: bool,
    fail_on_finding: bool,
    run_id: str | None,
) -> None:
    """Generate and run mobile tests from a recorded source.

    SOURCE is a .hil interaction trace, a .apk, or a .har capture. Without a
    source, pass --demo to see the pipeline on built-in scenarios.

    \b
    Examples:
      cherenkov mobile flows.hil --app-id com.acme.app
      cherenkov mobile app.apk --no-execute
      cherenkov mobile --demo
    """
    if not source and not demo:
        raise click.UsageError(
            "Provide a mobile source (.hil, .apk, or .har), or pass --demo "
            "to run the built-in scenarios."
        )

    # ── Ingest ───────────────────────────────────────────────────────────────
    ingested = None
    if source:
        # Checked by extension, not by parse result: an empty .har parses to an
        # empty list, which must not slip through into demo scenarios.
        if Path(source).suffix.lower() == ".har":
            raise click.ClickException(
                "A .har capture records network traffic, not screen "
                "interactions, so no mobile flow can be planned from it. Use a "
                ".hil trace or a .apk, or run `cherenkov verify` to check that "
                "traffic against an API spec."
            )
        try:
            ingested = MobileSourceAdapter().ingest(source)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise click.ClickException(str(exc)) from exc

    # ── Plan ─────────────────────────────────────────────────────────────────
    plan_output = MobilePlanStage(run_id=run_id).run(ingested)
    if not plan_output.scenarios:
        raise click.ClickException(
            f"No scenarios could be planned from {source}: the source records "
            "no recognisable interactions."
        )
    # Planning from a source must never silently degrade to the demo fixture —
    # that would report flows about an app the source never described.
    if source and plan_output.source == "demo":
        raise click.ClickException(
            f"No mobile flows could be derived from {source}. Expected a .hil "
            "trace with recorded actions, or a .apk."
        )

    is_demo = plan_output.source == "demo"
    effective_app_id = app_id or plan_output.app_id or None

    # A demo flow describes no real app; putting it on a device would produce a
    # verdict about nothing.
    will_execute = execute and not is_demo
    run_notes: list[str] = []
    if is_demo and execute:
        run_notes.append(
            "Demo scenarios are not executed against a device (they describe no "
            "real app). Pass a .hil or .apk source to execute."
        )

    device_runner = None
    if will_execute:
        device_runner = _build_runner(runner)
        if not device_runner.health_check():
            will_execute = False
            run_notes.append(
                f"{runner} is not available "
                f"({'binary not on PATH' if runner == 'maestro' else 'server unreachable'})"
                "; flows were generated and gated but not executed."
            )

    generate = MobileGenerateStage(run_id=run_id, app_id=effective_app_id)
    review = MobileReviewStage(run_id=run_id, strict=strict)

    out_path = Path(os.path.abspath(out_dir))
    out_path.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for scenario in plan_output.scenarios:
        gen_output = generate.run(scenario)
        review_output = review.run(gen_output)

        flow_file = out_path / f"{_safe_name(scenario.id)}.yaml"
        flow_file.write_text(gen_output.yaml_content, encoding="utf-8")

        entry: dict = {
            "scenario_id": scenario.id,
            "name": scenario.name,
            "source": scenario.source,
            "app_id": gen_output.app_id,
            "flow_file": str(flow_file),
            "review_passed": review_output.passed,
            "errors": review_output.errors,
            "warnings": review_output.warnings,
            "executed": False,
            "status": "not_executed",
        }

        # A flow that failed the integrity gate is not worth device time.
        if review_output.passed and will_execute and device_runner is not None:
            run_result = device_runner.run_test(str(flow_file))
            entry["executed"] = bool(run_result.get("executed", False))
            entry["status"] = run_result.get("status", "unknown")
            if run_result.get("stderr"):
                entry["stderr"] = run_result["stderr"].strip()[:2000]
            if run_result.get("reason"):
                entry["reason"] = run_result["reason"]
        elif not review_output.passed:
            entry["status"] = "review_failed"

        results.append(entry)

    review_failures = [r for r in results if not r["review_passed"]]
    exec_failures = [r for r in results if r["status"] == "failed"]
    executed_count = sum(1 for r in results if r["executed"])

    if as_json:
        click.echo(
            _json.dumps(
                {
                    "source": source,
                    "source_kind": plan_output.source,
                    "app_id": effective_app_id or "",
                    "out_dir": str(out_path),
                    "executed": executed_count,
                    "review_failures": len(review_failures),
                    "execution_failures": len(exec_failures),
                    "notes": run_notes,
                    "flows": results,
                },
                indent=2,
            )
        )
    else:
        click.echo(
            f"Planned {len(results)} flow(s) from "
            f"{source or 'built-in demo scenarios'} ({plan_output.source})"
        )
        for entry in results:
            marker = {
                "passed": "[PASS]",
                "failed": "[FAIL]",
                "review_failed": "[GATE]",
                "skipped": "[SKIP]",
                "not_executed": "[----]",
            }.get(entry["status"], "[????]")
            click.echo(f"  {marker} {entry['scenario_id']} — {entry['status']}")
            for err in entry["errors"]:
                click.echo(f"      error:   {err}")
            for warn in entry["warnings"]:
                click.echo(f"      warning: {warn}")

        click.echo(f"\nFlows written to {out_path}")
        click.echo(
            f"Executed {executed_count}/{len(results)} on device "
            f"via {runner}."
        )
        for note in run_notes:
            click.echo(f"Note: {note}")
        if executed_count == 0 and not is_demo:
            click.echo(
                "Run them yourself once a device is attached:\n"
                f"  {runner} test {out_path}"
            )

    if fail_on_finding and (review_failures or exec_failures):
        raise SystemExit(1)
