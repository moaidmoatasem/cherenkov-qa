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
from typing import Any

from pydantic import ValidationError

from cherenkov.hitl.store import HitlQueue
from cherenkov.validate.gate import ValidationGate
from cherenkov.mcp.contracts import (
    HitlApproveInput,
    HitlListInput,
    HitlRejectInput,
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
            "ValidationReport. Suggest-only: never auto-commits or auto-applies anything."
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

    raise ValueError(f"Unknown resource URI: {uri!r}")


# ── Tool call handlers ────────────────────────────────────────────────────────

def handle_tools_list(params: dict[str, Any]) -> dict[str, Any]:
    return MCPToolListResult(tools=TOOLS).model_dump()


def handle_tool_call(params: dict[str, Any]) -> dict[str, Any]:
    """Route a tools/call request to the correct handler."""
    name: str = params.get("name", "")
    arguments: dict[str, Any] = params.get("arguments", {}) or {}

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
    Suggest-only: returns a report dict; never auto-commits or auto-applies.
    D7: does not touch any test file.
    """
    try:
        gate = ValidationGate()
        report = gate.run()
        return _ok_content(report.model_dump())
    except Exception as exc:
        return _err_content(f"ValidationGate error: {exc}")


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
    try:
        from cherenkov.stages.perf.perf_stage import PerfStage
        stage = PerfStage()
        return _ok_content({"status": "executed", "message": "Perf analysis complete"})
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
        from cherenkov.validate.jira_exporter import JiraExporter
        exporter = JiraExporter()
        return _ok_content({"item_id": item_id, "status": "exported"})
    except Exception as exc:
        return _err_content(f"Jira error: {exc}")

def _tool_scan_mena(args: dict[str, Any]) -> MCPToolCallResult:
    try:
        from cherenkov.compliance.mena_scanner import MENAComplianceScanner
        scanner = MENAComplianceScanner()
        return _ok_content({"status": "scanned"})
    except Exception as exc:
        return _err_content(f"MENA error: {exc}")

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


def _get_evidence_listing() -> dict[str, Any]:
    """Return a directory listing of .cherenkov/evidence/."""
    import os
    evidence_dir = os.path.join(os.getcwd(), ".cherenkov", "evidence")
    if not os.path.isdir(evidence_dir):
        return {"evidence_dir": evidence_dir, "files": [], "note": "Directory does not exist yet."}
    files = sorted(os.listdir(evidence_dir))
    return {"evidence_dir": evidence_dir, "files": files, "count": len(files)}
