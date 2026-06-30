"""Data models for the Playbooks system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlaybookTrigger:
    """Conditions that determine whether a playbook applies to an endpoint."""

    path_prefix: str | None = None
    path_contains: str | None = None
    methods: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any([
            self.path_prefix,
            self.path_contains,
            self.methods,
            self.tags,
        ])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlaybookTrigger":
        return cls(
            path_prefix=data.get("path_prefix"),
            path_contains=data.get("path_contains"),
            methods=[m.upper() for m in data.get("methods", [])],
            tags=data.get("tags", []),
        )


@dataclass
class PlaybookFinding:
    """A violation or notice raised when a playbook's actions evaluate an endpoint."""

    playbook_name: str
    endpoint: str
    method: str
    level: str  # "info" | "warn" | "error"
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "playbook": self.playbook_name,
            "endpoint": self.endpoint,
            "method": self.method,
            "level": self.level,
            "message": self.message,
        }


@dataclass
class Playbook:
    """A named, reusable validation strategy that fires automatically when its
    trigger conditions match an endpoint during a daemon check cycle."""

    name: str
    description: str = ""
    trigger: PlaybookTrigger = field(default_factory=PlaybookTrigger)

    # Actions — what to enforce when this playbook fires
    required_headers: list[str] = field(default_factory=list)
    expected_status: list[int] = field(default_factory=list)
    forbidden_response_fields: list[str] = field(default_factory=list)
    required_response_fields: list[str] = field(default_factory=list)

    severity: str = "warn"
    source_path: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: str = "") -> "Playbook":
        trigger_data = data.get("trigger", {})
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            trigger=PlaybookTrigger.from_dict(trigger_data),
            required_headers=data.get("required_headers", []),
            expected_status=data.get("expected_status", []),
            forbidden_response_fields=data.get("forbidden_response_fields", []),
            required_response_fields=data.get("required_response_fields", []),
            severity=data.get("severity", "warn"),
            source_path=source_path,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "trigger": {
                "path_prefix": self.trigger.path_prefix,
                "path_contains": self.trigger.path_contains,
                "methods": self.trigger.methods,
                "tags": self.trigger.tags,
            },
            "required_headers": self.required_headers,
            "expected_status": self.expected_status,
            "forbidden_response_fields": self.forbidden_response_fields,
            "required_response_fields": self.required_response_fields,
            "severity": self.severity,
        }
