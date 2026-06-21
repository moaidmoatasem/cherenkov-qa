"""
cherenkov/core/staleness.py — Test staleness detection.

Tracks which spec hash produced which generated test files so that when a
spec changes, stale tests can be flagged before they silently mis-report.

Manifest lives at .cherenkov/test_manifest.json:
    {
      "spec_path": "stub/target_spec.json",
      "spec_hash":  "<sha256>",
      "generated_at": "<iso8601>",
      "tests": ["stub/generated_tests/foo.spec.ts", ...]
    }

Usage:
    from cherenkov.core.staleness import TestManifest

    m = TestManifest()
    m.record(spec_path="stub/target_spec.json", test_files=[...])

    report = m.check()
    if report.stale:
        for f in report.stale_files:
            print(f"STALE: {f}")
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


_MANIFEST_PATH = Path(".cherenkov/test_manifest.json")


@dataclass
class StalenessReport:
    stale: bool
    spec_path: str
    recorded_hash: str
    current_hash: str
    stale_files: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    message: str = ""


def _file_sha256(path: str | Path) -> str:
    """SHA-256 of a file's content. Returns empty string if file is unreadable."""
    try:
        data = Path(path).read_bytes()
        return hashlib.sha256(data).hexdigest()
    except OSError:
        return ""


class TestManifest:
    """Records and checks spec→tests provenance."""

    def __init__(self, manifest_path: Path = _MANIFEST_PATH):
        self._path = manifest_path

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def record(
        self,
        spec_path: str,
        test_files: Sequence[str],
    ) -> None:
        """Write a new manifest entry after generating tests from *spec_path*."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "spec_path": str(spec_path),
            "spec_hash": _file_sha256(spec_path),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tests": [str(f) for f in test_files],
        }
        self._path.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    def check(self) -> StalenessReport:
        """Compare current spec hash against the recorded hash.

        Returns a StalenessReport. stale=True when:
          - No manifest exists (never recorded)
          - Spec file has changed since tests were generated
          - Any recorded test file is missing from disk
        """
        data = self._load()
        if not data:
            return StalenessReport(
                stale=True,
                spec_path="",
                recorded_hash="",
                current_hash="",
                message="No manifest found — tests may never have been generated.",
            )

        spec_path = data.get("spec_path", "")
        recorded_hash = data.get("spec_hash", "")
        test_files = data.get("tests", [])

        current_hash = _file_sha256(spec_path)

        missing = [f for f in test_files if not Path(f).exists()]
        hash_changed = recorded_hash != current_hash

        stale = hash_changed or bool(missing)
        parts: list[str] = []
        if hash_changed:
            parts.append(f"spec '{spec_path}' has changed since tests were generated")
        if missing:
            parts.append(f"{len(missing)} test file(s) are missing from disk")

        return StalenessReport(
            stale=stale,
            spec_path=spec_path,
            recorded_hash=recorded_hash,
            current_hash=current_hash,
            stale_files=test_files if hash_changed else [],
            missing_files=missing,
            message="; ".join(parts) if parts else "Tests are up to date.",
        )

    def info(self) -> dict:
        """Return raw manifest data for display."""
        return self._load()
