import click
import os
import json
import sys

from cherenkov.execution.validate import ValidationEngine

@click.command('validate')
@click.option('--target', '-t', required=True, help='The real server target base URL')
@click.option('--source', type=click.Choice(['openapi', 'graphql', 'grpc', 'accessibility']), default='openapi', help='Source type for ingestion')
@click.option('--format', type=click.Choice(['json', 'text', 'sarif', 'html', 'junit', 'allure']), default=None, help='Output report format')
@click.option('--workers', type=int, default=1, help='Number of parallel workers for Playwright tests')
@click.option('--no-html', is_flag=True, help='Disable automatic HTML report generation')
@click.option('--no-cache', is_flag=True, help='Disable incremental test generation cache')
@click.option('--spec', help='Path to OpenAPI spec (JSON/YAML) — legacy compat')
@click.option('--output', default='.cherenkov/report', help='Output path (extension inferred from --format if not given)')
def validate_cmd(target, source, format, workers, no_html, no_cache, spec, output):
    """Validate E2E test suite against a real server"""
    if no_cache:
        from cherenkov.cache.endpoint_cache import EndpointCache
        EndpointCache().clear()

    if source == 'graphql':
        from cherenkov.sources.graphql.adapter import GraphQLSourceAdapter
        from cherenkov.stages.plan_graphql import GraphQLScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        gql_source = GraphQLSourceAdapter(spec)
        scenarios = GraphQLScenarioPlanner().plan(gql_source)
        for sc in scenarios:
            GenerateStage('cli_validate').run(scenario=sc, source_type='graphql')
    elif source == 'grpc':
        from cherenkov.sources.grpc.adapter import gRPCSourceAdapter
        from cherenkov.stages.plan_grpc import gRPCScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        grpc_source = gRPCSourceAdapter(spec)
        scenarios = gRPCScenarioPlanner().plan(grpc_source)
        for sc in scenarios:
            GenerateStage('cli_validate').run(scenario=sc, source_type='grpc')
    elif source == 'accessibility':
        from cherenkov.sources.accessibility.adapter import AccessibilitySourceAdapter
        from cherenkov.stages.plan_accessibility import AccessibilityScenarioPlanner
        from cherenkov.stages.generate import GenerateStage

        a11y_source = AccessibilitySourceAdapter(spec)
        scenarios = AccessibilityScenarioPlanner().plan(a11y_source)
        for sc in scenarios:
            GenerateStage('cli_validate').run(scenario=sc, source_type='accessibility')

    # The engine handles the heavy lifting
    engine = ValidationEngine('cli_validate')
    results = engine.validate_suite(target, workers=workers)

    if format == 'sarif':
        from cherenkov.execution.emitters.sarif import SARIFEmitter
        os.makedirs('.cherenkov', exist_ok=True)
        emitter = SARIFEmitter()
        from types import SimpleNamespace
        from cherenkov.core.contracts import DivergenceFinding
        report_obj = SimpleNamespace(findings=[])
        for r in results.get('reports', []):
            if not r.get('passed', False):
                report_obj.findings.append(DivergenceFinding(
                    violation_type='conformance-drift',
                    endpoint=r.get('scenario_id', 'unknown'),
                    http_method='ANY',
                    expected='Valid response',
                    actual=r.get('error', ''),
                    summary='Response drift detected',
                    description=f"Error: {r.get('error', '')}",
                    severity='high',
                    remediation='Update API or spec'
                ))
        sarif_data = emitter.emit(report_obj, spec or 'openapi.yaml')
        out_path = output if output.endswith('.sarif') else output + '.sarif'
        with open(out_path, 'w') as f:
            json.dump(sarif_data, f, indent=2)
        print(f"SARIF report written to {out_path}")
        sys.exit(0 if results.get('status') != 'empty' and all(r.get('passed', False) for r in results.get('reports', [])) else 1)
