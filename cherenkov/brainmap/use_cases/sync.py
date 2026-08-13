"""Build and sync — the engine loop.

One code path serves both commands: a *build* is a sync against an empty store.
Each run walks the project, hashes every in-scope file, and does work only for
files whose digest moved. Deleted files are detected as the set difference
between what the store remembers and what the walk found, so a removed module
takes its nodes and edges with it instead of haunting the map forever.

Reconciliation always runs over the *whole* map, even when one file changed:
resolution is global by nature (a new module can satisfy a link that was
dangling in a file nobody touched), and it is cheap compared with parsing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from cherenkov.brainmap.adapters.sqlite_store import SQLiteBrainMapStore
from cherenkov.brainmap.config import BrainMapProfile, load_profile
from cherenkov.brainmap.domain.models import BrainMap, ExtractionResult, SourceFile, utc_now
from cherenkov.brainmap.extractors.base import build_extractors, read_text, walk_files
from cherenkov.brainmap.ports import ExtractContext
from cherenkov.brainmap.reconcile import ReconcileOptions, Reconciler, diff_maps


@dataclass
class SyncReport:
    """What one sync run did.

    Attributes:
        project: Map namespace.
        scanned: Files walked and hashed.
        parsed: Files whose digest moved and were re-extracted.
        skipped: Files unchanged since the last run.
        removed: Files that vanished from the project.
        duration_ms: Wall-clock time for the run.
        stats: The resulting map's :meth:`BrainMap.stats`.
        delta: What changed versus the previous map, when computed.
    """

    project: str = ""
    scanned: int = 0
    parsed: int = 0
    skipped: int = 0
    removed: int = 0
    duration_ms: int = 0
    stats: dict[str, Any] = field(default_factory=dict)
    delta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the report."""
        return {
            "project": self.project,
            "scanned": self.scanned,
            "parsed": self.parsed,
            "skipped": self.skipped,
            "removed": self.removed,
            "duration_ms": self.duration_ms,
            "stats": self.stats,
            "delta": self.delta,
        }


class BrainMapEngine:
    """Builds, syncs and serves a project's brain map."""

    def __init__(
        self,
        profile: BrainMapProfile | None = None,
        store: SQLiteBrainMapStore | None = None,
        options: ReconcileOptions | None = None,
    ) -> None:
        self.profile = profile or load_profile()
        self.store = store or SQLiteBrainMapStore(self.profile.resolved_db_path())
        self.reconciler = Reconciler(options)

    # ── main entry points ───────────────────────────────────────────────────
    def sync(
        self,
        full: bool = False,
        with_delta: bool = False,
        progress: Callable[[str, int, int], None] | None = None,
    ) -> SyncReport:
        """Bring the stored map in line with what is on disk.

        Args:
            full (bool): Ignore stored digests and re-extract everything.
            with_delta (bool): Compute a before/after delta. Costs one extra
                full load, so it is opt-in.
            progress (Callable[[str, int, int], None] | None): Called as
                ``(path, done, total)`` for each parsed file.

        Returns:
            SyncReport: Counts, timings and the resulting map statistics.
        """
        started = time.monotonic()
        project = self.profile.project
        before = self.store.load(project, resolved=True) if with_delta else None

        if full:
            self.store.drop_project(project)
            known: dict[str, SourceFile] = {}
        else:
            known = self.store.known_files(project)

        extractors = build_extractors(self.profile.extractors)
        found: dict[str, tuple[Path, str, int]] = {}
        report = SyncReport(project=project)

        candidates = list(walk_files(self.profile))
        all_files = [rel for rel, _ in candidates]
        inventory: set[str] = set(all_files)
        for rel in all_files:
            parts = rel.split("/")[:-1]
            for index in range(len(parts)):
                inventory.add("/".join(parts[: index + 1]))
        ctx = ExtractContext(self.profile.root, self.profile, all_files)

        pending: list[tuple[str, Path, str, int]] = []
        for rel, absolute in candidates:
            if not any(extractor.claims(rel) for extractor in extractors):
                continue
            report.scanned += 1
            try:
                raw = absolute.read_bytes()
            except OSError:
                continue
            if len(raw) > self.profile.max_file_bytes:
                continue
            digest = SourceFile.digest(raw)
            found[rel] = (absolute, digest, len(raw))
            previous = known.get(rel)
            if previous is not None and previous.sha256 == digest:
                report.skipped += 1
                continue
            pending.append((rel, absolute, digest, len(raw)))

        total = len(pending)
        for index, (rel, absolute, digest, size) in enumerate(pending, start=1):
            text = read_text(absolute, self.profile.max_file_bytes)
            if text is None:
                continue
            result = ExtractionResult()
            claimed: list[str] = []
            for extractor in extractors:
                if not extractor.claims(rel):
                    continue
                claimed.append(extractor.name)
                result.extend(extractor.extract(rel, text, ctx))
            if self.profile.is_fixture(rel):
                # A corpus file is read, not run: a generated-test fixture
                # importing the client module that only exists after ejection
                # is correct, not broken. Mark its references soft at the
                # source, so the distinction is stored with the evidence
                # rather than re-derived on every reconciliation.
                for edge in result.edges:
                    edge.attrs["soft"] = True
            source = SourceFile(
                path=rel,
                sha256=digest,
                size=size,
                extractor=",".join(claimed),
                scanned_at=utc_now(),
            )
            self.store.replace_file(project, source, result)
            report.parsed += 1
            if progress:
                progress(rel, index, total)

        vanished = [path for path in known if path not in found]
        if vanished:
            self.store.forget_files(project, vanished)
            report.removed = len(vanished)

        map_ = self.reconcile(inventory)
        report.stats = map_.stats()
        report.duration_ms = int((time.monotonic() - started) * 1000)
        if before is not None:
            report.delta = diff_maps(before, map_).to_dict()
        return report

    def reconcile(self, known_paths: set[str] | None = None) -> BrainMap:
        """Reconcile the stored evidence and publish the resolved graph.

        Args:
            known_paths (set[str] | None): Path inventory from the caller's
                walk. Omit and one is taken here — walking is cheap next to
                parsing, and reconciling without it would misreport every
                link to a non-source file as broken.

        Returns:
            BrainMap: The reconciled map, already persisted.
        """
        project = self.profile.project
        map_ = self.store.load(project)
        map_.root = str(self.profile.root)
        map_.built_at = utc_now()
        self.reconciler.reconcile(map_, known_paths if known_paths is not None else self.path_inventory())
        self.store.save_reconciled(project, map_)
        return map_

    def path_inventory(self) -> set[str]:
        """Return every in-scope path, files and their parent directories.

        Directories are included because documentation links to them
        constantly (``see [the ADRs](docs/adr)``), and a link to a directory
        that exists is not a broken link.

        Returns:
            set[str]: Repo-relative paths.
        """
        paths: set[str] = set()
        for rel, _ in walk_files(self.profile):
            paths.add(rel)
            parts = rel.split("/")[:-1]
            for index in range(len(parts)):
                paths.add("/".join(parts[: index + 1]))
        return paths

    def graph(self) -> BrainMap:
        """Return the published, reconciled map without re-scanning anything."""
        return self.store.load(self.profile.project, resolved=True)

    def neighborhood(self, node_id: str, depth: int = 1) -> BrainMap:
        """Return the subgraph around one node."""
        return self.store.neighborhood(self.profile.project, node_id, depth)

    def watch(
        self,
        interval: float = 2.0,
        on_change: Callable[[SyncReport], None] | None = None,
        max_cycles: int | None = None,
    ) -> int:
        """Re-sync whenever the project changes.

        Polling rather than inotify: the engine already computes a digest per
        file, poll intervals of a second or two are entirely adequate for a
        knowledge map, and it behaves identically on Linux, macOS, Windows and
        inside a container with a mounted volume.

        Args:
            interval (float): Seconds between passes.
            on_change (Callable[[SyncReport], None] | None): Called after each
                pass that parsed or removed something.
            max_cycles (int | None): Stop after this many passes; ``None``
                runs until interrupted.

        Returns:
            int: Number of passes that changed the map.
        """
        cycles = 0
        changes = 0
        while max_cycles is None or cycles < max_cycles:
            cycles += 1
            report = self.sync()
            if report.parsed or report.removed:
                changes += 1
                if on_change:
                    on_change(report)
            if max_cycles is not None and cycles >= max_cycles:
                break
            time.sleep(interval)
        return changes


def build_engine(
    root: Path | str | None = None,
    overrides: dict[str, Any] | None = None,
    options: ReconcileOptions | None = None,
) -> BrainMapEngine:
    """Construct an engine for a project root.

    Args:
        root (Path | str | None): Project root; defaults to the cwd.
        overrides (dict[str, Any] | None): Profile overrides.
        options (ReconcileOptions | None): Reconciliation switches.

    Returns:
        BrainMapEngine: A ready engine.
    """
    return BrainMapEngine(profile=load_profile(root, overrides), options=options)
