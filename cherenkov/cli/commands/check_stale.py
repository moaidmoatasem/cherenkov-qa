"""cherenkov/cli/commands/check_stale.py — `cherenkov check-stale` command."""

import sys
import click


@click.command("check-stale")
@click.option(
    "--spec",
    default=None,
    help="Path to OpenAPI spec. Overrides the spec path stored in the manifest.",
)
@click.option(
    "--manifest",
    default=".cherenkov/test_manifest.json",
    help="Path to the test manifest file [default: .cherenkov/test_manifest.json]",
)
@click.option(
    "--fail-on-stale",
    is_flag=True,
    default=False,
    help="Exit 1 if tests are stale (for CI use).",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON.")
def check_stale_cmd(spec, manifest, fail_on_stale, as_json):
    """Check whether generated tests are stale relative to the spec.

    Reads .cherenkov/test_manifest.json (written by `cherenkov validate` or
    `cherenkov generate`) and compares the stored spec hash against the current
    file content. Flags missing test files too.

    Example:
        cherenkov check-stale --fail-on-stale
        cherenkov check-stale --spec openapi.yaml --json
    """
    from pathlib import Path
    from cherenkov.core.staleness import TestManifest

    m = TestManifest(manifest_path=Path(manifest))

    if spec:
        # Inject the spec override into the manifest for this check only
        data = m.info()
        if not data:
            click.echo(click.style(
                f"No manifest found at {manifest}. Run `cherenkov validate` first.",
                fg="yellow",
            ), err=True)
            sys.exit(1 if fail_on_stale else 0)
        from cherenkov.core.staleness import _file_sha256, StalenessReport
        from pathlib import Path as _Path
        import json as _json
        current_hash = _file_sha256(spec)
        recorded_hash = data.get("spec_hash", "")
        test_files = data.get("tests", [])
        missing = [f for f in test_files if not _Path(f).exists()]
        hash_changed = recorded_hash != current_hash
        stale = hash_changed or bool(missing)
        parts = []
        if hash_changed:
            parts.append(f"spec '{spec}' has changed since tests were generated")
        if missing:
            parts.append(f"{len(missing)} test file(s) missing")
        report = StalenessReport(
            stale=stale,
            spec_path=spec,
            recorded_hash=recorded_hash,
            current_hash=current_hash,
            stale_files=test_files if hash_changed else [],
            missing_files=missing,
            message="; ".join(parts) if parts else "Tests are up to date.",
        )
    else:
        report = m.check()

    if as_json:
        import json
        click.echo(json.dumps({
            "stale": report.stale,
            "spec_path": report.spec_path,
            "recorded_hash": report.recorded_hash[:12] if report.recorded_hash else "",
            "current_hash": report.current_hash[:12] if report.current_hash else "",
            "stale_files": len(report.stale_files),
            "missing_files": report.missing_files,
            "message": report.message,
        }, indent=2))
    else:
        color = "red" if report.stale else "green"
        status = "STALE" if report.stale else "UP TO DATE"
        click.echo(click.style(f"[{status}] {report.message}", fg=color, bold=True))

        if report.stale_files:
            click.echo(f"  {len(report.stale_files)} test file(s) may be stale:")
            for f in report.stale_files[:10]:
                click.echo(f"    - {f}")
            if len(report.stale_files) > 10:
                click.echo(f"    ... and {len(report.stale_files) - 10} more")

        if report.missing_files:
            click.echo(click.style(f"  Missing files:", fg="red"))
            for f in report.missing_files[:10]:
                click.echo(f"    - {f}")

        if report.stale:
            click.echo(click.style(
                "\nRun `cherenkov validate --spec <spec>` to regenerate tests.",
                fg="yellow",
            ))

    if report.stale and fail_on_stale:
        sys.exit(1)
