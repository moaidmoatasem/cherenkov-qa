"""
cherenkov/cli/commands/verify.py — E1.1: `cherenkov verify` UX.

Zero-config entry point: given a spec and a live server URL, runs the
divergence proof and prints a clean human-readable summary.  No LLM
required in the default (offline) mode — making it instantly usable
without an Ollama setup.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from cherenkov.divergence.proof_run import run_proof


@click.command("verify")
@click.option(
    "--url",
    "-u",
    required=True,
    help="Base URL of the live server to probe (e.g. https://petstore3.swagger.io/api/v3)",
)
@click.option(
    "--spec",
    "-s",
    default=None,
    help="Path or URL to the OpenAPI spec JSON/YAML file.  Omit to use the built-in Petstore demo spec.",
)
@click.option(
    "--llm/--offline",
    default=False,
    help="Use the LLM Skeptic for hypothesis generation (requires Ollama).  Default: offline mode (no LLM).",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Write the JSON divergence report to this file.",
)
@click.option(
    "--fail-on-divergence",
    is_flag=True,
    default=False,
    help="Exit with code 1 if any divergences are found (CI gate mode).",
)
def verify_cmd(
    url: str,
    spec: str | None,
    llm: bool,
    output: str | None,
    fail_on_divergence: bool,
) -> None:
    """Verify a live API against its OpenAPI spec -- find spec<->implementation divergences.

    Runs in offline mode by default (no LLM, no Ollama required).  Pass --llm
    to engage the full Skeptic agent for richer hypothesis generation.

    \b
    Examples:
      # Zero-config demo against the public Petstore:
      cherenkov verify --url https://petstore3.swagger.io/api/v3

      # Point at your own service:
      cherenkov verify --url http://localhost:8080 --spec ./openapi.json

      # CI gate: fail if divergences are found:
      cherenkov verify --url http://localhost:8080 --spec ./openapi.json --fail-on-divergence
    """
    spec_dict: dict | None = None
    if spec is not None:
        spec_dict = _load_spec(spec)
        if spec_dict is None:
            sys.exit(2)

    mode_label = "LLM Skeptic" if llm else "offline (no LLM required)"
    click.echo("\nCHERENKOV verify")
    click.echo(f"  Target  : {url}")
    click.echo(f"  Spec    : {spec or 'built-in Petstore demo'}")
    click.echo(f"  Mode    : {mode_label}")
    click.echo("")

    try:
        reports = run_proof(base_url=url, spec=spec_dict, use_llm=llm)
    except Exception as exc:
        click.echo(f"\n[ERROR] Probe failed: {exc}", err=True)
        sys.exit(2)

    _print_summary(reports)

    if output:
        _write_json(reports, output)
        click.echo(f"\nReport written to {output}")

    if fail_on_divergence and reports:
        sys.exit(1)


# ── helpers ────────────────────────────────────────────────────────────────────

def _load_spec(spec_path: str) -> dict | None:
    """Load an OpenAPI spec from a local file path or HTTP URL."""
    import urllib.request

    if spec_path.startswith("http://") or spec_path.startswith("https://"):
        try:
            with urllib.request.urlopen(spec_path, timeout=15) as resp:  # noqa: S310
                raw = resp.read()
        except Exception as exc:
            click.echo(f"[ERROR] Could not fetch spec from {spec_path}: {exc}", err=True)
            return None
    else:
        p = Path(spec_path)
        if not p.exists():
            click.echo(f"[ERROR] Spec file not found: {spec_path}", err=True)
            return None
        raw = p.read_bytes()

    try:
        if spec_path.endswith((".yaml", ".yml")):
            import yaml  # type: ignore[import]
            return yaml.safe_load(raw)
        return json.loads(raw)
    except Exception as exc:
        click.echo(f"[ERROR] Could not parse spec: {exc}", err=True)
        return None


_SEVERITY_COLOUR = {
    "HIGH": "red", "high": "red",
    "MEDIUM": "yellow", "medium": "yellow",
    "LOW": "cyan", "low": "cyan",
}


def _print_summary(reports: list) -> None:
    width = 68
    click.echo("=" * width)
    n = len(reports)
    if n == 0:
        click.echo("  No divergences found.")
    else:
        colour = "red" if n else "green"
        click.echo(click.style(f"  {n} divergence(s) found", fg=colour, bold=True))

    click.echo("=" * width)

    for i, r in enumerate(reports, 1):
        sev = getattr(r, "severity", "MEDIUM")
        if hasattr(sev, "value"):
            sev = sev.value
        sev_str = click.style(f"[{sev.upper()}]", fg=_SEVERITY_COLOUR.get(sev, "white"), bold=True)
        dc = getattr(r, "divergence_class", "")
        if hasattr(dc, "value"):
            dc = dc.value
        ep = getattr(r, "endpoint", "")
        click.echo(f"\n{i}. {sev_str} {dc}  {ep}")
        click.echo(f"   Spec says : {getattr(r, 'claim_a', '')[:100]}")
        click.echo(f"   Actual    : {getattr(r, 'claim_b', '')[:100]}")
        ev = getattr(r, "evidence", None)
        if ev:
            req = getattr(ev, "request_summary", "") or ""
            diff = getattr(ev, "diff", "") or ""
            if req:
                click.echo(f"   Request   : {req}")
            if diff:
                click.echo(f"   Diff      : {diff[:120]}")
        repro = getattr(r, "repro_steps", [])
        if repro:
            click.echo("   Repro:")
            for step in repro[:3]:
                click.echo(f"     {step}")

    click.echo("")


def _write_json(reports: list, path: str) -> None:
    data = []
    for r in reports:
        try:
            data.append(r.model_dump() if hasattr(r, "model_dump") else vars(r))
        except Exception:
            data.append(str(r))
    Path(path).write_text(json.dumps(data, indent=2, default=str))
