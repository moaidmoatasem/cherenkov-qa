"""Extractor registry and the shared file walk.

The registry is the extension point: an extractor registers under a name, and a
profile's ``extractors`` list decides which names run. Registration is by
factory so that enabling an extractor costs nothing until it is actually used.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterator

from cherenkov.brainmap.config import BrainMapProfile
from cherenkov.brainmap.ports import Extractor

_REGISTRY: dict[str, Callable[[], Extractor]] = {}


def register(name: str, factory: Callable[[], Extractor]) -> None:
    """Register an extractor factory under ``name``.

    Args:
        name (str): Profile-facing name, e.g. ``"python"``.
        factory (Callable[[], Extractor]): Zero-argument constructor.
    """
    _REGISTRY[name] = factory


def registered_names() -> list[str]:
    """Return every registered extractor name, sorted."""
    _load_builtins()
    return sorted(_REGISTRY)


def build_extractors(names: list[str]) -> list[Extractor]:
    """Instantiate the named extractors, skipping unknown names.

    Args:
        names (list[str]): Extractor names from the profile, in run order.

    Returns:
        list[Extractor]: Instantiated extractors.
    """
    _load_builtins()
    return [_REGISTRY[name]() for name in names if name in _REGISTRY]


def _load_builtins() -> None:
    """Import the bundled extractor modules so they self-register."""
    if _REGISTRY:
        return
    from cherenkov.brainmap.extractors import (  # noqa: F401
        cli_commands,
        docs,
        frontend,
        http_routes,
        python_modules,
        tests_layer,
    )


def walk_files(profile: BrainMapProfile) -> Iterator[tuple[str, Path]]:
    """Yield every in-scope file under the profile root.

    Directory pruning happens during the walk rather than after it: on a repo
    with a ``node_modules`` the difference between pruning and filtering is
    tens of thousands of stat calls.

    Args:
        profile (BrainMapProfile): Active profile.

    Yields:
        tuple[str, Path]: Repo-relative forward-slash path, absolute path.
    """
    root = profile.root
    for dirpath, dirnames, filenames in os.walk(root, followlinks=profile.follow_symlinks):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if rel_dir == ".":
            rel_dir = ""
        kept: list[str] = []
        for name in dirnames:
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if not profile.is_excluded(rel) and not profile.is_excluded(rel + "/"):
                kept.append(name)
        dirnames[:] = sorted(kept)
        for name in sorted(filenames):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if profile.is_excluded(rel):
                continue
            yield rel, Path(dirpath) / name


def read_text(path: Path, max_bytes: int) -> str | None:
    """Read a file as UTF-8 text, or return ``None`` when it is not mappable.

    Args:
        path (Path): Absolute file path.
        max_bytes (int): Size ceiling; larger files are skipped.

    Returns:
        str | None: Decoded text, or ``None`` for oversized, binary or
        unreadable files.
    """
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def first_line(text: str | None, limit: int = 160) -> str:
    """Return the first non-empty line of ``text``, trimmed to ``limit``."""
    if not text:
        return ""
    for line in text.strip().splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:limit]
    return ""
