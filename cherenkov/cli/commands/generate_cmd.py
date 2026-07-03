import os
import sys

import click


@click.command("generate")
@click.option(
    "--spec",
    required=True,
    help="Path to the OpenAPI spec (JSON/YAML) to generate tests for",
)
@click.option(
    "--output-dir",
    default="stub/generated_tests",
    help="Directory to write the generated Playwright test files to",
)
@click.option(
    "--repair/--no-repair",
    default=True,
    help="Run the generate→review→repair loop (ChatTester-style). Default: on.",
)
@click.option(
    "--max-attempts",
    default=3,
    show_default=True,
    type=click.IntRange(1, 10),
    help="Maximum repair attempts per scenario (only used with --repair).",
)
def generate_cmd(spec, output_dir, repair, max_attempts):
    """Generate Playwright E2E tests from an OpenAPI specification.

    Uses the ChatTester-style repair loop by default: each scenario is generated,
    reviewed against the spec, and repaired up to --max-attempts times before
    the highest-quality result is written to disk.  Pass --no-repair to skip
    the review/repair cycle and write the first generation directly.
    """
    from cherenkov.stages.ingest import IngestStage
    from cherenkov.stages.plan import PlanStage

    click.echo(f"Ingesting OpenAPI spec: {spec}")
    try:
        ingest_stage = IngestStage("cli_generate")
        ingest_out = ingest_stage.run(spec)

        plan_stage = PlanStage("cli_generate")
        plan_out = plan_stage.run(ingest_out)

        scenarios = plan_out.scenarios
    except Exception as e:
        click.echo(f"[ERROR] Failed to plan scenarios from spec: {e}", err=True)
        sys.exit(1)

    click.echo(f"Planned {len(scenarios)} scenarios. Handing off to AI Generator...")
    if repair:
        click.echo(f"  Mode: repair loop (max {max_attempts} attempt(s) per scenario)")
    else:
        click.echo("  Mode: single-pass (--no-repair)")

    os.makedirs(output_dir, exist_ok=True)

    ep_map = {}
    for ep in ingest_out.endpoints:
        ep_map[ep.path + ":" + ep.method] = ep

    success_count = 0
    for sc in scenarios:
        click.echo(f"  Generating tests for scenario: {sc.mutation_id}...")
        ep = ep_map.get(sc.endpoint + ":" + sc.method)
        ep_operation = ep.operation if ep else None
        ep_schemas = ep.schemas if ep else None

        try:
            if repair:
                from cherenkov.stages.repair import RepairLoop
                loop = RepairLoop(run_id=f"cli_generate_{sc.mutation_id}", max_attempts=max_attempts)
                gen_out, review = loop.run(
                    scenario=sc,
                    path=sc.endpoint,
                    method=sc.method,
                    operation=ep_operation,
                    schemas=ep_schemas,
                    instruction=getattr(sc, "instruction", ""),
                    source_type="openapi",
                    spec_path=spec,
                )
                if review is not None:
                    score = getattr(review, "quality_score", None)
                    verdict = getattr(review, "verdict", None)
                    verdict_val = getattr(verdict, "value", verdict) if verdict else None
                    click.echo(
                        f"    review: verdict={verdict_val}, quality={score:.2f}"
                        if score is not None
                        else f"    review: verdict={verdict_val}"
                    )
            else:
                from cherenkov.stages.generate import GenerateStage
                stage = GenerateStage("cli_generate")
                gen_out = stage.run(
                    scenario=sc,
                    path=sc.endpoint,
                    method=sc.method,
                    operation=ep_operation,
                    schemas=ep_schemas,
                    instruction=getattr(sc, "instruction", ""),
                    source_type="openapi",
                )

            test_file = os.path.join(output_dir, f"{sc.mutation_id}.spec.ts")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(gen_out.test_code)
            success_count += 1
        except Exception as e:
            click.echo(f"  [ERROR] Generation failed for {sc.mutation_id}: {e}", err=True)

    click.echo(f"Successfully generated {success_count}/{len(scenarios)} test suites.")
    click.echo(f"Output located in {output_dir}/")
