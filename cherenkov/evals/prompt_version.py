"""
cherenkov/evals/prompt_version.py — Prompt version tracking for eval regression.

Computes a stable SHA-256 fingerprint of every prompt file that influences
LLM output. The fingerprint is embedded in EvalReport and the eval baseline
so the RegressionGuard can warn when a prompt change is the actual cause of
a metric shift rather than a model quality regression.

Usage:
    from cherenkov.evals.prompt_version import get_prompt_fingerprint

    fingerprint = get_prompt_fingerprint()
    # {"sha256": "abc123...", "files": {"generator_system.txt": "def456..."}}
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Prompt files that directly affect generated test quality
_PROMPT_FILES = [
    "generator_system.txt",
    "graphql_test.j2",
    "grpc_test.j2",
    "asyncapi_test.j2",
    "accessibility_test.j2",
]


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
    except FileNotFoundError:
        h.update(b"<missing>")
    return h.hexdigest()[:16]


def get_prompt_fingerprint(prompts_dir: Path | None = None) -> dict:
    """Return a content-addressed fingerprint of all prompt files.

    Returns:
        {
            "sha256": "<combined 16-char hash>",
            "files": {"generator_system.txt": "<per-file hash>", ...}
        }
    """
    root = prompts_dir or _PROMPTS_DIR
    per_file: dict[str, str] = {}
    for name in _PROMPT_FILES:
        per_file[name] = _file_sha256(root / name)

    # Combined hash: deterministic JSON of sorted items
    combined = hashlib.sha256(
        json.dumps(sorted(per_file.items()), sort_keys=True).encode()
    )
    return {"sha256": combined.hexdigest()[:16], "files": per_file}


def prompt_changed(baseline_fingerprint: dict, current_fingerprint: dict) -> list[str]:
    """Return list of prompt files that changed between baseline and current.

    Returns empty list if nothing changed.
    """
    changed = []
    baseline_files = baseline_fingerprint.get("files", {})
    current_files = current_fingerprint.get("files", {})
    for name in set(list(baseline_files.keys()) + list(current_files.keys())):
        if baseline_files.get(name) != current_files.get(name):
            changed.append(name)
    return sorted(changed)
