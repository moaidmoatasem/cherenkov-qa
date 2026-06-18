from dataclasses import dataclass
from typing import Iterator
import re


@dataclass
class gRPCOperation:
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
    assert text[start] == "{"
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
    pattern = re.compile(r"service\s+(\w+)\s*{")
    for match in pattern.finditer(proto):
        service_name = match.group(1)
        body_start = match.end() - 1  # point to the opening {
        closing = _balanced_brace_match(proto, body_start)
        if closing != -1:
            body = proto[body_start + 1 : closing]
            results.append((service_name, body))
    return results


class gRPCSourceAdapter:
    """Parses .proto files into EndpointSlice-equivalent operations."""

    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        if spec_path.startswith("buf:"):
            # Shell out to `buf export`
            import subprocess
            import tempfile
            import os
            
            buf_module = spec_path[4:]
            self.temp_dir = tempfile.mkdtemp()
            try:
                subprocess.run(
                    ["buf", "export", buf_module, "--output", self.temp_dir],
                    check=True,
                    capture_output=True
                )
                # Find the first .proto file
                proto_file = None
                for root, _, files in os.walk(self.temp_dir):
                    for f in files:
                        if f.endswith(".proto"):
                            proto_file = os.path.join(root, f)
                            break
                    if proto_file:
                        break
                        
                if proto_file:
                    with open(proto_file, "r", encoding="utf-8") as f:
                        self.proto_content = f.read()
                else:
                    self.proto_content = ""
            except FileNotFoundError:
                raise RuntimeError("The 'buf' CLI is not installed. Please install it to use buf: schema sources.")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"buf export failed: {e.stderr.decode()}")
        else:
            with open(self.spec_path, "r", encoding="utf-8") as f:
                self.proto_content = f.read()

    def iter_operations(self) -> Iterator[gRPCOperation]:
        # Remove single-line and multi-line comments before parsing
        content = re.sub(r"//.*", "", self.proto_content)
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # Extract service blocks with proper brace matching
        service_blocks = _extract_service_blocks(content)

        for service_name, service_body in service_blocks:
            # Find RPC definitions within the service body
            rpc_pattern = re.compile(
                r"rpc\s+(\w+)\s*\(\s*(stream\s+)?(\w+)\s*\)\s*"
                r"returns\s*\(\s*(stream\s+)?(\w+)\s*\)"
            )
            for rpc_match in rpc_pattern.finditer(service_body):
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
