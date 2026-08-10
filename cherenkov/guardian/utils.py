# cherenkov/guardian/utils.py
"""Utility helpers for the Spec Guardian daemon.
Provides functions to derive default endpoints from an OpenAPI spec and to parse
user‑provided `--endpoint` options.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

from cherenkov.cli.loaders import load_yaml_or_json

def default_endpoints(spec_path: str) -> List[dict[str, Any]]:
    """Derive a safe, read‑only list of concrete GET endpoints from an OpenAPI spec.

    Parameters
    ----------
    spec_path: str
        Path to the OpenAPI YAML/JSON file.

    Returns
    -------
    List[dict]
        List of endpoint dictionaries with ``method`` and ``path`` keys.
    """
    spec = load_yaml_or_json(spec_path, "spec")
    endpoints: List[dict[str, Any]] = []
    for path, item in (spec.get("paths") or {}).items():
        if "{" in path or not isinstance(item, dict):
            continue
        if "get" in item:
            endpoints.append({"method": "GET", "path": path})
    return endpoints


def parse_endpoint_opts(raw: tuple[str, ...]) -> List[dict[str, Any]]:
    """Parse repeatable ``--endpoint METHOD:PATH`` CLI options.

    Returns a list of dictionaries suitable for the daemon loop.
    """
    endpoints: List[dict[str, Any]] = []
    for entry in raw:
        method, sep, path = entry.partition(":")
        if not sep:
            raise ValueError(f"--endpoint must be METHOD:PATH, got: {entry!r}")
        endpoints.append({"method": method.strip().upper(), "path": path.strip()})
    return endpoints
