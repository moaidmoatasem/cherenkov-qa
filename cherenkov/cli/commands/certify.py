"""
cherenkov/cli/commands/certify.py — E3.2: `cherenkov certify`.

Runs the divergence proof and issues a signed VerificationCertificate.
Zero external dependencies in offline mode.

Examples:
  # Zero-config demo:
  cherenkov certify

  # Point at your own service:
  cherenkov certify --url http://localhost:8080 --spec ./openapi.json

  # CI gate (exit 1 if FAIL):
  cherenkov certify --url http://localhost:8080 --fail-on-fail --output cert.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from cherenkov.core.certificate import compliance_profile, issue_certificate, load_certificate
from cherenkov.divergence.coverage import compute_coverage, CoverageReport
from cherenkov.divergence.proof_run import PETSTORE_BASE_URL, run_proof


_VERDICT_COLOUR = {"PASS": "green", "WARN": "yellow", "FAIL": "red"}


@click.command("certify")
@click.option(
    "--url", "-u", default=None,
    help="Base URL of the live server.  Defaults to public Petstore demo.",
)
@click.option(
    "--spec", "-s", default=None,
    help="Path or URL to the OpenAPI spec JSON/YAML.  Omit for built-in Petstore spec.",
)
@click.option(
    "--llm/--offline", default=False,
    help="Use the LLM Skeptic (requires Ollama).  Default: offline.",
)
@click.option(
    "--output", "-o", default=None,
    help="Write the JSON certificate to this file.",
)
@click.option(
    "--signing-key", default=None, envvar="CHERENKOV_CERT_KEY",
    help="Hex-encoded 32-byte signing key.  Also read from CHERENKOV_CERT_KEY env var.",
)
@click.option(
    "--fail-on-fail", is_flag=True, default=False,
    help="Exit with code 1 if the certificate verdict is FAIL (CI gate mode).",
)
@click.option(
    "--verify", "verify_file", default=None,
    help="Verify an existing certificate file rather than running a new proof.",
)
@click.option(
    "--compliance", is_flag=True, default=False,
    help="Print the compliance evidence mapping (EU AI Act / SOC 2 / ISO 25010) after issuing.",
)
@click.option(
    "--coverage-report", "coverage_report", is_flag=True, default=False,
    help="Print a spec coverage-gap report showing which endpoints were probed (requires --spec).",
)
def certify_cmd(
    url: str | None,
    spec: str | None,
    llm: bool,
    output: str | None,
    signing_key: str | None,
    fail_on_fail: bool,
    verify_file: str | None,
    compliance: bool,
    coverage_report: bool,
) -> None:
    """Issue a signed verification certificate for a live API.

    \b
    The certificate carries:
      · a SHA-256 fingerprint of all fields (tamper-evident offline)
      · an optional HMAC-SHA256 signature when --signing-key is provided
      · a human-readable verdict (PASS / WARN / FAIL)

    \b
    Verdict rules:
      PASS  — zero divergences
      WARN  — only MEDIUM/LOW divergences found
      FAIL  — at least one HIGH or CRITICAL divergence

    \b
    Examples:
      cherenkov certify
      cherenkov certify --url http://localhost:8080 --output cert.json
      cherenkov certify --verify cert.json
    """
    # ── verify-only mode ────────────────────────────────────────────────────────
    if verify_file:
        _verify_cert_file(verify_file, signing_key)
        return

    # ── proof run ───────────────────────────────────────────────────────────────
    using_demo = url is None
    effective_url = url or PETSTORE_BASE_URL

    spec_dict: dict | None = None
    if spec is not None:
        spec_dict = _load_spec(spec)
        if spec_dict is None:
            sys.exit(2)

    key_bytes: bytes | None = None
    if signing_key:
        try:
            key_bytes = bytes.fromhex(signing_key)
        except ValueError:
            click.echo("[ERROR] --signing-key must be a hex string.", err=True)
            sys.exit(2)

    click.echo("\nCHERENKOV certify")
    if using_demo:
        click.echo(click.style(
            "  (demo mode — no --url given, probing public Petstore)", fg="yellow"
        ))
    click.echo(f"  Target  : {effective_url}")
    click.echo(f"  Spec    : {spec or 'built-in Petstore demo'}")
    click.echo(f"  Mode    : {'LLM Skeptic' if llm else 'offline (no LLM required)'}")
    click.echo("")

    try:
        reports = run_proof(base_url=effective_url, spec=spec_dict, use_llm=llm)
    except Exception as exc:
        click.echo(f"\n[ERROR] Proof run failed: {exc}", err=True)
        sys.exit(2)

    cert = issue_certificate(
        reports=reports,
        base_url=effective_url,
        spec=spec_dict,
        signing_key=key_bytes,
    )

    _print_certificate(cert)

    if compliance:
        _print_compliance(cert)

    if coverage_report:
        if spec_dict is None:
            click.echo(
                "[WARN] --coverage-report requires --spec; skipping coverage output.",
                err=True,
            )
        else:
            from cherenkov.cli.commands.verify import _print_coverage
            cov = compute_coverage(spec_dict, reports)
            _print_coverage(cov)

    if output:
        Path(output).write_text(
            json.dumps(cert.model_dump(), indent=2, default=str)
        )
        click.echo(f"\nCertificate written to {output}")

    if fail_on_fail and cert.verdict == "FAIL":
        sys.exit(1)


# ── helpers ────────────────────────────────────────────────────────────────────

def _print_certificate(cert) -> None:
    width = 68
    verdict_colour = _VERDICT_COLOUR.get(cert.verdict, "white")
    verdict_label = click.style(cert.verdict, fg=verdict_colour, bold=True)

    click.echo("=" * width)
    click.echo(f"  CHERENKOV Certificate  [{verdict_label}]")
    click.echo("=" * width)
    click.echo(f"  ID        : {cert.cert_id}")
    click.echo(f"  Issued    : {cert.issued_at}")
    click.echo(f"  Subject   : {cert.subject.base_url}")
    click.echo(f"  Divergences: {cert.summary.total}"
               f"  (HIGH={cert.summary.high}"
               f"  MEDIUM={cert.summary.medium}"
               f"  LOW={cert.summary.low})")
    fp_short = cert.fingerprint[:16] + "..." if len(cert.fingerprint) > 16 else cert.fingerprint
    click.echo(f"  Fingerprint: {fp_short}")
    if cert.signature:
        sig_short = cert.signature[:16] + "..."
        click.echo(f"  Signature  : {sig_short}")
    click.echo("=" * width)
    click.echo("")


def _print_compliance(cert) -> None:
    width = 68
    click.echo("\n" + "─" * width)
    click.echo("  Compliance evidence mapping (E3.5)")
    click.echo("─" * width)
    for item in compliance_profile(cert):
        click.echo(f"\n  [{item.framework}] {item.provision} — {item.title}")
        click.echo(f"    Fields  : {', '.join(item.cert_fields)}")
        click.echo(f"    Evidence: {item.evidence}")
        if item.caveat:
            click.echo(f"    Caveat  : {item.caveat}")
    click.echo("─" * width + "\n")


def _verify_cert_file(path: str, signing_key: str | None) -> None:
    p = Path(path)
    if not p.exists():
        click.echo(f"[ERROR] Certificate file not found: {path}", err=True)
        sys.exit(2)
    try:
        data = json.loads(p.read_text())
        cert = load_certificate(data)
    except Exception as exc:
        click.echo(f"[ERROR] Could not parse certificate: {exc}", err=True)
        sys.exit(2)

    key_bytes: bytes | None = None
    if signing_key:
        try:
            key_bytes = bytes.fromhex(signing_key)
        except ValueError:
            click.echo("[ERROR] --signing-key must be a hex string.", err=True)
            sys.exit(2)

    valid = cert.verify(signing_key=key_bytes)
    verdict_colour = _VERDICT_COLOUR.get(cert.verdict, "white")
    click.echo(f"\nCHERENKOV Certificate — {path}")
    click.echo(f"  Verdict     : {click.style(cert.verdict, fg=verdict_colour, bold=True)}")
    click.echo(f"  Issued      : {cert.issued_at}")
    click.echo(f"  Subject     : {cert.subject.base_url}")
    integrity = click.style("VALID", fg="green", bold=True) if valid else click.style("TAMPERED", fg="red", bold=True)
    click.echo(f"  Integrity   : {integrity}")
    if not valid:
        sys.exit(3)


def _load_spec(spec_path: str) -> dict | None:
    import urllib.request

    if spec_path.startswith("http://") or spec_path.startswith("https://"):
        try:
            with urllib.request.urlopen(spec_path, timeout=15) as resp:  # noqa: S310
                raw = resp.read()
        except Exception as exc:
            click.echo(f"[ERROR] Could not fetch spec: {exc}", err=True)
            return None
    else:
        p = Path(spec_path)
        if not p.exists():
            click.echo(f"[ERROR] Spec file not found: {spec_path}", err=True)
            return None
        raw = p.read_bytes()

    try:
        if spec_path.endswith((".yaml", ".yml")):
            import yaml
            return yaml.safe_load(raw)
        return json.loads(raw)
    except Exception as exc:
        click.echo(f"[ERROR] Could not parse spec: {exc}", err=True)
        return None
