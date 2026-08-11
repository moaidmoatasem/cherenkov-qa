"""cherenkov/cli/generate_cmd.py — CLI command module."""

from __future__ import annotations

import os
import re
import sys

import click

_FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def scenario_spec_filename(endpoint: str, method: str, mutation_id: str) -> str:
    """Build a collision-free ``.spec.ts`` filename for one scenario.

``mutation_id`` alone is not unique across scenarios: every endpoint
contributes a ``happy_path`` and ``unauthorized`` mutation, so keying the
file on mutation_id alone silently overwrites earlier scenarios (the CLI
would report "38/38 generated" while only four files persist). Including
method + sanitized endpoint path guarantees each scenario gets its own
file, e.g. ``POST_pet_happy_path.spec.ts``.

Args:
    endpoint (str): Parameter endpoint.
    method (str): Parameter method.
    mutation_id (str): Parameter mutation_id.

Returns:
    str: Command execution result.
    """
    path_part = _FILENAME_UNSAFE.sub("_", endpoint.strip("/")).strip("_")
    return f"{method}_{path_part}_{mutation_id}.spec.ts"


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

Args:
    spec: Parameter spec.
    output_dir: Parameter output_dir.
    repair: Parameter repair.
    max_attempts: Parameter max_attempts.

Returns:
    None: Command execution result.
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

    # The review/repair loop's tsc + Prism gates must physically write the
    # candidate file into stub/generated_tests/ (tsconfig.json + playwright
    # config only know about that path). When --output-dir points somewhere
    # else, that write is just scratch working state, not the user's real
    # output — clean it up afterwards instead of leaving stray files behind
    # in the tracked fixture directory.
    from cherenkov.stages.review import default_review_scratch_dir
    _writing_to_scratch_dir = os.path.abspath(output_dir) == os.path.abspath(
        default_review_scratch_dir()
    )

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
                loop = RepairLoop(
                    run_id=f"cli_generate_{sc.mutation_id}",
                    max_attempts=max_attempts,
                    cleanup_scratch=not _writing_to_scratch_dir,
                )
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

            test_file = os.path.join(
                output_dir,
                scenario_spec_filename(sc.endpoint, sc.method, sc.mutation_id),
            )
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(gen_out.test_code)
            if repair and _writing_to_scratch_dir:
                # The repair loop's review gates always write a scratch copy
                # at {mutation_id}.spec.ts (tsc/Prism only know that path).
                # With unique output filenames that scratch copy no longer
                # doubles as the final artifact — drop the stale,
                # collision-prone file instead of leaving it behind.
                scratch = os.path.join(output_dir, f"{sc.mutation_id}.spec.ts")
                if os.path.exists(scratch):
                    try:
                        os.remove(scratch)
                    except OSError as e:
                        click.echo(
                            f"  [WARN] could not remove review scratch {scratch}: {e}",
                            err=True,
                        )
            success_count += 1
        except Exception as e:
            click.echo(f"  [ERROR] Generation failed for {sc.mutation_id}: {e}", err=True)

    click.echo(f"Successfully generated {success_count}/{len(scenarios)} test suites.")
    click.echo(f"Output located in {output_dir}/")
