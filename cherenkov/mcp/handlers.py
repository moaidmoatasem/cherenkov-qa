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

import glob
import hashlib
import ipaddress
import json
import os
import socket
import time
import urllib.request
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from cherenkov.chat.guard import get_guard
from cherenkov.divergence.proof_run import run_proof
from cherenkov.events import get_event_bus
from cherenkov.events.bridge import to_cherenkov_event
from cherenkov.hitl.store import HitlQueue
from cherenkov.mcp.client import MCPClientError
from cherenkov.mcp.contracts import (
    ChatExplainDivergenceInput,
    ChatQueryIdiomsInput,
    ChatQueryVerdictsInput,
    ChatRunTestInput,
    CheckSuiteInput,
    ComplianceFindingsInput,
    EventBusGetInput,
    EventBusListInput,
    EventBusPublishInput,
    ExplainFindingInput,
    ExportJiraInput,
    GenerateInput,
    GetTighteningInput,
    GovernanceCertificationInput,
    HitlApproveInput,
    HitlListInput,
    HitlRejectInput,
    ListDriftFindingsInput,
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
    MenaComplianceEnhancedInput,
    RunConformanceCheckInput,
    RunK6PerfInput,
    ValidateRunGateInput,
    VerifyInput,
    VerifySuiteInput,
    VerifySystemInput,
    VisualDiffBaselineInput,
)
from cherenkov.mcp.mesh_router import get_registry
from cherenkov.mcp.policy import PolicyEngine
from cherenkov.mcp.tools.sentinel import SENTINEL_HANDLERS, SENTINEL_TOOL_DEFS
from cherenkov.mcp.tools.core_cli import CORE_CLI_HANDLERS, CORE_CLI_TOOL_DEFS
from cherenkov.validate.gate import ValidationGate

# ── Policy engine instance ─────────────────────────────────────────────────────
_policy = PolicyEngine()

# ── Input validation helpers ───────────────────────────────────────────────────

def _validate_spec_path(path: str) -> str:
    """Validate that the provided spec_path is within the working directory and has a valid spec extension.

    Args:
        path (str): The file path string to validate.

    Returns:
        str: Absolute resolved path string.

    Raises:
        ValueError: If path escapes the working directory or does not end with .yaml, .yml, or .json.
    """
    resolved = os.path.realpath(os.path.abspath(path))
    cwd = os.path.realpath(os.path.abspath("."))
    if not resolved.startswith(cwd):
        raise ValueError("spec_path must be within working directory")
    if not resolved.endswith((".yaml", ".yml", ".json")):
        raise ValueError("spec_path must be a .yaml, .yml, or .json file")
    return resolved


def _resolve_within_cwd(path: str, must_exist: bool = True) -> Path | str:
    """Resolve a caller-supplied path inside the working directory.

    Returns the resolved ``Path`` on success, or an error message string
    (meant for ``_err_content``) when the path escapes the working directory
    or does not exist. MCP peers are untrusted — path containment is part of
    the trust boundary.
    """
    resolved = Path(path).resolve()
    cwd = Path.cwd().resolve()
    if not str(resolved).startswith(str(cwd)):
        return f"{path} must be within the working directory."
    if must_exist and not resolved.exists():
        return f"File not found: {path}"
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
    MCPResource(
        uri="cherenkov://gates",
        name="CHERENKOV Integrity Gates",
        description="Machine-readable description of the 6 REVIEW gates so agents can "
        "self-correct before calling verify_suite. Each entry explains what the gate "
        "checks, what a passing test must contain, and what cheat pattern it catches.",
    ),
]

# ── Tool catalogue ────────────────────────────────────────────────────────────

TOOLS: list[MCPTool] = [
    MCPTool(
        name="hitl_list",
        description="List HITL queue items matching the given status. Returns a hitl/v1 envelope.",
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
        description="Approve a pending HITL item. Returns a hitl/v1 envelope.",
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(
                    type="string", description="ID of the HITL item to approve."
                ),
                "actor": MCPToolParam(type="string", description="Reviewer identity."),
            },
            required=["item_id"],
        ),
    ),
    MCPTool(
        name="hitl_reject",
        description="Reject a pending HITL item. Returns a hitl/v1 envelope.",
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(
                    type="string", description="ID of the HITL item to reject."
                ),
                "actor": MCPToolParam(type="string", description="Reviewer identity."),
                "reason": MCPToolParam(type="string", description="Rejection reason."),
            },
            required=["item_id"],
        ),
    ),
    MCPTool(
        name="verify_suite",
        description=(
            "Run the 6-gate integrity check on an AI-generated test suite and return a "
            "VerificationReport (verify/v1). Suggest-only — never auto-applies fixes."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "suite_path": MCPToolParam(
                    type="string",
                    description="Path to a .spec.ts file to verify (must be within working directory).",
                ),
                "suite_inline": MCPToolParam(
                    type="string",
                    description="Raw TypeScript test code to verify inline.",
                ),
                "spec_source": MCPToolParam(
                    type="string",
                    description="Path to the OpenAPI spec for oracle derivation. Defaults to stub/openapi_3_1.yaml.",
                ),
                "scenario_id": MCPToolParam(
                    type="string",
                    description="Scenario identifier used in finding IDs.",
                ),
                "endpoint": MCPToolParam(
                    type="string",
                    description="API endpoint under test, e.g. /users.",
                ),
                "method": MCPToolParam(
                    type="string",
                    description="HTTP method (GET, POST, PUT, DELETE, PATCH). Default: POST.",
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="verify_system",
        description=(
            "Probe a live server against its OpenAPI spec; return spec-drift divergences "
            "as a VerificationReport (verify/v1). Offline by default — no LLM required."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "base_url": MCPToolParam(
                    type="string",
                    description="Base URL of the live server to probe (e.g. https://petstore3.swagger.io/api/v3).",
                ),
                "spec_source": MCPToolParam(
                    type="string",
                    description="Path or HTTP URL to the OpenAPI spec JSON/YAML. Omit for built-in Petstore demo.",
                ),
                "use_llm": MCPToolParam(
                    type="boolean",
                    description="If true, use the LLM Skeptic (requires Ollama). Default: false (offline mode).",
                ),
                "run_id": MCPToolParam(
                    type="string",
                    description="Optional run identifier for correlation.",
                ),
            },
            required=["base_url"],
        ),
    ),
    # ── Issue #812: Deepened agent-invokable tool surface ─────────────────────
    MCPTool(
        name="check_suite",
        description=(
            "Static integrity check of a candidate test suite against a "
            "baseline: catches WEAKENED, DELETED, and HALLUCINATED assertions "
            "(`cherenkov check-suite`). Fast, offline, no execution."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "candidate_path": MCPToolParam(
                    type="string",
                    description="Path to the candidate test suite (.py or .ts) to check.",
                ),
                "candidate_inline": MCPToolParam(
                    type="string",
                    description="Raw test code to check inline (when the file isn't on disk yet).",
                ),
                "baseline_path": MCPToolParam(
                    type="string",
                    description="Path to the known-honest baseline suite. "
                    "Required for WEAKENED and DELETED detection.",
                ),
                "baseline_inline": MCPToolParam(
                    type="string",
                    description="Raw baseline test code inline.",
                ),
                "spec_path": MCPToolParam(
                    type="string",
                    description="Path to the OpenAPI spec (YAML/JSON). Required for "
                    "HALLUCINATED detection on Python suites.",
                ),
                "fail_on_finding": MCPToolParam(
                    type="boolean",
                    description="Report verdict 'fail' if any integrity violation is found.",
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="verify",
        description=(
            "Probe a live server against its OpenAPI spec and return "
            "spec-drift divergences (`cherenkov verify`). Offline by default — "
            "no LLM required. Supports coverage and health-score reports."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "base_url": MCPToolParam(
                    type="string",
                    description="Base URL of the live server to probe "
                    "(e.g. https://petstore3.swagger.io/api/v3).",
                ),
                "spec_source": MCPToolParam(
                    type="string",
                    description="Path or URL to the OpenAPI spec JSON/YAML. "
                    "Omit for the built-in Petstore demo.",
                ),
                "use_llm": MCPToolParam(
                    type="boolean",
                    description="Use the LLM Skeptic (requires Ollama). Default: false.",
                ),
                "max_probes": MCPToolParam(
                    type="integer",
                    description="Maximum spec-derived endpoint probes (1-500, default 40).",
                ),
                "allow_mutations": MCPToolParam(
                    type="boolean",
                    description="Allow happy-path probes for POST/PUT/DELETE. Default: false.",
                ),
                "identifiers": MCPToolParam(
                    type="string",
                    description="JSON file path or inline JSON mapping path parameters "
                    "to known valid values.",
                ),
                "coverage_report": MCPToolParam(
                    type="boolean",
                    description="Include spec coverage-gap report (requires spec_source).",
                ),
                "health_score": MCPToolParam(
                    type="boolean",
                    description="Include A-F health grade (requires spec_source).",
                ),
                "run_id": MCPToolParam(
                    type="string",
                    description="Optional run identifier for correlation.",
                ),
            },
            required=["base_url"],
        ),
    ),
    MCPTool(
        name="generate",
        description=(
            "Generate Playwright E2E tests from an OpenAPI spec "
            "(`cherenkov generate`). Returns generated test code inline, or "
            "writes files when output_dir is given."
        ),
        inputSchema=MCPToolInputSchema(
            properties={
                "spec_path": MCPToolParam(
                    type="string",
                    description="Path to the OpenAPI spec (JSON/YAML) to generate tests for.",
                ),
                "output_dir": MCPToolParam(
                    type="string",
                    description="Directory to write generated test files to. "
                    "Omit to return code inline.",
                ),
                "repair": MCPToolParam(
                    type="boolean",
                    description="Run the generate→review→repair loop. Default: true.",
                ),
                "max_attempts": MCPToolParam(
                    type="integer",
                    description="Max repair attempts per scenario (1-10, default 3).",
                ),
            },
            required=["spec_path"],
        ),
    ),
    MCPTool(
        name="validate_run_gate",
        description="Run the Validation Gate and return a validate/v1 ValidationReport. Suggest-only.",
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
        description="List policy allow/block rules from cherenkov-policy.json.",
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
    MCPTool(
        name="policy_reload",
        description="Reload cherenkov-policy.json from disk without restarting the server.",
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
    MCPTool(
        name="visual_diff_baseline",
        description="Run visual snapshot regression and UI matching checks.",
        inputSchema=MCPToolInputSchema(
            properties={
                "target_url": MCPToolParam(
                    type="string", description="Optional target URL."
                )
            },
            required=[],
        ),
    ),
    # ── Issue #457: Enhanced Visual Diff Baseline Tool ──────────────────────
    MCPTool(
        name="visual_diff_baseline_enhanced",
        description="Run comprehensive visual snapshot regression with baseline management, "
        "configurable diff thresholds, pixel/structural/auto comparison modes, "
        "and custom report paths.",
        inputSchema=MCPToolInputSchema(
            properties={
                "target_url": MCPToolParam(
                    type="string",
                    description="Optional target URL for visual testing",
                ),
                "baseline_dir": MCPToolParam(
                    type="string",
                    description="Baseline directory path (default: stub/visual_baselines)",
                ),
                "diff_threshold": MCPToolParam(
                    type="number",
                    description="Pixel diff threshold (0.0-1.0, default: 0.5)",
                ),
                "comparison_mode": MCPToolParam(
                    type="string",
                    description="Comparison mode: pixel, structural, or auto",
                ),
                "report_path": MCPToolParam(
                    type="string",
                    description="Path to save visual report (default: .cherenkov/visual_report.json)",
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="run_k6_perf",
        description="Run K6 performance load testing and latency analysis.",
        inputSchema=MCPToolInputSchema(
            properties={
                "target_url": MCPToolParam(
                    type="string", description="Target API base URL."
                ),
                "scenario_name": MCPToolParam(
                    type="string", description="K6 scenario name (default: soak)."
                ),
                "duration": MCPToolParam(
                    type="string", description="Duration string (default: 30s)."
                ),
                "vus": MCPToolParam(
                    type="integer", description="Virtual users count (default: 10)."
                ),
                "endpoint": MCPToolParam(
                    type="string", description="Endpoint path (default: /)."
                ),
                "method": MCPToolParam(
                    type="string", description="HTTP method (default: GET)."
                ),
                "use_ml": MCPToolParam(
                    type="boolean", description="Enable ML latency anomaly detection (default: false)."
                ),
                "traffic_file": MCPToolParam(
                    type="string", description="HAR or traffic log file path (optional)."
                ),
            },
            required=["target_url"],
        ),
    ),
    MCPTool(
        name="query_rag_index",
        description="Query the SQLite RAG index for test historical artifacts.",
        inputSchema=MCPToolInputSchema(
            properties={
                "query": MCPToolParam(
                    type="string", description="Natural language query."
                )
            },
            required=["query"],
        ),
    ),
    MCPTool(
        name="export_jira_ticket",
        description="Suggest-only Jira export for failed validation items or custom summary/description.",
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(
                    type="string", description="Validation item ID (optional if summary and description provided)."
                ),
                "summary": MCPToolParam(
                    type="string", description="Ticket summary/title."
                ),
                "description": MCPToolParam(
                    type="string", description="Ticket description."
                ),
                "project_key": MCPToolParam(
                    type="string", description="Jira project key (default: QA)."
                ),
                "sandbox_only": MCPToolParam(
                    type="boolean", description="Sandbox mode flag (default: true)."
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="export_linear_ticket",
        description="Suggest-only Linear export for failed validation items.",
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(
                    type="string", description="Validation item ID."
                )
            },
            required=["item_id"],
        ),
    ),
    MCPTool(
        name="export_github_ticket",
        description="Suggest-only GitHub issue export for failed validation items.",
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(
                    type="string", description="Validation item ID."
                )
            },
            required=["item_id"],
        ),
    ),
    MCPTool(
        name="auto_heal_code",
        description="Generate a suggested code patch for a failed validation item. Suggest-only.",
        inputSchema=MCPToolInputSchema(
            properties={
                "item_id": MCPToolParam(
                    type="string", description="Validation item ID."
                )
            },
            required=["item_id"],
        ),
    ),
    MCPTool(
        name="scan_mena_compliance",
        description="Run the MENA compliance localization and data residency checks.",
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
    # ── Issue #458: Compliance and Governance MCP Tools ────────────────────
    MCPTool(
        name="scan_mena_compliance_enhanced",
        description="Run targeted MENA compliance checks (SAMA CCSF / Egypt CBE FinCSF) against a live API.",
        inputSchema=MCPToolInputSchema(
            properties={
                "target_url": MCPToolParam(
                    type="string",
                    description="Target API base URL",
                ),
                "spec_path": MCPToolParam(
                    type="string",
                    description="Path to OpenAPI spec (default: stub/openapi.yaml)",
                ),
                "framework": MCPToolParam(
                    type="string",
                    description="Compliance framework: sama_ccsf or egypt_cbef",
                ),
            },
            required=["target_url"],
        ),
    ),
    MCPTool(
        name="validate_governance_certification",
        description="Validate a governance certification ID against quality standards.",
        inputSchema=MCPToolInputSchema(
            properties={
                "cert_id": MCPToolParam(
                    type="string",
                    description="Certification ID to validate",
                ),
                "validation_criteria": MCPToolParam(
                    type="string",
                    description="Validation criteria or standards to check against",
                ),
            },
            required=["cert_id", "validation_criteria"],
        ),
    ),
    MCPTool(
        name="report_compliance_findings",
        description="Return structured compliance findings, filterable by severity and endpoint.",
        inputSchema=MCPToolInputSchema(
            properties={
                "severity": MCPToolParam(
                    type="string",
                    description="Filter by severity: high, medium, low, or all",
                ),
                "endpoint": MCPToolParam(
                    type="string",
                    description="Filter by endpoint path (optional)",
                ),
                "limit": MCPToolParam(
                    type="integer",
                    description="Maximum results to return (default: 20)",
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="chat_query_verdicts",
        description="Query recent test verdicts from the Reflector.",
        inputSchema=MCPToolInputSchema(
            properties={
                "endpoint": MCPToolParam(
                    type="string", description="Filter by endpoint (optional)."
                ),
                "status_code": MCPToolParam(
                    type="integer", description="Filter by HTTP status code (optional)."
                ),
                "limit": MCPToolParam(
                    type="integer", description="Max results to return (default 10)."
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="chat_query_idioms",
        description="Query learned idiom patterns from the Reflector.",
        inputSchema=MCPToolInputSchema(
            properties={
                "pattern": MCPToolParam(
                    type="string", description="Filter by pattern substring (optional)."
                ),
                "limit": MCPToolParam(
                    type="integer", description="Max results to return (default 10)."
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="chat_explain_divergence",
        description="Explain a divergence using the Knowledge Mesh GraphRAG.",
        inputSchema=MCPToolInputSchema(
            properties={
                "endpoint": MCPToolParam(
                    type="string", description="API endpoint that diverged."
                ),
                "method": MCPToolParam(
                    type="string", description="HTTP method (default GET)."
                ),
            },
            required=["endpoint"],
        ),
    ),
    MCPTool(
        name="chat_run_test",
        description="Plan test scenarios for a specific endpoint (suggest-only, does not execute).",
        inputSchema=MCPToolInputSchema(
            properties={
                "endpoint": MCPToolParam(
                    type="string", description="API endpoint to plan tests for."
                ),
                "method": MCPToolParam(
                    type="string", description="HTTP method (default GET)."
                ),
                "spec_path": MCPToolParam(
                    type="string", description="Path to OpenAPI spec (optional)."
                ),
            },
            required=["endpoint"],
        ),
    ),
    # ── Issue #441: Conformance tools ──────────────────────────────────────
    MCPTool(
        name="run_conformance_check",
        description="Run cherenkov validate against a target URL and return the report summary.",
        inputSchema=MCPToolInputSchema(
            properties={
                "target_url": MCPToolParam(
                    type="string", description="Target API base URL."
                ),
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
                "method": MCPToolParam(
                    type="string", description="HTTP method (default GET)."
                ),
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
    MCPTool(
        name="mcp_registry_list",
        description="List all MCP servers registered in the mesh registry.",
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
    MCPTool(
        name="mcp_registry_publish",
        description="Register an external MCP server with the mesh registry.",
        inputSchema=MCPToolInputSchema(
            properties={
                "name": MCPToolParam(type="string", description="Server name."),
                "url": MCPToolParam(type="string", description="Server URL."),
                "tools": MCPToolParam(
                    type="string", description="JSON list of tool definitions."
                ),
                "resources": MCPToolParam(
                    type="string", description="JSON list of resource definitions."
                ),
                "version": MCPToolParam(
                    type="string", description="Server version (default 1.0.0)."
                ),
            },
            required=["name", "url", "tools"],
        ),
    ),
    # ── Event bus tools (ADR-016 UnifiedEventBus wiring) ─────────────────────
    MCPTool(
        name="event_bus_list",
        description="Fetch events from the UnifiedEventBus, optionally filtered "
        "by category. Pipeline runs publish stage_start, stage_success, "
        "test_generated, replan_trigger, and pipeline_complete events.",
        inputSchema=MCPToolInputSchema(
            properties={
                "category": MCPToolParam(
                    type="string",
                    description="Filter by event category (pipeline, hitl, healing, "
                    "knowledge, system). Omit for all.",
                ),
                "limit": MCPToolParam(
                    type="integer", description="Max events to return (default 50)."
                ),
                "after_id": MCPToolParam(
                    type="string",
                    description="Only fetch events whose event_id sorts after this id.",
                ),
            },
            required=[],
        ),
    ),
    MCPTool(
        name="event_bus_get",
        description="Fetch a single event from the UnifiedEventBus by event_id.",
        inputSchema=MCPToolInputSchema(
            properties={
                "event_id": MCPToolParam(
                    type="string", description="Event ID to fetch."
                ),
            },
            required=["event_id"],
        ),
    ),
    MCPTool(
        name="event_bus_publish",
        description="Publish a CHERENKOVEvent to the UnifiedEventBus for downstream "
        "consumers (sinks, sources, subscribed handlers).",
        inputSchema=MCPToolInputSchema(
            properties={
                "name": MCPToolParam(
                    type="string", description="Event name, e.g. pipeline.start."
                ),
                "category": MCPToolParam(
                    type="string",
                    description="Event category: pipeline | hitl | healing | knowledge | system.",
                ),
                "severity": MCPToolParam(
                    type="string", description="info | warning | error."
                ),
                "payload": MCPToolParam(
                    type="object", description="Arbitrary JSON event payload."
                ),
            },
            required=["name"],
        ),
    ),
    MCPTool(
        name="event_bus_stats",
        description="Return UnifiedEventBus statistics (queue size, sink/source/"
        "filter/handler counts, running state).",
        inputSchema=MCPToolInputSchema(properties={}, required=[]),
    ),
]

# ── Sentinel tools (Pillar 2: IDE Integrity Feedback) ────────────────────────
TOOLS.extend([
    MCPTool(
        name=t["name"],
        description=t["description"],
        inputSchema=MCPToolInputSchema(
            type=t["inputSchema"].get("type", "object"),
            properties={
                k: MCPToolParam(
                    type=v.get("type") or (v.get("anyOf", [{}])[0].get("type", "string") if "anyOf" in v else "string"),
                    description=v.get("description", "")
                )
                for k, v in t["inputSchema"]["properties"].items()
            },
            required=t["inputSchema"].get("required", []),
        ),
    )
    for t in SENTINEL_TOOL_DEFS
])

# ── Core CLI tools (#812) ─────────────────────────────────────────────────────
TOOLS.extend([
    MCPTool(
        name=t["name"],
        description=t["description"],
        inputSchema=MCPToolInputSchema(
            type=t["inputSchema"].get("type", "object"),
            properties={
                k: MCPToolParam(
                    type=v.get("type") or (v.get("anyOf", [{}])[0].get("type", "string") if "anyOf" in v else "string"),
                    description=v.get("description", "")
                )
                for k, v in (t["inputSchema"].get("properties") or {}).items()
            },
            required=t["inputSchema"].get("required", []),
        ),
    )
    for t in CORE_CLI_TOOL_DEFS
])

# ── Internal helpers ──────────────────────────────────────────────────────────

def _queue() -> HitlQueue:
    """Return an instantiated HitlQueue store instance.

    Returns:
        HitlQueue: Instantiated HITL queue object.
    """
    return HitlQueue()


def _ok_content(payload: Any) -> MCPToolCallResult:
    """Wrap a payload into a successful MCPToolCallResult object.

    Args:
        payload (Any): Result payload to JSON-serialize.

    Returns:
        MCPToolCallResult: Successful MCPToolCallResult with text content.
    """
    return MCPToolCallResult(
        content=[MCPContent(text=json.dumps(payload, default=str))],
        isError=False,
    )


def _err_content(message: str) -> MCPToolCallResult:
    """Wrap an error message into an error MCPToolCallResult object.

    Args:
        message (str): Diagnostic error message string.

    Returns:
        MCPToolCallResult: Error MCPToolCallResult with error message.
    """
    return MCPToolCallResult(
        content=[MCPContent(text=json.dumps({"error": message}))],
        isError=True,
    )


def _resource_content(uri: str, payload: Any) -> MCPResourceReadResult:
    """Wrap a payload into an MCPResourceReadResult object.

    Args:
        uri (str): Resource URI string.
        payload (Any): Payload to JSON-serialize.

    Returns:
        MCPResourceReadResult: Constructed resource read result object.
    """
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

def handle_resources_list(_params: dict[str, Any]) -> dict[str, Any]:
    """Handle resources/list requests by returning the available resource catalogue.

    Args:
        _params (dict[str, Any]): Request parameters (unused).

    Returns:
        dict[str, Any]: Serialized list of available MCP resources.
    """
    return MCPResourceListResult(resources=RESOURCES).model_dump()


def handle_resource_read(params: dict[str, Any]) -> dict[str, Any]:
    """Handle resources/read requests for specified resource URI.

    Args:
        params (dict[str, Any]): Request parameters containing 'uri'.

    Returns:
        dict[str, Any]: Serialized resource content dictionary.

    Raises:
        ValueError: If URI is missing or unknown.
    """
    uri: str = params.get("uri", "")

    if uri == "cherenkov://hitl/pending":
        q = _queue()
        items = q.list(status="pending")
        payload = {
            "schema_version": "hitl/v1",
            "ok": True,
            "command": "hitl.list",
            "payload": [i.model_dump() for i in items],
            "error": None,
        }
        return _resource_content(uri, payload).model_dump()

    if uri.startswith("cherenkov://hitl/item/"):
        item_id = uri.removeprefix("cherenkov://hitl/item/").strip()
        if not item_id:
            raise ValueError("item_id missing from URI")
        q = _queue()
        item = q.get(item_id)
        if item is None:
            payload = {
                "schema_version": "hitl/v1",
                "ok": False,
                "command": "hitl.show",
                "payload": None,
                "error": {
                    "code": "not_found",
                    "message": f"{item_id} not found.",
                    "detail": {},
                },
            }
        else:
            payload = {
                "schema_version": "hitl/v1",
                "ok": True,
                "command": "hitl.show",
                "payload": item.model_dump(),
                "error": None,
            }
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

    if uri == "cherenkov://gates":
        payload = {
            "schema_version": "verify/v1",
            "description": "CHERENKOV 6-gate REVIEW stage — integrity contract for AI-generated test suites.",
            "gates": [
                {
                    "id": "syntax",
                    "name": "Syntax Gate",
                    "catches": "Empty code; markdown code-fence leakage",
                    "pass_requires": "Non-empty code with no stray ``` fences",
                },
                {
                    "id": "structure",
                    "name": "Structure Gate",
                    "catches": "Missing framework or client imports",
                    "pass_requires": "Both '@playwright/test' and '../client' imports present",
                },
                {
                    "id": "ast",
                    "name": "AST Gate",
                    "catches": "Raw fetch/axios bypass of the openapi-fetch client",
                    "pass_requires": "client.GET|POST|PUT|DELETE|PATCH call; no raw fetch/axios/throw",
                },
                {
                    "id": "assertion",
                    "name": "Assertion Gate",
                    "catches": "Weakened assertions (e.g. toBeLessThan instead of toBe); deleted body checks",
                    "pass_requires": "At least one .toBe(<3-digit-status>) AND one toHaveProperty()/typeof check",
                },
                {
                    "id": "tsc",
                    "name": "TypeScript Compilation Gate",
                    "catches": "Type errors; assertions against fields absent from spec-generated types",
                    "pass_requires": "tsc --noEmit passes with zero errors in the test file",
                },
                {
                    "id": "prism-dryrun",
                    "name": "Prism Dynamic Dry-Run Gate",
                    "catches": "Hallucinated oracles; wrong status codes; fields absent from spec response",
                    "pass_requires": "Test passes execution against a spec-derived Prism mock server",
                    "requires_docker": True,
                },
            ],
            "integrity_contract": (
                "Gates are declarative and independent of the suite's own claims. "
                "CHERENKOV re-derives expected behaviour from the spec — it does not "
                "trust what the assertions say, only what the spec says they must say."
            ),
        }
        return _resource_content(uri, payload).model_dump()

    raise ValueError(f"Unknown resource URI: {uri!r}")

# ── Tool call handlers ────────────────────────────────────────────────────────

def handle_tools_list(_params: dict[str, Any]) -> dict[str, Any]:
    """Handle tools/list requests by returning the registered tool catalogue.

    Args:
        _params (dict[str, Any]): Request parameters (unused).

    Returns:
        dict[str, Any]: Serialized list of available MCP tools.
    """
    return MCPToolListResult(tools=TOOLS).model_dump()


def handle_tool_call(params: dict[str, Any]) -> dict[str, Any]:
    """Route a tools/call request to the correct handler with policy enforcement.

    Args:
        params (dict[str, Any]): Request parameters containing 'name' and 'arguments'.

    Returns:
        dict[str, Any]: Tool call result serialized dictionary.
    """

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
        if name == "verify_suite":
            return _tool_verify_suite(arguments).model_dump()
        if name == "verify_system":
            return _tool_verify_system(arguments).model_dump()
        if name == "check_suite":
            return _tool_check_suite(arguments).model_dump()
        if name == "verify":
            return _tool_verify(arguments).model_dump()
        if name == "generate":
            return _tool_generate(arguments).model_dump()
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
        if name == "visual_diff_baseline_enhanced":
            return _tool_visual_diff_enhanced(arguments).model_dump()
        if name == "run_k6_perf":
            return _tool_run_perf(arguments).model_dump()
        if name == "query_rag_index":
            return _tool_query_rag(arguments).model_dump()
        if name == "export_jira_ticket":
            return _tool_export_jira(arguments).model_dump()
        if name == "export_linear_ticket":
            return _tool_export_linear(arguments).model_dump()
        if name == "export_github_ticket":
            return _tool_export_github(arguments).model_dump()
        if name == "scan_mena_compliance":
            return _tool_scan_mena(arguments).model_dump()
        if name == "scan_mena_compliance_enhanced":
            return _tool_scan_mena_enhanced(arguments).model_dump()
        if name == "validate_governance_certification":
            return _tool_validate_governance(arguments).model_dump()
        if name == "report_compliance_findings":
            return _tool_report_compliance(arguments).model_dump()
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
        if name == "mcp_registry_list":
            return _tool_registry_list(arguments).model_dump()
        if name == "mcp_registry_publish":
            return _tool_registry_publish(arguments).model_dump()
        if name == "event_bus_list":
            return _tool_event_bus_list(arguments).model_dump()
        if name == "event_bus_get":
            return _tool_event_bus_get(arguments).model_dump()
        if name == "event_bus_publish":
            return _tool_event_bus_publish(arguments).model_dump()
        if name == "event_bus_stats":
            return _tool_event_bus_stats(arguments).model_dump()
        if name == "auto_heal_code":
            return _tool_auto_heal_code(arguments).model_dump()
        # ── Sentinel tools (Pillar 2 — IDE Integrity Feedback) ────────────────────
        if name in SENTINEL_HANDLERS:
            result = SENTINEL_HANDLERS[name](arguments)
            return MCPToolCallResult(
                content=[MCPContent(type="text", text=str(result))],
                isError=False,
            ).model_dump()
            
        # ── Core CLI tools (#812) ────────────────────────────────────────────────
        if name in CORE_CLI_HANDLERS:
            result = CORE_CLI_HANDLERS[name](arguments)
            return MCPToolCallResult(
                content=[MCPContent(type="text", text=json.dumps(result, default=str))],
                isError=False,
            ).model_dump()
    except ValidationError as exc:
        return _err_content(f"Invalid input: {exc}").model_dump()
    except Exception as exc:
        return _err_content(f"Handler error: {exc}").model_dump()

    # ── Mesh forwarding: try registered external servers (E2.2) ───────────────
    try:
        result = get_registry().forward_tool_call(name, arguments)
        if result is not None:
            return result
    except MCPClientError as exc:
        return _err_content(f"Mesh forward error for '{name}': {exc}").model_dump()
    except Exception as exc:
        return _err_content(f"Mesh routing error: {exc}").model_dump()

    return _err_content(f"Unknown tool: {name!r}").model_dump()

# ── Individual tools ──────────────────────────────────────────────────────────

def _tool_hitl_list(args: dict[str, Any]) -> MCPToolCallResult:
    """List HITL queue items matching criteria.

    Args:
        args (dict[str, Any]): Dictionary of arguments matching HitlListInput.

    Returns:
        MCPToolCallResult: Result containing hitl/v1 list payload.
    """
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
    """Approve a pending HITL queue item.

    Args:
        args (dict[str, Any]): Dictionary of arguments matching HitlApproveInput.

    Returns:
        MCPToolCallResult: Result containing hitl/v1 approval payload.
    """
    inp = HitlApproveInput.model_validate(args)
    q = _queue()
    env = q.approve(item_id=inp.item_id, actor=inp.actor, source="mcp")
    return _ok_content(env.model_dump())


def _tool_hitl_reject(args: dict[str, Any]) -> MCPToolCallResult:
    """Reject a pending HITL queue item.

    Args:
        args (dict[str, Any]): Dictionary of arguments matching HitlRejectInput.

    Returns:
        MCPToolCallResult: Result containing hitl/v1 rejection payload.
    """
    inp = HitlRejectInput.model_validate(args)
    q = _queue()
    env = q.reject(
        item_id=inp.item_id, actor=inp.actor, reason=inp.reason, source="mcp"
    )
    return _ok_content(env.model_dump())


def _tool_verify_suite(args: dict[str, Any]) -> MCPToolCallResult:
    """Verify the integrity of a test suite via the 6-gate REVIEW stage.

    Returns a VerificationReport (verify/v1) flagging weakened assertions,
    deleted checks, or hallucinated oracles. Suggest-only — never auto-applies.

    Args:
        args (dict[str, Any]): Arguments matching VerifySuiteInput.

    Returns:
        MCPToolCallResult: Result containing verify/v1 VerificationReport payload.
    """
    inp = VerifySuiteInput.model_validate(args)


    # ── Load test code ────────────────────────────────────────────────────────
    if inp.suite_inline:
        code = inp.suite_inline
        suite_ref = f"inline:{hashlib.sha256(code.encode()).hexdigest()[:12]}"
    elif inp.suite_path:
        resolved = os.path.realpath(os.path.abspath(inp.suite_path))
        cwd = os.path.realpath(os.path.abspath("."))
        if not resolved.startswith(cwd):
            return _err_content("suite_path must be within the working directory.")
        if not os.path.isfile(resolved):
            return _err_content(f"File not found: {inp.suite_path}")
        with open(resolved, encoding="utf-8") as fh:
            code = fh.read()
        suite_ref = inp.suite_path
    else:
        return _err_content("One of suite_path or suite_inline is required.")

    code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
    scenario_id = inp.scenario_id or f"mcp_verify_{code_hash}"
    spec_source = inp.spec_source or "stub/openapi_3_1.yaml"

    # ── Resolve spec path ─────────────────────────────────────────────────────
    spec_resolved = os.path.realpath(os.path.abspath(spec_source))
    if not os.path.isfile(spec_resolved):
        return _err_content(f"spec_source not found: {spec_source}")

    # ── Run the 6-gate REVIEW stage ───────────────────────────────────────────
    try:
        from cherenkov.core.contracts import (
            GenerateOutput,
            StageMeta,
            Status,
            Verdict,
        )
        from cherenkov.core.errors import LoggerConfig
        from cherenkov.stages.review import ReviewStage

        LoggerConfig.suppress_stderr = True  # keep MCP output clean

        generate_out = GenerateOutput(
            scenario_id=scenario_id,
            test_code=code,
            endpoint=inp.endpoint,
            method=inp.method or "POST",
            status=Status.OK,
            metadata=StageMeta(stage="GENERATE"),
        )

        t0 = time.monotonic()
        stage = ReviewStage(run_id=f"mcp-{scenario_id}")
        review = stage.run(generate_out, spec_path=spec_resolved)
        duration_ms = int((time.monotonic() - t0) * 1000)

    except Exception as exc:
        return _err_content(f"verify_suite error running ReviewStage: {exc}")

    # ── Map ReviewOutput → VerificationReport (verify/v1) ────────────────────
    verdict_map = {
        Verdict.AUTO_APPROVE: "pass",
        Verdict.HITL: "warn",
        Verdict.REGENERATE: "fail",
    }
    report_verdict = verdict_map.get(review.verdict, "warn")

    # Classify failed gates into integrity categories
    weakened_assertions = []
    deleted_checks = []
    hallucinated_oracles = []
    findings = []

    for gate in review.gates:
        if gate.passed or gate.skipped:
            continue

        finding_id = f"{scenario_id}:{gate.gate}"
        severity = "high" if gate.gate in ("assertion", "prism-dryrun") else "med"

        if gate.gate == "assertion":
            detail_lower = gate.detail.lower()
            if "status" in detail_lower:
                # Weakened assertion — specific status code check failed
                weakened_assertions.append(
                    {
                        "test": scenario_id,
                        "before": "expect(response.status).toBe(<spec-status>)",
                        "after": "(loosened or missing — no .toBe(<3-digit-code>) found)",
                        "evidence": gate.detail,
                    }
                )
            elif "body" in detail_lower or "property" in detail_lower:
                # Deleted body-shape check
                deleted_checks.append(
                    {
                        "test": scenario_id,
                        "evidence": gate.detail,
                    }
                )
        elif gate.gate == "prism-dryrun":
            # Dynamic gate failure — hallucinated oracle or wrong expected value
            hallucinated_oracles.append(
                {
                    "test": scenario_id,
                    "missing_target": "Field/status not present in spec-derived Prism response",
                    "evidence": gate.detail,
                }
            )

        findings.append(
            {
                "id": finding_id,
                "severity": severity,
                "category": gate.gate,
                "title": f"Gate '{gate.gate}' failed",
                "evidence": gate.detail,
                "reproduction": (
                    "Run: python demos/catch-the-ai-cheating/run_demo.py\n"
                    "Or call verify_suite with the same suite_inline."
                ),
                "suggested_fix": (
                    "Review the gate description at cherenkov://gates for what "
                    "a passing test must contain. Fix applied as suggestion only — "
                    "CHERENKOV never auto-modifies test code (D7 invariant)."
                ),
            }
        )

    report = {
        "schema_version": "verify/v1",
        "report_id": str(uuid.uuid4()),
        "target": {
            "kind": "suite",
            "ref": suite_ref,
            "hash": code_hash,
        },
        "verdict": report_verdict,
        "integrity": {
            "weakened_assertions": weakened_assertions,
            "deleted_checks": deleted_checks,
            "hallucinated_oracles": hallucinated_oracles,
        },
        "findings": findings,
        "gates": [
            {
                "gate": g.gate,
                "passed": g.passed,
                "skipped": g.skipped,
                "detail": g.detail,
            }
            for g in review.gates
        ],
        "coverage": {
            "claimed": review.quality_score,
            "verified": review.quality_score,
        },
        "meta": {
            "engine_version": "1.0.0",
            "model_used": None,
            "duration_ms": duration_ms,
            "local_only": True,
        },
    }

    return _ok_content(report)

def _tool_verify_system(args: dict[str, Any]) -> MCPToolCallResult:
    """Verify a live server against its OpenAPI spec — find spec↔impl divergences.

    Wraps the Skeptic→Witness divergence engine (cherenkov verify CLI).
    Offline mode by default — no LLM or Ollama required.

    Args:
        args (dict[str, Any]): Arguments matching VerifySystemInput.

    Returns:
        MCPToolCallResult: Result containing verify/v1 VerificationReport payload.
    """
    inp = VerifySystemInput.model_validate(args)


    # ── Load spec (optional) ──────────────────────────────────────────────────
    spec_dict: dict | None = None
    if inp.spec_source:
        if inp.spec_source.startswith("http://") or inp.spec_source.startswith("https://"):
            try:
                with urllib.request.urlopen(inp.spec_source, timeout=15) as resp:
                    spec_dict = json.loads(resp.read())
            except Exception as exc:
                return _err_content(f"Could not fetch spec from {inp.spec_source}: {exc}")
        else:
            resolved = os.path.realpath(os.path.abspath(inp.spec_source))
            cwd = os.path.realpath(os.path.abspath("."))
            if not resolved.startswith(cwd):
                return _err_content("spec_source must be within the working directory.")
            if not os.path.isfile(resolved):
                return _err_content(f"spec_source not found: {inp.spec_source}")
            try:
                with open(resolved, encoding="utf-8") as fh:
                    spec_dict = json.load(fh)
            except Exception as exc:
                return _err_content(f"Could not parse spec: {exc}")

    # ── Run divergence engine ──────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        reports = run_proof(
            base_url=inp.base_url,
            spec=spec_dict,
            use_llm=inp.use_llm,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        return _err_content(f"verify_system error running divergence engine: {exc}")

    # ── Map DivergenceReport list → VerificationReport (verify/v1) ────────────
    findings = []
    for r in reports:
        sev = getattr(r.severity, "value", str(r.severity))
        dc = getattr(r.divergence_class, "value", str(r.divergence_class))
        ev = r.evidence
        reproduction = ""
        if r.repro_steps:
            reproduction = "\n".join(r.repro_steps[:3])
        findings.append(
            {
                "id": r.id,
                "severity": sev,
                "category": dc,
                "title": f"{dc} — {r.endpoint or 'unknown'}",
                "evidence": ev.request_summary if ev else "",
                "diff": ev.diff if ev else "",
                "claim_a": r.claim_a,
                "claim_b": r.claim_b,
                "reproduction": reproduction,
                "suggested_fix": "Investigate the divergence and fix the implementation or spec.",
            }
        )

    verdict = "fail" if findings else "pass"
    report = {
        "schema_version": "verify/v1",
        "report_id": inp.run_id or str(uuid.uuid4()),
        "target": {
            "kind": "system",
            "ref": inp.base_url,
            "spec": inp.spec_source or "built-in Petstore demo",
        },
        "verdict": verdict,
        "divergences": findings,
        "summary": {
            "total": len(findings),
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "medium": sum(1 for f in findings if f["severity"] == "medium"),
            "low": sum(1 for f in findings if f["severity"] == "low"),
        },
        "meta": {
            "engine_version": "1.0.0",
            "mode": "llm" if inp.use_llm else "offline",
            "duration_ms": duration_ms,
            "local_only": True,
        },
    }

    return _ok_content(report)

def _tool_check_suite(args: dict[str, Any]) -> MCPToolCallResult:
    """Static integrity check of a candidate suite (#812).

    Machine-facing twin of `cherenkov check-suite` (E2.5). Detects the three
    canonical "AI cheating" patterns against a baseline + spec:
      WEAKENED, DELETED, HALLUCINATED.

    Args:
        args (dict[str, Any]): Arguments matching CheckSuiteInput.

    Returns:
        MCPToolCallResult: Result containing check-suite/v1 payload.
    """
    inp = CheckSuiteInput.model_validate(args)


    # ── Resolve candidate code (path xor inline) ─────────────────────────────
    if inp.candidate_path:
        resolved = _resolve_within_cwd(inp.candidate_path, must_exist=True)
        if isinstance(resolved, str):
            return _err_content(resolved)
        candidate_code = resolved.read_text(encoding="utf-8")
        candidate_ref = inp.candidate_path
        is_ts = resolved.suffix == ".ts"
    elif inp.candidate_inline:
        candidate_code = inp.candidate_inline
        candidate_ref = f"inline:{hashlib.sha256(candidate_code.encode()).hexdigest()[:12]}"
        try:
            compile(candidate_code, "<candidate>", "exec")
            is_ts = False
        except SyntaxError:
            is_ts = True
    else:
        return _err_content("One of candidate_path or candidate_inline is required.")

    # ── Resolve baseline (optional; required for WEAKENED/DELETED) ───────────
    baseline_code = None
    if inp.baseline_path:
        resolved = _resolve_within_cwd(inp.baseline_path, must_exist=True)
        if isinstance(resolved, str):
            return _err_content(resolved)
        baseline_code = resolved.read_text(encoding="utf-8")
    elif inp.baseline_inline:
        baseline_code = inp.baseline_inline

    # ── Resolve spec (optional; required for HALLUCINATED on Python) ─────────
    spec_path = None
    if inp.spec_path:
        resolved = _resolve_within_cwd(inp.spec_path, must_exist=True)
        if isinstance(resolved, str):
            return _err_content(resolved)
        spec_path = resolved

    # ── Run the static analysis engine ───────────────────────────────────────
    try:
        if is_ts:
            from cherenkov.cli.commands.check_suite import _check_typescript

            findings = _check_typescript(candidate_code, baseline_code, spec_path)
        else:
            from cherenkov.cli.commands.check_suite import check_integrity

            findings = check_integrity(spec_path, baseline_code or "", candidate_code)
    except Exception as exc:
        return _err_content(f"check_suite error running static analysis: {exc}")

    counts = {"WEAKENED": 0, "DELETED": 0, "HALLUCINATED": 0}
    for f in findings:
        tag = f.split()[0]
        if tag in counts:
            counts[tag] += 1

    report = {
        "schema_version": "check-suite/v1",
        "candidate": candidate_ref,
        "language": "typescript" if is_ts else "python",
        "verdict": "fail" if (findings and inp.fail_on_finding) else ("pass" if not findings else "warn"),
        "ok": not findings,
        "findings": findings,
        "summary": counts,
        "baseline_present": baseline_code is not None,
        "spec_present": spec_path is not None,
        "meta": {
            "engine": "cherenkov check-suite (E2.5)",
            "local_only": True,
            "suggest_only": True,
        },
    }
    return _ok_content(report)

def _tool_verify(args: dict[str, Any]) -> MCPToolCallResult:
    """Verify a live server against its OpenAPI spec (#812).

    Machine-facing twin of `cherenkov verify` (E1.1). Runs the
    Skeptic→Witness divergence engine in offline mode by default, optionally
    extending the report with spec-coverage and health-score sections.

    Args:
        args (dict[str, Any]): Arguments matching VerifyInput.

    Returns:
        MCPToolCallResult: Result containing verify/v1 VerificationReport payload.
    """
    inp = VerifyInput.model_validate(args)


    # ── Load spec (optional) ──────────────────────────────────────────────────
    spec_dict: dict | None = None
    if inp.spec_source:
        if inp.spec_source.startswith("http://") or inp.spec_source.startswith("https://"):
            try:
                with urllib.request.urlopen(inp.spec_source, timeout=15) as resp:
                    spec_dict = json.loads(resp.read())
            except Exception as exc:
                return _err_content(f"Could not fetch spec from {inp.spec_source}: {exc}")
        else:
            resolved = _resolve_within_cwd(inp.spec_source, must_exist=True)
            if isinstance(resolved, str):
                return _err_content(resolved)
            try:
                import yaml  # type: ignore[import]

                text = resolved.read_text(encoding="utf-8")
                if resolved.suffix in (".yaml", ".yml"):
                    spec_dict = yaml.safe_load(text)
                else:
                    spec_dict = json.loads(text)
            except Exception as exc:
                return _err_content(f"Could not parse spec: {exc}")

    # ── Load known identifiers (file path or inline JSON) ────────────────────
    known_identifiers: dict[str, list[str]] | None = None
    if inp.identifiers:
        raw: str = inp.identifiers
        if os.path.isfile(raw) and _resolve_within_cwd(raw, must_exist=True) is not None:
            try:
                with open(raw, encoding="utf-8") as fh:
                    known_identifiers = json.load(fh)
            except Exception as exc:
                return _err_content(f"Could not load identifiers: {exc}")
        else:
            try:
                known_identifiers = json.loads(raw)
            except Exception as exc:
                return _err_content(f"identifiers must be a JSON file path or inline JSON: {exc}")

    # ── Run divergence engine ─────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        reports = run_proof(
            base_url=inp.base_url,
            spec=spec_dict,
            use_llm=inp.use_llm,
            max_probes=inp.max_probes,
            known_identifiers=known_identifiers,
            allow_mutations=inp.allow_mutations,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        return _err_content(f"verify error running divergence engine: {exc}")

    # ── Map DivergenceReport list → VerificationReport (verify/v1) ────────────
    findings = []
    for r in reports:
        sev = getattr(r.severity, "value", str(r.severity))
        dc = getattr(r.divergence_class, "value", str(r.divergence_class))
        ev = r.evidence
        reproduction = ""
        if r.repro_steps:
            reproduction = "\n".join(r.repro_steps[:3])
        findings.append(
            {
                "id": r.id,
                "severity": sev,
                "category": dc,
                "title": f"{dc} — {r.endpoint or 'unknown'}",
                "evidence": ev.request_summary if ev else "",
                "diff": ev.diff if ev else "",
                "claim_a": r.claim_a,
                "claim_b": r.claim_b,
                "reproduction": reproduction,
                "suggested_fix": "Investigate the divergence and fix the implementation or spec.",
            }
        )

    report: dict[str, Any] = {
        "schema_version": "verify/v1",
        "report_id": inp.run_id or str(uuid.uuid4()),
        "target": {
            "kind": "system",
            "ref": inp.base_url,
            "spec": inp.spec_source or "built-in Petstore demo",
        },
        "verdict": "fail" if findings else "pass",
        "divergences": findings,
        "summary": {
            "total": len(findings),
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "medium": sum(1 for f in findings if f["severity"] == "medium"),
            "low": sum(1 for f in findings if f["severity"] == "low"),
        },
        "meta": {
            "engine_version": "1.0.0",
            "mode": "llm" if inp.use_llm else "offline",
            "duration_ms": duration_ms,
            "local_only": True,
        },
    }

    # ── Optional coverage / health sections ───────────────────────────────────
    if (inp.coverage_report or inp.health_score) and spec_dict is not None:
        try:
            from cherenkov.divergence.coverage import compute_coverage
            from cherenkov.divergence.health import compute_health_score

            probed_endpoints = [
                (parts[0], parts[1])
                if (parts := r.endpoint.split(" ", 1)) and len(parts) == 2
                else (r.endpoint or "", "")
                for r in reports
            ]
            cov = compute_coverage(spec_dict, reports, probed_endpoints=probed_endpoints)
            if inp.coverage_report:
                report["coverage"] = {
                    "coverage_pct": cov.coverage_pct,
                    "tested_count": cov.tested_count,
                    "untested_count": cov.untested_count,
                    "total_endpoints": cov.total_endpoints,
                    "gap_endpoints": [
                        {"method": ep.method, "path": ep.path, "operation_id": ep.operation_id}
                        for ep in cov.gap_endpoints
                    ],
                }
            if inp.health_score:
                health = compute_health_score(cov)
                report["health"] = {
                    "grade": health.grade,
                    "score": health.score,
                    "coverage_component": health.coverage_component,
                    "integrity_component": health.integrity_component,
                    "divergence_component": health.divergence_component,
                    "deductions": [str(d) for d in health.deductions],
                }
        except Exception as exc:
            report["warning"] = f"coverage/health computation failed: {exc}"

    return _ok_content(report)

def _tool_generate(args: dict[str, Any]) -> MCPToolCallResult:
    """Generate Playwright E2E tests from an OpenAPI spec (#812).

    Machine-facing twin of `cherenkov generate`. Runs Ingest→Plan→
    Generate(→Review→Repair). Returns test code inline by default; pass
    output_dir to write files to disk. D7: only writes to the caller's
    explicitly requested output_dir.

    Args:
        args (dict[str, Any]): Arguments matching GenerateInput.

    Returns:
        MCPToolCallResult: Result containing generate/v1 payload.
    """
    inp = GenerateInput.model_validate(args)


    spec_resolved = _resolve_within_cwd(inp.spec_path, must_exist=True)
    if isinstance(spec_resolved, str):
        return _err_content(spec_resolved)
    spec = str(spec_resolved)

    try:
        from cherenkov.stages.generate import GenerateStage
        from cherenkov.stages.ingest import IngestStage
        from cherenkov.stages.plan import PlanStage
        from cherenkov.stages.repair import RepairLoop
        from cherenkov.stages.review import default_review_scratch_dir

        write_dir = None
        if inp.output_dir:
            resolved_out = _resolve_within_cwd(inp.output_dir, must_exist=False)
            if isinstance(resolved_out, str):
                return _err_content(resolved_out)
            write_dir = str(resolved_out)
            os.makedirs(write_dir, exist_ok=True)
        else:
            os.makedirs(default_review_scratch_dir(), exist_ok=True)

        ingest_stage = IngestStage("mcp_generate")
        ingest_out = ingest_stage.run(spec)
        plan_stage = PlanStage("mcp_generate")
        plan_out = plan_stage.run(ingest_out)

        ep_map = {
            ep.path + ":" + ep.method: ep for ep in ingest_out.endpoints
        }
        generated: list[dict[str, Any]] = []
        for sc in plan_out.scenarios:
            ep = ep_map.get(sc.endpoint + ":" + sc.method)
            ep_operation = ep.operation if ep else None
            ep_schemas = ep.schemas if ep else None
            entry: dict[str, Any] = {
                "scenario_id": sc.mutation_id or sc.endpoint,
                "endpoint": sc.endpoint,
                "method": sc.method,
                "case_type": sc.case_type,
                "expected_status": sc.expected_status,
            }
            try:
                if inp.repair:
                    loop = RepairLoop(
                        run_id=f"mcp_generate_{sc.mutation_id or 'scenario'}",
                        max_attempts=inp.max_attempts,
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
                        spec_path=spec,
                    )
                    if review is not None:
                        entry["verdict"] = getattr(
                            getattr(review, "verdict", None), "value", None
                        )
                        entry["quality_score"] = getattr(review, "quality_score", None)
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
            except Exception as exc:
                entry["error"] = str(exc)
                generated.append(entry)
                continue

            if write_dir is not None:
                file_name = f"{sc.mutation_id or sc.endpoint.replace('/', '_')}.spec.ts"
                file_path = os.path.join(write_dir, file_name)
                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.write(gen_out.test_code)
                entry["file_path"] = file_path
            else:
                entry["test_code"] = gen_out.test_code
            generated.append(entry)

        return _ok_content(
            {
                "schema_version": "generate/v1",
                "spec_path": spec,
                "output_dir": write_dir,
                "repair": inp.repair,
                "max_attempts": inp.max_attempts,
                "generated": len(generated),
                "success_count": sum(1 for g in generated if "error" not in g),
                "scenarios": generated,
                "meta": {
                    "engine": "cherenkov generate (ChatTester repair loop)",
                    "local_only": False,
                    "suggest_only": False,
                },
            }
        )
    except Exception as exc:
        return _err_content(f"generate error: {exc}")

def _tool_validate_gate(args: dict[str, Any]) -> MCPToolCallResult:
    """Runs ValidationGate in report-only mode.

    Supports optional provider param for sandbox backend selection.
    Suggest-only: returns a report dict; never auto-commits or auto-applies.
    D7: does not touch any test file.

    Args:
        args (dict[str, Any]): Arguments matching ValidateRunGateInput.

    Returns:
        MCPToolCallResult: Result containing ValidationReport payload.
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

def _tool_policy_list(_args: dict[str, Any]) -> MCPToolCallResult:
    """Return current policy rules for all profiles.

    Args:
        _args (dict[str, Any]): Request arguments (unused).

    Returns:
        MCPToolCallResult: Result containing current policy dictionary.
    """
    return _ok_content(_policy.list_policy())


def _tool_policy_reload(_args: dict[str, Any]) -> MCPToolCallResult:
    """Reload policy from cherenkov-policy.json.

    Args:
        _args (dict[str, Any]): Request arguments (unused).

    Returns:
        MCPToolCallResult: Result containing reload status and updated policy.
    """
    _policy.reload()
    return _ok_content({"status": "reloaded", "policy": _policy.list_policy()})


def _tool_registry_list(_args: dict[str, Any]) -> MCPToolCallResult:
    """List registered MCP servers in the mesh registry.

    Args:
        _args (dict[str, Any]): Request arguments (unused).

    Returns:
        MCPToolCallResult: Result containing list of registered servers.
    """
    from cherenkov.mcp.mesh_router import get_registry

    servers = get_registry().list_servers()
    return _ok_content({"servers": servers})


def _tool_registry_publish(args: dict[str, Any]) -> MCPToolCallResult:
    """Register an external MCP server with the mesh registry.

    Args:
        args (dict[str, Any]): Dictionary containing name, url, tools, resources, and optional version.

    Returns:
        MCPToolCallResult: Result containing status and registration_id.
    """

    from cherenkov.mcp.mesh_router import get_registry

    inp = args
    parsed_url = urlparse(inp.get("url", ""))
    if parsed_url.scheme not in ("http", "https"):
        return _err_content("Only http/https server URLs allowed")
    host = parsed_url.hostname or ""
    blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal"}
    if host.lower() in blocked_hosts:
        return _err_content("Internal network URLs not allowed")
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return _err_content("Internal network URLs not allowed")
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            return _err_content("Cannot resolve server host")
        for info in infos:
            try:
                resolved = ipaddress.ip_address(info[4][0])
                if resolved.is_private or resolved.is_loopback or resolved.is_link_local or resolved.is_reserved:
                    return _err_content("Internal network URLs not allowed")
            except ValueError:
                pass
    tools = json.loads(inp.get("tools", "[]"))
    resources = json.loads(inp.get("resources", "[]"))
    reg_id = get_registry().register_server(
        name=inp["name"],
        url=inp["url"],
        tools=tools,
        resources=resources,
        version=inp.get("version", "1.0.0"),
    )
    return _ok_content({"status": "ok", "registration_id": reg_id})

# ── Event bus tools (ADR-016 UnifiedEventBus wiring) ─────────────────────────

def _tool_event_bus_list(args: dict[str, Any]) -> MCPToolCallResult:
    """Fetch events from the UnifiedEventBus.

    Args:
        args (dict[str, Any]): Arguments matching EventBusListInput.

    Returns:
        MCPToolCallResult: Result containing events list.
    """
    inp = EventBusListInput.model_validate(args)
    bus = get_event_bus()
    events = bus.fetch_events(
        after_id=inp.after_id, limit=inp.limit, category=inp.category
    )
    payload = {
        "schema_version": "events/v1",
        "ok": True,
        "events": [e.to_dict() for e in events],
        "total": len(events),
    }
    return _ok_content(payload)


def _tool_event_bus_get(args: dict[str, Any]) -> MCPToolCallResult:
    """Fetch a single event from the UnifiedEventBus by id.

    Args:
        args (dict[str, Any]): Arguments matching EventBusGetInput.

    Returns:
        MCPToolCallResult: Result containing requested event details.
    """
    inp = EventBusGetInput.model_validate(args)
    event = get_event_bus().get_event(inp.event_id)
    if event is None:
        return _err_content(f"Event not found: {inp.event_id}")
    return _ok_content({"schema_version": "events/v1", "ok": True, "event": event.to_dict()})


def _tool_event_bus_publish(args: dict[str, Any]) -> MCPToolCallResult:
    """Publish a CHERENKOVEvent to the UnifiedEventBus.

    Args:
        args (dict[str, Any]): Arguments matching EventBusPublishInput.

    Returns:
        MCPToolCallResult: Result containing created event_id.
    """
    inp = EventBusPublishInput.model_validate(args)
    event = to_cherenkov_event(inp.name, inp.payload, run_id="mcp")
    event.category = _coerce_event_category(inp.category)
    event.severity = _coerce_event_severity(inp.severity)
    get_event_bus().publish(event)
    return _ok_content({"schema_version": "events/v1", "ok": True, "event_id": event.event_id})


def _tool_event_bus_stats(_args: dict[str, Any]) -> MCPToolCallResult:
    """Return UnifiedEventBus statistics.

    Args:
        _args (dict[str, Any]): Request arguments (unused).

    Returns:
        MCPToolCallResult: Result containing event bus stats payload.
    """
    return _ok_content({"schema_version": "events/v1", "ok": True, "stats": get_event_bus().get_stats()})


def _coerce_event_category(value: str):
    """Coerce string into EventCategory enum, defaulting to PIPELINE.

    Args:
        value (str): Category string.

    Returns:
        EventCategory: Matching EventCategory enum value.
    """
    from cherenkov.core.events import EventCategory

    try:
        return EventCategory(value)
    except ValueError:
        return EventCategory.PIPELINE


def _coerce_event_severity(value: str):
    """Coerce string into EventSeverity enum, defaulting to INFO.

    Args:
        value (str): Severity string.

    Returns:
        EventSeverity: Matching EventSeverity enum value.
    """
    from cherenkov.core.events import EventSeverity

    try:
        return EventSeverity(value)
    except ValueError:
        return EventSeverity.INFO


# ── Track B/C tools ───────────────────────────────────────────────────────────

def _tool_visual_diff(args: dict[str, Any]) -> MCPToolCallResult:
    """Run visual snapshot regression and UI matching checks.

    Args:
        args (dict[str, Any]): Arguments containing optional target_url string.

    Returns:
        MCPToolCallResult: Result containing visual validation report payload.
    """
    target_url = args.get("target_url")
    try:
        from cherenkov.execution.visual_diff import VisualDiffEngine

        engine = VisualDiffEngine()
        report = engine.run_visual_validation(api_url=target_url)
        return _ok_content(report)
    except Exception as exc:
        return _err_content(f"VisualDiff error: {exc}")


def _tool_visual_diff_enhanced(args: dict[str, Any]) -> MCPToolCallResult:
    """Enhanced visual diff tool with baseline management, configurable thresholds, and report output."""
    try:
        inp = VisualDiffBaselineInput.model_validate(args)
        target_url = (
            inp.target_url or os.environ.get("API_URL") or "http://localhost:8000"
        )
        baseline_dir = inp.baseline_dir or os.path.join(
            os.getcwd(), "stub", "visual_baselines"
        )
        diff_threshold = inp.diff_threshold or 0.5
        comparison_mode = inp.comparison_mode or "pixel"
        report_path = inp.report_path or os.path.join(
            os.getcwd(), ".cherenkov", "visual_report.json"
        )

        from cherenkov.execution.visual_diff import VisualDiffEngine

        engine = VisualDiffEngine()
        base_report = engine.run_visual_validation(api_url=target_url)

        # Build enriched report with baseline management fields
        enriched = {
            "target_url": target_url,
            "baseline_dir": baseline_dir,
            "diff_threshold": diff_threshold,
            "comparison_mode": comparison_mode,
            "report_path": report_path,
            "passed": base_report.get("passed", False),
            "exit_code": base_report.get("exit_code", -1),
            "mismatch_detected": base_report.get("mismatch_detected", True),
            "message": base_report.get("message", "Visual diff completed."),
        }

        # Write report to disk
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2)

        return _ok_content(enriched)
    except Exception as exc:
        return _err_content(f"VisualDiff enhanced error: {exc}")

def _tool_run_perf(args: dict[str, Any]) -> MCPToolCallResult:
    try:
        inp = RunK6PerfInput.model_validate(args)
        target_url = inp.target_url
        scenario_name = inp.scenario_name or "soak"

        duration_sec = 30
        if inp.duration is not None:
            if isinstance(inp.duration, int):
                duration_sec = inp.duration
            else:
                dur_str = str(inp.duration).strip().rstrip("s").rstrip("S")
                try:
                    duration_sec = int(dur_str)
                except ValueError:
                    duration_sec = 30

        vus = inp.vus if inp.vus is not None else 10
        endpoint = inp.endpoint or "/"
        method = inp.method or "GET"
        use_ml = bool(inp.use_ml)
        traffic_file = inp.traffic_file

        from cherenkov.core.contracts import PerfSlice

        sl = PerfSlice(
            name=scenario_name,
            target_url=target_url,
            endpoint=endpoint,
            method=method,
            vus=vus,
            duration_sec=duration_sec,
        )
        from cherenkov.stages.perf.perf_stage import PerfStage

        stage = PerfStage()
        report = stage.run(sl, use_ml=use_ml, traffic_file=traffic_file)
        return _ok_content(
            {
                "scenario_id": report.scenario_id,
                "status": report.status.value
                if hasattr(report.status, "value")
                else str(report.status),
                "verdict": report.verdict.value
                if hasattr(report.verdict, "value")
                else str(report.verdict),
                "errors": [e.detail for e in report.errors],
                "gates": [
                    {
                        "gate": g.gate,
                        "passed": g.passed,
                        "latency_ms": g.latency_ms,
                        "anomaly_detected": g.anomaly_detected,
                        "k6_available": g.k6_available,
                    }
                    for g in report.gates
                ],
            }
        )
    except Exception as exc:
        return _err_content(f"Perf error: {exc}")

def _tool_query_rag(args: dict[str, Any]) -> MCPToolCallResult:
    import logging
    import sqlite3

    query = args.get("query", "")
    _handler_log = logging.getLogger(__name__)
    try:
        from cherenkov.knowledge.rag_index import RAGIndex

        rag = RAGIndex()
        res = rag.query_similar_incidents(query)
        return _ok_content({"query": query, "results": res})
    except sqlite3.OperationalError as exc:
        # SQLite transient errors (database locked, disk I/O, etc.) are not
        # code defects — degrade gracefully with an empty result set and a
        # warning so callers still get a well-formed success response.
        _handler_log.warning("RAG index temporarily unavailable: %s", exc)
        return _ok_content({"query": query, "results": [], "warning": f"RAG index unavailable: {exc}"})
    except Exception as exc:
        # Also treat "database is locked" errors surfaced through other exception types.
        if "database is locked" in str(exc).lower() or "disk i/o" in str(exc).lower():
            _handler_log.warning("RAG index temporarily unavailable: %s", exc)
            return _ok_content({"query": query, "results": [], "warning": f"RAG index unavailable: {exc}"})
        return _err_content(f"RAG error: {exc}")


def _tool_export_jira(args: dict[str, Any]) -> MCPToolCallResult:
    try:
        inp = ExportJiraInput.model_validate(args)
        from cherenkov.validate.jira_exporter import JiraExporter

        project_key = inp.project_key or "QA"
        exporter = JiraExporter(jira_project=project_key)
        item_id = inp.item_id or "direct_export"
        summary = inp.summary
        description = inp.description
        file_path = None

        if inp.item_id:
            q = _queue()
            item = q.get(inp.item_id)
            if item:
                if not summary:
                    summary = f"🛑 CHERENKOV QA — DRIFT DETECTED: {item.id}"
                if not description:
                    description = exporter.format_ticket(
                        scenario_id=item.id,
                        failure_class=item.mutation_label or "conformance-drift",
                        error_message=item.review_gate_failed or "Validation failed",
                        expected_status="Valid response",
                        received_status="Divergent response",
                        hypothesis=item.confidence_reason,
                        compliance_score=80,
                    )
                file_path = exporter.export_ticket(
                    scenario_id=item.id,
                    failure_class=item.mutation_label or "conformance-drift",
                    error_message=item.review_gate_failed or "Validation failed",
                    expected_status="Valid response",
                    received_status="Divergent response",
                    hypothesis=item.confidence_reason,
                    compliance_score=80,
                )
            elif not (summary and description):
                return _err_content(f"HITL item {inp.item_id} not found in queue and missing summary/description.")

        if not summary or not description:
            return _err_content("Either valid item_id in queue or both summary and description must be provided.")

        if file_path is None:
            file_path = exporter.export_ticket(
                scenario_id=item_id,
                failure_class="direct-export",
                error_message=description,
                expected_status="N/A",
                received_status="N/A",
                hypothesis=summary,
            )

        issue_key = None
        if not inp.sandbox_only:
            try:
                issue_key = exporter.create_jira_issue(summary, description)
            except Exception:
                issue_key = None

        return _ok_content(
            {
                "item_id": item_id,
                "summary": summary,
                "description": description,
                "project_key": project_key,
                "sandbox_only": inp.sandbox_only,
                "status": "exported",
                "file_path": file_path,
                "jira_issue_key": issue_key or "sandboxed",
            }
        )
    except Exception as exc:
        return _err_content(f"Jira error: {exc}")

def _tool_export_linear(args: dict[str, Any]) -> MCPToolCallResult:
    item_id = args.get("item_id", "")
    try:
        q = _queue()
        item = q.get(item_id)
        if not item:
            return _err_content(f"HITL item {item_id} not found in queue.")

        from cherenkov.validate.linear_exporter import LinearExporter
        exporter = LinearExporter()

        file_path = exporter.export_ticket(
            scenario_id=item.id,
            failure_class=item.mutation_label or "conformance-drift",
            error_message=item.review_gate_failed or "Validation failed",
            expected_status="Valid response",
            received_status="Divergent response",
            hypothesis=item.confidence_reason
        )

        summary = f"🛑 CHERENKOV QA — DRIFT DETECTED: {item.id}"
        description = exporter.format_ticket(
            scenario_id=item.id,
            failure_class=item.mutation_label or "conformance-drift",
            error_message=item.review_gate_failed or "Validation failed",
            expected_status="Valid response",
            received_status="Divergent response",
            hypothesis=item.confidence_reason
        )

        issue_key = exporter.create_linear_issue(summary, description)

        return _ok_content(
            {
                "item_id": item_id,
                "status": "exported",
                "file_path": file_path,
                "linear_issue_key": issue_key or "sandboxed",
            }
        )
    except Exception as exc:
        return _err_content(f"Linear error: {exc}")

def _tool_export_github(args: dict[str, Any]) -> MCPToolCallResult:
    item_id = args.get("item_id", "")
    try:
        q = _queue()
        item = q.get(item_id)
        if not item:
            return _err_content(f"HITL item {item_id} not found in queue.")

        from cherenkov.validate.github_exporter import GitHubExporter
        from cherenkov.validate.linear_exporter import LinearExporter

        # We reuse LinearExporter's format_ticket for markdown generation
        formatter = LinearExporter()
        summary = f"🛑 CHERENKOV QA — DRIFT DETECTED: {item.id}"
        description = formatter.format_ticket(
            scenario_id=item.id,
            failure_class=item.mutation_label or "conformance-drift",
            error_message=item.review_gate_failed or "Validation failed",
            expected_status="Valid response",
            received_status="Divergent response",
            hypothesis=item.confidence_reason
        )

        exporter = GitHubExporter()
        issue_url = exporter.create_github_issue(summary, description)

        return _ok_content(
            {
                "item_id": item_id,
                "status": "exported",
                "github_issue_url": issue_url or "sandboxed",
            }
        )
    except Exception as exc:
        return _err_content(f"GitHub error: {exc}")

def _tool_scan_mena(args: dict[str, Any]) -> MCPToolCallResult:
    target_url = (
        args.get("target_url") or os.environ.get("API_URL") or "http://localhost:8000"
    )
    spec_path = args.get("spec_path") or "stub/openapi.yaml"
    try:
        from cherenkov.compliance.mena_scanner import MENAComplianceScanner

        scanner = MENAComplianceScanner()
        report = scanner.run_compliance_audit(
            target_url=target_url, spec_path=spec_path
        )
        violations = []
        framework_mappings = report.get("framework_mappings", {})
        sama_ccsf = framework_mappings.get("SAMA_CCSF", {})
        egypt_fincsf = framework_mappings.get("EGYPT_FinCSF", {})

        for domain, details in sama_ccsf.items():
            if isinstance(details, dict) and details.get("status") == "NON-COMPLIANT":
                violations.append(f"{domain}: {details.get('remediation', '')}")
        for domain, details in egypt_fincsf.items():
            if isinstance(details, dict) and details.get("status") == "NON-COMPLIANT":
                violations.append(f"{domain}: {details.get('remediation', '')}")

        return _ok_content(
            {
                "compliance_score": report.get("overall_compliance_score", 0),
                "violations": violations,
                "mappings": framework_mappings,
                "sama_ccsf": sama_ccsf,
                "egypt_fincsf": egypt_fincsf,
                "audit_results": report.get("audit_results", {}),
            }
        )
    except Exception as exc:
        return _err_content(f"MENA error: {exc}")

def _tool_scan_mena_enhanced(args: dict[str, Any]) -> MCPToolCallResult:
    """Enhanced MENA compliance tool with framework-specific scanning."""
    try:
        inp = MenaComplianceEnhancedInput.model_validate(args)
        spec_path = inp.spec_path
        try:
            spec_path = _validate_spec_path(spec_path)
        except ValueError as exc:
            return _err_content(f"Invalid spec_path: {exc}")

        from cherenkov.compliance.mena_scanner import MENAComplianceScanner

        scanner = MENAComplianceScanner()
        report = scanner.run_compliance_audit(
            target_url=inp.target_url, spec_path=spec_path
        )

        # Filter by requested framework
        framework_key = inp.framework.upper()
        if framework_key == "SAMA_CCSF":
            mappings = {"SAMA_CCSF": report["framework_mappings"]["SAMA_CCSF"]}
        elif framework_key == "EGYPT_CBEF" or framework_key == "EGYPT_FINCSF":
            mappings = {"EGYPT_FinCSF": report["framework_mappings"]["EGYPT_FinCSF"]}
        else:
            mappings = report["framework_mappings"]

        violations = []
        for _domain, details in mappings.items():
            for sub_domain, sub_details in (
                details.items() if isinstance(details, dict) else []
            ):
                if (
                    isinstance(sub_details, dict)
                    and sub_details.get("status") == "NON-COMPLIANT"
                ):
                    violations.append(
                        f"{sub_domain}: {sub_details.get('remediation', '')}"
                    )

        return _ok_content(
            {
                "compliance_score": report.get("overall_compliance_score", 0),
                "framework": inp.framework,
                "violations": violations,
                "mappings": mappings,
                "sama_ccsf": report.get("framework_mappings", {}).get("SAMA_CCSF", {}),
                "egypt_fincsf": report.get("framework_mappings", {}).get("EGYPT_FinCSF", {}),
                "audit_results": report.get("audit_results", {}),
            }
        )
    except Exception as exc:
        return _err_content(f"MENA enhanced error: {exc}")

def _tool_validate_governance(args: dict[str, Any]) -> MCPToolCallResult:
    """Validate governance certifications against established standards."""
    try:
        inp = GovernanceCertificationInput.model_validate(args)
        from cherenkov.governance.kpi import GovernanceCollector

        collector = GovernanceCollector()
        report = collector.collect()
        kpi_json = report.render_json()

        # Simulate certification validation against criteria
        cert_valid = kpi_json["health_score"] >= 0.7
        findings = []
        if kpi_json["escape_rate"] > 0.1:
            findings.append(
                f"Escape rate ({kpi_json['escape_rate']:.1%}) exceeds 10% threshold"
            )
        if kpi_json["false_positive_rate"] > 0.15:
            findings.append(
                f"False positive rate ({kpi_json['false_positive_rate']:.1%}) exceeds 15% threshold"
            )
        if kpi_json["coverage"] < 0.5:
            findings.append(
                f"Coverage ({kpi_json['coverage']:.1%}) below 50% threshold"
            )

        return _ok_content(
            {
                "cert_id": inp.cert_id,
                "validation_criteria": inp.validation_criteria,
                "certified": cert_valid,
                "health_score": kpi_json["health_score"],
                "findings": findings,
                "kpi_summary": kpi_json,
            }
        )
    except Exception as exc:
        return _err_content(f"Governance validation error: {exc}")

def _tool_report_compliance(args: dict[str, Any]) -> MCPToolCallResult:
    """Generate structured compliance reports with filtering."""
    try:
        inp = ComplianceFindingsInput.model_validate(args)
        from cherenkov.compliance.mena_scanner import MENAComplianceScanner

        scanner = MENAComplianceScanner()
        report = scanner.run_compliance_audit(
            target_url=os.environ.get("API_URL", "http://localhost:8000"),
            spec_path="stub/openapi.yaml",
        )

        # Build compliance findings from the report
        all_findings = []
        for domain, details in report["framework_mappings"].items():
            for sub_domain, sub_details in (
                details.items() if isinstance(details, dict) else []
            ):
                if isinstance(sub_details, dict):
                    severity = (
                        "high"
                        if sub_details.get("status") == "NON-COMPLIANT"
                        else "low"
                    )
                    finding = {
                        "domain": sub_domain,
                        "framework": domain,
                        "severity": severity,
                        "status": sub_details.get("status", "UNKNOWN"),
                        "remediation": sub_details.get("remediation", ""),
                        "endpoint": "/",
                    }
                    all_findings.append(finding)

        # Apply filters
        filtered = all_findings
        if inp.severity and inp.severity != "all":
            filtered = [f for f in filtered if f["severity"] == inp.severity]
        if inp.endpoint:
            filtered = [f for f in filtered if inp.endpoint in f.get("endpoint", "")]
        filtered = filtered[: inp.limit]

        return _ok_content(
            {
                "total_findings": len(all_findings),
                "displayed": len(filtered),
                "findings": filtered,
                "filters_applied": {
                    "severity": inp.severity or "all",
                    "endpoint": inp.endpoint or "none",
                },
                "compliance_score": report.get("overall_compliance_score", 0),
            }
        )
    except Exception as exc:
        return _err_content(f"Compliance report error: {exc}")

# ── Chat knowledge tools ──────────────────────────────────────────────────────

def _tool_chat_query_verdicts(args: dict[str, Any]) -> MCPToolCallResult:
    inp = ChatQueryVerdictsInput.model_validate(args)
    from cherenkov.chat.tools import query_verdicts

    result = query_verdicts(
        endpoint=inp.endpoint, status_code=inp.status_code, limit=inp.limit
    )
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
    """Return the most recent ValidationReport from evidence/, or a stub dictionary.

    Returns:
        dict[str, Any]: Most recent report JSON dictionary or stub report dictionary.
    """
    evidence_dir = os.path.join(os.getcwd(), ".cherenkov", "evidence")
    pattern = os.path.join(evidence_dir, "*.json")
    files = sorted(glob.glob(pattern), reverse=True)
    if files:
        with open(files[0], encoding="utf-8") as f:
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
        _validate_spec_path(inp.spec_path)
    except ValueError as exc:
        return _err_content(f"Invalid spec_path: {exc}")
    try:
        from cherenkov.execution.validate import ValidationEngine

        engine = ValidationEngine()
        report = engine.validate_suite(target_url=inp.target_url, workers=inp.workers)
        return _ok_content(
            {
                "status": "complete",
                "passed": report.get("passed", 0),
                "failed": report.get("failed", 0),
                "drift_count": report.get(
                    "drift_count", len(report.get("reports", []))
                ),
                "report_path": ".cherenkov/report.json",
                "summary": report,
            }
        )
    except Exception as exc:
        return _err_content(f"Conformance check error: {exc}")

def _tool_get_last_report(_args: dict[str, Any]) -> MCPToolCallResult:
    """Return the most recent .cherenkov/report.json without triggering a new run."""
    report_path = os.path.join(os.getcwd(), ".cherenkov", "report.json")
    if not os.path.exists(report_path):
        return _ok_content(
            {
                "error": "No report found.",
                "hint": "Run `cherenkov validate --target <url>` first.",
            }
        )
    try:
        with open(report_path, encoding="utf-8") as f:
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
        patterns: list[str] = []
        if os.path.isdir(evidence_dir):
            for ev_file in sorted(glob.glob(os.path.join(evidence_dir, "*.json")))[
                -10:
            ]:
                with open(ev_file, encoding="utf-8") as f:
                    ev = json.load(f)
                if (
                    inp.endpoint in ev.get("endpoint", "")
                    and ev.get("method", "GET").upper() == inp.method.upper()
                ):
                    suggestions = TighteningAnalyzer.analyze(
                        ev.get("request_body", ""), ev.get("response_body", "")
                    )
                    patterns.extend(suggestions)
        return _ok_content(
            {
                "endpoint": inp.endpoint,
                "method": inp.method,
                "suggestions": list(dict.fromkeys(patterns)),  # dedup preserving order
            }
        )
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
        (
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

def _tool_auto_heal_code(args: dict[str, Any]) -> MCPToolCallResult:
    """Diagnose a failed validation item and generate a suggested code patch.

    Suggest-only (D7 invariant): the patch is returned as a string, never
    written to disk automatically. The caller decides whether to apply it.
    """
    item_id = args.get("item_id", "")
    if not item_id:
        return _err_content("item_id is required.")
    try:
        q = _queue()
        item = q.get(item_id)
        if not item:
            return _err_content(f"HITL item {item_id} not found.")

        # Attempt LLM-assisted repair via the AI router
        try:
            from cherenkov.core.contracts import ReasoningRequest
            from cherenkov.substrate.router import SubstrateRouter

            router = SubstrateRouter()
            prompt = (
                f"A CHERENKOV HITL validation item failed.\n"
                f"Item ID: {item.id}\n"
                f"Failure: {item.review_gate_failed or 'unknown gate'}\n"
                f"Label: {item.mutation_label or 'unknown'}\n"
                f"Reason: {item.confidence_reason or 'no detail'}\n\n"
                "Produce a minimal Python or TypeScript code patch that fixes the "
                "failing assertion. Return only the patch — no explanation. "
                "IMPORTANT: Suggest-only; the caller applies the patch."
            )
            req = ReasoningRequest(task=prompt, capability_tier="small")
            patch = str(router.route(req).content)
        except Exception:
            patch = (
                f"# Auto-heal unavailable (LLM/router error).\n"
                f"# Manual fix required for item {item_id}.\n"
                f"# Gate that failed: {item.review_gate_failed or 'unknown'}\n"
                f"# Hint: {item.confidence_reason or 'no detail available'}"
            )

        return _ok_content(
            {
                "item_id": item_id,
                "gate_failed": item.review_gate_failed,
                "suggested_patch": patch,
                "applied": False,
                "note": "Suggest-only (D7 invariant). Review before applying.",
            }
        )
    except Exception as exc:
        return _err_content(f"auto_heal_code error: {exc}")

_TOOL_DISPATCH: dict[str, Callable[[dict[str, Any]], MCPToolCallResult]] = {
    "verify_suite": _tool_verify_suite,
    "verify_system": _tool_verify_system,
    "check_suite": _tool_check_suite,
    "verify": _tool_verify,
    "generate": _tool_generate,
    "hitl_list": _tool_hitl_list,
    "hitl_approve": _tool_hitl_approve,
    "hitl_reject": _tool_hitl_reject,
    "validate_run_gate": _tool_validate_gate,
    "visual_diff_baseline": _tool_visual_diff,
    "visual_diff_baseline_enhanced": _tool_visual_diff_enhanced,
    "run_k6_perf": _tool_run_perf,
    "query_rag_index": _tool_query_rag,
    "export_jira_ticket": _tool_export_jira,
    "export_linear_ticket": _tool_export_linear,
    "export_github_ticket": _tool_export_github,
    "scan_mena_compliance": _tool_scan_mena,
    "scan_mena_compliance_enhanced": _tool_scan_mena_enhanced,
    "validate_governance_certification": _tool_validate_governance,
    "report_compliance_findings": _tool_report_compliance,
    "chat_query_verdicts": _tool_chat_query_verdicts,
    "chat_query_idioms": _tool_chat_query_idioms,
    "chat_explain_divergence": _tool_chat_explain_divergence,
    "chat_run_test": _tool_chat_run_test,
    "run_conformance_check": _tool_run_conformance_check,
    "get_last_report": _tool_get_last_report,
    "list_drift_findings": _tool_list_drift_findings,
    "get_tightening_suggestions": _tool_get_tightening_suggestions,
    "explain_finding": _tool_explain_finding,
    "policy_list": _tool_policy_list,
    "policy_reload": _tool_policy_reload,
    "mcp_registry_list": _tool_registry_list,
    "mcp_registry_publish": _tool_registry_publish,
    "event_bus_list": _tool_event_bus_list,
    "event_bus_get": _tool_event_bus_get,
    "event_bus_publish": _tool_event_bus_publish,
    "event_bus_stats": _tool_event_bus_stats,
    "auto_heal_code": _tool_auto_heal_code,
}

def _get_evidence_listing() -> dict[str, Any]:
    """Return a directory listing dictionary of .cherenkov/evidence/.

    Returns:
        dict[str, Any]: Dictionary containing evidence_dir path and list of evidence filenames.
    """
    evidence_dir = os.path.join(os.getcwd(), ".cherenkov", "evidence")
    if not os.path.isdir(evidence_dir):
        return {
            "evidence_dir": evidence_dir,
            "files": [],
            "note": "Directory does not exist yet.",
        }
    files = sorted(os.listdir(evidence_dir))
    return {"evidence_dir": evidence_dir, "files": files, "count": len(files)}

