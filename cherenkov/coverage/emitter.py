"""
CHERENKOV coverage/emitter.py — Epoch 11 Unit-Test Emitter.
Generates unit-level tests (pytest for Python, jest for TypeScript)
from individual endpoint schemas, then ejects them as standalone files.
"""

from __future__ import annotations

import json
import os
import re
import time

from cherenkov.core.settings import get_settings
from cherenkov.core.contracts import GenerateOutput, Status, StageMeta, StageError
from cherenkov.core.errors import get_logger


PYTEST_TEMPLATE = '''"""Unit test for {endpoint} — {method} {path}"""
import pytest
import requests


BASE_URL = "{base_url}"


class Test{cls_name}:

    def test_{test_name}_happy(self):
        """{scenario_description}"""
        response = requests.{method}(
            f"{{BASE_URL}}{path}",
            {body_kwargs}
        )
        assert response.status_code == {expected_status}
        data = response.json()
        assert data is not None

    def test_{test_name}_shape(self):
        """Response body matches expected shape"""
        response = requests.{method}(f"{{BASE_URL}}{path}"{body_kwargs_no_http})
        assert response.status_code == {expected_status}
        data = response.json()
        {shape_assertions}
'''


JEST_TEMPLATE = """/** Unit test for {endpoint} — {method} {path} */
import fetch from "node-fetch";

const BASE_URL = "{base_url}";

describe("{cls_name}", () => {{

  it("should return {expected_status} on happy path", async () => {{
    const response = await fetch(`${{BASE_URL}}{path}`, {{
      method: "{method_upper}",
      {jest_headers}
    }});
    expect(response.status).toBe({expected_status});
    const data = await response.json();
    expect(data).not.toBeNull();
  }});

  it("should return correct response shape", async () => {{
    const response = await fetch(`${{BASE_URL}}{path}`, {{
      method: "{method_upper}",
      {jest_headers}
    }});
    const data = await response.json();
    {jest_shape_assertions}
  }});
}});
"""


class UnitTestEmitter:
    """Generates standalone unit tests from OpenAPI endpoint schemas.

    Supports two output formats:
    - ``pytest``: Python unittest-style with requests library
    - ``jest``: TypeScript with node-fetch

    Tests are designed to be ejected with zero CHERENKOV dependency.
    """

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("COVERAGE_EMITTER", run_id)

    def emit(
        self,
        endpoint_slices: list,
        output_dir: str = "generated_unit_tests",
        framework: str = "pytest",
        base_url: str = "",
    ) -> list[GenerateOutput]:
        """Emit unit tests for a list of endpoint slices.

        Args:
            endpoint_slices: list of endpoint slice dicts with path/method/operation
            output_dir: where to write test files
            framework: "pytest" or "jest"
            base_url: the API base URL

        Returns:
            list of GenerateOutput with test_code populated
        """
        base_url = base_url or get_settings().API_URL
        os.makedirs(output_dir, exist_ok=True)
        results: list[GenerateOutput] = []

        for slice_data in endpoint_slices:
            t0 = time.time()
            path = slice_data.get("path", "/")
            method = slice_data.get("method", "GET").lower()
            slice_data.get("operation", {})
            scenario_id = f"{method}_{path.replace('/', '_').strip('_')}"

            try:
                if framework == "pytest":
                    code = self._emit_pytest(slice_data, base_url)
                elif framework == "jest":
                    code = self._emit_jest(slice_data, base_url)
                else:
                    raise ValueError(
                        f"Unknown framework '{framework}'. Use 'pytest' or 'jest'."
                    )

                file_ext = ".py" if framework == "pytest" else ".ts"
                filename = f"{scenario_id}{file_ext}"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "w") as f:
                    f.write(code)

                results.append(
                    GenerateOutput(
                        scenario_id=scenario_id,
                        test_code=code,
                        status=Status.OK,
                        metadata=StageMeta(
                            stage="UNIT_EMITTER",
                            duration_ms=int((time.time() - t0) * 1000),
                        ),
                    )
                )
            except Exception as e:
                self.log.error("emit failed", scenario=scenario_id, error=str(e))
                results.append(
                    GenerateOutput(
                        scenario_id=scenario_id,
                        test_code="",
                        status=Status.FAILED,
                        errors=[StageError(code="EMIT_FAILED", detail=str(e))],
                        metadata=StageMeta(
                            stage="UNIT_EMITTER",
                            duration_ms=int((time.time() - t0) * 1000),
                        ),
                    )
                )

        return results

    def _emit_pytest(self, slice_data: dict, base_url: str) -> str:
        """Generate a pytest-compatible test file from an endpoint slice."""
        path = slice_data.get("path", "/")
        method = slice_data.get("method", "GET").lower()
        operation = slice_data.get("operation", {})
        summary = operation.get("summary", "") or ""
        cls_name = self._to_class_name(path, method)
        test_name = self._to_test_name(path, method)
        expected_status = self._infer_expected_status(operation)

        body_kwargs = ""
        body_kwargs_no_http = ""
        if method in ("post", "put", "patch"):
            sample_body = self._generate_sample_body(operation)
            body_kwargs = f"json={json.dumps(sample_body)},"
            body_kwargs_no_http = f", json={json.dumps(sample_body)}"

        shape_assertions = self._generate_shape_assertions(operation)

        return PYTEST_TEMPLATE.format(
            endpoint=f"{method.upper()} {path}",
            method=method,
            path=path,
            base_url=base_url,
            cls_name=cls_name,
            test_name=test_name,
            scenario_description=summary or f"{method.upper()} {path} unit test",
            body_kwargs=body_kwargs,
            body_kwargs_no_http=body_kwargs_no_http,
            expected_status=expected_status,
            shape_assertions=shape_assertions,
        )

    def _emit_jest(self, slice_data: dict, base_url: str) -> str:
        """Generate a jest-compatible test file from an endpoint slice."""
        path = slice_data.get("path", "/")
        method = slice_data.get("method", "GET")
        operation = slice_data.get("operation", {})
        cls_name = self._to_class_name(path, method.lower())
        expected_status = self._infer_expected_status(operation)

        body_kwargs = ""
        jest_headers = ""
        if method.lower() in ("post", "put", "patch"):
            sample_body = self._generate_sample_body(operation)
            body_kwargs = json.dumps(sample_body)
            jest_headers = '"Content-Type": "application/json",'

        jest_shape_assertions = self._generate_jest_shape_assertions(operation)

        return JEST_TEMPLATE.format(
            endpoint=f"{method.upper()} {path}",
            method=method.lower(),
            method_upper=method.upper(),
            path=path,
            base_url=base_url,
            cls_name=cls_name,
            expected_status=expected_status,
            body_kwargs=body_kwargs,
            jest_headers=jest_headers,
            jest_shape_assertions=jest_shape_assertions,
        )

    def _infer_expected_status(self, operation: dict) -> int:
        """Derive expected status from spec responses."""
        responses = operation.get("responses", {})
        for code in ("200", "201", "204", "202"):
            if code in responses:
                return int(code)
        for code in responses:
            try:
                return int(code)
            except (ValueError, TypeError):
                continue
        return 200

    def _generate_sample_body(self, operation: dict) -> dict:
        """Generate a minimal sample request body from the spec."""
        body = {}
        req_body = operation.get("requestBody", {})
        content = req_body.get("content", {})
        for media_type in ("application/json",):
            schema = content.get(media_type, {}).get("schema", {})
            props = schema.get("properties", {})
            for prop_name, prop_schema in props.items():
                prop_type = prop_schema.get("type", "string")
                if prop_type == "string":
                    body[prop_name] = "test"
                elif prop_type == "integer":
                    body[prop_name] = 1  # type: ignore
                elif prop_type == "boolean":
                    body[prop_name] = True  # type: ignore
                elif prop_type == "number":
                    body[prop_name] = 1.0  # type: ignore
                elif prop_type == "array":
                    body[prop_name] = []  # type: ignore
                elif prop_type == "object":
                    body[prop_name] = {}  # type: ignore
                else:
                    body[prop_name] = "test"
            break
        return body

    def _generate_shape_assertions(self, operation: dict) -> str:
        """Generate pytest shape assertions from response schema."""
        assertions = []
        responses = operation.get("responses", {})
        for status_code in ("200", "201"):
            content = responses.get(status_code, {}).get("content", {})
            for media_type in ("application/json",):
                schema = content.get(media_type, {}).get("schema", {})
                props = schema.get("properties", {})
                for prop_name in props:
                    assertions.append(f'        assert "{prop_name}" in data')
                if props:
                    assertions.append("        assert len(data) > 0")
                break
            if assertions:
                break
        if not assertions:
            assertions.append(
                "        assert isinstance(data, dict) or isinstance(data, list)"
            )
        return "\n".join(assertions)

    def _generate_jest_shape_assertions(self, operation: dict) -> str:
        """Generate jest shape assertions from response schema."""
        assertions = []
        responses = operation.get("responses", {})
        for status_code in ("200", "201"):
            content = responses.get(status_code, {}).get("content", {})
            for media_type in ("application/json",):
                schema = content.get(media_type, {}).get("schema", {})
                props = schema.get("properties", {})
                for prop_name in props:
                    assertions.append(
                        f'    expect(data).toHaveProperty("{prop_name}");'
                    )
                break
            if assertions:
                break
        if not assertions:
            assertions.append('    expect(typeof data).toBe("object");')
        return "\n".join(assertions)

    @staticmethod
    def _to_class_name(path: str, method: str) -> str:
        """Convert path/method to a PascalCase class name."""
        parts = re.findall(r"[a-zA-Z0-9]+", path)
        return "Test" + "".join(p.capitalize() for p in parts) + method.capitalize()

    @staticmethod
    def _to_test_name(path: str, method: str) -> str:
        """Convert path/method to a snake_case test name."""
        parts = re.findall(r"[a-zA-Z0-9]+", path)
        return "_".join(p.lower() for p in parts) + f"_{method}"
