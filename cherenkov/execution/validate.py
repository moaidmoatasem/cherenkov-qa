"""
CHERENKOV execution/validate.py — validation and value assertion tightening report engine. Track A surface only.
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml
except ImportError:
    _yaml = None  # type: ignore[assignment]

from cherenkov.core.errors import get_logger
from cherenkov.execution.playwright_invoke import PlaywrightRunner
from cherenkov.execution.trace_reader import TraceReader


def _preflight_check(tests_dir: str, spec_path: str | None) -> list[str]:
    """Return warnings for tests that assert fields not present in the spec's response schemas."""
    warnings: list[str] = []
    if not spec_path or not os.path.exists(spec_path):
        return warnings
    try:
        with open(spec_path, encoding="utf-8") as f:
            if spec_path.endswith(".json"):
                spec = json.load(f)
            elif _yaml is not None:
                spec = _yaml.safe_load(f)
            else:
                return warnings
    except Exception:
        return warnings

    # Collect all property names defined in response schemas
    spec_fields: set[str] = set()
    components = spec.get("components", {}).get("schemas", {})
    for schema in components.values():
        props = schema.get("properties", {})
        spec_fields.update(props.keys())

    if not spec_fields or not os.path.isdir(tests_dir):
        return warnings

    # Scan test files for toHaveProperty('field') assertions
    field_re = re.compile(r"toHaveProperty\(['\"](\w+)['\"]")
    for fname in os.listdir(tests_dir):
        if not fname.endswith(".spec.ts"):
            continue
        fpath = os.path.join(tests_dir, fname)
        try:
            with open(fpath, encoding="utf-8") as fh:
                code = fh.read()
        except Exception:
            continue
        for match in field_re.finditer(code):
            field = match.group(1)
            if field not in spec_fields:
                warnings.append(
                    f"  [{fname}] asserts toHaveProperty('{field}') — field not in spec schemas"
                )
    return warnings


def _is_stable_value(v: object) -> bool:
    """Return False for values likely to change between runs (timestamps, UUIDs, large ints)."""
    if isinstance(v, str):
        # Skip UUID-like strings
        if re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", v, re.I
        ):
            return False
        # Skip ISO timestamps
        if re.match(r"^\d{4}-\d{2}-\d{2}T", v):
            return False
    return not (isinstance(v, int) and v > 100000)


class TighteningAnalyzer:
    """Compares sent request bodies vs received response bodies to suggest stronger value assertions."""

    @staticmethod
    def analyze(request_body_raw: str, response_body_raw: str) -> list[str]:
        suggestions = []
        if not request_body_raw or not response_body_raw:
            return suggestions

        try:
            req_json = json.loads(request_body_raw)
            resp_json = json.loads(response_body_raw)
        except Exception:
            return suggestions

        if not isinstance(req_json, dict) or not isinstance(resp_json, dict):
            return suggestions

        for rk, rv in req_json.items():
            for pk, pv in resp_json.items():
                if rv == pv and rv is not None and _is_stable_value(pv):
                    suggestions.append(
                        f"expect(data.{pk}).toBe('{pv}')"
                        if isinstance(pv, str)
                        else f"expect(data.{pk}).toBe({pv})"
                    )
                    if rk == pk:
                        suggestions.append(f"expect(data.{pk}).toBe(body.{rk})")
        return suggestions


class ValidationEngine:
    """Runs the Playwright test suite against a real server and produces value tightening reports."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or "validate"
        self.log = get_logger("VALIDATE", self.run_id)
        self.stub_dir = str(Path(__file__).parent.parent.parent / "stub")
        self.tests_dir = str(Path(self.stub_dir) / "generated_tests")

    def validate_suite(
        self,
        target_url: str,
        workers: int = 1,
        headed: bool = False,
        spec_path: str | None = None,
    ) -> dict[str, Any]:
        """Runs all spec tests in generated_tests against target_url and parses trace files for tightening suggestions."""
        self.log.info(
            "starting suite validation", target_url=target_url, workers=workers, headed=headed
        )

        preflight = _preflight_check(self.tests_dir, spec_path)
        if preflight:
            self.log.warning("pre-flight spec/test drift warnings", warnings=preflight)
            print("\nPRE-FLIGHT WARNINGS — tests assert fields not found in spec schemas:")  # noqa: T201
            for w in preflight:
                print(w)  # noqa: T201
            print()  # noqa: T201

        if not os.path.exists(self.tests_dir):
            self.log.warning("no generated tests directory found")
            return {
                "status": "empty",
                "message": "No generated tests found.",
                "reports": [],
            }

        test_files = [f for f in os.listdir(self.tests_dir) if f.endswith(".spec.ts")]
        if not test_files:
            return {"status": "empty", "message": "No spec files found.", "reports": []}

        reports = []

        def _run_single_test(t_file: str) -> dict:
            scenario_id = t_file.replace(".spec.ts", "")
            test_path = os.path.join(self.tests_dir, t_file)

            with open(test_path, encoding="utf-8") as f:
                code = f.read()

            runner = PlaywrightRunner(run_id=self.run_id)
            reader = TraceReader(run_id=self.run_id)
            self.log.info("validating scenario", scenario_id=scenario_id)

            result = runner.execute_test(
                scenario_id=scenario_id, api_url=target_url, test_code=code, headed=headed
            )

            trace_path = result.get("trace_path", "")
            passed = result.get("passed", False)
            suggestions = []
            req_body_str = ""
            resp_body_str = ""

            if passed and trace_path:
                method_match = re.search(
                    r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code
                )
                gql_match = re.search(r"request\.post\('([^']+)'", code)

                target_method = None
                target_url_path = None
                if method_match:
                    target_method = method_match.group(1)
                    target_url_path = method_match.group(2)
                elif gql_match:
                    target_method = "POST"
                    target_url_path = gql_match.group(1)

                if target_method and target_url_path:
                    response_info = reader.extract_http_response(
                        trace_path, target_url_path, target_method
                    )
                    if response_info:
                        req_body_str = response_info.get("request_body_raw", "")
                        resp_body_str = response_info.get("body_raw", "")
                        suggestions = TighteningAnalyzer.analyze(
                            req_body_str, resp_body_str
                        )

            return {
                "scenario_id": scenario_id,
                "passed": passed,
                "request_body": req_body_str,
                "response_body": resp_body_str,
                "suggestions": suggestions,
                "error": result.get("failure_message", "") if not passed else "",
            }

        if workers <= 1:
            # Sequential: avoids thread+subprocess interaction on Windows
            for tf in test_files:
                reports.append(_run_single_test(tf))
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(_run_single_test, tf) for tf in test_files]
                for future in as_completed(futures):
                    reports.append(future.result())

        return {
            "status": "success",
            "target_url": target_url,
            "reports": reports,
        }
