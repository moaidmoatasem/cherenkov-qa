"""
cherenkov/cli/commands/verify.py — E1.1: `cherenkov verify` UX.

Zero-config entry point: given a spec and a live server URL, runs the
divergence proof and prints a clean human-readable summary.  No LLM
required in the default (offline) mode — making it instantly usable
without an Ollama setup.

--rich-verdict (default on) engages the full multi-agent verdict engine:
  - Divergence Probe  (Skeptic → Witness loop)
  - Mutation Oracle   (proves detection has teeth)
  - Semantic Judge    (LLM-as-judge evidence quality)
  - Traffic Capture   (golden fixtures from real traffic)
  - Spec Coverage     (endpoint gap analysis)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, cast

import click
import httpx

from cherenkov.cli.loaders import load_spec
from cherenkov.divergence.coverage import CoverageReport, compute_coverage
from cherenkov.divergence.health import HealthScore, compute_health_score
from cherenkov.divergence.proof_run import run_proof
from cherenkov.persistence.run_store import RunRecord, get_run_store
from cherenkov.persistence.run_store import spec_hash as _spec_hash

_log = logging.getLogger(__name__)


@click.command("verify")
@click.option(
    "--url",
    "--base-url",
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
    help="Write the divergence report to this file.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "text"], case_sensitive=False),
    default="json",
    help="Report format for --output: json (default) or text.",
)
@click.option(
    "--fail-on-divergence",
    is_flag=True,
    default=False,
    help="Exit with code 1 if any divergences are found (CI gate mode).",
)
@click.option(
    "--coverage-report",
    is_flag=True,
    default=False,
    help="Print a spec coverage-gap report after the proof run (requires --spec).",
)
@click.option(
    "--health-score",
    is_flag=True,
    default=False,
    help="Print an A-F health grade for the proof run (coverage + divergence density; requires --spec).",
)
@click.option(
    "--rich-verdict/--simple",
    default=True,
    help="Run the full multi-agent verdict engine (default: on).  Pass --simple for the legacy summary.",
)
@click.option(
    "--no-mutation-oracle",
    is_flag=True,
    default=False,
    help="Skip the mutation oracle dimension (faster, but less thorough).",
)
@click.option(
    "--no-traffic-capture",
    is_flag=True,
    default=False,
    help="Skip golden-fixture capture from real traffic.",
)
@click.option(
    "--fixture-dir",
    default=".cherenkov/fixtures",
    show_default=True,
    help="Directory for captured golden fixtures.",
)
@click.option(
    "--max-probes",
    default=40,
    show_default=True,
    type=click.IntRange(1, 500),
    help="Maximum spec-derived endpoint probes per run (requires --spec).",
)
@click.option(
    "--identifiers",
    type=click.Path(exists=True),
    default=None,
    help="JSON file mapping path parameters to known valid values.",
)
@click.option(
    "--allow-mutations",
    is_flag=True,
    default=False,
    help="Allow planning of happy-path probes for POST/PUT/DELETE.",
)
def verify_cmd(
    url: str,
    spec: str | None,
    llm: bool,
    output: str | None,
    output_format: str,  # noqa: ARG001
    fail_on_divergence: bool,
    coverage_report: bool,
    health_score: bool,
    rich_verdict: bool,
    no_mutation_oracle: bool,
    no_traffic_capture: bool,
    fixture_dir: str,
    max_probes: int,
    identifiers: str | None,
    allow_mutations: bool,
) -> None:
    """Verify a live API against its OpenAPI spec -- find spec<->implementation divergences.

    Runs in offline mode by default (no LLM, no Ollama required).  Pass --llm
    to engage the full Skeptic agent for richer hypothesis generation.

    By default, the full multi-agent verdict engine runs all 5 dimensions in
    parallel.  Use --simple to fall back to the legacy single-probe summary.

    \b
    Examples:
      # Zero-config demo against the public Petstore:
      cherenkov verify --url https://petstore3.swagger.io/api/v3

      # Point at your own service:
      cherenkov verify --url http://localhost:8080 --spec ./openapi.json

      # CI gate: fail if divergences are found:
      cherenkov verify --url http://localhost:8080 --spec ./openapi.json --fail-on-divergence

      # Fast mode — skip mutation oracle and traffic capture:
      cherenkov verify --url http://localhost:8080 --no-mutation-oracle --no-traffic-capture
    """
    spec_dict: dict | None = None
    if spec is not None:
        spec_dict = load_spec(spec)
        if spec_dict is None:
            sys.exit(2)

    known_identifiers: dict[str, list[str]] | None = None
    if identifiers:
        try:
            with open(identifiers, encoding="utf-8") as f:
                known_identifiers = json.load(f)
        except Exception as exc:
            click.echo(f"[ERROR] Could not load identifiers from {identifiers}: {exc}", err=True)
            sys.exit(2)

    mode_label = "LLM Skeptic" if llm else "offline (no LLM required)"
    click.echo("\nCHERENKOV verify")
    click.echo(f"  Target  : {url}")
    click.echo(f"  Spec    : {spec or 'built-in Petstore demo'}")
    click.echo(f"  Mode    : {mode_label}")
    if rich_verdict:
        click.echo("  Engine  : multi-agent (rich verdict)")
    click.echo("")

    _warn_unprobed(
        spec_dict,
        max_probes=max_probes,
        use_llm=llm,
        known_identifiers=known_identifiers,
        allow_mutations=allow_mutations,
    )

    _assert_reachable(url)

    t_start = time.monotonic()

    if rich_verdict:
        rich, reports, cov = _run_rich_verdict(
            url=url,
            spec_dict=spec_dict,
            spec_source=spec or "built-in",
            llm=llm,
            run_mutation=not no_mutation_oracle,
            run_traffic=not no_traffic_capture,
            fixture_dir=fixture_dir,
            max_probes=max_probes,
            known_identifiers=known_identifiers,
            allow_mutations=allow_mutations,
        )
        duration_ms = int((time.monotonic() - t_start) * 1000)

        # Print the rich verdict card
        click.echo(rich.render())
        click.echo("")

        # Also print per-divergence detail
        if reports:
            _print_summary(reports)

        if coverage_report:
            if spec_dict is not None:
                _print_coverage(cov)
            else:
                click.echo("[WARN] --coverage-report requires --spec; skipping.", err=True)

        if health_score:
            if cov is not None:
                _print_health(compute_health_score(cov))
            else:
                click.echo("[WARN] --health-score requires --spec; skipping.", err=True)

        if output:
            _write_rich_json(rich, reports, output, spec_dict=spec_dict)
            click.echo(f"\nReport written to {output}")

        _persist_run(
            url,
            spec_dict,
            rich.overall.value,
            len(reports),
            rich.coverage_pct,
            duration_ms,
            rich=rich,
        )

        if fail_on_divergence and reports:
            sys.exit(1)

    else:
        # Legacy simple path
        probed_endpoints: list[tuple[str, str]] = []
        try:
            reports = run_proof(
                base_url=url,
                spec=spec_dict,
                use_llm=llm,
                max_probes=max_probes,
                probed_endpoints=probed_endpoints,
                known_identifiers=known_identifiers,
                allow_mutations=allow_mutations,
            )
        except Exception as exc:
            click.echo(f"\n[ERROR] Probe failed: {exc}", err=True)
            sys.exit(2)
        duration_ms = int((time.monotonic() - t_start) * 1000)

        _print_summary(reports)

        cov_report: CoverageReport | None = None
        if coverage_report:
            if spec_dict is None:
                click.echo("[WARN] --coverage-report requires --spec; skipping.", err=True)
            else:
                cov_report = compute_coverage(spec_dict, reports, probed_endpoints=probed_endpoints)
                _print_coverage(cov_report)

        if health_score:
            if spec_dict is None:
                click.echo("[WARN] --health-score requires --spec; skipping.", err=True)
            else:
                cov_report = cov_report or compute_coverage(
                    spec_dict, reports, probed_endpoints=probed_endpoints
                )
                _print_health(compute_health_score(cov_report))

        if output:
            _write_json(reports, output)
            click.echo(f"\nReport written to {output}")

        _persist_run(url, spec_dict, "FAIL" if reports else "PASS", len(reports), None, duration_ms)

        if fail_on_divergence and reports:
            sys.exit(1)


# ── rich verdict runner ────────────────────────────────────────────────────────


def _run_rich_verdict(
    url: str,
    spec_dict: dict | None,
    spec_source: str,
    llm: bool,
    run_mutation: bool,
    run_traffic: bool,
    fixture_dir: str,
    max_probes: int = 40,
    known_identifiers: dict[str, list[str]] | None = None,
    allow_mutations: bool = False,
) -> tuple:
    from cherenkov.divergence.coverage import compute_coverage
    from cherenkov.verdict.engine import VerdictEngine

    engine = VerdictEngine(
        base_url=url,
        spec=spec_dict,
        spec_source=spec_source,
        use_llm=llm,
        run_mutation_oracle=run_mutation,
        run_semantic_judge=True,
        run_traffic_capture=run_traffic,
        fixture_dir=fixture_dir,
        max_probes=max_probes,
        known_identifiers=known_identifiers,
        allow_mutations=allow_mutations,
    )
    try:
        rich = engine.run()
    except Exception as exc:
        click.echo(f"\n[ERROR] Verdict engine failed: {exc}", err=True)
        sys.exit(2)

    # Reuse the probe sweep the engine already ran for detail printing and
    # coverage — re-running run_proof() here used to double every live
    # request against the target and print the same probe sweep twice.
    reports = engine.divergence_reports
    probed_endpoints = getattr(engine, "_probed_endpoints", [])

    cov = None
    if spec_dict is not None:
        try:
            cov = compute_coverage(spec_dict, reports, probed_endpoints=probed_endpoints)
        except Exception:
            _log.debug("coverage computation failed (non-critical)", exc_info=True)

    return rich, reports, cov


# ── helpers ────────────────────────────────────────────────────────────────────


def _persist_run(
    url: str,
    spec_dict: dict | None,
    verdict_str: str,
    divergence_count: int,
    coverage_pct: float | None,
    duration_ms: int,
    rich: object | None = None,
) -> None:
    try:
        meta: dict = {}
        if rich is not None:
            try:
                meta["rich_verdict"] = rich.model_dump() if hasattr(rich, "model_dump") else {}  # type: ignore[union-attr]
            except Exception:
                _log.debug("rich verdict serialization failed", exc_info=True)
        record = RunRecord(
            command="verify",
            target_url=url,
            spec_hash=_spec_hash(json.dumps(spec_dict, sort_keys=True).encode())
            if spec_dict
            else "",
            verdict=cast(Any, verdict_str),
            divergence_count=divergence_count,
            coverage_pct=coverage_pct,
            duration_ms=duration_ms,
            meta_json=json.dumps(meta, default=str),
        )
        saved = get_run_store().save(record)
        click.echo(f"  Run ID: {saved.run_id}", err=True)
    except Exception:
        _log.debug("run record persist failed (non-critical)", exc_info=True)


def _assert_reachable(url: str) -> None:
    """Fail fast if the target is not reachable.

    A down or wrong-address target must not be scored — otherwise every probe
    fails identically, yields zero divergences, and the run exits 0, silently
    reporting an outage as a clean pass. Any HTTP response (even 4xx/5xx) counts
    as reachable; only connection-level failures abort.
    """
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            client.get(url)
    except httpx.HTTPError as exc:
        click.echo(
            f"[ERROR] Target {url} is not reachable: {type(exc).__name__}. "
            "Aborting — a target that cannot be contacted cannot be verified.",
            err=True,
        )
        sys.exit(2)


def _warn_unprobed(
    spec_dict: dict | None,
    max_probes: int,
    use_llm: bool,
    limit: int = 10,
    known_identifiers: dict[str, list[str]] | None = None,
    allow_mutations: bool = False,
) -> None:
    """Tell the user which endpoints will not be probed, and why.

    A zero-probe endpoint produces zero divergences, which is indistinguishable
    from a conformant one: the run exits 0 and the user believes it was checked.
    Silence here is how a PathItem-level `parameters` declaration removed an
    endpoint from coverage entirely without anyone noticing.

    Advisory, not fatal — an unprobeable endpoint is often a legitimately
    under-specified one, and only the user can judge whether it matters.
    """
    if spec_dict is None:
        return
    from cherenkov.divergence.probe_planner import unprobed_endpoints

    missing = unprobed_endpoints(
        spec_dict,
        max_probes=max_probes,
        include_bare=use_llm,
        known_identifiers=known_identifiers,
        allow_mutations=allow_mutations,
    )
    if not missing:
        return

    click.echo(f"  [WARN] {len(missing)} endpoint(s) will NOT be probed:", err=True)
    for item in missing[:limit]:
        click.echo(f"         {item}", err=True)
    if len(missing) > limit:
        click.echo(f"         ... and {len(missing) - limit} more", err=True)
    click.echo(
        "         These contribute no divergences, so a clean result does not " "cover them.",
        err=True,
    )
    click.echo("", err=True)


_SEVERITY_COLOUR = {
    "HIGH": "red",
    "high": "red",
    "MEDIUM": "yellow",
    "medium": "yellow",
    "LOW": "cyan",
    "low": "cyan",
    "CRITICAL": "red",
    "critical": "red",
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


def _write_rich_json(rich: object, reports: list, path: str, spec_dict: dict | None = None) -> None:
    data: dict = {}
    try:
        data["rich_verdict"] = rich.model_dump() if hasattr(rich, "model_dump") else vars(rich)  # type: ignore[union-attr]
    except Exception:
        data["rich_verdict"] = str(rich)
    data["divergences"] = []
    for r in reports:
        try:
            data["divergences"].append(r.model_dump() if hasattr(r, "model_dump") else vars(r))
        except Exception:
            data["divergences"].append(str(r))
    total = len(spec_dict.get("paths", {})) if spec_dict else max(1, len(reports))
    passed = max(0, total - len(reports))
    data["total"] = total
    data["passed"] = passed
    data["pass_rate"] = passed / total if total > 0 else 1.0
    Path(path).write_text(json.dumps(data, indent=2, default=str))


def _print_coverage(cov: CoverageReport) -> None:
    width = 68
    click.echo("\n" + "─" * width)
    pct = cov.coverage_pct
    colour = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"
    click.echo(
        "  Spec coverage: "
        + click.style(f"{pct:.1f}%", fg=colour, bold=True)
        + f"  ({cov.tested_count}/{cov.total_endpoints} endpoints probed)"
    )
    if cov.gap_endpoints:
        click.echo(f"\n  Gap — {cov.untested_count} endpoint(s) NOT probed:")
        for ep in cov.gap_endpoints:
            op = f"  [{ep.operation_id}]" if ep.operation_id else ""
            click.echo(f"    {ep.method:<7} {ep.path}{op}")
    else:
        click.echo("  All spec endpoints were probed.")
    if cov.tested_endpoints:
        click.echo(f"\n  Probed — {cov.tested_count} endpoint(s):")
        for ep in cov.tested_endpoints:
            div_tag = f"  ({ep.divergence_count} divergence(s))" if ep.divergence_count else ""
            click.echo(f"    {ep.method:<7} {ep.path}{div_tag}")
    click.echo("─" * width + "\n")


def _print_health(health: HealthScore) -> None:
    width = 68
    colour = {"A": "green", "B": "green", "C": "yellow", "D": "red", "F": "red"}.get(
        health.grade, "white"
    )
    click.echo("\n" + "─" * width)
    click.echo(
        "  Health grade: "
        + click.style(f"{health.grade}", fg=colour, bold=True)
        + f"  ({health.score:.1f}/100)"
    )
    click.echo(
        f"    coverage {health.coverage_component:.1f}  ·  "
        f"integrity {health.integrity_component:.1f}  ·  "
        f"divergence {health.divergence_component:.1f}"
    )
    for d in health.deductions:
        click.echo(f"    {d}")
    click.echo("─" * width + "\n")
