"""Project profile — the one file you edit to point the brain map at a new repo.

A profile is pure data: what to scan, what to ignore, which extractors to run,
where the vault and database live, and how paths map to architectural layers.
CHERENKOV's own profile is the default; any other project gets mapped by
dropping a ``brainmap.toml`` at its root (or a ``[brainmap]`` table inside an
existing ``cherenkov.toml``) and running ``cherenkov brain build --root``.

Nothing in this module imports an extractor, a store or the web layer, so a
profile can be constructed and inspected without pulling the engine in.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_FILENAMES = ("brainmap.toml", "cherenkov.toml", "pyproject.toml")

DEFAULT_EXCLUDES = [
    "**/.git/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/.mypy_cache/**",
    "**/.pytest_cache/**",
    "**/dist/**",
    "**/build/**",
    "**/target/**",
    "**/.next/**",
    "**/coverage/**",
    "**/*.egg-info/**",
    "**/.brainmap/**",
    "**/brain-vault/**",
]

DEFAULT_EXTRACTORS = [
    "python",
    "frontend",
    "cli",
    "routes",
    "docs",
    "tests",
]


@dataclass
class BrainMapProfile:
    """Scan configuration for one project.

    Attributes:
        project: Namespace for the map; also the SQLite partition key.
        root: Absolute project root.
        excludes: Glob patterns never scanned, matched against repo-relative
            paths.
        extractors: Names of enabled extractors, in run order.
        source_roots: Directory prefixes treated as Python import roots, used
            to turn a file path into a dotted module name.
        doc_roots: Directory prefixes whose markdown is treated as
            documentation rather than incidental prose.
        test_roots: Directory prefixes holding tests.
        fixture_roots: Directory prefixes holding *corpora* — files that are
            read as data rather than executed. A generated-test fixture
            legitimately imports a client module that only exists once the
            suite is ejected, so an unresolved reference from one of these
            trees is not a broken link and must not be reported as one.
        layers: Path prefix → layer label, longest prefix wins.
        symbol_depth: How deep the Python extractor descends —
            ``"module"`` (modules only), ``"class"`` (plus classes, the
            default) or ``"function"`` (plus module-level functions). The
            knob exists because symbol-level nodes are what turn a readable
            map into an unreadable one on a large repo.
        max_file_bytes: Files larger than this are skipped — a vendored bundle
            has no place in a concept map and would dominate the scan cost.
        db_path: Where the SQLite store lives, relative to root unless absolute.
        vault_path: Where the Obsidian vault is written.
        follow_symlinks: Whether the walker descends symlinked directories.
    """

    project: str = "project"
    root: Path = field(default_factory=Path.cwd)
    excludes: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    extractors: list[str] = field(default_factory=lambda: list(DEFAULT_EXTRACTORS))
    source_roots: list[str] = field(default_factory=list)
    doc_roots: list[str] = field(default_factory=lambda: ["docs", "."])
    test_roots: list[str] = field(default_factory=lambda: ["tests", "test"])
    fixture_roots: list[str] = field(default_factory=list)
    layers: dict[str, str] = field(default_factory=dict)
    symbol_depth: str = "class"
    max_file_bytes: int = 512_000
    db_path: str = ".brainmap/brainmap.db"
    vault_path: str = "brain-vault"
    follow_symlinks: bool = False

    # ── derived paths ───────────────────────────────────────────────────────
    def resolved_db_path(self) -> Path:
        """Absolute path to the SQLite store."""
        p = Path(self.db_path)
        return p if p.is_absolute() else (self.root / p)

    def resolved_vault_path(self) -> Path:
        """Absolute path to the Obsidian vault directory."""
        p = Path(self.vault_path)
        return p if p.is_absolute() else (self.root / p)

    # ── scan policy ─────────────────────────────────────────────────────────
    def is_excluded(self, rel_path: str) -> bool:
        """Whether a repo-relative path matches any exclude pattern."""
        for pattern in self.excludes:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            # ``**/x/**`` does not match the directory's own entries on all
            # platforms, so also test the bare-prefix form.
            bare = pattern.strip("*/")
            if bare and (rel_path == bare or rel_path.startswith(bare + "/")):
                return True
        return False

    def is_fixture(self, rel_path: str) -> bool:
        """Whether a path lives in a corpus of files that are read, not run.

        Args:
            rel_path (str): Repo-relative path.

        Returns:
            bool: True when unresolved references from this file are expected.
        """
        return any(
            rel_path == root or rel_path.startswith(root.rstrip("/") + "/")
            for root in self.fixture_roots
        )

    def layer_for(self, rel_path: str) -> str:
        """Return the layer label for a path (longest matching prefix wins)."""
        best = ""
        best_len = -1
        for prefix, label in self.layers.items():
            if rel_path.startswith(prefix) and len(prefix) > best_len:
                best, best_len = label, len(prefix)
        return best

    def module_name(self, rel_path: str) -> str:
        """Convert a Python file path into its dotted module name.

        Args:
            rel_path (str): Repo-relative path to a ``.py`` file.

        Returns:
            str: Dotted module name, with ``__init__`` collapsed to the
            package name and any configured source root stripped.
        """
        path = rel_path[:-3] if rel_path.endswith(".py") else rel_path
        for source_root in sorted(self.source_roots, key=len, reverse=True):
            prefix = source_root.rstrip("/") + "/"
            if path.startswith(prefix):
                path = path[len(prefix) :]
                break
        parts = [p for p in path.split("/") if p]
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the profile."""
        return {
            "project": self.project,
            "root": str(self.root),
            "excludes": list(self.excludes),
            "extractors": list(self.extractors),
            "source_roots": list(self.source_roots),
            "doc_roots": list(self.doc_roots),
            "test_roots": list(self.test_roots),
            "fixture_roots": list(self.fixture_roots),
            "layers": dict(self.layers),
            "symbol_depth": self.symbol_depth,
            "max_file_bytes": self.max_file_bytes,
            "db_path": self.db_path,
            "vault_path": self.vault_path,
        }


# CHERENKOV's own layering, used when a repo ships no configuration of its own
# but does look like this repo.
CHERENKOV_LAYERS = {
    "cherenkov/core": "core",
    "cherenkov/ports": "core",
    "cherenkov/domain": "core",
    "cherenkov/adapters": "adapters",
    "cherenkov/web": "web",
    "cherenkov/cli": "cli",
    "cherenkov/stages": "pipeline",
    "cherenkov/mcp": "integrations",
    "cherenkov/integrations": "integrations",
    "docs": "docs",
    "tests": "tests",
}


def _read_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file, returning ``{}`` when it is absent or unreadable."""
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, ValueError):
        return {}


def _detect_source_roots(root: Path) -> list[str]:
    """Guess the Python import root for a project.

    Only the ``src/`` layout needs a root: a package sitting directly under
    the project root is already importable by its own path, which the empty
    default handles. Returning ``["src"]`` makes ``src/pkg/mod.py`` map to
    ``pkg.mod`` rather than to ``src.pkg.mod``, so its imports resolve.

    Args:
        root (Path): Project root.

    Returns:
        list[str]: Import-root prefixes, most specific first.
    """
    if (root / "src").is_dir() and any(root.glob("src/*/__init__.py")):
        return ["src"]
    return []


def load_profile(root: Path | str | None = None, overrides: dict[str, Any] | None = None) -> BrainMapProfile:
    """Build the profile for a project root.

    Resolution order, each layer overriding the previous: built-in defaults →
    detected repo shape → ``brainmap.toml`` / ``[brainmap]`` in
    ``cherenkov.toml`` / ``[tool.cherenkov.brainmap]`` in ``pyproject.toml`` →
    explicit ``overrides``.

    Args:
        root (Path | str | None): Project root; defaults to the cwd.
        overrides (dict[str, Any] | None): Values that win over every file.

    Returns:
        BrainMapProfile: The effective profile.
    """
    root_path = Path(root or Path.cwd()).resolve()
    profile = BrainMapProfile(project=root_path.name, root=root_path)
    profile.source_roots = _detect_source_roots(root_path)
    if (root_path / "cherenkov").is_dir():
        profile.layers = dict(CHERENKOV_LAYERS)

    data: dict[str, Any] = {}
    for filename in CONFIG_FILENAMES:
        candidate = root_path / filename
        if not candidate.exists():
            continue
        raw = _read_toml(candidate)
        if filename == "pyproject.toml":
            section = raw.get("tool", {}).get("cherenkov", {}).get("brainmap", {})
        elif filename == "cherenkov.toml":
            section = raw.get("brainmap", {})
        else:
            section = raw.get("brainmap", raw)
        if isinstance(section, dict) and section:
            data.update(section)

    for key, value in {**data, **(overrides or {})}.items():
        if key == "root":
            continue
        if not hasattr(profile, key):
            continue
        if key == "excludes" and isinstance(value, list):
            # Configured excludes extend the defaults; a project that wants a
            # bare list can pass ``excludes_replace``.
            profile.excludes = list(DEFAULT_EXCLUDES) + [v for v in value if v not in DEFAULT_EXCLUDES]
        else:
            setattr(profile, key, value)

    if isinstance(profile.root, str):
        profile.root = Path(profile.root)
    return profile
