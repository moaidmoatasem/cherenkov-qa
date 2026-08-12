"""Brain-map domain model — the vocabulary every extractor and adapter speaks.

The model is deliberately small and project-agnostic: a brain map is a set of
:class:`Node` records and a set of :class:`Edge` records, each stamped with the
source file it was derived from. That single field (``origin``) is what makes
the whole system incremental — when a file changes, everything it produced is
dropped and re-derived, and nothing else is touched.

Node and edge *kinds* are plain strings rather than closed enums. The constants
below are the ones CHERENKOV's own extractors emit; another project plugging in
its own extractor is free to invent ``kind="terraform_module"`` without
patching this file.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

# ── Node kinds emitted by the built-in extractors ───────────────────────────
KIND_MODULE = "module"
KIND_PACKAGE = "package"
KIND_CLASS = "class"
KIND_FUNCTION = "function"
KIND_COMPONENT = "component"
KIND_ROUTE = "route"
KIND_CLI_COMMAND = "cli_command"
KIND_DOC = "doc"
KIND_ADR = "adr"
KIND_TEST = "test"
KIND_CONCEPT = "concept"
KIND_EXTERNAL = "external"

# ── Edge kinds ──────────────────────────────────────────────────────────────
EDGE_IMPORTS = "imports"
EDGE_CONTAINS = "contains"
EDGE_DEFINES = "defines"
EDGE_LINKS = "links"
EDGE_MENTIONS = "mentions"
EDGE_TESTS = "tests"
EDGE_HANDLED_BY = "handled_by"
EDGE_DOCUMENTS = "documents"
EDGE_CALLS = "calls"

_SLUG_UNSAFE = re.compile(r"[^A-Za-z0-9._:/{}-]+")


def make_id(kind: str, slug: str) -> str:
    """Build a stable node id of the form ``kind:slug``.

    Ids must survive a rebuild on another machine, another checkout path and
    another OS, so the slug is always a *logical* name (dotted module path,
    repo-relative file path, ``METHOD /path`` for a route) — never an absolute
    path and never anything derived from mtime or ordering.

    Args:
        kind (str): Node kind, e.g. ``"module"``.
        slug (str): Logical, checkout-independent identity within that kind.

    Returns:
        str: The canonical node id.
    """
    cleaned = _SLUG_UNSAFE.sub("-", slug.strip()).strip("-")
    return f"{kind}:{cleaned}"


@dataclass
class Node:
    """A single concept in the map.

    Attributes:
        id: Canonical ``kind:slug`` identity — see :func:`make_id`.
        kind: What sort of thing this is (module, route, doc, …).
        title: Human-facing label, shown in the UI and used as the Obsidian
            note name.
        origin: Repo-relative path of the file this node was derived from.
            ``None`` for synthetic nodes (e.g. inferred packages) that no
            single file owns.
        summary: One-line description, usually the first docstring line.
        tags: Free-form labels; exported as Obsidian tags.
        attrs: Extractor-specific payload (line numbers, HTTP method, …).
        layer: Optional architectural layer used for grouping/colouring.
        weight: Relative importance hint (LOC, fan-in) used for node sizing.
    """

    id: str
    kind: str
    title: str
    origin: str | None = None
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    attrs: dict[str, Any] = field(default_factory=dict)
    layer: str = ""
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of this node."""
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "origin": self.origin,
            "summary": self.summary,
            "tags": list(self.tags),
            "attrs": dict(self.attrs),
            "layer": self.layer,
            "weight": self.weight,
        }


@dataclass
class Edge:
    """A directed relationship between two nodes.

    Edges may be emitted *unresolved*: an extractor reading one file often
    knows the target only by hint (an import string, a wikilink title) and
    cannot know whether that target exists until every other file has been
    read. Those edges carry ``target_hint`` with ``dst=None`` and are resolved
    — or reported as dangling — by the reconciler.

    Attributes:
        src: Source node id.
        kind: Relationship kind (imports, documents, tests, …).
        dst: Target node id once resolved.
        target_hint: What the extractor saw, when ``dst`` is not yet known.
        origin: Repo-relative path of the file this edge came from.
        weight: Multiplicity (e.g. how many times a doc mentions a module).
        attrs: Extractor-specific payload.
    """

    src: str
    kind: str
    dst: str | None = None
    target_hint: str = ""
    origin: str | None = None
    weight: float = 1.0
    attrs: dict[str, Any] = field(default_factory=dict)

    @property
    def resolved(self) -> bool:
        """Whether this edge points at a known node."""
        return self.dst is not None

    def key(self) -> tuple[str, str, str]:
        """Deduplication key: same source, kind and target is the same edge."""
        return (self.src, self.kind, self.dst or f"?{self.target_hint}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of this edge."""
        return {
            "src": self.src,
            "kind": self.kind,
            "dst": self.dst,
            "target_hint": self.target_hint,
            "origin": self.origin,
            "weight": self.weight,
            "attrs": dict(self.attrs),
        }


@dataclass
class SourceFile:
    """A file that was scanned, with the digest that makes sync incremental.

    Attributes:
        path: Repo-relative path.
        sha256: Content digest at scan time.
        size: Byte size at scan time.
        extractor: Name of the extractor that claimed the file.
        scanned_at: UTC ISO-8601 timestamp of the scan.
    """

    path: str
    sha256: str
    size: int = 0
    extractor: str = ""
    scanned_at: str = ""

    @staticmethod
    def digest(data: bytes) -> str:
        """Return the sha256 hex digest used for change detection."""
        return hashlib.sha256(data).hexdigest()


@dataclass
class ExtractionResult:
    """What a single extractor produced for a single file."""

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def extend(self, other: "ExtractionResult") -> None:
        """Merge another result into this one, in place."""
        self.nodes.extend(other.nodes)
        self.edges.extend(other.edges)


@dataclass
class Finding:
    """One reconciliation problem, in the shape the UI and CLI both render.

    Attributes:
        code: Machine-readable class, e.g. ``dangling_link``.
        severity: ``info`` | ``warn`` | ``error``.
        message: Human-readable one-liner.
        node_id: Node the finding is anchored to, when there is one.
        origin: Repo-relative file to look at.
        detail: Structured payload for programmatic consumers.
    """

    code: str
    severity: str
    message: str
    node_id: str | None = None
    origin: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of this finding."""
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "node_id": self.node_id,
            "origin": self.origin,
            "detail": dict(self.detail),
        }


@dataclass
class BrainMap:
    """A whole map: nodes, edges, the files they came from, and findings.

    Attributes:
        project: Project name — the map's namespace.
        nodes: Node id → node.
        edges: Deduplicated edge list.
        files: Repo-relative path → scan record.
        findings: Reconciliation output (empty until reconciled).
        built_at: UTC ISO-8601 timestamp of the last full or partial build.
        root: Absolute path the map was built from, for display only.
    """

    project: str = "project"
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    files: dict[str, SourceFile] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    built_at: str = ""
    root: str = ""

    def add_node(self, node: Node) -> Node:
        """Insert a node, merging into any existing node with the same id.

        Two extractors legitimately describe the same thing from different
        angles — the Python extractor knows a module's docstring, the test
        extractor knows it is covered. Neither should clobber the other, so
        merging fills blanks and unions tags rather than replacing.

        Args:
            node (Node): The node to insert or merge.

        Returns:
            Node: The node now stored under that id.
        """
        existing = self.nodes.get(node.id)
        if existing is None:
            self.nodes[node.id] = node
            return node
        if not existing.summary and node.summary:
            existing.summary = node.summary
        if not existing.origin and node.origin:
            existing.origin = node.origin
        if not existing.layer and node.layer:
            existing.layer = node.layer
        existing.weight = max(existing.weight, node.weight)
        for tag in node.tags:
            if tag not in existing.tags:
                existing.tags.append(tag)
        for key, value in node.attrs.items():
            existing.attrs.setdefault(key, value)
        return existing

    def add_edge(self, edge: Edge) -> None:
        """Append an edge (deduplication happens during reconciliation)."""
        self.edges.append(edge)

    def ingest(self, result: ExtractionResult) -> None:
        """Merge a raw extraction result into the map."""
        for node in result.nodes:
            self.add_node(node)
        for edge in result.edges:
            self.add_edge(edge)

    def degree(self) -> dict[str, int]:
        """Return node id → number of resolved edges touching it."""
        counts: dict[str, int] = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            if edge.src in counts:
                counts[edge.src] += 1
            if edge.dst and edge.dst in counts:
                counts[edge.dst] += 1
        return counts

    def stats(self) -> dict[str, Any]:
        """Return counts by node kind, edge kind and finding severity."""
        by_kind: dict[str, int] = {}
        for node in self.nodes.values():
            by_kind[node.kind] = by_kind.get(node.kind, 0) + 1
        by_edge: dict[str, int] = {}
        for edge in self.edges:
            by_edge[edge.kind] = by_edge.get(edge.kind, 0) + 1
        by_severity: dict[str, int] = {}
        for finding in self.findings:
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
        return {
            "project": self.project,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "files": len(self.files),
            "findings": len(self.findings),
            "by_kind": dict(sorted(by_kind.items())),
            "by_edge_kind": dict(sorted(by_edge.items())),
            "by_severity": by_severity,
            "built_at": self.built_at,
            "root": self.root,
        }

    def to_dict(self) -> dict[str, Any]:
        """Return the whole map as JSON-serialisable data."""
        return {
            "project": self.project,
            "built_at": self.built_at,
            "root": self.root,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "files": [
                {
                    "path": f.path,
                    "sha256": f.sha256,
                    "size": f.size,
                    "extractor": f.extractor,
                    "scanned_at": f.scanned_at,
                }
                for f in self.files.values()
            ],
            "findings": [f.to_dict() for f in self.findings],
            "stats": self.stats(),
        }


@dataclass
class MapDelta:
    """What changed between two snapshots of the same project.

    Attributes:
        added_nodes: Node ids present now and absent before.
        removed_nodes: Node ids present before and absent now.
        changed_files: Files whose digest moved.
        added_edges: Edge keys that appeared.
        removed_edges: Edge keys that vanished.
    """

    added_nodes: list[str] = field(default_factory=list)
    removed_nodes: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    added_edges: list[str] = field(default_factory=list)
    removed_edges: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        """Whether nothing at all changed."""
        return not (
            self.added_nodes
            or self.removed_nodes
            or self.changed_files
            or self.added_edges
            or self.removed_edges
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of this delta."""
        return {
            "added_nodes": self.added_nodes,
            "removed_nodes": self.removed_nodes,
            "changed_files": self.changed_files,
            "added_edges": self.added_edges,
            "removed_edges": self.removed_edges,
            "empty": self.empty,
        }


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string with a ``Z`` suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def dedupe_edges(edges: Iterable[Edge]) -> list[Edge]:
    """Collapse duplicate edges, summing their weights.

    Args:
        edges (Iterable[Edge]): Edges in extraction order.

    Returns:
        list[Edge]: One edge per ``(src, kind, dst)`` triple, weights summed,
        in first-seen order so output stays deterministic.
    """
    merged: dict[tuple[str, str, str], Edge] = {}
    for edge in edges:
        key = edge.key()
        seen = merged.get(key)
        if seen is None:
            merged[key] = edge
        else:
            seen.weight += edge.weight
    return list(merged.values())
