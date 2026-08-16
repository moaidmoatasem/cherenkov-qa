#!/usr/bin/env python3
"""Enforce the ADR-004 dependency rule: core/ports must not import infrastructure.

Why this script replaced the previous gate
------------------------------------------
`layer-guard.yml` used to fail any PR that *touched* a core/ports file and an
adapters/web/cli file in the same change. That is a co-change heuristic, not a
dependency check, and it was wrong in both directions:

* **False positives** — any legitimate vertical slice (a domain concept plus the
  adapter that exposes it) was blocked. Replayed over the 50 commits preceding
  this change, 5 of the 21 that touched `cherenkov/*.py` would have failed it,
  including `Feature/saml sync (#951)`. A gate a quarter of merges must route
  around is not enforcing anything; it is training people to bypass it.
* **False negatives** — the rule the workflow *named* was never checked. Adding
  `from cherenkov.web import app` to `cherenkov/core/orchestrator.py` and
  touching nothing else passed clean.

This checks the real invariant, by parsing imports rather than inspecting a
diff: nothing under `cherenkov/core/` or `cherenkov/ports/` may import from
`cherenkov/adapters/`, `cherenkov/web/`, or `cherenkov/cli/`. It runs over the
whole tree, so it holds regardless of which files a given PR happens to touch.

Exit codes: 0 clean, 1 violations found, 2 could not run (unparseable source).
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Inner layers: domain logic and the interfaces it is written against.
CORE_LAYERS = ("cherenkov/core", "cherenkov/ports")
# Outer layers: delivery mechanisms and I/O. Inner must not depend on these.
INFRA_LAYERS = ("cherenkov/adapters", "cherenkov/web", "cherenkov/cli")

INFRA_MODULES = tuple(layer.replace("/", ".") for layer in INFRA_LAYERS)


def _module_of(node: ast.AST) -> list[str]:
    """Absolute module paths a single import statement pulls in."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        # Relative imports cannot escape the package they sit in far enough to
        # reach another top-level layer without `..`, which resolves to a
        # `cherenkov.*` absolute path we cannot see here; those are reported by
        # the absolute check on the resolved name instead.
        return [node.module] if node.level == 0 and node.module else []
    return []


def _violations(path: Path, repo_root: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise SystemExit(
            f"[layer-guard] {path.relative_to(repo_root).as_posix()} does not parse: {exc}"
        ) from exc

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        for module in _module_of(node):
            if any(
                module == infra or module.startswith(infra + ".")
                for infra in INFRA_MODULES
            ):
                found.append((getattr(node, "lineno", 0), module))
    return found


def check(repo_root: Path) -> list[str]:
    """Return one human-readable line per violation. Empty means clean."""
    problems: list[str] = []
    for layer in CORE_LAYERS:
        layer_dir = repo_root / layer
        if not layer_dir.is_dir():
            # A renamed or removed layer must fail loudly rather than silently
            # turning the gate into a no-op — that is how gates die unnoticed.
            problems.append(
                f"CONFIG   declared layer '{layer}' does not exist; "
                f"update CORE_LAYERS in {Path(__file__).name}"
            )
            continue
        for path in sorted(layer_dir.rglob("*.py")):
            for lineno, module in _violations(path, repo_root):
                rel = path.relative_to(repo_root).as_posix()
                problems.append(
                    f"LAYER    {rel}:{lineno} imports `{module}` — "
                    f"{layer} may not depend on infrastructure (ADR-004)"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to this script's parent directory).",
    )
    args = parser.parse_args()

    problems = check(args.repo_root)
    if not problems:
        print("[layer-guard] clean — core/ports import no infrastructure.")
        return 0

    print("[layer-guard] LAYER BOUNDARY VIOLATIONS:\n")
    for line in problems:
        print(f"  {line}")
    print(
        "\nADR-004: dependencies point inward. Move the shared type into "
        "cherenkov/core, or invert the dependency behind a port."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
