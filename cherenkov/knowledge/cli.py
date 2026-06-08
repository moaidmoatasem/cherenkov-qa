from __future__ import annotations

import json

import click

from cherenkov.knowledge.domain.models import KnowledgeQuery
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository


@click.group()
def knowledge():
    """Knowledge management commands."""


@knowledge.command()
@click.argument("query_text")
@click.option("--source", type=str, help="Filter by source")
@click.option("--limit", type=int, default=10, help="Maximum results")
@click.option(
    "--format",
    type=click.Choice(["json", "text", "pretty"]),
    default="pretty",
    help="Output format",
)
def query(query_text: str, source: str | None, limit: int, format: str):
    """Query knowledge repository."""
    repo = SQLiteKnowledgeRepository()
    q = KnowledgeQuery(query=query_text, source=source, limit=limit)
    result = repo.query(q)
    if format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    elif format == "text":
        click.echo(f"Source: {result.source}")
        click.echo(f"Confidence: {result.confidence}")
        count = len(result.data) if isinstance(result.data, list) else 1
        click.echo(f"Results: {count}")
        click.echo(f"Data: {result.data}")
    else:
        click.echo(f"\nKnowledge Query Results")
        click.echo(f"{'=' * 50}")
        click.echo(f"Source: {result.source}")
        click.echo(f"Confidence: {result.confidence:.2f}")
        count = len(result.data) if isinstance(result.data, list) else 1
        click.echo(f"Results: {count}")
        click.echo(f"\n{json.dumps(result.data, indent=2)}")
