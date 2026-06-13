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

    def to_success(self, id: int | str | None, result: Any) -> "JsonRpcResponse":
        return JsonRpcResponse(id=id, result=result)

    def to_error(self, id: int | str | None, code: int, message: str, data: Any = None) -> "JsonRpcResponse":
        return JsonRpcResponse(id=id, error=JsonRpcError(code=code, message=message, data=data))


# ── MCP capability advertisement ─────────────────────────────────────────────

class MCPServerInfo(BaseModel):
    name: str = "cherenkov"
    version: str = "1.0.0"


class MCPCapabilities(BaseModel):
    resources: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, Any] = Field(default_factory=dict)
    prompts: dict[str, Any] = Field(default_factory=dict)


class MCPInitializeResult(BaseModel):
    protocolVersion: str = "2024-11-05"
    serverInfo: MCPServerInfo = Field(default_factory=MCPServerInfo)
    capabilities: MCPCapabilities = Field(default_factory=MCPCapabilities)


# ── MCP Resource shapes ───────────────────────────────────────────────────────

class MCPResource(BaseModel):
    uri: str
    name: str
    description: str
    mimeType: str = "application/json"


class MCPResourceContent(BaseModel):
    uri: str
    mimeType: str = "application/json"
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
    inputSchema: MCPToolInputSchema


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
    isError: bool = False


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
    spec_path: str = Field(default="stub/openapi.yaml", description="Path to OpenAPI spec")
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
    finding_id: str = Field(min_length=1, description="Finding ID from list_drift_findings")
    detail_level: Literal["concise", "detailed"] = Field(default="concise")


# ── JSON-RPC error codes (MCP uses standard JSON-RPC + MCP extensions) ───────
PARSE_ERROR      = -32700
INVALID_REQUEST  = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS   = -32602
INTERNAL_ERROR   = -32603

