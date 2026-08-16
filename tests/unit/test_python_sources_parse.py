"""Every Python file in the repository must parse.

This gate exists because four files in this repository did not, and nothing
caught it. They were not exotic: two had a docstring inserted *inside* a
multi-line signature by an automated sweep, one was truncated mid-statement,
and one carried a UTF-8 BOM. None is imported by the test suite, so no test
failed — a file that cannot be parsed simply sat there being broken.

Parsing is the cheapest possible check and the one with no excuses. It runs in
well under a second over a thousand files, needs no imports, and executes
nothing.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories that are not this project's source: vendored dependencies, build
# output, virtualenvs, caches, and the brain map's own generated artefacts.
SKIP_DIRS = {
    ".git",
    ".claude",
    ".agents",
    ".freebuff",
    ".qwen",
    ".brainmap",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "brain-vault",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "target",
    "test_pypi_venv",
    "venv",
    ".venv",
}


def iter_python_files() -> list[Path]:
    """Return every first-party ``.py`` file in the repository.

    Returns:
        list[Path]: Absolute paths, sorted for a stable failure message.
    """
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        for name in filenames:
            if name.endswith(".py"):
                found.append(Path(dirpath) / name)
    return sorted(found)


def test_every_python_file_parses():
    """No file in the repository may be syntactically broken."""
    files = iter_python_files()
    assert files, "found no Python files — the walk is misconfigured"

    broken: list[str] = []
    for path in files:
        rel = path.relative_to(REPO_ROOT)
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
        except SyntaxError as exc:
            broken.append(f"{rel}:{exc.lineno}: {exc.msg}")
        except UnicodeDecodeError as exc:
            broken.append(f"{rel}: not valid UTF-8 ({exc.reason})")

    assert not broken, "Python files that do not parse:\n  " + "\n  ".join(broken)


def test_no_source_file_starts_with_a_byte_order_mark():
    """A BOM makes CPython reject the file; name it as a BOM, not as syntax.

    The test above already catches this — reading with the ``utf-8`` codec
    keeps the mark as ``U+FEFF``, which ``ast.parse`` rejects — but it reports
    ``invalid non-printable character U+FEFF at line 1``, which sends you
    looking for an invisible character rather than at the first three bytes.
    This assertion exists for its error message.
    """
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in iter_python_files()
        if path.read_bytes()[:3] == b"\xef\xbb\xbf"
    ]
    assert not offenders, "Python files starting with a UTF-8 BOM:\n  " + "\n  ".join(offenders)
