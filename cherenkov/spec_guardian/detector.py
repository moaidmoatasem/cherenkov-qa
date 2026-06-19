"""Spec drift detector - compares actual API responses against OpenAPI spec."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from cherenkov.spec_guardian.core import (
    DriftEvent,
    DriftSeverity,
    DriftType,
)


class SpecDriftDetector:
    """Detects drift between actual API responses and OpenAPI spec."""
    
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.spec = self._load_spec(spec_path)
    
    def _load_spec(self, spec_path: str) -> dict[str, Any]:
        """Load OpenAPI spec from YAML or JSON file."""
        path = Path(spec_path)
        content = path.read_text(encoding="utf-8")
        
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(content)
        else:
            return json.loads(content)
    
    def check_response(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_body: Any,
        response_headers: dict[str, str] | None = None,
    ) -> list[DriftEvent]:
        """Check if an actual API response matches the spec.
        
        Args:
            endpoint: API endpoint path (e.g., "/users/{id}")
            method: HTTP method (e.g., "GET")
            status_code: Actual HTTP status code
            response_body: Actual response body (parsed JSON)
            response_headers: Optional response headers
            
        Returns:
            List of DriftEvent objects (empty if fully compliant)
        """
        events: list[DriftEvent] = []
        
        # Find the operation in the spec
        operation = self._find_operation(endpoint, method)
        if operation is None:
            events.append(DriftEvent(
                drift_type=DriftType.SCHEMA_DRIFT,
                severity=DriftSeverity.CRITICAL,
                endpoint=endpoint,
                method=method,
                field_path=None,
                expected="operation defined in spec",
                actual="operation not found",
                message=f"Endpoint {method.upper()} {endpoint} not found in spec",
            ))
            return events
        
        # Check status code
        status_events = self._check_status_code(
            endpoint, method, status_code, operation
        )
        events.extend(status_events)
        
        # Check response body schema
        if status_code < 400 and response_body is not None:
            schema = self._get_response_schema(operation, status_code)
            if schema is not None:
                schema_events = self._check_schema(
                    endpoint, method, response_body, schema, field_path=""
                )
                events.extend(schema_events)
        
        return events
    
    def _find_operation(self, endpoint: str, method: str) -> dict[str, Any] | None:
        """Find an operation in the spec by endpoint and method."""
        paths = self.spec.get("paths", {})
        
        # Try exact match first
        if endpoint in paths:
            operation = paths[endpoint].get(method.lower())
            if operation:
                return operation
        
        # Try pattern matching for path parameters
        for path_pattern, path_item in paths.items():
            if self._path_matches(endpoint, path_pattern):
                operation = path_item.get(method.lower())
                if operation:
                    return operation
        
        return None
    
    def _path_matches(self, actual_path: str, pattern: str) -> bool:
        """Check if an actual path matches a pattern with parameters."""
        # Simple pattern matching: split by / and compare segments
        actual_segments = actual_path.strip("/").split("/")
        pattern_segments = pattern.strip("/").split("/")
        
        if len(actual_segments) != len(pattern_segments):
            return False
        
        for actual_seg, pattern_seg in zip(actual_segments, pattern_segments):
            if pattern_seg.startswith("{") and pattern_seg.endswith("}"):
                continue  # Path parameter, matches anything
            if actual_seg != pattern_seg:
                return False
        
        return True
    
    def _check_status_code(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        operation: dict[str, Any],
    ) -> list[DriftEvent]:
        """Check if status code matches spec."""
        events: list[DriftEvent] = []
        responses = operation.get("responses", {})
        
        # Check for exact status code match
        status_str = str(status_code)
        if status_str not in responses:
            # Check for range (2XX, 4XX, etc.)
            range_str = f"{status_code // 100}XX"
            if range_str not in responses:
                # Check for "default" response
                if "default" not in responses:
                    events.append(DriftEvent(
                        drift_type=DriftType.STATUS_DRIFT,
                        severity=DriftSeverity.WARNING,
                        endpoint=endpoint,
                        method=method,
                        field_path=None,
                        expected=list(responses.keys()),
                        actual=status_code,
                        message=f"Status code {status_code} not defined in spec",
                    ))
        
        return events
    
    def _get_response_schema(
        self,
        operation: dict[str, Any],
        status_code: int,
    ) -> dict[str, Any] | None:
        """Extract response schema for a status code."""
        responses = operation.get("responses", {})
        status_str = str(status_code)
        
        response_def = responses.get(status_str)
        if response_def is None:
            range_str = f"{status_code // 100}XX"
            response_def = responses.get(range_str)
        
        if response_def is None:
            return None
        
        # Handle OpenAPI 3.0 content structure
        content = response_def.get("content", {})
        if "application/json" in content:
            schema = content["application/json"].get("schema")
            if schema:
                return self._resolve_schema(schema)
        
        # Handle OpenAPI 2.0 schema structure
        schema = response_def.get("schema")
        if schema:
            return self._resolve_schema(schema)
        
        return None
    
    def _resolve_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Resolve $ref references in schema."""
        if "$ref" in schema:
            ref_path = schema["$ref"]
            return self._resolve_ref(ref_path)
        return schema
    
    def _resolve_ref(self, ref_path: str) -> dict[str, Any]:
        """Resolve a $ref path to the actual schema."""
        # Handle #/components/schemas/Name or #/definitions/Name
        if ref_path.startswith("#/"):
            parts = ref_path[2:].split("/")
            current = self.spec
            for part in parts:
                current = current.get(part, {})
            return current
        return {}
    
    def _check_schema(
        self,
        endpoint: str,
        method: str,
        actual: Any,
        schema: dict[str, Any],
        field_path: str,
    ) -> list[DriftEvent]:
        """Recursively check if actual value matches schema."""
        events: list[DriftEvent] = []
        
        schema_type = schema.get("type")
        
        if schema_type == "object":
            events.extend(self._check_object(endpoint, method, actual, schema, field_path))
        elif schema_type == "array":
            events.extend(self._check_array(endpoint, method, actual, schema, field_path))
        elif schema_type in ("string", "integer", "number", "boolean"):
            events.extend(self._check_primitive(endpoint, method, actual, schema, field_path))
        
        return events
    
    def _check_object(
        self,
        endpoint: str,
        method: str,
        actual: Any,
        schema: dict[str, Any],
        field_path: str,
    ) -> list[DriftEvent]:
        """Check object against schema."""
        events: list[DriftEvent] = []
        
        if not isinstance(actual, dict):
            events.append(DriftEvent(
                drift_type=DriftType.TYPE_MISMATCH,
                severity=DriftSeverity.CRITICAL,
                endpoint=endpoint,
                method=method,
                field_path=field_path or "(root)",
                expected="object",
                actual=type(actual).__name__,
                message=f"Expected object at {field_path or '(root)'}, got {type(actual).__name__}",
            ))
            return events
        
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Check for missing required fields
        for req_field in required:
            if req_field not in actual:
                events.append(DriftEvent(
                    drift_type=DriftType.REQUIRED_MISSING,
                    severity=DriftSeverity.CRITICAL,
                    endpoint=endpoint,
                    method=method,
                    field_path=f"{field_path}.{req_field}" if field_path else req_field,
                    expected="field present",
                    actual="field missing",
                    message=f"Required field '{req_field}' missing at {field_path or '(root)'}",
                ))
        
        # Check for extra fields not in spec
        for field in actual:
            if field not in properties:
                events.append(DriftEvent(
                    drift_type=DriftType.FIELD_EXTRA,
                    severity=DriftSeverity.INFO,
                    endpoint=endpoint,
                    method=method,
                    field_path=f"{field_path}.{field}" if field_path else field,
                    expected="field not in spec",
                    actual="field present",
                    message=f"Extra field '{field}' at {field_path or '(root)'} not in spec",
                ))
        
        # Recursively check defined properties
        for field, field_schema in properties.items():
            if field in actual:
                child_path = f"{field_path}.{field}" if field_path else field
                resolved_schema = self._resolve_schema(field_schema)
                events.extend(self._check_schema(
                    endpoint, method, actual[field], resolved_schema, child_path
                ))
        
        return events
    
    def _check_array(
        self,
        endpoint: str,
        method: str,
        actual: Any,
        schema: dict[str, Any],
        field_path: str,
    ) -> list[DriftEvent]:
        """Check array against schema."""
        events: list[DriftEvent] = []
        
        if not isinstance(actual, list):
            events.append(DriftEvent(
                drift_type=DriftType.TYPE_MISMATCH,
                severity=DriftSeverity.CRITICAL,
                endpoint=endpoint,
                method=method,
                field_path=field_path or "(root)",
                expected="array",
                actual=type(actual).__name__,
                message=f"Expected array at {field_path or '(root)'}, got {type(actual).__name__}",
            ))
            return events
        
        # Check array items
        items_schema = schema.get("items", {})
        if items_schema:
            resolved_items_schema = self._resolve_schema(items_schema)
            for i, item in enumerate(actual[:10]):  # Limit to first 10 items
                item_path = f"{field_path}[{i}]"
                events.extend(self._check_schema(
                    endpoint, method, item, resolved_items_schema, item_path
                ))
        
        return events
    
    def _check_primitive(
        self,
        endpoint: str,
        method: str,
        actual: Any,
        schema: dict[str, Any],
        field_path: str,
    ) -> list[DriftEvent]:
        """Check primitive value against schema."""
        events: list[DriftEvent] = []
        
        schema_type = schema.get("type")
        
        # Type checking
        type_ok = False
        if schema_type == "string":
            type_ok = isinstance(actual, str)
        elif schema_type == "integer":
            type_ok = isinstance(actual, int) and not isinstance(actual, bool)
        elif schema_type == "number":
            type_ok = isinstance(actual, (int, float)) and not isinstance(actual, bool)
        elif schema_type == "boolean":
            type_ok = isinstance(actual, bool)
        
        if not type_ok:
            events.append(DriftEvent(
                drift_type=DriftType.TYPE_MISMATCH,
                severity=DriftSeverity.CRITICAL,
                endpoint=endpoint,
                method=method,
                field_path=field_path or "(root)",
                expected=schema_type,
                actual=type(actual).__name__,
                message=f"Type mismatch at {field_path or '(root)'}: expected {schema_type}, got {type(actual).__name__}",
            ))
            return events
        
        # Range validation
        if schema_type in ("integer", "number"):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and actual < minimum:
                events.append(DriftEvent(
                    drift_type=DriftType.RANGE_VIOLATION,
                    severity=DriftSeverity.WARNING,
                    endpoint=endpoint,
                    method=method,
                    field_path=field_path or "(root)",
                    expected=f">= {minimum}",
                    actual=actual,
                    message=f"Value {actual} below minimum {minimum} at {field_path or '(root)'}",
                ))
            if maximum is not None and actual > maximum:
                events.append(DriftEvent(
                    drift_type=DriftType.RANGE_VIOLATION,
                    severity=DriftSeverity.WARNING,
                    endpoint=endpoint,
                    method=method,
                    field_path=field_path or "(root)",
                    expected=f"<= {maximum}",
                    actual=actual,
                    message=f"Value {actual} above maximum {maximum} at {field_path or '(root)'}",
                ))
        
        # Pattern validation
        if schema_type == "string":
            pattern = schema.get("pattern")
            if pattern and not self._matches_pattern(actual, pattern):
                events.append(DriftEvent(
                    drift_type=DriftType.PATTERN_VIOLATION,
                    severity=DriftSeverity.WARNING,
                    endpoint=endpoint,
                    method=method,
                    field_path=field_path or "(root)",
                    expected=f"pattern: {pattern}",
                    actual=actual,
                    message=f"Value does not match pattern at {field_path or '(root)'}",
                ))
        
        return events
    
    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches regex pattern."""
        import re
        try:
            return bool(re.match(pattern, value))
        except re.error:
            return True  # Invalid pattern, skip check
