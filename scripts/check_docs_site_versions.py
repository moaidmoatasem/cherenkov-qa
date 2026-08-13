#!/usr/bin/env python3
"""
check_docs_site_versions.py -- keep the published docs site's version aliases
honest.

`scripts/ci_version_check.py` covers versions *inside* the repo (pyproject,
package.json, manifest.json, README badge). This checker covers the one surface
that lives outside it: the mike/gh-pages docs site, where a `latest` alias can
silently point at an older minor while newer content sits under it.

That is exactly the failure this exists to prevent: `make docs-deploy-release
VERSION=1.2` run from a main checkout *after* v1.3.0 shipped, which rebuilds the
1.2 URL from tip-of-main content and drags the `latest` alias backwards with it.

Two modes:

    # Audit — is the live site's alias set coherent?
    python scripts/check_docs_site_versions.py

    # Guard — would deploying this version with `latest` be a regression?
    python scripts/check_docs_site_versions.py --target 1.2

Audit rules:
  1. Exactly one deployed version carries the `latest` alias.
  2. That version is the highest numeric version deployed.
  3. It matches pyproject.toml's major.minor.

Exit codes:
    0 -- coherent (or gh-pages unavailable and --strict not set)
    1 -- incoherent, or the requested --target would move `latest` backwards
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PAGES_REF = "origin/gh-pages"
_VERSIONS_FILE = "versions.json"


def fail(msg: str) -> None:
    """Print a failure message and exit non-zero.

    Args:
        msg: Error message string to print.

    Raises:
        SystemExit: Always exits the process with code 1.
    """
    print(f"[FAIL] {msg}")
    sys.exit(1)


def read_pyproject_version() -> str:
    """Return the authoritative package version from pyproject.toml.

    Returns:
        The version string, e.g. "1.3.0".
    """
    path = os.path.join(_REPO_ROOT, "pyproject.toml")
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r'^version\s*=\s*"([^"]+)"', line.strip())
            if match:
                return match.group(1)
    fail("no [project] version found in pyproject.toml")
    return ""  # unreachable, keeps type checkers quiet


def minor_series(version: str) -> str:
    """Reduce a version to the major.minor series mike deploys under.

    Args:
        version: A version string such as "1.3.0" or "1.3".

    Returns:
        The major.minor prefix, e.g. "1.3".
    """
    return ".".join(version.split(".")[:2])


def version_key(version: str) -> tuple[int, ...] | None:
    """Return a sortable tuple for a numeric version, or None if non-numeric.

    Args:
        version: A deployed version name, e.g. "1.3" or "dev".

    Returns:
        Tuple of integer components, or None for aliases like "dev".
    """
    parts = version.split(".")
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def load_deployed_versions(fetch: bool) -> list[dict] | None:
    """Read mike's versions.json from the gh-pages branch.

    Args:
        fetch: Whether to fetch origin/gh-pages when the ref is missing locally.

    Returns:
        The parsed versions.json list, or None when gh-pages is unreachable.
    """
    def show() -> str | None:
        result = subprocess.run(
            ["git", "show", f"{_PAGES_REF}:{_VERSIONS_FILE}"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else None

    raw = show()
    if raw is None and fetch:
        print(f"[INFO] {_PAGES_REF} not present locally — fetching...")
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", "gh-pages"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
        )
        raw = show()
    if raw is None:
        return None
    return json.loads(raw)


def find_latest_holders(deployed: list[dict]) -> list[str]:
    """Return the deployed versions carrying the `latest` alias.

    Args:
        deployed: Parsed versions.json entries.

    Returns:
        Version names holding the alias (normally exactly one).
    """
    return [
        entry["version"]
        for entry in deployed
        if "latest" in entry.get("aliases", []) or entry["version"] == "latest"
    ]


def highest_numeric(deployed: list[dict]) -> str | None:
    """Return the highest numeric version deployed.

    Args:
        deployed: Parsed versions.json entries.

    Returns:
        The highest version name, or None when nothing numeric is deployed.
    """
    numeric = [
        entry["version"]
        for entry in deployed
        if version_key(entry["version"]) is not None
    ]
    if not numeric:
        return None
    return max(numeric, key=version_key)  # type: ignore[arg-type,return-value]


def audit(deployed: list[dict], package_series: str) -> int:
    """Check that the site's `latest` alias points where it should.

    Args:
        deployed: Parsed versions.json entries.
        package_series: The package's major.minor, e.g. "1.3".

    Returns:
        Process exit code: 0 when coherent, 1 otherwise.
    """
    names = ", ".join(entry["version"] for entry in deployed)
    print(f"[INFO] deployed docs versions: {names}")

    holders = find_latest_holders(deployed)
    if len(holders) != 1:
        found = ", ".join(holders) if holders else "none"
        print(f"[FAIL] expected exactly one version aliased 'latest', found: {found}")
        return 1

    latest = holders[0]
    top = highest_numeric(deployed)
    print(f"[INFO] 'latest' -> {latest}; highest deployed: {top}; package: {package_series}")

    if top is not None and latest != top:
        print(
            f"[FAIL] 'latest' points at {latest} but {top} is deployed — readers "
            f"landing on /latest/ get the older minor."
        )
        print(f"       Fix: mike deploy --push --update-aliases {top} latest && "
              f"mike set-default --push latest  (build from tag v{top}.x)")
        return 1

    if latest != package_series:
        print(
            f"[FAIL] 'latest' points at {latest} but the package is {package_series} — "
            f"the {package_series} docs were never published, or {latest} was "
            f"redeployed after the {package_series} release."
        )
        print(f"       Fix: run the Deploy Docs workflow with version={package_series} "
              f"(builds from tag v{package_series}.x).")
        return 1

    print(f"[PASS] docs site aliases are coherent — 'latest' -> {latest}")
    return 0


def guard(deployed: list[dict], target: str, package_series: str, force: bool) -> int:
    """Check that deploying `target` with the `latest` alias is not a regression.

    Args:
        deployed: Parsed versions.json entries.
        target: The version alias about to be deployed, e.g. "1.2" or "dev".
        package_series: The package's major.minor, e.g. "1.3".
        force: Whether to downgrade refusals to warnings.

    Returns:
        Process exit code: 0 when the deploy is safe, 1 otherwise.
    """
    if version_key(target) is None:
        print(f"[PASS] '{target}' is a non-numeric alias — no 'latest' regression possible")
        return 0

    problems: list[str] = []
    top = highest_numeric(deployed)
    if top is not None and version_key(target) < version_key(top):  # type: ignore[operator]
        problems.append(
            f"deploying {target} with the 'latest' alias would move 'latest' "
            f"backwards from {top} to {target}"
        )
    if minor_series(target) != package_series:
        problems.append(
            f"target {target} does not match the package version series "
            f"{package_series} (pyproject.toml)"
        )

    if not problems:
        print(f"[PASS] deploying {target} as 'latest' is consistent with {package_series}")
        return 0

    label = "WARN" if force else "FAIL"
    for problem in problems:
        print(f"[{label}] {problem}")
    if force:
        print("[WARN] --force given — proceeding anyway")
        return 0
    print(
        "       If this is an intentional backport, deploy without the alias:\n"
        "         cd docs-site && mike deploy --push --update-aliases "
        f"{target}   # no 'latest'\n"
        "       Otherwise re-run with the current series: "
        f"make docs-deploy-release VERSION={package_series}"
    )
    return 1


def main() -> int:
    """Parse arguments and run the requested check.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        help="version about to be deployed with the 'latest' alias (guard mode)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="downgrade guard refusals to warnings",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail when gh-pages cannot be read instead of skipping",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="do not fetch origin/gh-pages when it is missing locally",
    )
    args = parser.parse_args()

    package_series = minor_series(read_pyproject_version())
    deployed = load_deployed_versions(fetch=not args.no_fetch)
    if deployed is None:
        message = f"could not read {_PAGES_REF}:{_VERSIONS_FILE} — is gh-pages fetched?"
        if args.strict:
            fail(message)
        print(f"[SKIP] {message}")
        return 0

    if args.target:
        return guard(deployed, args.target, package_series, args.force)
    return audit(deployed, package_series)


if __name__ == "__main__":
    sys.exit(main())
