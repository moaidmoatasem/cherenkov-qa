from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

_RE_SERVICE_BLOCK = re.compile(r"service\s+(\w+)\s*{")
_RE_RPC_DEF = re.compile(
    r"rpc\s+(\w+)\s*\(\s*(stream\s+)?(\w+)\s*\)\s*"
    r"returns\s*\(\s*(stream\s+)?(\w+)\s*\)"
)
_RE_LINE_COMMENT = re.compile(r"//.*")
_RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


@dataclass
class gRPCOperation:  # noqa: N801
    service: str
    rpc_name: str
    input_message: str
    output_message: str
    proto_content: str


def _balanced_brace_match(text: str, start: int) -> int:
    """
    Find the closing brace matching the opening brace at text[start].
    Handles nested braces. Returns the index of the closing brace.
    """
    if text[start] != "{":
        raise ValueError(f"Expected '{{' at position {start}, got {text[start]!r}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _extract_service_blocks(proto: str) -> list[tuple[str, str]]:
    """Extract (service_name, body) for each service block, handling nested braces."""
    results = []
    for match in _RE_SERVICE_BLOCK.finditer(proto):
        service_name = match.group(1)
        body_start = match.end() - 1  # point to the opening {
        closing = _balanced_brace_match(proto, body_start)
        if closing != -1:
            body = proto[body_start + 1 : closing]
            results.append((service_name, body))
    return results


class gRPCSourceAdapter:  # noqa: N801
    """Parses .proto files into EndpointSlice-equivalent operations."""

    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        with open(self.spec_path, encoding="utf-8") as f:
            self.proto_content = f.read()

    def iter_operations(self) -> Iterator[gRPCOperation]:
        # Remove single-line and multi-line comments before parsing
        content = _RE_LINE_COMMENT.sub("", self.proto_content)
        content = _RE_BLOCK_COMMENT.sub("", content)

        # Extract service blocks with proper brace matching
        service_blocks = _extract_service_blocks(content)

        for service_name, service_body in service_blocks:
            # Find RPC definitions within the service body
            for rpc_match in _RE_RPC_DEF.finditer(service_body):
                rpc_name = rpc_match.group(1)
                input_msg = rpc_match.group(3)
                output_msg = rpc_match.group(5)

                yield gRPCOperation(
                    service=service_name,
                    rpc_name=rpc_name,
                    input_message=input_msg,
                    output_message=output_msg,
                    proto_content=self.proto_content,
                )
