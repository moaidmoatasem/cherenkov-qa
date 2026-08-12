"""SQLite store — the map on disk, written one file at a time.

The schema is shaped around a single operation: *replace everything derived
from one source file*. Every node and edge row carries its ``origin``, so a
changed file is a `DELETE … WHERE origin = ?` followed by an insert, and an
unchanged file costs one digest comparison and no I/O. That is what makes
``brain sync`` cheap enough to run on every commit of a repo this size.

Nodes are stored per (project, id, origin) rather than per (project, id):
several files legitimately contribute to the same node — a package node named
by its own ``__init__.py`` and by each submodule — and deleting one
contributor must not delete the node. Reads merge the contributions back
together using the same rules as :meth:`BrainMap.add_node`.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from cherenkov.brainmap.domain.models import (
    BrainMap,
    Edge,
    ExtractionResult,
    Finding,
    Node,
    SourceFile,
    dedupe_edges,
    utc_now,
)

_BUSY_TIMEOUT_S = 30.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bm_nodes (
    project TEXT NOT NULL,
    id      TEXT NOT NULL,
    origin  TEXT NOT NULL DEFAULT '',
    kind    TEXT NOT NULL,
    title   TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    layer   TEXT NOT NULL DEFAULT '',
    weight  REAL NOT NULL DEFAULT 1.0,
    tags    TEXT NOT NULL DEFAULT '[]',
    attrs   TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (project, id, origin)
);
CREATE INDEX IF NOT EXISTS idx_bm_nodes_origin ON bm_nodes(project, origin);
CREATE INDEX IF NOT EXISTS idx_bm_nodes_kind ON bm_nodes(project, kind);

CREATE TABLE IF NOT EXISTS bm_edges (
    project     TEXT NOT NULL,
    src         TEXT NOT NULL,
    kind        TEXT NOT NULL,
    dst         TEXT,
    target_hint TEXT NOT NULL DEFAULT '',
    origin      TEXT NOT NULL DEFAULT '',
    weight      REAL NOT NULL DEFAULT 1.0,
    attrs       TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_bm_edges_origin ON bm_edges(project, origin);
CREATE INDEX IF NOT EXISTS idx_bm_edges_src ON bm_edges(project, src);

-- Reconciled projection of bm_edges: only resolved edges, rewritten in bulk
-- after each reconciliation. Reads (UI, exporters, neighbourhood queries) go
-- here; bm_edges stays the raw per-file evidence that incremental sync owns.
CREATE TABLE IF NOT EXISTS bm_links (
    project TEXT NOT NULL,
    src     TEXT NOT NULL,
    kind    TEXT NOT NULL,
    dst     TEXT NOT NULL,
    origin  TEXT NOT NULL DEFAULT '',
    weight  REAL NOT NULL DEFAULT 1.0,
    attrs   TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (project, src, kind, dst)
);
CREATE INDEX IF NOT EXISTS idx_bm_links_src ON bm_links(project, src);
CREATE INDEX IF NOT EXISTS idx_bm_links_dst ON bm_links(project, dst);

CREATE TABLE IF NOT EXISTS bm_files (
    project    TEXT NOT NULL,
    path       TEXT NOT NULL,
    sha256     TEXT NOT NULL,
    size       INTEGER NOT NULL DEFAULT 0,
    extractor  TEXT NOT NULL DEFAULT '',
    scanned_at TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (project, path)
);

CREATE TABLE IF NOT EXISTS bm_findings (
    project  TEXT NOT NULL,
    code     TEXT NOT NULL,
    severity TEXT NOT NULL,
    message  TEXT NOT NULL,
    node_id  TEXT,
    origin   TEXT,
    detail   TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_bm_findings_project ON bm_findings(project);

CREATE TABLE IF NOT EXISTS bm_meta (
    project  TEXT NOT NULL PRIMARY KEY,
    built_at TEXT NOT NULL DEFAULT '',
    root     TEXT NOT NULL DEFAULT ''
);
"""


class SQLiteBrainMapStore:
    """Incremental, thread-safe SQLite persistence for brain maps."""

    def __init__(self, db_path: str | Path = ".brainmap/brainmap.db") -> None:
        self.db_path = str(db_path)
        self._local = threading.local()
        self._init_db()

    # ── connection handling ─────────────────────────────────────────────────
    def _connect(self) -> sqlite3.Connection:
        """Return this thread's connection, reconnecting if it went stale."""
        con = getattr(self._local, "con", None)
        if con is not None:
            try:
                con.execute("SELECT 1")
                return con
            except sqlite3.Error:
                pass
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        con = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        self._local.con = con
        return con

    def _init_db(self) -> None:
        """Create the schema if this is a fresh database."""
        self._connect().executescript(_SCHEMA)

    def close(self) -> None:
        """Close this thread's connection, if any."""
        con = getattr(self._local, "con", None)
        if con is not None:
            con.close()
            self._local.con = None

    # ── writes ──────────────────────────────────────────────────────────────
    def replace_file(self, project: str, source: SourceFile, result: ExtractionResult) -> None:
        """Replace everything derived from one file, atomically.

        Args:
            project (str): Map namespace.
            source (SourceFile): Scan record for the file.
            result (ExtractionResult): Everything the extractors produced
                for it.
        """
        con = self._connect()
        with con:
            con.execute("DELETE FROM bm_nodes WHERE project = ? AND origin = ?", (project, source.path))
            con.execute("DELETE FROM bm_edges WHERE project = ? AND origin = ?", (project, source.path))
            con.executemany(
                "INSERT OR REPLACE INTO bm_nodes"
                " (project, id, origin, kind, title, summary, layer, weight, tags, attrs)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        project,
                        n.id,
                        n.origin or source.path,
                        n.kind,
                        n.title,
                        n.summary,
                        n.layer,
                        n.weight,
                        json.dumps(n.tags),
                        json.dumps(n.attrs),
                    )
                    for n in result.nodes
                ],
            )
            con.executemany(
                "INSERT INTO bm_edges (project, src, kind, dst, target_hint, origin, weight, attrs)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        project,
                        e.src,
                        e.kind,
                        e.dst,
                        e.target_hint,
                        e.origin or source.path,
                        e.weight,
                        json.dumps(e.attrs),
                    )
                    for e in result.edges
                ],
            )
            con.execute(
                "INSERT OR REPLACE INTO bm_files (project, path, sha256, size, extractor, scanned_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    project,
                    source.path,
                    source.sha256,
                    source.size,
                    source.extractor,
                    source.scanned_at or utc_now(),
                ),
            )

    def forget_files(self, project: str, paths: list[str]) -> None:
        """Drop every trace of the given files (they were deleted or excluded)."""
        if not paths:
            return
        con = self._connect()
        with con:
            for chunk_start in range(0, len(paths), 500):
                chunk = paths[chunk_start : chunk_start + 500]
                marks = ",".join("?" * len(chunk))
                args = [project, *chunk]
                con.execute(f"DELETE FROM bm_nodes WHERE project = ? AND origin IN ({marks})", args)
                con.execute(f"DELETE FROM bm_edges WHERE project = ? AND origin IN ({marks})", args)
                con.execute(f"DELETE FROM bm_files WHERE project = ? AND path IN ({marks})", args)

    def save_reconciled(self, project: str, map_: BrainMap) -> None:
        """Persist a reconciled map: links, synthetic nodes, findings, stamp.

        Only this method writes ``bm_links``. Extraction writes evidence
        (``bm_edges``); reconciliation publishes the resolved graph that every
        reader then queries, so a reader never has to redo edge resolution and
        a half-finished sync can never publish a partial graph.

        Args:
            project (str): Map namespace.
            map_ (BrainMap): A reconciled map.
        """
        con = self._connect()
        with con:
            con.execute("DELETE FROM bm_links WHERE project = ?", (project,))
            con.executemany(
                "INSERT OR REPLACE INTO bm_links (project, src, kind, dst, origin, weight, attrs)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (project, e.src, e.kind, e.dst, e.origin or "", e.weight, json.dumps(e.attrs))
                    for e in map_.edges
                    if e.dst
                ],
            )
            # Nodes the reconciler synthesised (external packages) own no file,
            # so incremental extraction never writes them — and never cleans
            # them up either, hence the delete before the insert.
            con.execute("DELETE FROM bm_nodes WHERE project = ? AND origin = ''", (project,))
            con.executemany(
                "INSERT OR REPLACE INTO bm_nodes"
                " (project, id, origin, kind, title, summary, layer, weight, tags, attrs)"
                " VALUES (?, ?, '', ?, ?, ?, ?, ?, ?, ?)",
                [
                    (project, n.id, n.kind, n.title, n.summary, n.layer, n.weight, json.dumps(n.tags), json.dumps(n.attrs))
                    for n in map_.nodes.values()
                    if not n.origin
                ],
            )
            con.execute("DELETE FROM bm_findings WHERE project = ?", (project,))
            con.executemany(
                "INSERT INTO bm_findings (project, code, severity, message, node_id, origin, detail)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (project, f.code, f.severity, f.message, f.node_id, f.origin, json.dumps(f.detail))
                    for f in map_.findings
                ],
            )
            con.execute(
                "INSERT OR REPLACE INTO bm_meta (project, built_at, root) VALUES (?, ?, ?)",
                (project, map_.built_at or utc_now(), map_.root),
            )

    def drop_project(self, project: str) -> None:
        """Delete an entire project's map."""
        con = self._connect()
        with con:
            for table in ("bm_nodes", "bm_edges", "bm_links", "bm_files", "bm_findings", "bm_meta"):
                con.execute(f"DELETE FROM {table} WHERE project = ?", (project,))

    # ── reads ───────────────────────────────────────────────────────────────
    def known_files(self, project: str) -> dict[str, SourceFile]:
        """Return the scan records from the previous sync, keyed by path."""
        rows = self._connect().execute(
            "SELECT path, sha256, size, extractor, scanned_at FROM bm_files WHERE project = ?",
            (project,),
        )
        return {
            row["path"]: SourceFile(
                path=row["path"],
                sha256=row["sha256"],
                size=row["size"],
                extractor=row["extractor"],
                scanned_at=row["scanned_at"],
            )
            for row in rows
        }

    def projects(self) -> list[str]:
        """Return every project that has a stored map."""
        rows = self._connect().execute("SELECT DISTINCT project FROM bm_files ORDER BY project")
        return [row["project"] for row in rows]

    def load(self, project: str, resolved: bool = False) -> BrainMap:
        """Load the stored map for a project.

        Args:
            project (str): Map namespace.
            resolved (bool): ``False`` (default) loads the raw per-file
                evidence, which is what a rebuild reconciles. ``True`` loads
                the published, already-resolved graph, which is what readers
                want.

        Returns:
            BrainMap: The stored map.
        """
        con = self._connect()
        map_ = BrainMap(project=project)
        for row in con.execute(
            "SELECT id, origin, kind, title, summary, layer, weight, tags, attrs"
            " FROM bm_nodes WHERE project = ? ORDER BY id, origin",
            (project,),
        ):
            map_.add_node(_row_to_node(row))
        if resolved:
            map_.edges = [
                Edge(
                    src=row["src"],
                    kind=row["kind"],
                    dst=row["dst"],
                    origin=row["origin"] or None,
                    weight=row["weight"],
                    attrs=json.loads(row["attrs"]),
                )
                for row in con.execute(
                    "SELECT src, kind, dst, origin, weight, attrs"
                    " FROM bm_links WHERE project = ? ORDER BY src, kind, dst",
                    (project,),
                )
            ]
        else:
            map_.edges = dedupe_edges(
                _row_to_edge(row)
                for row in con.execute(
                    "SELECT src, kind, dst, target_hint, origin, weight, attrs"
                    " FROM bm_edges WHERE project = ? ORDER BY src, kind, dst",
                    (project,),
                )
            )
        map_.files = self.known_files(project)
        map_.findings = [
            Finding(
                code=row["code"],
                severity=row["severity"],
                message=row["message"],
                node_id=row["node_id"],
                origin=row["origin"],
                detail=json.loads(row["detail"]),
            )
            for row in con.execute(
                "SELECT code, severity, message, node_id, origin, detail FROM bm_findings WHERE project = ?",
                (project,),
            )
        ]
        meta = con.execute("SELECT built_at, root FROM bm_meta WHERE project = ?", (project,)).fetchone()
        if meta:
            map_.built_at = meta["built_at"]
            map_.root = meta["root"]
        return map_

    def neighborhood(self, project: str, node_id: str, depth: int = 1) -> BrainMap:
        """Return the subgraph within ``depth`` hops of a node.

        Expansion is done in SQL, one hop per round trip, so the cost tracks
        the size of the neighbourhood rather than the size of the map. This is
        the query the UI uses to stay responsive on a graph with tens of
        thousands of nodes.

        Args:
            project (str): Map namespace.
            node_id (str): Centre of the neighbourhood.
            depth (int): Hops to expand, clamped to 1–5.

        Returns:
            BrainMap: A map containing only the reachable nodes and the edges
            among them.
        """
        con = self._connect()
        depth = max(1, min(int(depth), 5))
        frontier = {node_id}
        seen = set(frontier)
        for _ in range(depth):
            if not frontier:
                break
            marks = ",".join("?" * len(frontier))
            args = [project, *frontier, *frontier]
            rows = con.execute(
                f"SELECT src, dst FROM bm_links WHERE project = ?"
                f" AND (src IN ({marks}) OR dst IN ({marks}))",
                args,
            )
            nxt: set[str] = set()
            for row in rows:
                for candidate in (row["src"], row["dst"]):
                    if candidate and candidate not in seen:
                        seen.add(candidate)
                        nxt.add(candidate)
            frontier = nxt

        map_ = BrainMap(project=project)
        if not seen:
            return map_
        for chunk in _chunks(sorted(seen), 400):
            marks = ",".join("?" * len(chunk))
            for row in con.execute(
                f"SELECT id, origin, kind, title, summary, layer, weight, tags, attrs"
                f" FROM bm_nodes WHERE project = ? AND id IN ({marks})",
                [project, *chunk],
            ):
                map_.add_node(_row_to_node(row))
        edges: list[Edge] = []
        for chunk in _chunks(sorted(seen), 400):
            marks = ",".join("?" * len(chunk))
            for row in con.execute(
                f"SELECT src, kind, dst, origin, weight, attrs"
                f" FROM bm_links WHERE project = ? AND src IN ({marks})",
                [project, *chunk],
            ):
                if row["dst"] in map_.nodes:
                    edges.append(
                        Edge(
                            src=row["src"],
                            kind=row["kind"],
                            dst=row["dst"],
                            origin=row["origin"] or None,
                            weight=row["weight"],
                            attrs=json.loads(row["attrs"]),
                        )
                    )
        map_.edges = dedupe_edges(edges)
        return map_


def _row_to_node(row: sqlite3.Row) -> Node:
    """Rehydrate a node from a database row."""
    return Node(
        id=row["id"],
        kind=row["kind"],
        title=row["title"],
        origin=row["origin"] or None,
        summary=row["summary"],
        layer=row["layer"],
        weight=row["weight"],
        tags=json.loads(row["tags"]),
        attrs=json.loads(row["attrs"]),
    )


def _row_to_edge(row: sqlite3.Row) -> Edge:
    """Rehydrate an edge from a database row."""
    return Edge(
        src=row["src"],
        kind=row["kind"],
        dst=row["dst"],
        target_hint=row["target_hint"],
        origin=row["origin"] or None,
        weight=row["weight"],
        attrs=json.loads(row["attrs"]),
    )


def _chunks(items: list[str], size: int):
    """Yield fixed-size slices, keeping SQL parameter counts under the limit."""
    for start in range(0, len(items), size):
        yield items[start : start + size]
