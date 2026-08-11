#!/usr/bin/env python3
"""
ci_version_check.py -- enforce version consistency across the repo.

The authoritative package version lives in pyproject.toml (drives the Python
package and Release Please version bumps). Every other surfaced version must
match it. Drift is exactly the failure this checker exists to prevent: a
README badge or MCP manifest claiming 1.2.0 while the package is 1.3.0.

Checked sources:
  - pyproject.toml   [project] version          (authoritative)
  - package.json     "version"                  (Release Please bumps this)
  - manifest.json    "version"                  (MCP/Smithery manifest)
  - README.md        Version badge (img.shields.io/badge/Version-<v>-green)
"""

from __future__ import annotations

import json
import os
import re
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def fail(msg: str) -> None:
    """Print failure message and exit with non-zero exit code.

    Args:
        msg: Error message string to print.

    Raises:
        SystemExit: Always exits process with code 1.
    """
    print(f"[FAIL] {msg}")
    sys.exit(1)


def read_version_from_pyproject() -> str:
    """Read the authoritative package version string from pyproject.toml.

    Returns:
        Version string extracted from pyproject.toml.
    """
    with open(os.path.join(_REPO_ROOT, "pyproject.toml"), encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"^version\s*=\s*[\"']([^\"']+)[\"']", content, re.MULTILINE)
    if not m:
        fail("pyproject.toml has no [project] version")
    return m.group(1)


def read_version_from_json(path: str) -> str:
    """Read version field from a relative JSON file path.

    Args:
        path: Relative path string to JSON file.

    Returns:
        Version string from JSON object.
    """
    with open(os.path.join(_REPO_ROOT, path), encoding="utf-8") as f:
        data = json.load(f)
    version = data.get("version")
    if not version:
        fail(f"{path} has no top-level 'version'")
    return version


def read_version_from_readme() -> str:
    """Read version string from the README.md version badge.

    Returns:
        Version string extracted from README.md badge URL.
    """
    with open(os.path.join(_REPO_ROOT, "README.md"), encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"badge/Version-([^\-]+)-green", content)
    if not m:
        fail("README.md has no Version badge (badge/Version-<v>-green)")
    return m.group(1)


def main() -> None:
    """Check version consistency across repo files against pyproject.toml.

    Returns:
        None.
    """
    print("=======================================================")
    print("     CHERENKOV VERSION CONSISTENCY CHECKER")
    print("=======================================================\n")

    authoritative = read_version_from_pyproject()
    print(f"pyproject.toml (authoritative): {authoritative}")

    checks = [
        ("package.json", read_version_from_json("package.json")),
        ("manifest.json", read_version_from_json("manifest.json")),
        ("README.md", read_version_from_readme()),
    ]

    mismatches = []
    for source, version in checks:
        status = "OK" if version == authoritative else "DRIFT"
        print(f"  {source}: {version}  [{status}]")
        if version != authoritative:
            mismatches.append((source, version))

    print()
    if mismatches:
        lines = "\n".join(f"  {s}: {v}" for s, v in mismatches)
        fail(
            "Version drift detected:\n"
            + lines
            + f"\n\nAll surfaced versions must equal pyproject.toml ({authoritative}). "
            "Fix the stale source(s) (or bump pyproject.toml first if this is a real release)."
        )

    print(f"[PASS] All surfaced versions match pyproject.toml ({authoritative}).")
    sys.exit(0)


if __name__ == "__main__":
    main()
