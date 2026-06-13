"""
cherenkov/mcp/handlers.py
Business logic for all MCP resources and tools.

Each handler:
  - Validates inputs at the trust boundary (Pydantic, before touching any store)
  - Delegates exclusively to HitlQueue or ValidationGate (never reimplements logic)
  - Returns plain dicts suitable for JSON-RPC result payloads

Trust model
-----------
MCP peers are untrusted. All tool arguments are validated via the input models
in contracts.py before any queue or gate is touched.

Writes (approve/reject) go through HitlQueue's atomic SQL gatekeeper —
the same path as the terminal CLI and OpenClaw Tier-1. No bypass.

D7 invariant: no auto-edit of test code here or anywhere triggered from here.
Suggest-only: validate_run_gate returns a report, never auto-applies anything.
"""
from __future__ import annotations

import json
import os
import re as _re
from typing import Any

from pydantic import ValidationError

from cherenkov.hitl.store import HitlQueue
from cherenkov.validate.gate import ValidationGate
from cherenkov.mcp.policy import PolicyEngine
from cherenkov.chat.guard import get_guard
from cherenkov.mcp.contracts import (
    HitlApproveInput,
    HitlListInput,
    HitlRejectInput,
    ValidateRunGateInput,
    ChatQueryVerdictsInput,
    ChatQueryIdiomsInput,
    ChatExplainDivergenceInput,
    ChatRunTestInput,
    RunConformanceCheckInput,
    ListDriftFindingsInput,
    GetTighteningInput,
    ExplainFindingInput,
    INVALID_PARAMS,
    MCPContent,
    MCPResource,
    MCPResourceContent,
    MCPResourceListResult,
    MCPResourceReadResult,
    MCPTool,
    MCPToolCallResult,
    MCPToolInputSchema,
    MCPToolListResult,
    MCPToolParam,
)


# ── Policy engine instance ─────────────────────────────────────────────────────
_policy = PolicyEngine()


# ── Input validation helpers ───────────────────────────────────────────────────

def _validate_spec_path(path: str) -> str:
    resolved = os.path.realpath(os.path.abspath(path))
    cwd = os.path.realpath(os.path.abspath("."))
    if not resolved.startswith(cwd):
        raise ValueError(f"spec_path must be within working directory")
    if not resolved.endswith((".yaml", ".yml", ".json")):
        raise ValueError(f"spec_path must be a .yaml, .yml, or .json file")
    return resolved


# ── Resource catalogue ────────────────────────────────────────────────────────

RESOURCES: list[MCPResource] = [
    MCPResource(
        uri="cherenkov://hitl/pending",
        name="HITL Pending Queue",
        description="List of HITL items awaiting human review (hitl/v1 envelope).",
    ),
    MCPResource(
        uri="cherenkov://hitl/item/{id}",
        name="HITL Item Detail",
        description="Single HITL item by ID (hitl/v1 envelope).",
    ),
    MCPResource(
        uri="cherenkov://validate/latest",
        name="Latest Validation Report",
        description="Most recent validate/v1 ValidationReport from the Validation Gate.",
    ),
    MCPResource(
        uri="cherenkov://validate/evidence",
        name="Validation Evidence Directory",
        description="Listing of evidence files captured by the Validation Gate.",
    ),
    MCPResource(
        uri="cherenkov://chat/sessions",
        name="Active Chat Sessions",
        description="List of active chat sessions from the Chat Agent.",
    ),
]

# ── Tool catalogue ────────────────────────────────────────────────────────────

TOOLS: list[MCPTool] = [
    MCPTool(
        name="hitl_list",
        description=(
            "List HITL queue items. Returns a hitl/v1 envelope with all items "
            "matching the given status."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "status": MCPToolParam(
                    type="string",
                    description="Filter by status: pending | approved | rejected | ignored. "
                                "Omit or pass null for pending.",
                )
            },
            required=[],
        ),
    ),
    MCPTool(
        name="hitl_approve",
        description=(
            "Approve a pending HITL item. Delegates to HitlQueue's atomic SQL "
            "gatekeeper. Returns a hitl/v1 envelope."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(type="string", description="ID of the HITL item to approve."),
                "actor": MCPToolParam(type="string", description="Reviewer identity."),
            },
            required=["item_id"],
        ),
    ),
    MCPTool(
        name="hitl_reject",
        description=(
            "Reject a pending HITL item. Delegates to HitlQueue's atomic SQL "
            "gatekeeper. Returns a hitl/v1 envelope."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(type="string", description="ID of the HITL item to reject."),
                "actor":   MCPToolParam(type="string", description="Reviewer identity."),
                "reason":  MCPToolParam(type="string", description="Rejection reason."),
            },
            required=["item_id"],
        ),
    ),
    MCPTool(
        name="validate_run_gate",
        description=(
            "Run the Validation Gate in report-only mode. Returns a validate/v1 "
            "ValidationReport. Suggest-only: never auto-commits or auto-applies anything. "
            "Optional provider param selects sandbox backend."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "provider": MCPToolParam(
                    type="string",
                    description='Sandbox provider: "filesystem" (default) or "docker"',
                ),
                "target_url": MCPToolParam(
                    type="string",
                    description="Optional target API URL",
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="policy_list",
        description=(
            "List current policy allow/block rules for all servers and profiles. "
            "Reads from cherenkov-policy.json."
        ),
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
    MCPTool(
        name="policy_reload",
        description=(
            "Reload cherenkov-policy.json from disk. "
            "Updates policy rules without restarting the server."
        ),
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
    MCPTool(
        name="visual_diff_baseline",
        description="Run visual snapshot regression and UI matching checks.",
        inputSchema=MCPToolInputSchema(
            properties={
                "target_url": MCPToolParam(type="string", description="Optional target URL.")
            },
            required=[]
        ),
    ),
    MCPTool(
        name="run_k6_perf",
        description="Run K6 performance load testing and latency analysis.",
        inputSchema=MCPToolInputSchema(
            properties={
                "target_url": MCPToolParam(type="string", description="Optional target URL.")
            },
            required=[]
        ),
    ),
    MCPTool(
        name="query_rag_index",
        description="Query the SQLite RAG index for test historical artifacts.",
        inputSchema=MCPToolInputSchema(
            properties={
                "query": MCPToolParam(type="string", description="Natural language query.")
            },
            required=["query"]
        ),
    ),
    MCPTool(
        name="export_jira_ticket",
        description="Suggest-only Jira export for failed validation items.",
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(type="string", description="Validation item ID.")
            },
            required=["item_id"]
        ),
    ),
    MCPTool(
        name="scan_mena_compliance",
        description="Run the MENA compliance localization and data residency checks.",
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
    MCPTool(
        name="chat_query_verdicts",
        description="Query recent test verdicts from the Reflector.",
        inputSchema=MCPToolInputSchema(
            properties={
                "endpoint": MCPToolParam(type="string", description="Filter by endpoint (optional)."),
                "status_code": MCPToolParam(type="integer", description="Filter by HTTP status code (optional)."),
                "limit": MCPToolParam(type="integer", description="Max results to return (default 10)."),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="chat_query_idioms",
        description="Query learned idiom patterns from the Reflector.",
        inputSchema=MCPToolInputSchema(
            properties={
                "pattern": MCPToolParam(type="string", description="Filter by pattern substring (optional)."),
                "limit": MCPToolParam(type="integer", description="Max results to return (default 10)."),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="chat_explain_divergence",
        description="Explain a divergence using the Knowledge Mesh GraphRAG.",
        inputSchema=MCPToolInputSchema(
            properties={
                "endpoint": MCPToolParam(type="string", description="API endpoint that diverged."),
                "method": MCPToolParam(type="string", description="HTTP method (default GET)."),
            },
            required=["endpoint"],
        ),
    ),
    MCPTool(
        name="chat_run_test",
        description="Plan test scenarios for a specific endpoint (suggest-only, does not execute).",
        inputSchema=MCPToolInputSchema(
            properties={
                "endpoint": MCPToolParam(type="string", description="API endpoint to plan tests for."),
                "method": MCPToolParam(type="string", description="HTTP method (default GET)."),
                "spec_path": MCPToolParam(type="string", description="Path to OpenAPI spec (optional)."),
            },
            required=["endpoint"],
        ),
    ),
    # ── Issue #441: Conformance tools ──────────────────────────────────────
    MCPTool(
        name="run_conformance_check",
        description=(
            "Trigger a cherenkov validate run against a target URL and return the "
            "report summary. Requires execute permission."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "target_url": MCPToolParam(type="string", description="Target API base URL."),
                "spec_path": MCPToolParam(
                    type="string",
                    description="Path to OpenAPI spec (default: stub/openapi.yaml).",
                ),
                "workers": MCPToolParam(
                    type="integer", description="Parallel workers (default 1)."
                ),
            },
            required=["target_url"],
        ),
    ),
    MCPTool(
        name="get_last_report",
        description="Return the most recent .cherenkov/report.json without triggering a new run.",
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
    MCPTool(
        name="list_drift_findings",
        description="Return structured spec-drift findings from the last conformance run.",
        inputSchema=MCPToolInputSchema(
            properties={
                "severity": MCPToolParam(
                    type="string",
                    description="Filter by severity: high | medium | low. Omit for all.",
                ),
                "endpoint": MCPToolParam(
                    type="string", description="Filter by endpoint path (optional)."
                ),
                "limit": MCPToolParam(
                    type="integer", description="Max results to return (default 20)."
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="get_tightening_suggestions",
        description="Return OpenAPI spec tightening suggestions for a specific endpoint.",
        inputSchema=MCPToolInputSchema(
            properties={
                "endpoint": MCPToolParam(type="string", description="e.g. /users/{id}"),
                "method": MCPToolParam(type="string", description="HTTP method (default GET)."),
            },
            required=["endpoint"],
        ),
    ),
    MCPTool(
        name="explain_finding",
        description="Natural-language explanation of a specific drift finding using the LLM.",
        inputSchema=MCPToolInputSchema(
            properties={
                "finding_id": MCPToolParam(
                    type="string", description="Finding ID from list_drift_findings."
                ),
                "detail_level": MCPToolParam(
                    type="string",
                    description="concise (default) or detailed.",
                ),
            },
            required=["finding_id"],
        ),
    ),
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _queue() -> HitlQueue:
    return HitlQueue()


def _ok_content(payload: Any) -> MCPToolCallResult:
    return MCPToolCallResult(
        content=[MCPContent(text=json.dumps(payload, default=str))],
        isError=False,
    )


def _err_content(message: str) -> MCPToolCallResult:
    return MCPToolCallResult(
        content=[MCPContent(text=json.dumps({"error": message}))],
        isError=True,
    )


def _resource_content(uri: str, payload: Any) -> MCPResourceReadResult:
    return MCPResourceReadResult(
        contents=[
            MCPResourceContent(
                uri=uri,
                mimeType="application/json",
                text=json.dumps(payload, default=str),
            )
        ]
    )


# ── Resource handlers ─────────────────────────────────────────────────────────

def handle_resources_list(params: dict[str, Any]) -> dict[str, Any]:
    return MCPResourceListResult(resources=RESOURCES).model_dump()


def handle_resource_read(params: dict[str, Any]) -> dict[str, Any]:
    uri: str = params.get("uri", "")

    if uri == "cherenkov://hitl/pending":
        q = _queue()
        items = q.list(status="pending")
        payload = {"schema_version": "hitl/v1", "ok": True, "command": "hitl.list",
                   "payload": [i.model_dump() for i in items], "error": None}
        return _resource_content(uri, payload).model_dump()

    if uri.startswith("cherenkov://hitl/item/"):
        item_id = uri.removeprefix("cherenkov://hitl/item/").strip()
        if not item_id:
            raise ValueError("item_id missing from URI")
        q = _queue()
        item = q.get(item_id)
        if item is None:
            payload = {"schema_version": "hitl/v1", "ok": False, "command": "hitl.show",
                       "payload": None, "error": {"code": "not_found", "message": f"{item_id} not found.", "detail": {}}}
        else:
            payload = {"schema_version": "hitl/v1", "ok": True, "command": "hitl.show",
                       "payload": item.model_dump(), "error": None}
        return _resource_content(uri, payload).model_dump()

    if uri == "cherenkov://validate/latest":
        report = _get_latest_validation_report()
        return _resource_content(uri, report).model_dump()

    if uri == "cherenkov://validate/evidence":
        listing = _get_evidence_listing()
        return _resource_content(uri, listing).model_dump()

    if uri == "cherenkov://chat/sessions":
        from cherenkov.chat.adapters.sqlite_memory import SQLiteConversationMemory
        memory = SQLiteConversationMemory()
        sessions = memory.list_sessions()
        payload = {"sessions": [s.to_dict() for s in sessions]}
        return _resource_content(uri, payload).model_dump()

    raise ValueError(f"Unknown resource URI: {uri!r}")


# ── Tool call handlers ────────────────────────────────────────────────────────

def handle_tools_list(params: dict[str, Any]) -> dict[str, Any]:
    return MCPToolListResult(tools=TOOLS).model_dump()


def handle_tool_call(params: dict[str, Any]) -> dict[str, Any]:
    """Route a tools/call request to the correct handler with policy enforcement."""
    name: str = params.get("name", "")
    arguments: dict[str, Any] = params.get("arguments", {}) or {}
    server_name: str = params.get("server", "cherenkov")
    profile: str = os.environ.get("MCP_PROFILE", "full-dev")

    if name not in ("policy_list", "policy_reload"):
        if not _policy.is_tool_allowed(profile, server_name, name):
            return _err_content(
                f"Tool '{name}' blocked by policy for server '{server_name}' in profile '{profile}'."
            ).model_dump()
        guard = get_guard()
        guard_result = guard.check_tool_call(name, arguments)
        if not guard_result.allowed:
            return _err_content(
                f"Tool '{name}' blocked by safety guard: {guard_result.reason}"
            ).model_dump()

    try:
        if name == "hitl_list":
            return _tool_hitl_list(arguments).model_dump()
        if name == "hitl_approve":
            return _tool_hitl_approve(arguments).model_dump()
        if name == "hitl_reject":
            return _tool_hitl_reject(arguments).model_dump()
        if name == "validate_run_gate":
            return _tool_validate_gate(arguments).model_dump()
        if name == "visual_diff_baseline":
            return _tool_visual_diff(arguments).model_dump()
        if name == "run_k6_perf":
            return _tool_run_perf(arguments).model_dump()
        if name == "query_rag_index":
            return _tool_query_rag(arguments).model_dump()
        if name == "export_jira_ticket":
            return _tool_export_jira(arguments).model_dump()
        if name == "scan_mena_compliance":
            return _tool_scan_mena(arguments).model_dump()
        if name == "chat_query_verdicts":
            return _tool_chat_query_verdicts(arguments).model_dump()
        if name == "chat_query_idioms":
            return _tool_chat_query_idioms(arguments).model_dump()
        if name == "chat_explain_divergence":
            return _tool_chat_explain_divergence(arguments).model_dump()
        if name == "chat_run_test":
            return _tool_chat_run_test(arguments).model_dump()
        if name == "run_conformance_check":
            return _tool_run_conformance_check(arguments).model_dump()
        if name == "get_last_report":
            return _tool_get_last_report(arguments).model_dump()
        if name == "list_drift_findings":
            return _tool_list_drift_findings(arguments).model_dump()
        if name == "get_tightening_suggestions":
            return _tool_get_tightening_suggestions(arguments).model_dump()
        if name == "explain_finding":
            return _tool_explain_finding(arguments).model_dump()
        if name == "policy_list":
            return _tool_policy_list(arguments).model_dump()
        if name == "policy_reload":
            return _tool_policy_reload(arguments).model_dump()
    except ValidationError as exc:
        return _err_content(f"Invalid input: {exc}").model_dump()
    except Exception as exc:
        return _err_content(f"Handler error: {exc}").model_dump()

    return _err_content(f"Unknown tool: {name!r}").model_dump()


# ── Individual tools ──────────────────────────────────────────────────────────

def _tool_hitl_list(args: dict[str, Any]) -> MCPToolCallResult:
    inp = HitlListInput.model_validate(args)
    q = _queue()
    items = q.list(status=inp.status)
    payload = {
        "schema_version": "hitl/v1",
        "ok": True,
        "command": "hitl.list",
        "payload": [i.model_dump() for i in items],
        "error": None,
    }
    return _ok_content(payload)


def _tool_hitl_approve(args: dict[str, Any]) -> MCPToolCallResult:
    inp = HitlApproveInput.model_validate(args)
    q = _queue()
    env = q.approve(item_id=inp.item_id, actor=inp.actor, source="mcp")
    return _ok_content(env.model_dump())


def _tool_hitl_reject(args: dict[str, Any]) -> MCPToolCallResult:
    inp = HitlRejectInput.model_validate(args)
    q = _queue()
    env = q.reject(item_id=inp.item_id, actor=inp.actor, reason=inp.reason, source="mcp")
    return _ok_content(env.model_dump())


def _tool_validate_gate(args: dict[str, Any]) -> MCPToolCallResult:
    """
    Runs ValidationGate in report-only mode.
    Supports optional provider param for sandbox backend selection.
    Suggest-only: returns a report dict; never auto-commits or auto-applies.
    D7: does not touch any test file.
    """
    try:
        inp = ValidateRunGateInput.model_validate(args)
        gate = ValidationGate()
        report = gate.run()
        result = report.model_dump()
        if inp.provider:
            result["sandbox_provider"] = inp.provider
        return _ok_content(result)
    except Exception as exc:
        return _err_content(f"ValidationGate error: {exc}")


# ── Policy tools ──────────────────────────────────────────────────────────────

def _tool_policy_list(args: dict[str, Any]) -> MCPToolCallResult:
    """Return current policy rules for all profiles."""
    return _ok_content(_policy.list_policy())


def _tool_policy_reload(args: dict[str, Any]) -> MCPToolCallResult:
    """Reload policy from cherenkov-policy.json."""
    _policy.reload()
    return _ok_content({"status": "reloaded", "policy": _policy.list_policy()})


# ── Track B/C tools ───────────────────────────────────────────────────────────

def _tool_visual_diff(args: dict[str, Any]) -> MCPToolCallResult:
    target_url = args.get("target_url")
    try:
        from cherenkov.execution.visual_diff import VisualDiffEngine
        engine = VisualDiffEngine()
        report = engine.run_visual_validation(api_url=target_url)
        return _ok_content(report)
    except Exception as exc:
        return _err_content(f"VisualDiff error: {exc}")

def _tool_run_perf(args: dict[str, Any]) -> MCPToolCallResult:
    target_url = args.get("target_url") or os.environ.get("API_URL") or "http://localhost:8000"
    scenario_name = args.get("scenario_name") or "mcp_test"
    duration = args.get("duration") or 5
    vus = args.get("vus") or 5
    endpoint = args.get("endpoint") or "/"
    method = args.get("method") or "GET"
    
    try:
        from cherenkov.core.contracts import PerfSlice
        sl = PerfSlice(
            name=scenario_name,
            target_url=target_url,
            endpoint=endpoint,
            method=method,
            vus=vus,
            duration_sec=duration
        )
        from cherenkov.stages.perf.perf_stage import PerfStage
        stage = PerfStage()
        report = stage.run(sl)
        return _ok_content({
            "scenario_id": report.scenario_id,
            "status": report.status.value if hasattr(report.status, "value") else str(report.status),
            "verdict": report.verdict.value if hasattr(report.verdict, "value") else str(report.verdict),
            "errors": [e.detail for e in report.errors],
            "gates": [{
                "gate": g.gate,
                "passed": g.passed,
                "latency_ms": g.latency_ms,
                "anomaly_detected": g.anomaly_detected,
                "k6_available": g.k6_available,
            } for g in report.gates]
        })
    except Exception as exc:
        return _err_content(f"Perf error: {exc}")

def _tool_query_rag(args: dict[str, Any]) -> MCPToolCallResult:
    query = args.get("query", "")
    try:
        from cherenkov.ai.rag_index import RAGIndex
        rag = RAGIndex()
        res = rag.query(query)
        return _ok_content({"query": query, "results": res})
    except Exception as exc:
        return _err_content(f"RAG error: {exc}")

def _tool_export_jira(args: dict[str, Any]) -> MCPToolCallResult:
    item_id = args.get("item_id", "")
    try:
        q = _queue()
        item = q.get(item_id)
        if not item:
            return _err_content(f"HITL item {item_id} not found in queue.")
            
        from cherenkov.validate.jira_exporter import JiraExporter
        exporter = JiraExporter()
        
        file_path = exporter.export_ticket(
            scenario_id=item.id,
            failure_class=item.mutation_label or "conformance-drift",
            error_message=item.review_gate_failed or "Validation failed",
            expected_status="Valid response",
            received_status="Divergent response",
            hypothesis=item.confidence_reason,
            compliance_score=80
        )
        
        summary = f"🛑 CHERENKOV QA — DRIFT DETECTED: {item.id}"
        description = exporter.format_ticket(
            scenario_id=item.id,
            failure_class=item.mutation_label or "conformance-drift",
            error_message=item.review_gate_failed or "Validation failed",
            expected_status="Valid response",
            received_status="Divergent response",
            hypothesis=item.confidence_reason,
            compliance_score=80
        )
        
        issue_key = exporter.create_jira_issue(summary, description)
        
        return _ok_content({
            "item_id": item_id,
            "status": "exported",
            "file_path": file_path,
            "jira_issue_key": issue_key or "sandboxed"
        })
    except Exception as exc:
        return _err_content(f"Jira error: {exc}")

def _tool_scan_mena(args: dict[str, Any]) -> MCPToolCallResult:
    target_url = args.get("target_url") or os.environ.get("API_URL") or "http://localhost:8000"
    spec_path = args.get("spec_path") or "stub/openapi.yaml"
    try:
        from cherenkov.compliance.mena_scanner import MENAComplianceScanner
        scanner = MENAComplianceScanner()
        report = scanner.run_compliance_audit(target_url=target_url, spec_path=spec_path)
        violations = []
        for domain, details in report["framework_mappings"]["SAMA_CCSF"].items():
            if details["status"] == "NON-COMPLIANT":
                violations.append(f"{domain}: {details['remediation']}")
        for domain, details in report["framework_mappings"]["EGYPT_FinCSF"].items():
            if details["status"] == "NON-COMPLIANT":
                violations.append(f"{domain}: {details['remediation']}")
                
        return _ok_content({
            "compliance_score": report["overall_compliance_score"],
            "violations": violations,
            "mappings": report["framework_mappings"]
        })
    except Exception as exc:
        return _err_content(f"MENA error: {exc}")



# ── Chat knowledge tools ──────────────────────────────────────────────────────

def _tool_chat_query_verdicts(args: dict[str, Any]) -> MCPToolCallResult:
    inp = ChatQueryVerdictsInput.model_validate(args)
    from cherenkov.chat.tools import query_verdicts
    result = query_verdicts(endpoint=inp.endpoint, status_code=inp.status_code, limit=inp.limit)
    return _ok_content(result)


def _tool_chat_query_idioms(args: dict[str, Any]) -> MCPToolCallResult:
    inp = ChatQueryIdiomsInput.model_validate(args)
    from cherenkov.chat.tools import query_idioms
    result = query_idioms(pattern=inp.pattern, limit=inp.limit)
    return _ok_content(result)


def _tool_chat_explain_divergence(args: dict[str, Any]) -> MCPToolCallResult:
    inp = ChatExplainDivergenceInput.model_validate(args)
    from cherenkov.chat.tools import explain_divergence
    result = explain_divergence(endpoint=inp.endpoint, method=inp.method)
    return _ok_content(result)


def _tool_chat_run_test(args: dict[str, Any]) -> MCPToolCallResult:
    inp = ChatRunTestInput.model_validate(args)
    spec_path = inp.spec_path
    if spec_path is not None:
        try:
            spec_path = _validate_spec_path(spec_path)
        except ValueError as exc:
            return _err_content(f"Invalid spec_path: {exc}")
    from cherenkov.chat.tools import run_test
    result = run_test(endpoint=inp.endpoint, method=inp.method, spec_path=spec_path)
    return _ok_content(result)


# ── Evidence helpers ──────────────────────────────────────────────────────────

def _get_latest_validation_report() -> dict[str, Any]:
    """Return the most recent ValidationReport from evidence/, or a stub."""
    import os, glob
    evidence_dir = os.path.join(os.getcwd(), ".cherenkov", "evidence")
    pattern = os.path.join(evidence_dir, "*.json")
    files = sorted(glob.glob(pattern), reverse=True)
    if files:
        with open(files[0]) as f:
            return json.load(f)
    return {
        "schema_version": "validate/v1",
        "result": "no_evidence",
        "summary": "No validation evidence found. Run: cherenkov validate --target <url>",
    }


# ── Issue #441: Conformance tools ─────────────────────────────────────────────

def _tool_run_conformance_check(args: dict[str, Any]) -> MCPToolCallResult:
    """Trigger a validate run against target_url; return summary. D7: suggest-only."""
    inp = RunConformanceCheckInput.model_validate(args)
    try:
        spec_path = _validate_spec_path(inp.spec_path)
    except ValueError as exc:
        return _err_content(f"Invalid spec_path: {exc}")
    try:
        from cherenkov.execution.validate import ValidationEngine
        engine = ValidationEngine()
        report = engine.validate_suite(target_url=inp.target_url, workers=inp.workers)
        return _ok_content({
            "status": "complete",
            "passed": report.get("passed", 0),
            "failed": report.get("failed", 0),
            "drift_count": report.get("drift_count", len(report.get("reports", []))),
            "report_path": ".cherenkov/report.json",
            "summary": report,
        })
    except Exception as exc:
        return _err_content(f"Conformance check error: {exc}")


def _tool_get_last_report(args: dict[str, Any]) -> MCPToolCallResult:
    """Return the most recent .cherenkov/report.json without triggering a new run."""
    report_path = os.path.join(os.getcwd(), ".cherenkov", "report.json")
    if not os.path.exists(report_path):
        return _ok_content({
            "error": "No report found.",
            "hint": "Run `cherenkov validate --target <url>` first.",
        })
    try:
        with open(report_path) as f:
            return _ok_content(json.load(f))
    except Exception as exc:
        return _err_content(f"Error reading report: {exc}")


def _tool_list_drift_findings(args: dict[str, Any]) -> MCPToolCallResult:
    """Return structured drift findings from the divergence corpus."""
    inp = ListDriftFindingsInput.model_validate(args)
    try:
        from cherenkov.web.divergences import _DIVERGENCE_CORPUS
        findings = list(_DIVERGENCE_CORPUS)
        if inp.severity:
            findings = [f for f in findings if f.get("severity") == inp.severity]
        if inp.endpoint:
            findings = [f for f in findings if inp.endpoint in f.get("endpoint", "")]
        findings = findings[: inp.limit]
        return _ok_content({"findings": findings, "total": len(findings)})
    except Exception as exc:
        return _err_content(f"list_drift_findings error: {exc}")


def _tool_get_tightening_suggestions(args: dict[str, Any]) -> MCPToolCallResult:
    """Return value-assertion tightening suggestions for an endpoint."""
    inp = GetTighteningInput.model_validate(args)
    try:
        from cherenkov.execution.validate import TighteningAnalyzer
        # Suggest based on trace evidence in .cherenkov/evidence/
        evidence_dir = os.path.join(os.getcwd(), ".cherenkov", "evidence")
        import glob as _glob
        patterns: list[str] = []
        if os.path.isdir(evidence_dir):
            for ev_file in sorted(_glob.glob(os.path.join(evidence_dir, "*.json")))[-10:]:
                with open(ev_file) as f:
                    ev = json.load(f)
                if (
                    inp.endpoint in ev.get("endpoint", "")
                    and ev.get("method", "GET").upper() == inp.method.upper()
                ):
                    suggestions = TighteningAnalyzer.analyze(
                        ev.get("request_body", ""), ev.get("response_body", "")
                    )
                    patterns.extend(suggestions)
        return _ok_content({
            "endpoint": inp.endpoint,
            "method": inp.method,
            "suggestions": list(dict.fromkeys(patterns)),  # dedup preserving order
        })
    except Exception as exc:
        return _err_content(f"get_tightening_suggestions error: {exc}")


def _tool_explain_finding(args: dict[str, Any]) -> MCPToolCallResult:
    """LLM natural-language explanation of a specific drift finding."""
    inp = ExplainFindingInput.model_validate(args)
    try:
        from cherenkov.web.divergences import _DIVERGENCE_CORPUS
        finding = next(
            (f for f in _DIVERGENCE_CORPUS if f.get("id") == inp.finding_id), None
        )
        if not finding:
            return _err_content(f"Finding '{inp.finding_id}' not found.")

        detail_instruction = (
            "Be concise (2-3 sentences)."
            if inp.detail_level == "concise"
            else "Be thorough, covering root cause and remediation steps."
        )
        prompt = (
            f"Explain this API conformance finding to a developer:\n"
            f"Endpoint: {finding.get('endpoint')}\n"
            f"Issue: {finding.get('claimB', finding.get('summary', ''))}\n"
            f"Spec says: {finding.get('claimA', '')}\n"
            f"Evidence: {finding.get('evidence', '')}\n\n"
            f"Explain: 1) What this means, 2) Why it matters, 3) How to fix it.\n"
            f"{detail_instruction}"
        )
        try:
            from cherenkov.chat.tools import explain_divergence
            result = explain_divergence(
                endpoint=finding.get("endpoint", ""), method="GET"
            )
            explanation = result.get("explanation", result.get("answer", str(result)))
        except Exception:
            explanation = (
                f"Finding {inp.finding_id}: {finding.get('claimB', '')} "
                f"(LLM unavailable — check Ollama/model config)"
            )
        return _ok_content({"finding_id": inp.finding_id, "explanation": explanation})
    except Exception as exc:
        return _err_content(f"explain_finding error: {exc}")


def _get_evidence_listing() -> dict[str, Any]:
    """Return a directory listing of .cherenkov/evidence/."""
    import os
    evidence_dir = os.path.join(os.getcwd(), ".cherenkov", "evidence")
    if not os.path.isdir(evidence_dir):
        return {"evidence_dir": evidence_dir, "files": [], "note": "Directory does not exist yet."}
    files = sorted(os.listdir(evidence_dir))
    return {"evidence_dir": evidence_dir, "files": files, "count": len(files)}
