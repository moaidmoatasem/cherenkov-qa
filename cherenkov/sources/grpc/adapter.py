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

class gRPCSourceAdapter:
    """Parses .proto files → EndpointSlice-equivalent operations."""

    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        with open(self.spec_path, "r", encoding="utf-8") as f:
            self.proto_content = f.read()

    def iter_operations(self) -> Iterator[gRPCOperation]:
        # Simple regex to find service blocks and rpc definitions
        service_pattern = r'service\s+(\w+)\s*{([^}]+)}'
        rpc_pattern = r'rpc\s+(\w+)\s*\(\s*([^\)]+)\s*\)\s*returns\s*\(\s*([^\)]+)\s*\)'
        
        for svc_match in re.finditer(service_pattern, self.proto_content):
            service_name = svc_match.group(1)
            service_body = svc_match.group(2)
            
            for rpc_match in re.finditer(rpc_pattern, service_body):
                rpc_name = rpc_match.group(1)
                input_msg = rpc_match.group(2)
                output_msg = rpc_match.group(3)
                
                yield gRPCOperation(
                    service=service_name,
                    rpc_name=rpc_name,
                    input_message=input_msg,
                    output_message=output_msg,
                    proto_content=self.proto_content
                )
