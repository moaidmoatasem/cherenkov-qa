"""Reconciliation — where a pile of fragments becomes a map you can trust.

Extractors run per file and therefore know only hints: an import string, a
wikilink, a URL literal. Reconciliation is the global pass that joins those
hints to real nodes, and — this is the part that matters — *reports what did
not join* instead of quietly dropping it.

That reporting is the whole reason this subsystem belongs in CHERENKOV rather
than in a generic docs generator. A map that silently omits a broken link is
the same failure mode as a test that silently asserts nothing: it stays green
while reality drifts away from it. So every unresolved hard reference becomes a
:class:`~cherenkov.brainmap.domain.models.Finding`, and the map carries its own
defect list.

Findings emitted here:

===========================  ========  ====================================
code                         severity  meaning
===========================  ========  ====================================
``parse_error``              error     a source file the extractor could not read
``dangling_link``            warn      a doc or import points at nothing
``ui_calls_missing_route``   warn      the frontend calls an endpoint no handler serves
``route_untouched_by_ui``    info      an endpoint no frontend code calls
``untested_module``          info      a code module no test reaches
``undocumented_hub``         info      a heavily-connected module no doc mentions
``orphan_node``              info      a node nothing links to and that links to nothing
===========================  ========  ====================================
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from cherenkov.brainmap.domain.models import (
    EDGE_CALLS,
    EDGE_IMPORTS,
    EDGE_LINKS,
    EDGE_MENTIONS,
    EDGE_TESTS,
    KIND_ADR,
    KIND_CLASS,
    KIND_COMPONENT,
    KIND_DOC,
    KIND_EXTERNAL,
    KIND_FUNCTION,
    KIND_MODULE,
    KIND_PACKAGE,
    KIND_ROUTE,
    KIND_TEST,
    BrainMap,
    Edge,
    Finding,
    MapDelta,
    Node,
    dedupe_edges,
    make_id,
    utc_now,
)

CODE_KINDS = {KIND_MODULE, KIND_PACKAGE, KIND_COMPONENT}
DOC_KINDS = {KIND_DOC, KIND_ADR}
_PATH_PARAM = re.compile(r"\{[^}]*\}")
_FRONTEND_EXT = (".tsx", ".ts", ".jsx", ".js")

# A module with at least this many connections is a hub: if nothing documents
# it, that is worth surfacing. Below it, silence is normal and reporting would
# just be noise. Calibrated against this repo, where 12 flagged a third of all
# modules — a finding that fires on everything is a finding nobody reads.
HUB_DEGREE = 24

# ``sys.stdlib_module_names`` exists from 3.10; the fallback keeps the engine
# working on older interpreters without pretending the list is complete.
_STDLIB: frozenset[str] = getattr(
    sys,
    "stdlib_module_names",
    frozenset({"os", "sys", "re", "json", "typing", "pathlib", "dataclasses", "logging", "__future__"}),
)


@dataclass
class ReconcileOptions:
    """Switches for the reconciliation pass.

    Attributes:
        detect_externals: Create ``external`` nodes for third-party packages
            an internal module imports. Off makes the map purely first-party.
        include_stdlib: Also map standard-library imports. Off by default:
            ``os``, ``re`` and ``json`` appear in almost every module, so
            mapping them adds hub nodes that connect everything to everything
            and tell you nothing about the project.
        report_orphans: Emit ``orphan_node`` findings.
        report_coverage: Emit ``untested_module`` / ``route_untouched_by_ui``.
        hub_degree: Connection count above which a module counts as a hub.
    """

    detect_externals: bool = True
    include_stdlib: bool = False
    report_orphans: bool = True
    report_coverage: bool = True
    hub_degree: int = HUB_DEGREE


class Reconciler:
    """Resolves hinted edges against the node set and grades the result."""

    def __init__(self, options: ReconcileOptions | None = None) -> None:
        self.options = options or ReconcileOptions()

    def reconcile(self, map_: BrainMap, known_paths: set[str] | None = None) -> BrainMap:
        """Resolve every edge in ``map_`` and attach findings, in place.

        Args:
            map_ (BrainMap): A map whose nodes are complete but whose edges
                may still be hints.
            known_paths (set[str] | None): Every path that exists in the
                project, files and directories alike. Supplying it is what
                separates "this link points at something the map does not
                model" — a shell script, an image, a directory — from "this
                link points at nothing", and only the second is a defect.
                Without it every link to a non-source file reads as broken.

        Returns:
            BrainMap: The same object, with edges resolved and deduplicated
            and ``findings`` populated.
        """
        index = _Index(map_, known_paths)
        findings: list[Finding] = []
        kept: list[Edge] = []

        for edge in map_.edges:
            if edge.resolved:
                if edge.dst in map_.nodes:
                    kept.append(edge)
                continue
            resolved = self._resolve(edge, index, map_)
            if resolved is not None:
                edge.dst = resolved
                kept.append(edge)
                continue
            if not edge.attrs.get("soft"):
                finding = _dangling_finding(edge)
                if finding is not None:
                    findings.append(finding)
        map_.edges = dedupe_edges(kept)

        findings.extend(_parse_errors(map_))
        findings.extend(self._coverage_findings(map_))
        findings.extend(self._structure_findings(map_))
        map_.findings = sorted(
            findings,
            key=lambda f: ({"error": 0, "warn": 1, "info": 2}.get(f.severity, 3), f.code, f.node_id or ""),
        )
        map_.built_at = map_.built_at or utc_now()
        return map_

    # ── resolution ──────────────────────────────────────────────────────────
    def _resolve(self, edge: Edge, index: "_Index", map_: BrainMap) -> str | None:
        """Return the node id an edge's hint refers to, or ``None``.

        Resolution is per edge kind because the hints mean different things: a
        Python import is a dotted name, a frontend import is a path, a doc
        link may be either, and an API call is a URL that has to be matched
        against declared route patterns.

        Args:
            edge (Edge): An unresolved edge.
            index (_Index): Lookup tables built from the node set.
            map_ (BrainMap): The map, so external nodes can be added.

        Returns:
            str | None: Resolved node id, or ``None`` when nothing matches.
        """
        hint = edge.target_hint.strip()
        if not hint:
            return None

        if edge.kind == EDGE_CALLS:
            return index.route(hint)

        if edge.kind == EDGE_IMPORTS:
            if _looks_like_path(hint):
                return index.by_path(hint)
            hit = index.by_dotted(hint)
            if hit:
                return hit
            if not index.is_external(hint):
                return None
            root = hint.split(".")[0]
            if root in _STDLIB and not self.options.include_stdlib:
                # A deliberate omission is not a broken link: mark the edge so
                # it is dropped quietly instead of reported as dangling.
                edge.attrs["soft"] = True
                return None
            if self.options.detect_externals:
                return _ensure_external(map_, hint)
            edge.attrs["soft"] = True
            return None

        if edge.kind == EDGE_TESTS:
            return (
                index.by_dotted(hint)
                or index.by_path(hint)
                or (index.by_suffix(hint) if edge.attrs.get("by") == "naming-convention" else None)
            )

        if edge.kind in (EDGE_LINKS, EDGE_MENTIONS):
            hit = index.by_path(hint) or index.by_dotted(hint) or index.by_title(hint)
            if hit is None and index.path_exists(hint):
                edge.attrs["soft"] = True
            return hit

        return index.by_path(hint) or index.by_dotted(hint)

    # ── grading ─────────────────────────────────────────────────────────────
    def _coverage_findings(self, map_: BrainMap) -> list[Finding]:
        """Report code with no test edge and routes with no UI caller."""
        if not self.options.report_coverage:
            return []
        findings: list[Finding] = []
        tested: set[str] = {e.dst for e in map_.edges if e.kind == EDGE_TESTS and e.dst}
        called: set[str] = {e.dst for e in map_.edges if e.kind == EDGE_CALLS and e.dst}

        for node in map_.nodes.values():
            if node.kind == KIND_MODULE and node.origin and node.id not in tested:
                findings.append(
                    Finding(
                        code="untested_module",
                        severity="info",
                        message=f"No test reaches {node.title}",
                        node_id=node.id,
                        origin=node.origin,
                    )
                )
            elif node.kind == KIND_ROUTE and node.id not in called:
                findings.append(
                    Finding(
                        code="route_untouched_by_ui",
                        severity="info",
                        message=f"No frontend code calls {node.title}",
                        node_id=node.id,
                        origin=node.origin,
                        detail={"path": node.attrs.get("path", "")},
                    )
                )
        return findings

    def _structure_findings(self, map_: BrainMap) -> list[Finding]:
        """Report orphans and undocumented hubs."""
        findings: list[Finding] = []
        degree = map_.degree()
        documented: set[str] = {
            e.dst
            for e in map_.edges
            if e.dst
            and e.kind in (EDGE_MENTIONS, EDGE_LINKS)
            and (map_.nodes[e.src].kind in DOC_KINDS if e.src in map_.nodes else False)
        }

        for node in map_.nodes.values():
            if node.kind == KIND_EXTERNAL:
                continue
            connections = degree.get(node.id, 0)
            if self.options.report_orphans and connections == 0:
                findings.append(
                    Finding(
                        code="orphan_node",
                        severity="info",
                        message=f"{node.title} is connected to nothing",
                        node_id=node.id,
                        origin=node.origin,
                    )
                )
            elif (
                node.kind in CODE_KINDS
                and connections >= self.options.hub_degree
                and node.id not in documented
            ):
                findings.append(
                    Finding(
                        code="undocumented_hub",
                        severity="info",
                        message=f"{node.title} has {connections} connections and no documentation",
                        node_id=node.id,
                        origin=node.origin,
                        detail={"degree": connections},
                    )
                )
        return findings


class _Index:
    """Lookup tables over a map's node set, built once per reconciliation."""

    def __init__(self, map_: BrainMap, known_paths: set[str] | None = None) -> None:
        self.map = map_
        self.known_paths = known_paths or set()
        self._fs_cache: dict[str, bool] = {}
        self.by_dotted_name: dict[str, str] = {}
        self.by_path_name: dict[str, str] = {}
        self.by_title_name: dict[str, str] = {}
        self.by_route_path: dict[str, str] = {}
        self.internal_roots: set[str] = set()

        for node in map_.nodes.values():
            # Only Python nodes carry dotted names. A frontend module's title
            # is a basename — ``playwright.config`` — which would otherwise
            # register ``playwright`` as a first-party package and make every
            # real ``playwright`` import look like a broken internal link.
            # (That is not hypothetical: this repo has five such files.)
            if "python" in node.tags:
                if node.kind in (KIND_CLASS, KIND_FUNCTION):
                    owner = node.attrs.get("module", "")
                    if owner:
                        self.by_dotted_name.setdefault(f"{owner}.{node.title}", node.id)
                elif node.kind in (KIND_MODULE, KIND_PACKAGE, KIND_TEST):
                    self.by_dotted_name.setdefault(str(node.title), node.id)
                    if node.kind in (KIND_MODULE, KIND_PACKAGE):
                        self.internal_roots.add(str(node.title).split(".")[0])
            if node.origin:
                self.by_path_name.setdefault(node.origin, node.id)
                self.by_path_name.setdefault(_strip_frontend_ext(node.origin), node.id)
            if node.kind == KIND_ROUTE:
                path = str(node.attrs.get("path", ""))
                if path:
                    self.by_route_path.setdefault(_normalise_route(path), node.id)
            key = str(node.title).strip().lower()
            if key:
                self.by_title_name.setdefault(key, node.id)

    def by_dotted(self, hint: str) -> str | None:
        """Resolve a dotted Python name, walking up to the nearest ancestor.

        ``a.b.c.Thing`` resolves to ``a.b.c`` when the symbol itself is not
        mapped — an import of a class still tells you the module dependency,
        which is the edge the map is actually about.
        """
        parts = hint.split(".")
        while parts:
            hit = self.by_dotted_name.get(".".join(parts))
            if hit:
                return hit
            parts.pop()
        return None

    def by_path(self, hint: str) -> str | None:
        """Resolve a repo-relative path, tolerating a missing extension."""
        hit = self.by_path_name.get(hint) or self.by_path_name.get(_strip_frontend_ext(hint))
        if hit:
            return hit
        for ext in _FRONTEND_EXT:
            hit = self.by_path_name.get(hint + ext)
            if hit:
                return hit
        return self.by_path_name.get(hint.rstrip("/") + "/index")

    def by_title(self, hint: str) -> str | None:
        """Resolve an Obsidian-style wikilink by note title."""
        return self.by_title_name.get(hint.strip().lower())

    def by_suffix(self, hint: str) -> str | None:
        """Resolve a bare name against the last segment of a dotted name."""
        for name, node_id in self.by_dotted_name.items():
            if name.rsplit(".", 1)[-1] == hint:
                return node_id
        return None

    def route(self, path: str) -> str | None:
        """Resolve an API path literal against declared route patterns."""
        normalised = _normalise_route(path)
        hit = self.by_route_path.get(normalised)
        if hit:
            return hit
        # A call site may append segments the route declares as parameters, so
        # fall back to the longest declared prefix that matches.
        best: tuple[int, str] | None = None
        for declared, node_id in self.by_route_path.items():
            if normalised.startswith(declared) and (best is None or len(declared) > best[0]):
                best = (len(declared), node_id)
        return best[1] if best else None

    def path_exists(self, hint: str) -> bool:
        """Whether a hint names something that exists but is not mapped.

        The inventory covers in-scope paths only, so a link into an excluded
        directory would otherwise read as broken — ``docs/_archive`` is not
        scanned, but a link to it still resolves for a reader. Hence the
        filesystem fallback, memoised because the same few targets are linked
        from many documents.

        Args:
            hint (str): The unresolved link target.

        Returns:
            bool: True when something exists at that path.
        """
        candidate = hint.strip().lstrip("/").rstrip("/")
        if not candidate:
            return False
        if candidate in self.known_paths:
            return True
        cached = self._fs_cache.get(candidate)
        if cached is None:
            root = self.map.root
            cached = bool(root) and (Path(root) / candidate).exists()
            self._fs_cache[candidate] = cached
        return cached

    def is_external(self, hint: str) -> bool:
        """Whether a dotted import names a package outside this project."""
        return hint.split(".")[0] not in self.internal_roots


def _ensure_external(map_: BrainMap, hint: str) -> str:
    """Add (once) an ``external`` node for a third-party top-level package."""
    root = hint.split(".")[0]
    node_id = make_id(KIND_EXTERNAL, root)
    if node_id not in map_.nodes:
        map_.add_node(
            Node(
                id=node_id,
                kind=KIND_EXTERNAL,
                title=root,
                summary="third-party dependency",
                layer="external",
                tags=["external"],
            )
        )
    return node_id


def _dangling_finding(edge: Edge) -> Finding | None:
    """Turn an unresolvable hard edge into the right finding, or ``None``."""
    if edge.kind == EDGE_CALLS:
        return Finding(
            code="ui_calls_missing_route",
            severity="warn",
            message=f"Frontend calls {edge.target_hint} but no route declares it",
            node_id=edge.src,
            origin=edge.origin,
            detail={"path": edge.target_hint},
        )
    if edge.kind in (EDGE_LINKS, EDGE_IMPORTS):
        return Finding(
            code="dangling_link",
            severity="warn",
            message=f"{edge.kind} → {edge.target_hint} resolves to nothing",
            node_id=edge.src,
            origin=edge.origin,
            detail={"hint": edge.target_hint, "kind": edge.kind},
        )
    return None


def _parse_errors(map_: BrainMap) -> list[Finding]:
    """Turn extractor parse failures into ``error`` findings."""
    return [
        Finding(
            code="parse_error",
            severity="error",
            message=f"{node.title}: {node.attrs.get('parse_error', 'unparseable')}",
            node_id=node.id,
            origin=node.origin,
            detail=dict(node.attrs),
        )
        for node in map_.nodes.values()
        if "unparseable" in node.tags
    ]


def _normalise_route(path: str) -> str:
    """Collapse path parameters so declared and called paths compare equal."""
    collapsed = _PATH_PARAM.sub("{}", path).rstrip("/")
    return collapsed or "/"


def _strip_frontend_ext(path: str) -> str:
    """Drop a frontend extension and ``/index`` suffix from a path."""
    for ext in _FRONTEND_EXT:
        if path.endswith(ext):
            path = path[: -len(ext)]
            break
    return path[: -len("/index")] if path.endswith("/index") else path


def _looks_like_path(hint: str) -> bool:
    """Whether an import hint is a file path rather than a dotted name."""
    return "/" in hint or hint.startswith(".")


def diff_maps(before: BrainMap, after: BrainMap) -> MapDelta:
    """Compute what changed between two snapshots of the same project.

    Args:
        before (BrainMap): Previous snapshot.
        after (BrainMap): Current snapshot.

    Returns:
        MapDelta: Added/removed nodes and edges plus files whose digest moved.
    """
    before_edges = {f"{e.src}|{e.kind}|{e.dst}" for e in before.edges}
    after_edges = {f"{e.src}|{e.kind}|{e.dst}" for e in after.edges}
    changed_files = [
        path
        for path, source in after.files.items()
        if path not in before.files or before.files[path].sha256 != source.sha256
    ]
    changed_files.extend(path for path in before.files if path not in after.files)
    return MapDelta(
        added_nodes=sorted(set(after.nodes) - set(before.nodes)),
        removed_nodes=sorted(set(before.nodes) - set(after.nodes)),
        changed_files=sorted(set(changed_files)),
        added_edges=sorted(after_edges - before_edges),
        removed_edges=sorted(before_edges - after_edges),
    )
