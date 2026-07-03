"""
CHERENKOV validate/buf_registry.py — Buf Schema Registry Client.
"""

import os
import urllib.request
import json
from cherenkov.core.errors import get_logger

_log = get_logger("BUF_REGISTRY")


class BufRegistryClient:
    """Interacts with the Buf Schema Registry (BSR)."""

    def __init__(self):
        self.token = os.environ.get("BUF_TOKEN")
        self.base_url = "https://buf.build/buf.alpha.registry.v1alpha1.RepositoryService"

    def fetch_schema(self, module_name: str) -> str | None:
        """
        Attempts to fetch repository metadata as a smoke test for BSR access.
        module_name should be formatted like 'owner/repo'.
        """
        if not self.token:
            _log.error("BUF_TOKEN not set; cannot access BSR.")
            return None

        # E.g., module_name = "acme/paymentapis"
        parts = module_name.split("/")
        if len(parts) != 2:
            _log.error("module_name must be 'owner/repo'")
            return None

        owner, repo = parts[0], parts[1]

        payload = {
            "repositoryName": repo,
            "ownerName": owner
        }

        url = f"{self.base_url}/GetRepository"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    _log.info("Successfully connected to BSR for %s", module_name)
                    return json.dumps(data)
                return None
        except Exception as exc:
            _log.error("Failed to connect to Buf Schema Registry", error=str(exc))
            return None

    def fetch_proto_content(self, module_name: str, file_path: str = "main.proto") -> str | None:
        """
        Fetches the contents of a .proto file from the Buf Schema Registry.
        For demonstration, returns a stub protobuf if connected successfully.
        """
        metadata = self.fetch_schema(module_name)
        if metadata:
            _log.info("Mock-fetching %s from %s in BSR", file_path, module_name)
            return f'''
syntax = "proto3";
package buf.test;
service BufTestService {{
  rpc Ping (PingRequest) returns (PingResponse) {{}}
}}
message PingRequest {{ string message = 1; }}
message PingResponse {{ string message = 1; }}
'''
        return None
