"""cherenkov/cli/loaders.py — shared spec/suite file loaders for CLI commands.

Two error conventions coexist in the CLI and are both preserved here:

  * `load_json` / `load_yaml_or_json` — hard failures: print and `sys.exit(1)`.
  * `load_spec` — soft failure: print and return `None` so the caller decides.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click


def _fail(message: str) -> None:
    click.echo(click.style(f"[ERROR] {message}", fg="red"), err=True)
    sys.exit(1)


def load_json(path: str, label: str) -> dict:
    """Load a JSON document, exiting with status 1 on any problem.

    Args:
        path (str): Path to the JSON file to load.
        label (str): Human-readable label for error messages.

    Returns:
        dict: Parsed JSON dictionary content.
    """
    p = Path(path)
    if not p.exists():
        _fail(f"{label} not found: {path}")
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        _fail(f"{label} is not valid JSON: {e}")
    raise AssertionError("unreachable")  # pragma: no cover


def load_yaml_or_json(path: str, label: str) -> dict:
    """Load a YAML (``.yaml``/``.yml``) or JSON document, exiting on any problem.

    Args:
        path (str): Path to the YAML or JSON file to load.
        label (str): Human-readable label for error messages.

    Returns:
        dict: Parsed YAML/JSON content dictionary.
    """
    p = Path(path)
    if not p.exists():
        _fail(f"{label} not found: {path}")
    text = p.read_text()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml

            return yaml.safe_load(text)
        except Exception as e:
            _fail(f"{label} YAML parse error: {e}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        _fail(f"{label} JSON parse error: {e}")
    raise AssertionError("unreachable")  # pragma: no cover


def load_spec(spec_path: str) -> dict | None:
    """Load an OpenAPI spec from a local file path or HTTP(S) URL.

    Args:
        spec_path (str): Local file path or HTTP(S) URL pointing to the spec.

    Returns:
        dict | None: Parsed OpenAPI specification dictionary, or None if reading/parsing failed.
    """
    if spec_path.startswith(("http://", "https://")):
        import requests

        try:
            resp = requests.get(spec_path, timeout=15)
            resp.raise_for_status()
            raw: Any = resp.content
        except Exception as exc:
            click.echo(f"[ERROR] Could not fetch spec from {spec_path}: {exc}", err=True)
            return None
    else:
        p = Path(spec_path)
        if not p.exists():
            click.echo(f"[ERROR] Spec file not found: {spec_path}", err=True)
            return None
        raw = p.read_bytes()

    try:
        if spec_path.endswith((".yaml", ".yml")):
            import yaml  # type: ignore[import]

            return yaml.safe_load(raw)
        return json.loads(raw)
    except Exception as exc:
        click.echo(f"[ERROR] Could not parse spec: {exc}", err=True)
        return None


