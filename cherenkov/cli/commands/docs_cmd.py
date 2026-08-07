"""`cherenkov docs [<topic>]` — the CLI's own documentation, as data.

Written for an agent that has landed in a repository cold and needs to find out
what CHERENKOV does without a browser. Every topic renders as a human table or,
with ``--json``, as ``{summary, commands, notes}`` a caller can parse.

The `notes` are the part worth maintaining: they carry the judgement a help
string cannot, e.g. that `verify` needs a live target, or that `eject` is the
exit path rather than a packaging step.
"""
from __future__ import annotations

import json as json_lib
from typing import TypedDict

import click


class Topic(TypedDict):
    summary: str
    commands: list[str]
    notes: list[str]


TOPICS: dict[str, Topic] = {
    "quickstart": {
        "summary": "Zero to a first conformance verdict against a live API.",
        "commands": [
            "cherenkov init",
            "cherenkov doctor",
            "cherenkov generate --spec openapi.yaml --output-dir tests/",
            "cherenkov verify --spec openapi.yaml --url https://api.example.com",
        ],
        "notes": [
            "`init` writes cherenkov.toml and autodetects the spec; it is safe to re-run.",
            "`doctor` reports what is missing before a run fails halfway through.",
            "No LLM available? `generate --no-repair` uses the template fallback.",
        ],
    },
    "generate": {
        "summary": "Turn an OpenAPI spec into Playwright tests.",
        "commands": [
            "cherenkov generate --spec openapi.yaml --output-dir tests/",
            "cherenkov generate --spec openapi.yaml --output-dir tests/ --no-repair",
            "cherenkov check-stale --spec openapi.yaml --json",
        ],
        "notes": [
            "The repair loop is gated on the meaningful-assertion check.",
            "A test that cannot fail a synthesized spec regression does not pass.",
            "One file per scenario. Filenames derive from the endpoint, not the mutation id.",
            "`check-stale` tells you whether committed tests still match the spec.",
        ],
    },
    "verify": {
        "summary": "Probe a live API against its spec and report divergences.",
        "commands": [
            "cherenkov verify --spec openapi.yaml --url https://api.example.com",
            "cherenkov verify --spec openapi.yaml --url URL --coverage-report",
            "cherenkov verify --spec openapi.yaml --url URL --health-score",
        ],
        "notes": [
            "Needs a reachable target: exits 2 on connection failure.",
            "An outage is never reported as a clean run.",
            "Coverage counts endpoints actually probed, so a clean target is not untested.",
            "An endpoint whose path parameters cannot be filled is reported, not skipped silently.",
        ],
    },
    "check-suite": {
        "summary": "Catch a test suite that passes without proving anything.",
        "commands": [
            "cherenkov check-suite --candidate tests/suite.py --baseline known_good.py",
            "cherenkov check-suite -c tests/suite.py -b known_good.py --fail-on-finding",
            "cherenkov audit --target URL --spec openapi.yaml --test-cmd \"pytest tests/\"",
        ],
        "notes": [
            "Detects WEAKENED, DELETED and HALLUCINATED assertions.",
            "Those are the three ways an AI-written suite goes green on a broken system.",
            "This is the check no other test tool runs. Wire this one into CI first.",
            "`--fail-on-finding` is the CI mode; the default reports without failing.",
        ],
    },
    "certify": {
        "summary": "Issue a signed conformance certificate for a live API.",
        "commands": [
            "cherenkov certify --spec openapi.yaml --url https://api.example.com",
            "cherenkov certify --spec openapi.yaml --url URL --coverage-report",
            "cherenkov certify --spec openapi.yaml --url URL --compliance",
        ],
        "notes": [
            "The format is an open spec: docs/specs/CHERENKOV_CERTIFICATE.md.",
            "It is not a proprietary artifact.",
            "`--compliance` maps onto ISO/IEC 42001 and the OWASP AI Testing Guide.",
            "It also covers the OWASP Top 10 for LLM Applications.",
            "certify reuses a single probe sweep; it does not re-probe per report flag.",
        ],
    },
    "eject": {
        "summary": "Leave. Export a standalone Playwright suite with no CHERENKOV imports.",
        "commands": [
            "cherenkov eject --output ./standalone",
            "cd standalone && npm install && npx playwright test",
        ],
        "notes": [
            "A supported exit, not a packaging step. Zero lock-in is an invariant.",
            "Ejected output has no `cherenkov` import and runs on vanilla Playwright.",
            "Eject before you decide whether to keep using CHERENKOV, not after.",
        ],
    },
    "journeys": {
        "summary": "Declarative multi-step flows, including chained CRUD.",
        "commands": [
            "cherenkov dashboard",
            "curl localhost:8000/api/v1/journeys",
            "cherenkov verify --spec openapi.yaml --url URL --allow-mutations",
        ],
        "notes": [
            "A journey is one YAML file the engine executes and the dashboard renders.",
            "A mutating chain refuses to run without --allow-mutations.",
            "Teardown runs on success, failure and exception.",
            "Teardown failures are reported, never swallowed.",
        ],
    },
    "mcp": {
        "summary": "Expose CHERENKOV to other agents over Model Context Protocol.",
        "commands": [
            "cherenkov mcp serve",
            "cherenkov mcp install",
            "cherenkov agent init",
        ],
        "notes": [
            "manifest.json is generated from handlers.TOOLS — never edit it by hand.",
            "Regenerate with scripts/gen_manifest.py.",
            "`agent init` is the faster path: it installs the skills and writes AGENTS.md.",
        ],
    },
    "ci": {
        "summary": "Run CHERENKOV as a gate in a pipeline.",
        "commands": [
            "cherenkov validate --target URL --spec openapi.yaml --fail-on-drift --quiet",
            "cherenkov check-suite -c tests/suite.py -b known_good.py --fail-on-finding",
            "cherenkov validate --target URL --spec openapi.yaml --json",
        ],
        "notes": [
            "A GitHub Action ships in action.yml.",
            "Use --json for anything a script reads. Exit codes are stable; text is not.",
            "Prefer --fail-on-drift / --fail-on-finding over parsing stdout to decide pass/fail.",
        ],
    },
    "agent": {
        "summary": "Make CHERENKOV discoverable to a coding agent in this repository.",
        "commands": [
            "cherenkov agent init",
            "cherenkov agent init --json",
            "cherenkov docs --json",
        ],
        "notes": [
            "Run once per repository. Installs the skills and writes a CHERENKOV block.",
            "That block is how an agent with no prior context finds the tool.",
            "It is idempotent: re-running replaces the block rather than appending.",
            "Nothing is sent anywhere: local file writes plus an optional `npx skills add`.",
        ],
    },
}


def _topic_payload(name: str) -> dict[str, object]:
    topic = TOPICS[name]
    return {"topic": name, **topic}


@click.command("docs")
@click.argument("topic", required=False)
@click.option("--json", "as_json", is_flag=True, help="Emit structured JSON instead of text.")
def docs_cmd(topic: str | None, as_json: bool):
    """Show CLI documentation for a topic, as text or JSON."""
    if topic is not None and topic not in TOPICS:
        available = ", ".join(sorted(TOPICS))
        raise click.ClickException(f'Unknown docs topic "{topic}". Available topics: {available}')

    if as_json:
        payload: dict[str, object]
        if topic is None:
            payload = {"topics": [_topic_payload(name) for name in sorted(TOPICS)]}
        else:
            payload = _topic_payload(topic)
        click.echo(json_lib.dumps(payload, indent=2))
        return

    if topic is None:
        click.echo(click.style("CHERENKOV CLI docs", bold=True, fg="blue"))
        click.echo("")
        click.echo("API conformance testing: spec in, Playwright tests out, zero lock-in.")
        click.echo("Use `cherenkov docs <topic>` for detail, `--json` for structured output.")
        click.echo("")
        click.echo(click.style("Topics:", bold=True))
        for name in sorted(TOPICS):
            click.echo(f"  {name:<12} {TOPICS[name]['summary']}")
        click.echo("")
        click.echo(click.style("Recommended agent start:", bold=True))
        click.echo("  cherenkov agent init")
        click.echo("  cherenkov doctor")
        click.echo("  cherenkov docs --json")
        return

    entry = TOPICS[topic]
    click.echo(click.style(f"CHERENKOV docs: {topic}", bold=True, fg="blue"))
    click.echo("")
    click.echo(str(entry["summary"]))
    click.echo("")
    click.echo(click.style("Commands:", bold=True))
    for command in entry["commands"]:
        click.echo(f"  $ {command}")
    click.echo("")
    click.echo(click.style("Notes:", bold=True))
    for note in entry["notes"]:
        click.echo(f"  - {note}")
