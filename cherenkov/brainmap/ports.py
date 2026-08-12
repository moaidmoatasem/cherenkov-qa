"""Ports for the brain-map engine.

Three seams keep the engine reusable outside CHERENKOV:

* :class:`Extractor` — turns one file into nodes and edges. Add one and the
  engine maps a new kind of artefact with no other change.
* :class:`BrainMapStore` — persists a map and answers subgraph queries. The
  bundled implementation is SQLite; a service could back it with Postgres.
* :class:`Exporter` — renders a reconciled map into some external form. The
  bundled implementation writes an Obsidian vault.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from cherenkov.brainmap.domain.models import BrainMap, ExtractionResult, SourceFile


@runtime_checkable
class Extractor(Protocol):
    """Turns a single source file into graph fragments.

    Implementations must be pure with respect to the file they are given: the
    same bytes must always produce the same nodes and edges, because the sync
    engine skips files whose digest has not moved and would otherwise serve
    stale output forever.
    """

    name: str

    def claims(self, rel_path: str) -> bool:
        """Whether this extractor wants to parse ``rel_path``.

        Args:
            rel_path (str): Repo-relative, forward-slash path.

        Returns:
            bool: True when the file belongs to this extractor.
        """

    def extract(self, rel_path: str, text: str, ctx: "ExtractContext") -> ExtractionResult:
        """Parse one file into nodes and edges.

        Args:
            rel_path (str): Repo-relative, forward-slash path.
            text (str): Decoded file contents.
            ctx (ExtractContext): Project-wide context (root, profile, helpers).

        Returns:
            ExtractionResult: Nodes and edges derived from this file only.
        """


@runtime_checkable
class BrainMapStore(Protocol):
    """Persistence for maps, with incremental writes and subgraph reads."""

    def load(self, project: str) -> BrainMap:
        """Load the whole stored map for a project (empty map if unknown)."""

    def replace_file(self, project: str, source: SourceFile, result: ExtractionResult) -> None:
        """Drop everything derived from ``source.path`` and store ``result``."""

    def forget_files(self, project: str, paths: list[str]) -> None:
        """Drop every node, edge and scan record owned by these paths."""

    def known_files(self, project: str) -> dict[str, SourceFile]:
        """Return the scan records from the last sync, keyed by path."""

    def save_findings(self, project: str, map_: BrainMap) -> None:
        """Persist reconciliation output and the map's build timestamp."""

    def neighborhood(self, project: str, node_id: str, depth: int) -> BrainMap:
        """Return the subgraph within ``depth`` hops of ``node_id``."""


@runtime_checkable
class Exporter(Protocol):
    """Renders a reconciled map into an external representation."""

    name: str

    def export(self, map_: BrainMap, target: Path) -> dict[str, Any]:
        """Write the map to ``target``.

        Args:
            map_ (BrainMap): A reconciled map.
            target (Path): Destination directory or file.

        Returns:
            dict[str, Any]: Summary counts for the CLI/API to report.
        """


class ExtractContext:
    """Everything an extractor may need beyond the file it was handed.

    Attributes:
        root: Absolute project root.
        profile: The active :class:`~cherenkov.brainmap.config.BrainMapProfile`.
        all_files: Every repo-relative path in scope for this build, so an
            extractor can resolve a relative link without touching the disk.
    """

    def __init__(self, root: Path, profile: Any, all_files: list[str] | None = None) -> None:
        self.root = root
        self.profile = profile
        self.all_files = all_files or []

    def layer_for(self, rel_path: str) -> str:
        """Return the architectural layer configured for ``rel_path``."""
        return self.profile.layer_for(rel_path)
