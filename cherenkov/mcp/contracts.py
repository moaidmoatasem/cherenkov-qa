"""
cherenkov/mcp/contracts.py
Pydantic v2 models for the MCP (Model Context Protocol) server.

schema_version = 'mcp/v1'

These models represent the wire shapes for the JSON-RPC 2.0 / MCP protocol.
They are local to the mcp/ package — never forking core/contracts.py.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "mcp/v1"

# ── JSON-RPC 2.0 frames ───────────────────────────────────────────────────────


class JsonRpcRequest(BaseModel):
    """Inbound JSON-RPC 2.0 request from an MCP client."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Any | None = None


class JsonRpcResponse(BaseModel):
    """Outbound JSON-RPC 2.0 response."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = None
    result: Any | None = None
    error: JsonRpcError | None = None

    def to_success(self, id: int | str | None, result: Any) -> JsonRpcResponse:
        """Construct a successful JsonRpcResponse instance.

        Args:
            id (int | str | None): Request identifier.
            result (Any): Successful result payload.

        Returns:
            JsonRpcResponse: Response instance configured with result.
        """
        return JsonRpcResponse(id=id, result=result)

    def to_error(
        self, id: int | str | None, code: int, message: str, data: Any = None
    ) -> JsonRpcResponse:
        """Construct an error JsonRpcResponse instance.

        Args:
            id (int | str | None): Request identifier.
            code (int): JSON-RPC error code integer.
            message (str): Human-readable error message.
            data (Any): Optional additional diagnostic data. Defaults to None.

        Returns:
            JsonRpcResponse: Response instance configured with error details.
        """
        return JsonRpcResponse(
            id=id, error=JsonRpcError(code=code, message=message, data=data)
        )



# ── MCP capability advertisement ─────────────────────────────────────────────


class MCPServerInfo(BaseModel):
    name: str = "cherenkov"
    version: str = "1.0.0"


class MCPCapabilities(BaseModel):
    resources: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, Any] = Field(default_factory=dict)
    prompts: dict[str, Any] = Field(default_factory=dict)


class MCPInitializeResult(BaseModel):
    protocolVersion: str = "2024-11-05"  # noqa: N815
    serverInfo: MCPServerInfo = Field(default_factory=MCPServerInfo)  # noqa: N815
    capabilities: MCPCapabilities = Field(default_factory=MCPCapabilities)


# ── MCP Resource shapes ───────────────────────────────────────────────────────


class MCPResource(BaseModel):
    uri: str
    name: str
    description: str
    mimeType: str = "application/json"  # noqa: N815


class MCPResourceContent(BaseModel):
    uri: str
    mimeType: str = "application/json"  # noqa: N815
    text: str  # JSON-serialised payload


class MCPResourceListResult(BaseModel):
    resources: list[MCPResource]


class MCPResourceReadResult(BaseModel):
    contents: list[MCPResourceContent]


# ── MCP Tool shapes ───────────────────────────────────────────────────────────


class MCPToolParam(BaseModel):
    type: str
    description: str


class MCPToolInputSchema(BaseModel):
    type: Literal["object"] = "object"
    properties: dict[str, MCPToolParam] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: MCPToolInputSchema  # noqa: N815


class MCPToolListResult(BaseModel):
    tools: list[MCPTool]


class MCPToolCallInput(BaseModel):
    """Validated inputs for a tool/call invocation from an MCP client."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class MCPToolCallResult(BaseModel):
    content: list[MCPContent]
    isError: bool = False  # noqa: N815


# ── Input validation models (trust boundary — MCP peers are untrusted) ───────


class HitlApproveInput(BaseModel):
    item_id: str = Field(min_length=1, max_length=256)
    actor: str = Field(min_length=1, max_length=128, default="mcp-peer")


class HitlRejectInput(BaseModel):
    item_id: str = Field(min_length=1, max_length=256)
    actor: str = Field(min_length=1, max_length=128, default="mcp-peer")
    reason: str = Field(min_length=1, max_length=1024, default="rejected via MCP")


class HitlListInput(BaseModel):
    status: Literal["pending", "approved", "rejected", "ignored"] | None = "pending"


class ValidateRunGateInput(BaseModel):
    provider: str | None = Field(
        default=None,
        description='Sandbox provider: "filesystem" (default) or "docker"',
    )
    target_url: str | None = Field(default=None, description="Optional target API URL")


class ChatQueryVerdictsInput(BaseModel):
    endpoint: str | None = None
    status_code: int | None = None
    limit: int = Field(default=10, ge=1, le=100)


class ChatQueryIdiomsInput(BaseModel):
    pattern: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class ChatExplainDivergenceInput(BaseModel):
    endpoint: str = Field(min_length=1)
    method: str = Field(default="GET")


class ChatRunTestInput(BaseModel):
    endpoint: str = Field(min_length=1)
    method: str = Field(default="GET")
    spec_path: str | None = None


# ── Issue #441: Conformance tools ─────────────────────────────────────────────


class RunConformanceCheckInput(BaseModel):
    target_url: str = Field(min_length=1, description="Target API base URL")
    spec_path: str = Field(
        default="stub/openapi.yaml", description="Path to OpenAPI spec"
    )
    workers: int = Field(default=1, ge=1, le=16, description="Parallel workers")


class ListDriftFindingsInput(BaseModel):
    severity: Literal["high", "medium", "low"] | None = Field(
        default=None, description="Filter by severity"
    )
    endpoint: str | None = Field(default=None, description="Filter by endpoint path")
    limit: int = Field(default=20, ge=1, le=200)


class GetTighteningInput(BaseModel):
    endpoint: str = Field(min_length=1, description="e.g. /users/{id}")
    method: str = Field(default="GET")


class ExplainFindingInput(BaseModel):
    finding_id: str = Field(
        min_length=1, description="Finding ID from list_drift_findings"
    )
    detail_level: Literal["concise", "detailed"] = Field(default="concise")


# ── Issue #457: Enhanced Visual Diff Baseline ────────────────────────────────


class VisualDiffBaselineInput(BaseModel):
    target_url: str | None = Field(
        default=None, description="Optional target URL for visual testing"
    )
    baseline_dir: str | None = Field(
        default=None,
        description="Baseline directory path (default: stub/visual_baselines)",
    )
    diff_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Pixel diff threshold (0.0-1.0, default: 0.5)",
    )
    comparison_mode: str | None = Field(
        default=None, description="Comparison mode: pixel, structural, or auto"
    )
    report_path: str | None = Field(
        default=None,
        description="Path to save visual report (default: .cherenkov/visual_report.json)",
    )


# ── Issue #458: Compliance and Governance MCP Tools ──────────────────────────


class MenaComplianceEnhancedInput(BaseModel):
    target_url: str = Field(min_length=1, description="Target API base URL")
    spec_path: str = Field(
        default="stub/openapi.yaml", description="Path to OpenAPI spec"
    )
    framework: str = Field(
        default="sama_ccsf", description="Compliance framework: sama_ccsf or egypt_cbef"
    )


class GovernanceCertificationInput(BaseModel):
    cert_id: str = Field(min_length=1, description="Certification ID to validate")
    validation_criteria: str = Field(
        min_length=1, description="Validation criteria or standards to check against"
    )


class ComplianceFindingsInput(BaseModel):
    severity: Literal["high", "medium", "low", "all"] | None = Field(
        default=None, description="Filter by severity"
    )
    endpoint: str | None = Field(
        default=None, description="Filter by endpoint path (optional)"
    )
    limit: int = Field(
        default=20, ge=1, le=200, description="Maximum results to return"
    )


class ExportJiraInput(BaseModel):
    item_id: str | None = Field(default=None, description="Validation item ID.")
    summary: str | None = Field(default=None, description="Ticket summary/title.")
    description: str | None = Field(default=None, description="Ticket description.")
    project_key: str | None = Field(default="QA", description="Jira project key.")
    sandbox_only: bool = Field(default=True, description="Sandbox mode flag.")


class RunK6PerfInput(BaseModel):
    target_url: str = Field(description="Target API base URL.")
    scenario_name: str | None = Field(
        default="soak", description="K6 scenario name."
    )
    duration: str | int | None = Field(
        default="30s", description="Test duration in seconds or duration string (e.g., '30s')."
    )
    vus: int | None = Field(
        default=10, ge=1, description="Virtual users (VUs) count."
    )
    endpoint: str | None = Field(default="/", description="Endpoint path.")
    method: str | None = Field(default="GET", description="HTTP method.")
    use_ml: bool | None = Field(
        default=False, description="Enable ML latency anomaly detection."
    )
    traffic_file: str | None = Field(
        default=None, description="Path to HAR/traffic file for load profile."
    )


# ── verify_suite (E2.1 — integrity check for AI-generated suites) ────────────


class VerifySuiteInput(BaseModel):
    """Input for the verify_suite MCP tool (MCP_VERIFICATION_SERVER.md §4.1).

    Exactly one of suite_path or suite_inline must be provided.
    spec_source defaults to stub/openapi_3_1.yaml when omitted.
    """

    suite_path: str | None = Field(
        default=None,
        description="Filesystem path to a .spec.ts file to verify. "
        "Must be within the working directory.",
    )
    suite_inline: str | None = Field(
        default=None,
        description="Raw TypeScript test code to verify inline "
        "(use when the file hasn't been written to disk yet).",
    )
    spec_source: str | None = Field(
        default=None,
        description="Path to the OpenAPI spec used to re-derive expected behaviour. "
        "Defaults to stub/openapi_3_1.yaml when omitted.",
    )
    scenario_id: str | None = Field(
        default=None,
        description="Logical identifier for the scenario (used in finding IDs). "
        "Defaults to a hash of the suite content.",
    )
    endpoint: str | None = Field(
        default=None,
        description="API endpoint under test (e.g. /users). Used in finding context.",
    )
    method: str | None = Field(
        default="POST",
        description="HTTP method (GET, POST, PUT, DELETE, PATCH).",
    )


# ── verify_system (E2.1 — conformance/drift of a live system) ────────────────


class VerifySystemInput(BaseModel):
    """Input for the verify_system MCP tool (MCP_VERIFICATION_SERVER.md §4.2).

    Probes a live server for spec↔implementation divergences using the
    CHERENKOV divergence engine (Skeptic → Witness loop).  No LLM required
    in the default offline mode.
    """

    base_url: str = Field(
        description="Base URL of the live server to probe "
        "(e.g. https://petstore3.swagger.io/api/v3).",
    )
    spec_source: str | None = Field(
        default=None,
        description="Path or URL to the OpenAPI spec JSON/YAML.  "
        "Omit to use the built-in Petstore demo spec.",
    )
    use_llm: bool = Field(
        default=False,
        description="If true, use the LLM Skeptic for hypothesis generation "
        "(requires Ollama). Default: offline mode (no LLM required).",
    )
    run_id: str | None = Field(
        default=None,
        description="Optional run identifier for correlation.",
    )


# ── check_suite (#812 — static integrity check of a candidate suite) ──────────


class CheckSuiteInput(BaseModel):
    """Input for the check_suite MCP tool (#812).

    Machine-facing twin of `cherenkov check-suite`. Exactly one of
    candidate_path or candidate_inline must be provided. The baseline is
    optional (required for WEAKENED/DELETED detection); the spec is required
    for HALLUCINATED detection on Python suites.
    """

    candidate_path: str | None = Field(
        default=None,
        description="Filesystem path to the candidate test suite (.py or .ts). "
        "Must be within the working directory.",
    )
    candidate_inline: str | None = Field(
        default=None,
        description="Raw test code to check inline (use when the file hasn't "
        "been written to disk yet).",
    )
    baseline_path: str | None = Field(
        default=None,
        description="Filesystem path to the known-honest baseline suite. "
        "Required for WEAKENED and DELETED detection.",
    )
    baseline_inline: str | None = Field(
        default=None,
        description="Raw baseline test code inline.",
    )
    spec_path: str | None = Field(
        default=None,
        description="Path to the OpenAPI spec (YAML/JSON). Required for "
        "HALLUCINATED detection on Python suites.",
    )
    fail_on_finding: bool = Field(
        default=False,
        description="If true, report verdict 'fail' when any integrity "
        "violation is found (CI gate mode).",
    )


# ── verify (#812 — divergence proof of a live system) ─────────────────────────


class VerifyInput(BaseModel):
    """Input for the verify MCP tool (#812).

    Machine-facing twin of `cherenkov verify`. Probes a live server against
    its OpenAPI spec using the Skeptic→Witness divergence engine. Offline by
    default — no LLM required.
    """

    base_url: str = Field(
        description="Base URL of the live server to probe "
        "(e.g. https://petstore3.swagger.io/api/v3).",
    )
    spec_source: str | None = Field(
        default=None,
        description="Path or URL to the OpenAPI spec JSON/YAML. "
        "Omit to use the built-in Petstore demo spec.",
    )
    use_llm: bool = Field(
        default=False,
        description="If true, use the LLM Skeptic for hypothesis generation "
        "(requires Ollama). Default: offline mode (no LLM required).",
    )
    max_probes: int = Field(
        default=40,
        ge=1,
        le=500,
        description="Maximum spec-derived endpoint probes per run (requires --spec).",
    )
    allow_mutations: bool = Field(
        default=False,
        description="Allow planning of happy-path probes for POST/PUT/DELETE.",
    )
    identifiers: str | None = Field(
        default=None,
        description="JSON file path or inline JSON object mapping path "
        "parameters to known valid values.",
    )
    coverage_report: bool = Field(
        default=False,
        description="Include a spec coverage-gap report in the result "
        "(requires spec_source).",
    )
    health_score: bool = Field(
        default=False,
        description="Include an A-F health grade in the result "
        "(requires spec_source).",
    )
    run_id: str | None = Field(
        default=None,
        description="Optional run identifier for correlation.",
    )


# ── generate (#812 — Playwright E2E suite generation from a spec) ─────────────


class GenerateInput(BaseModel):
    """Input for the generate MCP tool (#812).

    Machine-facing twin of `cherenkov generate`. Runs the Ingest→Plan→
    Generate (→Review→Repair) pipeline against an OpenAPI spec. By default the
    generated test code is returned inline; pass output_dir to write files to
    disk instead.
    """

    spec_path: str = Field(
        min_length=1,
        description="Path to the OpenAPI spec (JSON/YAML) to generate tests for. "
        "Must be within the working directory.",
    )
    output_dir: str | None = Field(
        default=None,
        description="Directory to write generated Playwright test files to. "
        "Omit to return generated test code inline (default).",
    )
    repair: bool = Field(
        default=True,
        description="Run the generate→review→repair loop. Default: on.",
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum repair attempts per scenario (only used with repair).",
    )


# ── Event bus tools (ADR-016 UnifiedEventBus wiring) ────────────────────────


class EventBusListInput(BaseModel):
    """Input for the event_bus_list MCP tool."""

    category: str | None = Field(
        default=None, description="Filter by event category (e.g. pipeline)."
    )
    limit: int = Field(default=50, ge=1, le=500)
    after_id: str | None = Field(
        default=None, description="Only fetch events with event_id greater than this."
    )


class EventBusGetInput(BaseModel):
    """Input for the event_bus_get MCP tool."""

    event_id: str = Field(min_length=1, max_length=64)


class EventBusPublishInput(BaseModel):
    """Input for the event_bus_publish MCP tool."""

    name: str = Field(min_length=1, max_length=256)
    category: str = Field(
        default="pipeline",
        description="Event category: pipeline | hitl | healing | knowledge | system.",
    )
    severity: str = Field(
        default="info", description="info | warning | error."
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary event payload."
    )


# ── JSON-RPC error codes (MCP uses standard JSON-RPC + MCP extensions) ───────
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
