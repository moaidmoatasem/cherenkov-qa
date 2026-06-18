import click
import os
import json
import sys

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
def validate_cmd(target, source, format, workers, no_html, no_cache, spec, output, fail_on_drift, json_summary):
    """Validate E2E test suite against a real server"""
    if no_cache:
        from cherenkov.cache.endpoint_cache import EndpointCache

        EndpointCache().clear()

    if source == "graphql":
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        gql_source = GraphQLSourceAdapter(spec)
        scenarios = GraphQLScenarioPlanner().plan(gql_source)
        for sc in scenarios:
            GenerateStage("cli_validate").run(scenario=sc, source_type="graphql")
    elif source == "grpc":
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        grpc_source = gRPCSourceAdapter(spec)
        scenarios = gRPCScenarioPlanner().plan(grpc_source)
        for sc in scenarios:
            GenerateStage("cli_validate").run(scenario=sc, source_type="grpc")
    elif source == "accessibility":
        from cherenkov.sources.accessibility.adapter import AccessibilitySourceAdapter
        from cherenkov.stages.plan_accessibility import AccessibilityScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        a11y_source = AccessibilitySourceAdapter(spec)
        scenarios = AccessibilityScenarioPlanner().plan(a11y_source)
        for sc in scenarios:
            GenerateStage("cli_validate").run(scenario=sc, source_type="accessibility")

    # The engine handles the heavy lifting
    engine = ValidationEngine("cli_validate")
    results = engine.validate_suite(target, workers=workers)

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
        with open(out_path, "w") as f:
            json.dump(sarif_data, f, indent=2)
        print(f"SARIF report written to {out_path}")

    elif format == "junit":
        from cherenkov.execution.emitters.junit import JUnitEmitter

        os.makedirs(".cherenkov", exist_ok=True)
        emitter = JUnitEmitter()
        reports = results.get("reports", [])
        out_path = output if output.endswith(".xml") else output + ".xml"
        with open(out_path, "w") as f:
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
        with open(json_summary, "w") as f:
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
