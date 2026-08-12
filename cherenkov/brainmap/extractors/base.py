"""Extractor resolution and the shared file walk.

A profile's ``extractors`` list is a list of *names*, and this module turns
those names into instances. Three sources are consulted, in order:

1. Anything an embedding application registered at runtime via :func:`register`.
2. The bundled extractors in :data:`BUILTIN_EXTRACTORS`.
3. A dotted spec — ``some.package.module:ExtractorClass`` — which is how another
   project adds its own extractor without patching CHERENKOV at all.

Resolution goes through :func:`importlib.import_module` rather than a top-level
import of each bundled extractor. That is not a workaround: a registry that
statically imports the modules which import the registry is a genuine import
cycle, and routing through the name keeps the dependency one-directional
(extractors → base, never back) while making (3) fall out for free.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Callable, Iterator

from cherenkov.brainmap.config import BrainMapProfile
from cherenkov.brainmap.ports import Extractor

# Bundled extractor name → ``module:ClassName``.
BUILTIN_EXTRACTORS: dict[str, str] = {
    "python": "cherenkov.brainmap.extractors.python_modules:PythonExtractor",
    "routes": "cherenkov.brainmap.extractors.http_routes:RouteExtractor",
    "cli": "cherenkov.brainmap.extractors.cli_commands:CliExtractor",
    "frontend": "cherenkov.brainmap.extractors.frontend:FrontendExtractor",
    "docs": "cherenkov.brainmap.extractors.docs:DocsExtractor",
    "tests": "cherenkov.brainmap.extractors.tests_layer:TestsExtractor",
}

_REGISTRY: dict[str, Callable[[], Extractor]] = {}


def register(name: str, factory: Callable[[], Extractor]) -> None:
    """Register an extractor factory under ``name``.

    For extractors constructed in-process. A project shipping its own extractor
    in its own package does not need this — it can name the class directly in
    its profile as ``my.package.module:MyExtractor``.

    Args:
        name (str): Profile-facing name, e.g. ``"terraform"``.
        factory (Callable[[], Extractor]): Zero-argument constructor.
    """
    _REGISTRY[name] = factory


def registered_names() -> list[str]:
    """Return every name that resolves without a dotted spec, sorted."""
    return sorted(set(BUILTIN_EXTRACTORS) | set(_REGISTRY))


def build_extractors(names: list[str]) -> list[Extractor]:
    """Instantiate the named extractors, skipping any that will not load.

    An unresolvable name is skipped rather than raised on: a profile naming an
    extractor from a package that is not installed should map everything else,
    not refuse to map anything.

    Args:
        names (list[str]): Extractor names or dotted specs, in run order.

    Returns:
        list[Extractor]: Instantiated extractors.
    """
    built: list[Extractor] = []
    for name in names:
        factory = _REGISTRY.get(name)
        if factory is not None:
            built.append(factory())
            continue
        spec = BUILTIN_EXTRACTORS.get(name, name if ":" in name else "")
        if not spec:
            continue
        loaded = _load(spec)
        if loaded is not None:
            built.append(loaded())
    return built


def _load(spec: str) -> Callable[[], Extractor] | None:
    """Import ``module:ClassName`` and return the class, or ``None``.

    Args:
        spec (str): Dotted module path and attribute, colon-separated.

    Returns:
        Callable[[], Extractor] | None: The extractor class, or ``None`` when
        the module is missing or does not define that attribute.
    """
    module_path, _, attr = spec.partition(":")
    try:
        module = importlib.import_module(module_path)
    except ImportError:
        return None
    factory = getattr(module, attr, None)
    return factory if callable(factory) else None


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
