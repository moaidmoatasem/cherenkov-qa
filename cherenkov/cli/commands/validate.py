import click
import os
import json
import sys
from pathlib import Path as _Path

from cherenkov.execution.validate import ValidationEngine


@click.command("validate")
@click.option("--target", "-t", required=True, help="The real server target base URL")
@click.option(
    "--source",
    type=click.Choice(["openapi", "graphql", "grpc", "accessibility"]),
    default="openapi",
    help="Source type for ingestion",
)
@click.option(
    "--format",
    type=click.Choice(["json", "text", "sarif", "html", "junit", "allure"]),
    default=None,
    help="Output report format",
)
@click.option(
    "--workers",
    type=int,
    default=1,
    help="Number of parallel workers for Playwright tests",
)
@click.option(
    "--no-html", is_flag=True, help="Disable automatic HTML report generation"
)
@click.option(
    "--no-cache", is_flag=True, help="Disable incremental test generation cache"
)
@click.option("--spec", help="Path to OpenAPI spec (JSON/YAML) — legacy compat")
@click.option(
    "--output",
    default=".cherenkov/report",
    help="Output path (extension inferred from --format if not given)",
)
@click.option(
    "--fail-on-drift",
    "fail_on_drift",
    is_flag=True,
    default=False,
    help="Exit with code 1 if any conformance violations are found (CI gate mode)",
)
@click.option(
    "--json-summary",
    "json_summary",
    default=None,
    help="Write a machine-readable JSON summary to this path (used by CI integrations)",
)
@click.option("--json", "json_out", is_flag=True, help="Output purely JSON to stdout")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
def validate_cmd(target, source, format, workers, no_html, no_cache, spec, output, fail_on_drift, json_summary, json_out, quiet):
    """Validate E2E test suite against a real server"""
    from cherenkov.core.errors import ExitCode
    
    if spec == "-":
        stdin_content = sys.stdin.read()
        os.makedirs(".cherenkov", exist_ok=True)
        spec = ".cherenkov/stdin_spec.yaml"
        with open(spec, "w", encoding="utf-8") as f:
            f.write(stdin_content)
            
    if no_cache:
        from cherenkov.cache.endpoint_cache import EndpointCache

        EndpointCache().clear()

    # Pre-ingest spec validation for OpenAPI specs
    if source == "openapi" and spec:
        from cherenkov.truth.spec_validator import validate_spec, Severity

        result = validate_spec(spec)
        for issue in result.issues:
            color = "red" if issue.severity == Severity.ERROR else "yellow"
            prefix = "error" if issue.severity == Severity.ERROR else "warn"
            loc = f" [{issue.location}]" if issue.location else ""
            click.echo(click.style(f"  {prefix}: {issue.message}{loc}", fg=color), err=True)
        if not result.ok:
            if json_out:
                click.echo(json.dumps({"status": "error", "message": "Spec validation failed", "issues": [str(i) for i in result.issues]}))
            else:
                click.echo(click.style(f"Spec validation failed: {spec}", fg="red", bold=True), err=True)
            sys.exit(ExitCode.VALIDATION_ERROR.value)
        if result.issues:
            click.echo(click.style(
                f"Spec OK with {len(result.warnings)} warning(s) — proceeding.", fg="yellow"
            ))

    if source == "graphql":
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        if not spec:
            click.echo(click.style("Error: --spec is required for --source graphql", fg="red"), err=True)
            sys.exit(1)
        click.echo(f"Ingesting GraphQL SDL: {spec}")
        gql_source = GraphQLSourceAdapter(spec)
        scenarios = GraphQLScenarioPlanner().plan(gql_source)
        click.echo(f"Planned {len(scenarios)} scenarios from {len(set(s.operation_name for s in scenarios))} operations")
        generator = GenerateStage("cli_validate")
        generated = 0
        for sc in scenarios:
            try:
                generator.run(scenario=sc, source_type="graphql")
                generated += 1
            except Exception as e:
                click.echo(click.style(f"  warn: skipped {sc.operation_name}/{sc.scenario_type}: {e}", fg="yellow"), err=True)
        click.echo(f"Generated {generated}/{len(scenarios)} test files")
    elif source == "grpc":
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        if not spec:
            click.echo(click.style("Error: --spec is required for --source grpc", fg="red"), err=True)
            sys.exit(1)
        
        # If spec does not end in .proto and looks like a buf module, fetch it
        if not spec.endswith(".proto") and "/" in spec:
            from cherenkov.validate.buf_registry import BufRegistryClient
            click.echo(f"Fetching gRPC proto from Buf Schema Registry: {spec}")
            buf_client = BufRegistryClient()
            proto_content = buf_client.fetch_proto_content(spec)
            if proto_content is None:
                click.echo(click.style(f"Error: failed to fetch from Buf Schema Registry: {spec}", fg="red"), err=True)
                sys.exit(1)
            
            import tempfile
            fd, temp_spec = tempfile.mkstemp(suffix=".proto")
            with os.fdopen(fd, "w") as f:
                f.write(proto_content)
            spec = temp_spec
            click.echo(f"Ingesting fetched gRPC proto.")
        else:
            click.echo(f"Ingesting gRPC proto: {spec}")
            
        grpc_source = gRPCSourceAdapter(spec)
        scenarios = gRPCScenarioPlanner().plan(grpc_source)
        click.echo(f"Planned {len(scenarios)} scenarios from {len(set(s.service for s in scenarios))} services")
        generator = GenerateStage("cli_validate")
        generated = 0
        for sc in scenarios:
            try:
                generator.run(scenario=sc, source_type="grpc")
                generated += 1
            except Exception as e:
                click.echo(click.style(f"  warn: skipped {sc.service}/{sc.rpc_name}: {e}", fg="yellow"), err=True)
        click.echo(f"Generated {generated}/{len(scenarios)} test files")
    elif source == "accessibility":
        from cherenkov.sources.accessibility.adapter import AccessibilitySourceAdapter
        from cherenkov.stages.plan_accessibility import AccessibilityScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        a11y_source = AccessibilitySourceAdapter(spec)
        scenarios = AccessibilityScenarioPlanner().plan(a11y_source)
        click.echo(f"Planned {len(scenarios)} accessibility scenarios")
        generator = GenerateStage("cli_validate")
        for sc in scenarios:
            generator.run(scenario=sc, source_type="accessibility")

    # Record manifest so `cherenkov check-stale` can detect spec drift later
    if source == "openapi" and spec:
        import glob as _glob
        from cherenkov.core.staleness import TestManifest

        tests_dir = str(_Path(__file__).parent.parent.parent.parent / "stub" / "generated_tests")
        test_files = _glob.glob(os.path.join(tests_dir, "*.spec.ts"))
        TestManifest().record(spec_path=spec, test_files=test_files)

    # The engine handles the heavy lifting
    click.echo(f"\nRunning tests against {target} ...")
    engine = ValidationEngine("cli_validate")
    results = engine.validate_suite(target, workers=workers)

    # Always print a human-readable summary so every source type gets output
    _reports = results.get("reports", [])
    _passed = sum(1 for r in _reports if r.get("passed", False))
    _total = len(_reports)
    _status_color = "green" if _passed == _total else ("yellow" if _passed > 0 else "red")
    click.echo(click.style(
        f"\nResults: {_passed}/{_total} passed  [{results.get('status', 'done').upper()}]",
        fg=_status_color,
        bold=True,
    ))
    for r in _reports:
        if not r.get("passed", False):
            click.echo(f"  FAIL  {r.get('scenario_id', '?')}  {r.get('error', '')[:120]}")

    if format == "sarif":
        from cherenkov.execution.emitters.sarif import SARIFEmitter

        os.makedirs(".cherenkov", exist_ok=True)
        emitter = SARIFEmitter()
        from types import SimpleNamespace
        from cherenkov.core.contracts import DivergenceFinding

        report_obj = SimpleNamespace(findings=[])
        for r in results.get("reports", []):
            if not r.get("passed", False):
                report_obj.findings.append(
                    DivergenceFinding(
                        violation_type="conformance-drift",
                        endpoint=r.get("scenario_id", "unknown"),
                        http_method="ANY",
                        expected="Valid response",
                        actual=r.get("error", ""),
                        summary="Response drift detected",
                        description=f"Error: {r.get('error', '')}",
                        severity="high",
                        remediation="Update API or spec",
                    )
                )
        sarif_data = emitter.emit(report_obj, spec or "openapi.yaml")
        out_path = output if output.endswith(".sarif") else output + ".sarif"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sarif_data, f, indent=2)
        print(f"SARIF report written to {out_path}")

    elif format == "junit":
        from cherenkov.execution.emitters.junit import JUnitEmitter

        os.makedirs(".cherenkov", exist_ok=True)
        emitter = JUnitEmitter()
        reports = results.get("reports", [])
        out_path = output if output.endswith(".xml") else output + ".xml"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(emitter.emit(reports))
        print(f"JUnit XML report written to {out_path}")

    # Write machine-readable JSON summary (consumed by CI integrations, action.yml)
    if json_summary:
        os.makedirs(os.path.dirname(json_summary) if os.path.dirname(json_summary) else ".", exist_ok=True)
        reports = results.get("reports", [])
        violations = [r for r in reports if not r.get("passed", True)]
        summary = {
            "violation_count": len(violations),
            "total_tests": len(reports),
            "passed": len(reports) - len(violations),
            "drift_detected": len(violations) > 0,
            "status": results.get("status", "unknown"),
        }
        with open(json_summary, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

    # Determine exit code
    reports = results.get("reports", [])
    has_violations = any(not r.get("passed", True) for r in reports)

    if fail_on_drift and has_violations:
        violation_count = sum(1 for r in reports if not r.get("passed", True))
        click.echo(
            click.style(
                f"\n❌ {violation_count} conformance violation(s) detected. Exiting 1 (--fail-on-drift).",
                fg="red",
            )
        )
        sys.exit(1)
