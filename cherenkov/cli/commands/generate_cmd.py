import click
import os
import sys

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
def generate_cmd(spec, output_dir):
    """Generate Playwright E2E tests from an OpenAPI specification."""
    from cherenkov.stages.ingest import IngestStage
    from cherenkov.stages.plan import PlanStage
    from cherenkov.stages.generate import GenerateStage

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

    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)

    stage = GenerateStage("cli_generate")
    
    # We must construct a map of endpoints for the generate stage
    # GenerateStage signature: run(self, scenario, path, method, operation, schemas, instruction, source_type, ...)
    ep_map = {}
    for ep in ingest_out.endpoints:
        ep_map[ep.path + ":" + ep.method] = ep

    success_count = 0
    for sc in scenarios:
        click.echo(f"  Generating tests for scenario: {sc.mutation_id}...")
        ep = ep_map.get(sc.endpoint + ":" + sc.method)
        try:
            out = stage.run(
                scenario=sc,
                path=sc.endpoint,
                method=sc.method,
                operation=ep.operation if ep else None,
                schemas=ep.schemas if ep else None,
                instruction=getattr(sc, "instruction", ""),
                source_type="openapi"
            )
            # Write to output dir
            test_file = os.path.join(output_dir, f"{sc.mutation_id}.spec.ts")
            with open(test_file, "w") as f:
                f.write(out.test_code)
            success_count += 1
        except Exception as e:
            click.echo(f"  [ERROR] Generation failed for {sc.mutation_id}: {e}", err=True)

    click.echo(f"Successfully generated {success_count}/{len(scenarios)} test suites.")
    click.echo(f"Output located in {output_dir}/")
