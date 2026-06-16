"""
CHERENKOV cherenkov/diff/spec_differ.py — OpenAPI spec diff and breaking-change detection. Issue #437.

Detects breaking vs additive changes between two OpenAPI YAML/JSON specs.
Breaking changes cause `cherenkov diff` to exit with code 1.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


class ChangeType(str, Enum):
    REMOVED_ENDPOINT = "removed_endpoint"
    REMOVED_REQUIRED_PARAM = "removed_required_param"
    REMOVED_RESPONSE_CODE = "removed_response_code"
    CHANGED_PARAM_TYPE = "changed_param_type"
    ADDED_ENDPOINT = "added_endpoint"
    ADDED_OPTIONAL_PARAM = "added_optional_param"
    CHANGED_DESCRIPTION = "changed_description"


@dataclass
class SpecChange:
    change_type: ChangeType
    breaking: bool
    endpoint: str
    method: str | None
    detail: str
    before: Any = None
    after: Any = None


@dataclass
class SpecDiffReport:
    breaking: list[SpecChange] = field(default_factory=list)
    additive: list[SpecChange] = field(default_factory=list)
    informational: list[SpecChange] = field(default_factory=list)

    @property
    def has_breaking_changes(self) -> bool:
        return len(self.breaking) > 0

    def to_dict(self) -> dict:
        def _change_to_dict(c: SpecChange) -> dict:
            return {
                "change_type": c.change_type.value,
                "breaking": c.breaking,
                "endpoint": c.endpoint,
                "method": c.method,
                "detail": c.detail,
            }

        return {
            "breaking": [_change_to_dict(c) for c in self.breaking],
            "additive": [_change_to_dict(c) for c in self.additive],
            "informational": [_change_to_dict(c) for c in self.informational],
            "has_breaking_changes": self.has_breaking_changes,
            "summary": {
                "breaking_count": len(self.breaking),
                "additive_count": len(self.additive),
                "informational_count": len(self.informational),
            },
        }


class SpecDiffer:
    """Compare two OpenAPI specs and classify changes as breaking, additive, or informational."""

    def diff(self, before_path: str, after_path: str) -> SpecDiffReport:
        before = self._load(before_path)
        after = self._load(after_path)
        report = SpecDiffReport()

        before_paths = set(before.get("paths", {}).keys())
        after_paths = set(after.get("paths", {}).keys())

        # Removed endpoints — BREAKING
        for p in sorted(before_paths - after_paths):
            for method in before["paths"][p]:
                if method.lower() in _HTTP_METHODS:
                    report.breaking.append(
                        SpecChange(
                            change_type=ChangeType.REMOVED_ENDPOINT,
                            breaking=True,
                            endpoint=p,
                            method=method.upper(),
                            detail=f"Endpoint {method.upper()} {p} was removed",
                        )
                    )

        # Added endpoints — ADDITIVE
        for p in sorted(after_paths - before_paths):
            for method in after["paths"][p]:
                if method.lower() in _HTTP_METHODS:
                    report.additive.append(
                        SpecChange(
                            change_type=ChangeType.ADDED_ENDPOINT,
                            breaking=False,
                            endpoint=p,
                            method=method.upper(),
                            detail=f"New endpoint {method.upper()} {p} added",
                        )
                    )

        # Changed endpoints — inspect operations
        for p in sorted(before_paths & after_paths):
            self._diff_path_item(
                before["paths"][p],
                after["paths"][p],
                p,
                report,
            )

        return report

    def _diff_path_item(
        self,
        before_item: dict,
        after_item: dict,
        path: str,
        report: SpecDiffReport,
    ) -> None:
        for method in before_item:
            if method.lower() not in _HTTP_METHODS:
                continue
            if method not in after_item:
                # Method removed — BREAKING (already caught at path level if whole path removed)
                report.breaking.append(
                    SpecChange(
                        change_type=ChangeType.REMOVED_ENDPOINT,
                        breaking=True,
                        endpoint=path,
                        method=method.upper(),
                        detail=f"HTTP method {method.upper()} removed from {path}",
                    )
                )
                continue
            before_op = before_item[method]
            after_op = after_item[method]
            self._diff_parameters(before_op, after_op, path, method, report)
            self._diff_response_codes(before_op, after_op, path, method, report)

    def _diff_parameters(
        self,
        before_op: dict,
        after_op: dict,
        path: str,
        method: str,
        report: SpecDiffReport,
    ) -> None:
        before_params = {p["name"]: p for p in before_op.get("parameters", [])}
        after_params = {p["name"]: p for p in after_op.get("parameters", [])}

        for name, param in before_params.items():
            if name not in after_params:
                if param.get("required", False):
                    report.breaking.append(
                        SpecChange(
                            change_type=ChangeType.REMOVED_REQUIRED_PARAM,
                            breaking=True,
                            endpoint=path,
                            method=method.upper(),
                            detail=(
                                f"Required parameter '{name}' removed from "
                                f"{method.upper()} {path}"
                            ),
                        )
                    )
                else:
                    report.additive.append(
                        SpecChange(
                            change_type=ChangeType.ADDED_OPTIONAL_PARAM,
                            breaking=False,
                            endpoint=path,
                            method=method.upper(),
                            detail=f"Optional parameter '{name}' removed from {method.upper()} {path}",
                        )
                    )
            else:
                # Check type change
                before_type = param.get("schema", {}).get("type")
                after_type = after_params[name].get("schema", {}).get("type")
                if before_type and after_type and before_type != after_type:
                    report.breaking.append(
                        SpecChange(
                            change_type=ChangeType.CHANGED_PARAM_TYPE,
                            breaking=True,
                            endpoint=path,
                            method=method.upper(),
                            detail=(
                                f"Parameter '{name}' type changed from "
                                f"'{before_type}' to '{after_type}' in {method.upper()} {path}"
                            ),
                            before=before_type,
                            after=after_type,
                        )
                    )

        for name in after_params:
            if name not in before_params and after_params[name].get("required", False):
                # New required param — BREAKING (callers don't know to send it)
                report.breaking.append(
                    SpecChange(
                        change_type=ChangeType.REMOVED_REQUIRED_PARAM,
                        breaking=True,
                        endpoint=path,
                        method=method.upper(),
                        detail=(
                            f"New required parameter '{name}' added to "
                            f"{method.upper()} {path} — breaks existing callers"
                        ),
                    )
                )

    def _diff_response_codes(
        self,
        before_op: dict,
        after_op: dict,
        path: str,
        method: str,
        report: SpecDiffReport,
    ) -> None:
        before_resp = set(before_op.get("responses", {}).keys())
        after_resp = set(after_op.get("responses", {}).keys())

        for code in before_resp - after_resp:
            report.breaking.append(
                SpecChange(
                    change_type=ChangeType.REMOVED_RESPONSE_CODE,
                    breaking=True,
                    endpoint=path,
                    method=method.upper(),
                    detail=f"Response status {code} removed from {method.upper()} {path}",
                )
            )

    @staticmethod
    def _load(path: str) -> dict:
        import yaml  # pyyaml in requirements.txt

        with open(path, "r", encoding="utf-8") as f:
            if path.endswith((".yaml", ".yml")):
                return yaml.safe_load(f) or {}
            return json.load(f)


def print_diff_report(report: SpecDiffReport, fmt: str = "text") -> None:
    """Print a human-readable or JSON diff report to stdout."""
    if fmt == "json":
        print(json.dumps(report.to_dict(), indent=2))
        return

    # Text format
    total = len(report.breaking) + len(report.additive) + len(report.informational)
    if total == 0:
        print("No changes detected between specs.")
        return

    if report.breaking:
        print(f"\nBREAKING CHANGES ({len(report.breaking)}):")
        for c in report.breaking:
            meth = f"[{c.method}]" if c.method else ""
            print(f"  \u274c {meth} {c.endpoint} — {c.detail}")

    if report.additive:
        print(f"\nADDITIVE CHANGES ({len(report.additive)}):")
        for c in report.additive:
            meth = f"[{c.method}]" if c.method else ""
            print(f"  \u2705 {meth} {c.endpoint} — {c.detail}")

    if report.informational:
        print(f"\nINFORMATIONAL ({len(report.informational)}):")
        for c in report.informational:
            print(f"  \u2139\ufe0f  {c.endpoint} — {c.detail}")

    print()
    if report.has_breaking_changes:
        print("Run `cherenkov validate` to re-generate tests for affected endpoints.")
