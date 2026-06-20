"""
cherenkov/truth/sources/grpc.py — E2.4: gRPC source adapter.

Parses .proto files (proto2 and proto3) to extract service definitions,
RPC methods, and message field contracts as normalized Claims.

Zero additional dependencies — pure regex over proto syntax.
"""

from __future__ import annotations

import re
from pathlib import Path

from cherenkov.core.contracts import Claim, Provenance, ProvenanceType, SCHEMA_VERSION
from cherenkov.truth.sources.interface import SourceAdapter

# Matches:  service Greeter {
_RE_SERVICE = re.compile(r"\bservice\s+(\w+)\s*\{", re.MULTILINE)
# Matches:  rpc SayHello (HelloRequest) returns (HelloReply);
#       or: rpc SayHello (stream HelloRequest) returns (stream HelloReply) { }
_RE_RPC = re.compile(
    r"\brpc\s+(\w+)\s*\(\s*(stream\s+)?(\w+)\s*\)\s*returns\s*\(\s*(stream\s+)?(\w+)\s*\)",
    re.MULTILINE,
)
# Matches:  message HelloRequest {
_RE_MESSAGE = re.compile(r"\bmessage\s+(\w+)\s*\{", re.MULTILINE)
# Matches field lines:  string name = 1;  or  repeated int32 ids = 2;
_RE_FIELD = re.compile(
    r"^\s*(repeated\s+|optional\s+|required\s+)?(\w+(?:\.\w+)*)\s+(\w+)\s*=\s*(\d+)\s*;",
    re.MULTILINE,
)
# Matches:  package foo.bar;
_RE_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
# Matches:  option (google.api.http) = { get: "/v1/messages/{name}" };
_RE_HTTP_OPTION = re.compile(
    r'option\s+\(google\.api\.http\)\s*=\s*\{[^}]*(?:get|post|put|delete|patch)\s*:\s*"([^"]+)"',
    re.DOTALL,
)


def _strip_comments(text: str) -> str:
    """Remove line (//) and block (/* */) comments from proto text."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _extract_block(text: str, start_pos: int) -> str:
    """Return the text of the { ... } block starting after start_pos."""
    depth = 0
    i = text.index("{", start_pos)
    start = i
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    return text[start:]


def _parse_proto(text: str) -> dict:
    """Parse proto text into a structured dict."""
    clean = _strip_comments(text)

    pkg_match = _RE_PACKAGE.search(clean)
    package = pkg_match.group(1) if pkg_match else ""

    # Parse messages and their fields
    messages: dict[str, list[dict]] = {}
    for m in _RE_MESSAGE.finditer(clean):
        msg_name = m.group(1)
        block = _extract_block(clean, m.start())
        fields = []
        for f in _RE_FIELD.finditer(block):
            fields.append(
                {
                    "label": (f.group(1) or "").strip() or "singular",
                    "type": f.group(2),
                    "name": f.group(3),
                    "field_number": int(f.group(4)),
                }
            )
        messages[msg_name] = fields

    # Parse services and their RPCs
    services: list[dict] = []
    for s in _RE_SERVICE.finditer(clean):
        svc_name = s.group(1)
        block = _extract_block(clean, s.start())
        rpcs = []
        for r in _RE_RPC.finditer(block):
            http_match = _RE_HTTP_OPTION.search(block[r.start() :])
            rpcs.append(
                {
                    "name": r.group(1),
                    "client_streaming": bool(r.group(2)),
                    "request_type": r.group(3),
                    "server_streaming": bool(r.group(4)),
                    "response_type": r.group(5),
                    "http_path": http_match.group(1) if http_match else None,
                }
            )
        services.append({"name": svc_name, "rpcs": rpcs})

    return {"package": package, "services": services, "messages": messages}


class GRPCSourceAdapter(SourceAdapter):
    """Source adapter for gRPC proto files.

    Accepts a single .proto file path or a directory of .proto files.
    Emits one Claim per RPC method (endpoint equivalent) and one Claim
    per message contract (schema equivalent).
    """

    def discover_claims(self, source_uri: str) -> list[Claim]:
        uri_path = Path(source_uri)

        proto_files: list[Path]
        if uri_path.is_dir():
            proto_files = sorted(uri_path.rglob("*.proto"))
        elif uri_path.suffix == ".proto":
            if not uri_path.exists():
                raise FileNotFoundError(f"Proto file not found: {source_uri}")
            proto_files = [uri_path]
        else:
            raise ValueError(f"Expected a .proto file or directory, got: {source_uri}")

        if not proto_files:
            raise FileNotFoundError(f"No .proto files found under: {source_uri}")

        claims: list[Claim] = []
        for proto_path in proto_files:
            text = proto_path.read_text(encoding="utf-8")
            parsed = _parse_proto(text)
            resolved = str(proto_path.resolve())
            pkg = parsed["package"]

            for service in parsed["services"]:
                svc = service["name"]
                qualified_svc = f"{pkg}.{svc}" if pkg else svc

                # Claim: service exists
                claims.append(
                    Claim(
                        id=f"grpc_{qualified_svc.replace('.', '_')}_exists",
                        category="grpc_service",
                        subject=qualified_svc,
                        value={"rpc_count": len(service["rpcs"]), "package": pkg},
                        provenance=Provenance(
                            source_type=ProvenanceType.SPEC,
                            source_uri=resolved,
                            details={"format": "proto", "type": "service_existence"},
                        ),
                        schema_version=SCHEMA_VERSION,
                    )
                )

                for rpc in service["rpcs"]:
                    rpc_name = rpc["name"]
                    qualified_rpc = f"{qualified_svc}/{rpc_name}"
                    safe_id = qualified_rpc.replace(".", "_").replace("/", "_")

                    streaming = []
                    if rpc["client_streaming"]:
                        streaming.append("client")
                    if rpc["server_streaming"]:
                        streaming.append("server")

                    # Claim: RPC method contract
                    claims.append(
                        Claim(
                            id=f"grpc_{safe_id}_rpc",
                            category="grpc_rpc",
                            subject=qualified_rpc,
                            value={
                                "request_type": rpc["request_type"],
                                "response_type": rpc["response_type"],
                                "streaming": streaming or ["unary"],
                                "http_path": rpc["http_path"],
                                "request_fields": parsed["messages"].get(
                                    rpc["request_type"], []
                                ),
                                "response_fields": parsed["messages"].get(
                                    rpc["response_type"], []
                                ),
                            },
                            provenance=Provenance(
                                source_type=ProvenanceType.SPEC,
                                source_uri=resolved,
                                details={
                                    "format": "proto",
                                    "type": "rpc_contract",
                                    "service": qualified_svc,
                                },
                            ),
                            schema_version=SCHEMA_VERSION,
                        )
                    )

            # Claim: one per top-level message (schema contract)
            for msg_name, fields in parsed["messages"].items():
                qualified_msg = f"{pkg}.{msg_name}" if pkg else msg_name
                safe_id = qualified_msg.replace(".", "_")
                claims.append(
                    Claim(
                        id=f"grpc_{safe_id}_message",
                        category="grpc_message",
                        subject=qualified_msg,
                        value={"fields": fields, "field_count": len(fields)},
                        provenance=Provenance(
                            source_type=ProvenanceType.SPEC,
                            source_uri=resolved,
                            details={"format": "proto", "type": "message_contract"},
                        ),
                        schema_version=SCHEMA_VERSION,
                    )
                )

        return claims
