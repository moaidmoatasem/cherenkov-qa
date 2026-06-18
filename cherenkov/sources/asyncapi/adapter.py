"""AsyncAPI source adapter - parses AsyncAPI specs into typed operations."""

from __future__ import annotations

from typing import Any, Iterator

import yaml

from cherenkov.sources.asyncapi.contracts import AsyncAPIOperation


class AsyncAPISourceAdapter:
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.raw = self._load_spec()

    def _load_spec(self) -> dict[str, Any]:
        with open(self.spec_path) as f:
            return yaml.safe_load(f)

    def _resolve_ref(self, ref: str, root: dict[str, Any] | None = None) -> dict:
        """Resolve a JSON Reference ($ref) within the spec."""
        root = root or self.raw
        parts = ref.lstrip("#/").split("/")
        current = root
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, {})
            else:
                return {}
        return current if isinstance(current, dict) else {}

    def _extract_schema(self, payload: dict, root: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in payload:
            return self._resolve_ref(payload["$ref"], root)
        if "payload" in payload:
            return self._extract_schema(payload["payload"], root)
        return payload

    def iter_operations(self) -> Iterator[AsyncAPIOperation]:
        channels = self.raw.get("channels", {})
        root = self.raw

        for channel_name, channel_item in channels.items():
            for operation in ("publish", "subscribe"):
                op_data = channel_item.get(operation)
                if not op_data:
                    continue

                message = op_data.get("message", {})
                if isinstance(message, list):
                    message = message[0] if message else {}

                message_name = None
                payload_schema = None
                headers_schema = None

                if isinstance(message, dict):
                    message_name = message.get("name")
                    if "$ref" in message:
                        ref = message["$ref"]
                        message = self._resolve_ref(ref, root)
                        message_name = message.get("name", ref.split("/")[-1])

                    payload = message.get("payload", {})
                    if payload:
                        payload_schema = self._extract_schema(
                            payload if isinstance(payload, dict) else {},
                            root,
                        )

                    headers = message.get("headers", {})
                    if headers:
                        headers_schema = self._extract_schema(
                            headers if isinstance(headers, dict) else {},
                            root,
                        )

                yield AsyncAPIOperation(
                    channel=channel_name,
                    operation=operation,
                    message_name=message_name,
                    content_type=(
                        message.get("contentType", "application/json")
                        if isinstance(message, dict)
                        else "application/json"
                    ),
                    payload_schema=payload_schema,
                    headers_schema=headers_schema,
                )
