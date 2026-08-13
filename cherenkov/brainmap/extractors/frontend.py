"""Frontend extractor — components, module imports, and cross-stack API calls.

Deliberately regex-based rather than TypeScript-parser-based: the engine must
run from a plain Python install with no Node toolchain present, and a
concept-level map does not need type resolution. The trade is accepted
knowingly — this recognises declarations, not semantics.

The interesting output is not the component list but the ``calls`` edges: every
``/api/...`` literal in the frontend becomes an unresolved edge that the
reconciler joins to the backend ``route`` node serving that path. That join is
what makes the map cross the stack, and what makes "endpoint no UI touches" and
"UI calling an endpoint that no longer exists" both fall out as findings.
"""

from __future__ import annotations

import posixpath
import re

from cherenkov.brainmap.domain.models import (
    EDGE_CALLS,
    EDGE_DEFINES,
    EDGE_IMPORTS,
    KIND_COMPONENT,
    KIND_MODULE,
    Edge,
    ExtractionResult,
    Node,
    make_id,
)
from cherenkov.brainmap.ports import ExtractContext

FRONTEND_SUFFIXES = (".tsx", ".ts", ".jsx", ".js", ".mjs")
DECLARATION_SUFFIXES = (".d.ts",)

_IMPORT = re.compile(r"""(?:import|export)[^'"\n]*?from\s+['"]([^'"]+)['"]""")
_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
_COMPONENT = re.compile(
    r"""export\s+(?:default\s+)?(?:const|function|class)\s+([A-Z][A-Za-z0-9_]*)""",
)
_BASE_CONST = re.compile(
    r"""(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*['"](/[^'"]*)['"]""",
)
_LITERAL_PATH = re.compile(r"""['"`](\$\{([A-Za-z_$][\w$]*)\})?(/[A-Za-z0-9_\-./{}$]*)""")
_TEMPLATE_HOLE = re.compile(r"\$\{[^}]*\}")
_TEMPLATE_LITERAL = re.compile(r"`[^`]*`", re.DOTALL)


class FrontendExtractor:
    """Maps TypeScript/JavaScript files to component and module nodes."""

    name = "frontend"

    def claims(self, rel_path: str) -> bool:
        """Whether ``rel_path`` is a mappable frontend source file."""
        if rel_path.endswith(DECLARATION_SUFFIXES):
            return False
        return rel_path.endswith(FRONTEND_SUFFIXES)

    def extract(self, rel_path: str, text: str, ctx: ExtractContext) -> ExtractionResult:
        """Parse one frontend file into graph fragments.

        Args:
            rel_path (str): Repo-relative path.
            text (str): File contents.
            ctx (ExtractContext): Project context.

        Returns:
            ExtractionResult: A file node, component nodes, relative-import
            edges and unresolved ``calls`` edges for each API path literal.
        """
        result = ExtractionResult()
        stem = _strip_ext(rel_path)
        components = _components(text)
        is_component = bool(components) and rel_path.endswith((".tsx", ".jsx"))
        kind = KIND_COMPONENT if is_component else KIND_MODULE
        file_id = make_id(kind, stem)
        loc = text.count("\n") + 1
        title = components[0] if is_component else posixpath.basename(stem)

        result.nodes.append(
            Node(
                id=file_id,
                kind=kind,
                title=title,
                origin=rel_path,
                summary=_header_comment(text),
                layer=ctx.layer_for(rel_path) or "ui",
                weight=float(loc),
                tags=["frontend"] + (["react"] if is_component else []),
                attrs={"loc": loc, "exports": components, "path": rel_path},
            )
        )

        # Additional exported components in the same file become their own
        # nodes: a barrel file exporting five components is five concepts.
        for name in components[1:]:
            symbol_id = make_id(KIND_COMPONENT, f"{stem}#{name}")
            result.nodes.append(
                Node(
                    id=symbol_id,
                    kind=KIND_COMPONENT,
                    title=name,
                    origin=rel_path,
                    layer=ctx.layer_for(rel_path) or "ui",
                    tags=["frontend", "react"],
                    attrs={"file": rel_path},
                )
            )
            result.edges.append(Edge(src=file_id, kind=EDGE_DEFINES, dst=symbol_id, origin=rel_path))

        # Imports are read with template literals blanked out. A file that
        # embeds a *sample* of generated test code in a backtick string — the
        # dashboard's pipeline mock does exactly this — otherwise contributes
        # that sample's imports as if they were its own, and the reconciler
        # then reports a perfectly healthy file as importing a module that
        # does not exist. API paths below still scan the raw text, because
        # `${API_BASE}/runs` is a real call site, not a quotation.
        import_text = _TEMPLATE_LITERAL.sub(" ", text)

        seen: set[str] = set()
        for match in list(_IMPORT.finditer(import_text)) + list(_REQUIRE.finditer(import_text)):
            spec = match.group(1)
            if not spec.startswith("."):
                continue  # package imports are dependencies, not project edges
            target = posixpath.normpath(posixpath.join(posixpath.dirname(rel_path), spec))
            if target in seen:
                continue
            seen.add(target)
            result.edges.append(
                Edge(src=file_id, kind=EDGE_IMPORTS, target_hint=_strip_ext(target), origin=rel_path)
            )

        for path in _api_paths(text):
            result.edges.append(
                Edge(src=file_id, kind=EDGE_CALLS, target_hint=path, origin=rel_path, attrs={"http_path": path})
            )
        return result


def _strip_ext(path: str) -> str:
    """Drop a frontend extension and any ``/index`` suffix from a path."""
    for suffix in FRONTEND_SUFFIXES:
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    if path.endswith("/index"):
        path = path[: -len("/index")]
    return path


def _components(text: str) -> list[str]:
    """Return exported PascalCase declaration names, in source order."""
    names: list[str] = []
    for match in _COMPONENT.finditer(text):
        name = match.group(1)
        if name not in names:
            names.append(name)
    return names


def _header_comment(text: str) -> str:
    """Return the first meaningful line of a leading block comment."""
    head = text[:600]
    if not head.lstrip().startswith("/*"):
        return ""
    for line in head.splitlines()[1:]:
        cleaned = line.strip().lstrip("*").strip()
        if cleaned and not cleaned.startswith("@") and not cleaned.startswith("*/"):
            return cleaned[:160]
    return ""


def _api_paths(text: str) -> list[str]:
    """Return normalised ``/api/...`` literals referenced by the file.

    Two shapes are recognised: a bare ``'/api/v1/runs'`` literal, and the
    far more common ``` `${API_BASE}/runs` ``` — resolved by first collecting
    the file's own path-valued constants, so a client module that defines
    ``API_BASE = '/api/v1'`` and then interpolates it everywhere still yields
    real, matchable paths. An interpolation whose constant is not defined in
    the same file is skipped rather than guessed at.

    Template holes (``${id}``) are collapsed to ``{}`` so that a call site
    building ``/api/v1/runs/${runId}`` still matches the declared route
    ``/api/v1/runs/{run_id}`` after the reconciler's own normalisation.

    Args:
        text (str): File contents.

    Returns:
        list[str]: Unique API paths, in first-seen order.
    """
    bases = {m.group(1): m.group(2) for m in _BASE_CONST.finditer(text)}
    found: list[str] = []
    for match in _LITERAL_PATH.finditer(text):
        const_name, tail = match.group(2), match.group(3)
        if const_name:
            base = bases.get(const_name)
            if base is None:
                continue
            path = base.rstrip("/") + tail
        else:
            path = tail
        path = _TEMPLATE_HOLE.sub("{}", path).split("?")[0].rstrip("&/")
        if path.startswith("/api") and path not in found:
            found.append(path)
    return found
