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
            "The repair loop is gated on the meaningful-assertion check: a test that "
            "cannot fail a synthesized spec regression does not pass the gate.",
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
            "Needs a reachable target: verify aborts with exit 2 on connection failure "
            "rather than reporting an outage as a clean run.",
            "Coverage counts endpoints actually probed, so a clean target does not read "
            "as untested.",
            "An endpoint whose path parameters cannot be filled is reported, not skipped silently.",
        ],
    },
    "check-suite": {
        "summary": "Catch a test suite that passes without proving anything.",
        "commands": [
            "cherenkov check-suite --candidate tests/suite.py --baseline known_good.py",
            "cherenkov check-suite --candidate tests/suite.py --baseline known_good.py --fail-on-finding",
            "cherenkov audit --target URL --spec openapi.yaml --test-cmd \"pytest tests/\"",
        ],
        "notes": [
            "Detects WEAKENED, DELETED and HALLUCINATED assertions — the three ways an "
            "AI-written suite goes green while the system is broken.",
            "This is the check no other test tool runs. If you only wire one gate into "
            "CI, wire this one.",
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
            "The certificate format is an open spec (docs/specs/CHERENKOV_CERTIFICATE.md), "
            "not a proprietary artifact.",
            "`--compliance` maps the result onto ISO/IEC 42001, the OWASP AI Testing Guide "
            "and the OWASP LLM Top 10.",
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
            "This is a supported exit, not a packaging step. Zero lock-in is an invariant: "
            "ejected output contains no `cherenkov` import and runs on vanilla Playwright.",
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
            "Teardown runs on success, failure and exception, and reports failures rather "
            "than swallowing them.",
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
            "The tool list in manifest.json is generated from handlers.TOOLS; regenerate "
            "with scripts/gen_manifest.py rather than editing it by hand.",
            "`agent init` is the faster path for a coding agent: it installs the skills "
            "and writes a discovery block into AGENTS.md.",
        ],
    },
    "ci": {
        "summary": "Run CHERENKOV as a gate in a pipeline.",
        "commands": [
            "cherenkov validate --target URL --spec openapi.yaml --fail-on-drift --quiet",
            "cherenkov check-suite --candidate tests/suite.py --baseline known_good.py --fail-on-finding",
            "cherenkov validate --target URL --spec openapi.yaml --json",
        ],
        "notes": [
            "A GitHub Action ships in action.yml.",
            "Use --json for anything a script or agent has to read; exit codes are stable, "
            "human text is not.",
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
            "Run once per repository. It installs the public skills and writes a "
            "CHERENKOV block into AGENTS.md, so an agent with no prior context can "
            "find the tool.",
            "It is idempotent: re-running replaces the block rather than appending.",
            "Nothing is sent anywhere. Both steps are local file operations plus an "
            "optional `npx skills add`.",
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
