"""
CHERENKOV stages/mobile_cmd.py — click command for mobile test generation pipeline.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import click

from cherenkov.stages.ingest import IngestStage
from cherenkov.stages.mobile_plan import MobilePlanStage
from cherenkov.stages.mobile_generate import MobileGenerateStage
from cherenkov.stages.mobile_review import MobileReviewStage


@click.command(name="mobile")
@click.argument("spec_path")
@click.option("--run-id", default=None, help="Run identifier for logging")
def mobile(spec_path: str, run_id: str | None) -> None:
    """Generate mobile tests from an OpenAPI spec via the Maestro pipeline.

    Runs IngestStage, MobilePlanStage, MobileGenerateStage, and
    MobileReviewStage in sequence.
    """
    ingest = IngestStage(run_id=run_id)
    plan = MobilePlanStage(run_id=run_id)
    generate = MobileGenerateStage(run_id=run_id)
    review = MobileReviewStage(run_id=run_id)

    click.echo(f"Ingesting spec: {spec_path}")
    ingest_output = ingest.run(spec_path)
    if ingest_output.status.value != "ok":
        click.echo(f"Ingest failed: {ingest_output.errors}", err=True)
        raise click.Abort()

    click.echo("Planning mobile scenarios...")
    plan_output = plan.run()

    for scenario in plan_output.scenarios:
        click.echo(f"  Generating: {scenario.name} ({scenario.id})")
        gen_output = generate.run(scenario)

        click.echo(f"  Reviewing:  {scenario.name}")
        review_output = review.run(gen_output)

        if review_output.passed:
            click.echo(f"    [PASS] {scenario.id}")
        else:
            click.echo(f"    [FAIL] {scenario.id}")
            for err in review_output.errors:
                click.echo(f"      - {err}")

    click.echo("Pipeline complete.")
