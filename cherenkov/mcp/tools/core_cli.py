"""
cherenkov/mcp/tools/core_cli.py
MCP tools for core CLI commands: check-suite, verify, and generate.
"""
from __future__ import annotations

import json
import os
import io
import contextlib
import sys
from pathlib import Path
from typing import Any, Callable

from cherenkov.mcp.contracts import CheckSuiteInput, VerifyInput, GenerateInput

def handle_check_suite(params: dict[str, Any]) -> dict[str, Any]:
    """MCP handler for cherenkov/check-suite tool.

    Args:
        params (dict[str, Any]): Dictionary of input parameters matching CheckSuiteInput schema.

    Returns:
        dict[str, Any]: Dictionary containing findings list and verdict string.
    """
    input_model = CheckSuiteInput.model_validate(params)
    
    from cherenkov.cli.commands.check_suite import check_integrity, _check_typescript
    
    baseline = input_model.baseline_inline
    if not baseline and input_model.baseline_path:
        baseline = Path(input_model.baseline_path).read_text(encoding="utf-8")
        
    candidate = input_model.candidate_inline
    if not candidate and input_model.candidate_path:
        candidate = Path(input_model.candidate_path).read_text(encoding="utf-8")
        
    if not candidate:
        return {"error": "Must provide either candidate_inline or candidate_path", "verdict": "fail"}
        
    spec_path_obj = Path(input_model.spec_path) if input_model.spec_path else None
    
    findings = []
    is_ts = False
    if input_model.candidate_path and input_model.candidate_path.endswith(".ts"):
        is_ts = True
    elif candidate and "expect(" in candidate and (".ts" not in str(input_model.candidate_path or "")):
        is_ts = True
        
    if is_ts:
        if baseline:
            findings.extend(_check_typescript(spec_path_obj, baseline, candidate))
    else:
        findings.extend(check_integrity(spec_path_obj, baseline or "", candidate))
        
    if findings and input_model.fail_on_finding:
        return {"findings": findings, "verdict": "fail"}
        
    return {"findings": findings, "verdict": "pass" if not findings else "weakened"}


def handle_verify(params: dict[str, Any]) -> dict[str, Any]:
    """MCP handler for cherenkov/verify tool.

    Args:
        params (dict[str, Any]): Dictionary of input parameters matching VerifyInput schema.

    Returns:
        dict[str, Any]: Dictionary containing verification doc payload and stdout log.
    """
    input_model = VerifyInput.model_validate(params)
    
    from cherenkov.cli.commands.verify import _verify_impl
    
    doc_sink: dict = {}
    
    try:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            _verify_impl(
                url=input_model.base_url,
                spec=input_model.spec_source,
                llm=input_model.use_llm,
                output=None,
                output_format="json",
                fail_on_divergence=False,
                coverage_report=input_model.coverage_report,
                health_score=input_model.health_score,
                rich_verdict=False,
                no_mutation_oracle=not input_model.allow_mutations,
                no_traffic_capture=True,
                fixture_dir="",
                max_probes=input_model.max_probes,
                identifiers=input_model.identifiers,
                allow_mutations=input_model.allow_mutations,
                doc_sink=doc_sink
            )
    except SystemExit:
        pass
    except Exception as e:
        return {"error": str(e), "doc": None}
        
    return {"doc": doc_sink.get("doc", {}), "log": buffer.getvalue()}


def handle_generate(params: dict[str, Any]) -> dict[str, Any]:
    """MCP handler for cherenkov/generate tool.

    Args:
        params (dict[str, Any]): Dictionary of input parameters matching GenerateInput schema.

    Returns:
        dict[str, Any]: Dictionary containing list of generated test items or error message.
    """
    input_model = GenerateInput.model_validate(params)

    
    from cherenkov.stages.ingest import IngestStage
    from cherenkov.stages.plan import PlanStage
    from cherenkov.stages.generate import GenerateStage
    
    try:
        ingest_stage = IngestStage("mcp_generate")
        ingest_out = ingest_stage.run(input_model.spec_path)
        
        plan_stage = PlanStage("mcp_generate")
        plan_out = plan_stage.run(ingest_out)
        
        ep_map = {}
        for ep in ingest_out.endpoints:
            ep_map[ep.path + ":" + ep.method] = ep
            
        generated_tests = []
        
        if input_model.repair:
            from cherenkov.stages.repair import RepairLoop
        else:
            RepairLoop = None # type: ignore
            
        for sc in plan_out.scenarios:
            ep = ep_map.get(sc.endpoint + ":" + sc.method)
            ep_operation = ep.operation if ep else None
            ep_schemas = ep.schemas if ep else None
            
            if input_model.repair and RepairLoop:
                loop = RepairLoop(
                    run_id=f"mcp_generate_{sc.mutation_id}",
                    max_attempts=3,
                    cleanup_scratch=True,
                )
                gen_out, review = loop.run(
                    scenario=sc,
                    path=sc.endpoint,
                    method=sc.method,
                    operation=ep_operation,
                    schemas=ep_schemas,
                    instruction=getattr(sc, "instruction", ""),
                    source_type="openapi",
                    spec_path=input_model.spec_path,
                )
                
                # Check verdict handling safely
                v = getattr(review, "verdict", None)
                v_val = v.value if hasattr(v, "value") else v
                
                generated_tests.append({
                    "scenario": sc.mutation_id,
                    "code": gen_out.test_code,
                    "quality_score": getattr(review, "quality_score", None) if review else None,
                    "verdict": v_val,
                })
            else:
                stage = GenerateStage("mcp_generate")
                gen_out = stage.run(
                    scenario=sc,
                    path=sc.endpoint,
                    method=sc.method,
                    operation=ep_operation,
                    schemas=ep_schemas,
                    instruction=getattr(sc, "instruction", ""),
                    source_type="openapi",
                )
                generated_tests.append({
                    "scenario": sc.mutation_id,
                    "code": gen_out.test_code
                })
                
        if input_model.output_dir:
            from cherenkov.cli.commands.generate_cmd import scenario_spec_filename
            os.makedirs(input_model.output_dir, exist_ok=True)
            for test in generated_tests:
                sc = next(s for s in plan_out.scenarios if s.mutation_id == test["scenario"])
                test_file = os.path.join(
                    input_model.output_dir,
                    scenario_spec_filename(sc.endpoint, sc.method, sc.mutation_id)
                )
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(test["code"])
                    
        return {"tests": generated_tests}
        
    except Exception as e:
        return {"error": str(e)}


CORE_CLI_TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "cherenkov/check-suite",
        "description": "Run the cherenkov check-suite static analysis to detect weakened, deleted, or hallucinated tests.",
        "inputSchema": CheckSuiteInput.model_json_schema()
    },
    {
        "name": "cherenkov/verify",
        "description": "Probe a live server against its OpenAPI spec to find divergences.",
        "inputSchema": VerifyInput.model_json_schema()
    },
    {
        "name": "cherenkov/generate",
        "description": "Generate Playwright E2E tests from an OpenAPI specification.",
        "inputSchema": GenerateInput.model_json_schema()
    }
]

CORE_CLI_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "cherenkov/check-suite": handle_check_suite,
    "cherenkov/verify": handle_verify,
    "cherenkov/generate": handle_generate,
}
