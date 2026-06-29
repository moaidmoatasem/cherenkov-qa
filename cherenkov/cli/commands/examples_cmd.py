"""Examples CLI Command (CC-6)."""
from __future__ import annotations

import click


@click.command("examples")
def examples_cmd():
    """Show a gallery of common CHERENKOV one-liners."""
    click.echo(click.style("CHERENKOV Useful One-Liners:", bold=True, fg="blue"))
    click.echo("")
    
    examples = [
        ("Validate against staging server:", "cherenkov validate --target https://api.staging.example.com --spec openapi.yaml"),
        ("Validate using stdin pipe (CC-6):", "cat swagger.json | cherenkov validate --target http://localhost:8080 --spec -"),
        ("Run in strict CI mode (fails on drift):", "cherenkov validate --target http://localhost:8080 --spec openapi.yaml --fail-on-drift --quiet"),
        ("Output JSON results for JQ parsing:", "cherenkov validate --target http://localhost:8080 --spec openapi.yaml --json"),
        ("Generate Playwright tests locally:", "cherenkov generate --spec openapi.yaml --output tests/"),
        ("Launch the CHERENKOV dashboard:", "cherenkov dashboard --port 3000"),
        ("Push session state to another device (CC-5):", "cherenkov teleport push my_session_123")
    ]
    
    for desc, cmd in examples:
        click.echo(click.style(desc, fg="green"))
        click.echo(f"  $ {cmd}")
        click.echo("")
