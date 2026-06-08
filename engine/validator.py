import sys
from typing import Any, Optional

import requests

from spec_loader import extract_routes


def expand_path(path: str) -> str:
    if "{" in path:
        return path.replace("{petId}", "1").replace("{", "").replace("}", "")
    return path


def http_get(url: str, timeout: int = 10) -> Optional[requests.Response]:
    try:
        return requests.get(url, timeout=timeout)
    except requests.RequestException as e:
        return None


def http_post(url: str, timeout: int = 10) -> Optional[requests.Response]:
    try:
        return requests.post(url, json={"name": "test"}, timeout=timeout)
    except requests.RequestException as e:
        return None


METHOD_HANDLERS = {
    "GET": http_get,
    "PUT": http_get,
    "DELETE": http_get,
    "PATCH": http_get,
    "HEAD": http_get,
    "OPTIONS": http_get,
    "POST": http_post,
}


def run_validation(spec_path: str, target_base: str, strict: bool = True) -> dict[str, Any]:
    with open(spec_path, "r") as f:
        import json
        try:
            import yaml
            if spec_path.endswith((".yaml", ".yml")):
                spec = yaml.safe_load(f.read())
            else:
                f.seek(0)
                spec = json.load(f)
        except Exception:
            f.seek(0)
            spec = json.load(f)

    routes = extract_routes(spec)
    if not routes:
        return {
            "passed": False,
            "divergences": ["No routes found in spec"],
            "summary": "Spec has no testable endpoints",
            "checks": [],
        }

    checked = 0
    passed = 0
    divergences = []
    checks = []

    for (method, path), expected_statuses in sorted(routes.items()):
        checked += 1
        expanded = expand_path(path)
        url = f"{target_base.rstrip('/')}{expanded}"
        handler = METHOD_HANDLERS.get(method)
        if handler is None:
            divergences.append(f"{method} {path}: unsupported method")
            checks.append({"method": method, "path": path, "url": url, "passed": False, "error": "unsupported method"})
            continue

        resp = handler(url)
        if resp is None:
            divergences.append(f"{method} {path}: connection failed")
            checks.append({"method": method, "path": path, "url": url, "passed": False, "error": "connection failed"})
            continue

        actual_status = resp.status_code
        expected_str = ",".join(str(s) for s in sorted(expected_statuses)) if expected_statuses else "any"

        check = {
            "method": method,
            "path": path,
            "url": url,
            "expected": list(expected_statuses) if expected_statuses else [],
            "actual": actual_status,
            "passed": True,
        }

        if expected_statuses and actual_status not in expected_statuses:
            check["passed"] = False
            msg = f"{method} {path}: expected [{expected_str}] got {actual_status}"
            divergences.append(msg)
        else:
            passed += 1

        checks.append(check)

    summary = f"{passed}/{checked} endpoints passed"
    if divergences:
        summary += f" — {len(divergences)} divergence(s)"

    return {
        "passed": len(divergences) == 0,
        "divergences": divergences,
        "summary": summary,
        "checks": checks,
    }
