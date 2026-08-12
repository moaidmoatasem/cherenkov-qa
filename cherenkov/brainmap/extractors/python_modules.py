"""Python extractor — modules, packages, classes and the import graph.

Parsing is AST-only: nothing is imported, so mapping a repo never runs its
code, never needs its dependencies installed, and cannot be defeated by an
import-time side effect. A file that does not parse is reported as a finding
rather than silently dropped.
"""

from __future__ import annotations

import ast

from cherenkov.brainmap.domain.models import (
    EDGE_CONTAINS,
    EDGE_DEFINES,
    EDGE_IMPORTS,
    KIND_CLASS,
    KIND_FUNCTION,
    KIND_MODULE,
    KIND_PACKAGE,
    KIND_TEST,
    Edge,
    ExtractionResult,
    Node,
    make_id,
)
from cherenkov.brainmap.extractors.base import first_line
from cherenkov.brainmap.ports import ExtractContext


def is_test_path(rel_path: str, test_roots: list[str]) -> bool:
    """Whether a Python file is a test module.

    Both conventions count: living under a configured test root, and the
    ``test_*.py`` / ``*_test.py`` filename convention anywhere in the tree —
    plenty of projects keep tests beside the code they exercise.

    Args:
        rel_path (str): Repo-relative path.
        test_roots (list[str]): Directory prefixes holding tests.

    Returns:
        bool: True when the file should be mapped as a test.
    """
    name = rel_path.rsplit("/", 1)[-1]
    if name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py":
        return True
    return any(rel_path == root or rel_path.startswith(root.rstrip("/") + "/") for root in test_roots)


class PythonExtractor:
    """Maps ``.py`` files to module/class nodes and import edges."""

    name = "python"

    def claims(self, rel_path: str) -> bool:
        """Whether ``rel_path`` is a Python source file."""
        return rel_path.endswith(".py")

    def extract(self, rel_path: str, text: str, ctx: ExtractContext) -> ExtractionResult:
        """Parse one Python file into graph fragments.

        Args:
            rel_path (str): Repo-relative path.
            text (str): File contents.
            ctx (ExtractContext): Project context.

        Returns:
            ExtractionResult: A module node, its package chain, optional
            symbol nodes, and one edge per import.
        """
        result = ExtractionResult()
        profile = ctx.profile
        module_name = profile.module_name(rel_path)
        if not module_name:
            return result

        try:
            tree = ast.parse(text, filename=rel_path)
        except SyntaxError as exc:
            result.nodes.append(
                Node(
                    id=make_id(KIND_MODULE, module_name),
                    kind=KIND_MODULE,
                    title=module_name,
                    origin=rel_path,
                    summary=f"unparseable: {exc.msg} (line {exc.lineno})",
                    layer=ctx.layer_for(rel_path),
                    tags=["unparseable"],
                    attrs={"parse_error": exc.msg, "line": exc.lineno},
                )
            )
            return result

        is_package = rel_path.endswith("__init__.py")
        # A test module is mapped as a test, not as a module: one node per
        # file, coloured by what it actually is. The tests extractor then only
        # has to add edges, never a second node for the same file.
        if is_package:
            kind = KIND_PACKAGE
        elif is_test_path(rel_path, profile.test_roots):
            kind = KIND_TEST
        else:
            kind = KIND_MODULE
        loc = text.count("\n") + 1
        module_id = make_id(kind, module_name)
        result.nodes.append(
            Node(
                id=module_id,
                kind=kind,
                title=module_name,
                origin=rel_path,
                summary=first_line(ast.get_docstring(tree)),
                layer=ctx.layer_for(rel_path),
                weight=float(loc),
                tags=["python"],
                attrs={"loc": loc, "package": is_package},
            )
        )

        # Parent package containment — synthesises the package node when the
        # package has no ``__init__.py`` of its own (namespace packages).
        if "." in module_name:
            parent = module_name.rsplit(".", 1)[0]
            parent_id = make_id(KIND_PACKAGE, parent)
            result.nodes.append(
                Node(id=parent_id, kind=KIND_PACKAGE, title=parent, tags=["python"], layer=ctx.layer_for(rel_path))
            )
            result.edges.append(Edge(src=parent_id, kind=EDGE_CONTAINS, dst=module_id, origin=rel_path))

        for hint in _imports(tree, module_name, is_package):
            result.edges.append(
                Edge(src=module_id, kind=EDGE_IMPORTS, target_hint=hint, origin=rel_path)
            )

        depth = getattr(profile, "symbol_depth", "class")
        if depth in ("class", "function"):
            result.extend(_symbols(tree, module_id, module_name, rel_path, ctx, depth))
        return result


def _imports(tree: ast.Module, module_name: str, is_package: bool) -> list[str]:
    """Return the dotted targets imported by a module.

    Relative imports are rebased onto the importing module's package so that
    ``from .. import x`` inside ``a.b.c`` resolves to ``a`` — without this the
    intra-package edges of any hexagonal codebase are all dangling.

    Args:
        tree (ast.Module): Parsed module.
        module_name (str): Dotted name of the importing module.
        is_package (bool): Whether the importer is a package ``__init__``.

    Returns:
        list[str]: Absolute dotted import targets, in source order.
    """
    package = module_name if is_package else module_name.rpartition(".")[0]
    hints: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hints.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".") if package else []
                trimmed = parts[: len(parts) - (node.level - 1)] if node.level > 1 else parts
                base = ".".join([p for p in trimmed if p] + ([base] if base else []))
            if not base:
                continue
            hints.append(base)
            # ``from pkg import submodule`` is an edge to the submodule too;
            # the reconciler discards whichever of the two does not exist.
            for alias in node.names:
                if alias.name != "*":
                    hints.append(f"{base}.{alias.name}")
    return hints


def _symbols(
    tree: ast.Module,
    module_id: str,
    module_name: str,
    rel_path: str,
    ctx: ExtractContext,
    depth: str,
) -> ExtractionResult:
    """Emit nodes for top-level classes (and functions at ``function`` depth).

    Only module-level definitions are mapped. Nested and private symbols are
    implementation detail: including them multiplies node count without adding
    a concept anyone navigates by.

    Args:
        tree (ast.Module): Parsed module.
        module_id (str): Id of the owning module node.
        module_name (str): Dotted module name.
        rel_path (str): Repo-relative path.
        ctx (ExtractContext): Project context.
        depth (str): ``"class"`` or ``"function"``.

    Returns:
        ExtractionResult: Symbol nodes plus their ``defines`` edges.
    """
    result = ExtractionResult()
    layer = ctx.layer_for(rel_path)
    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            kind, name = KIND_CLASS, stmt.name
        elif depth == "function" and isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind, name = KIND_FUNCTION, stmt.name
        else:
            continue
        if name.startswith("_"):
            continue
        symbol_id = make_id(kind, f"{module_name}.{name}")
        result.nodes.append(
            Node(
                id=symbol_id,
                kind=kind,
                title=name,
                origin=rel_path,
                summary=first_line(ast.get_docstring(stmt)),
                layer=layer,
                tags=["python"],
                attrs={"module": module_name, "line": stmt.lineno},
            )
        )
        result.edges.append(Edge(src=module_id, kind=EDGE_DEFINES, dst=symbol_id, origin=rel_path))
    return result
