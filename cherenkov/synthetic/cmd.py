"""CLI command for synthetic data generation."""

from __future__ import annotations

import click

from cherenkov.synthetic.generator import GenerationStrategy, generate_from_spec
from cherenkov.synthetic.runner import generate_for_endpoints


@click.command(name="synthetic")
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--endpoints", "-e", default=10, help="Max endpoints to process")
@click.option("--output", "-o", default=None, help="Output JSON file path")
@click.option("--strategy", "-s", type=click.Choice(["random", "llm"]), default="random",
              help="Generation strategy")
def synthetic_cmd(spec_path: str, endpoints: int, output: str | None, strategy: str) -> None:
    """Generate synthetic test data from an OpenAPI spec.

    SPEC_PATH is the path to an OpenAPI YAML or JSON specification file.
    """
    strat = GenerationStrategy.RANDOM if strategy == "random" else GenerationStrategy.LLM
    report = generate_for_endpoints(
        spec_path=spec_path,
        strategy=strat,
        max_endpoints=endpoints,
        output_path=output,
    )

    click.echo(f"\nSynthetic Data Generation Complete")
    click.echo(f"{'=' * 40}")
    click.echo(f"  Spec:          {spec_path}")
    click.echo(f"  Strategy:      {strategy}")
    click.echo(f"  Endpoints:     {report.endpoint_count}")
    click.echo(f"  Samples:       {report.generated_samples}")
    click.echo(f"  Fields:        {report.field_count}")
    click.echo(f"  Duration:      {report.duration_ms}ms")
    if output:
        click.echo(f"  Output:        {output}")
