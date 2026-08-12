"""HTTP route extractor — the API surface, read from decorators.

Recognises the FastAPI/Flask/Starlette decorator shape ``@<obj>.<verb>(path)``
on a module-level function. Routes are first-class nodes because "which module
serves this endpoint" is the question a QA tool's map most often has to answer,
and because an endpoint with no test edge is exactly the gap worth surfacing.
"""

from __future__ import annotations

import ast

from cherenkov.brainmap.domain.models import (
    EDGE_CONTAINS,
    EDGE_HANDLED_BY,
    KIND_MODULE,
    KIND_PACKAGE,
    KIND_ROUTE,
    Edge,
    ExtractionResult,
    Node,
    make_id,
)
from cherenkov.brainmap.extractors.ast_utils import decorator_calls, dotted, first_docline, literal_str
from cherenkov.brainmap.ports import ExtractContext

HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "options", "websocket", "route"}
ROUTER_HINTS = {"app", "router", "api", "blueprint", "bp", "sub_app"}


class RouteExtractor:
    """Maps decorated handler functions to ``route`` nodes."""

    name = "routes"

    def claims(self, rel_path: str) -> bool:
        """Whether ``rel_path`` is Python source that might declare routes."""
        return rel_path.endswith(".py")

    def extract(self, rel_path: str, text: str, ctx: ExtractContext) -> ExtractionResult:
        """Parse route declarations out of one Python file.

        Args:
            rel_path (str): Repo-relative path.
            text (str): File contents.
            ctx (ExtractContext): Project context.

        Returns:
            ExtractionResult: One node per route plus containment edges back
            to the declaring module.
        """
        result = ExtractionResult()
        # Cheap pre-filter: the AST parse is the expensive part, and most files
        # in a repo declare no routes at all.
        if "@" not in text or not any(f".{verb}(" in text for verb in HTTP_VERBS):
            return result
        try:
            tree = ast.parse(text, filename=rel_path)
        except SyntaxError:
            return result

        module_name = ctx.profile.module_name(rel_path)
        module_kind = KIND_PACKAGE if rel_path.endswith("__init__.py") else KIND_MODULE
        module_id = make_id(module_kind, module_name)
        prefix = _router_prefix(tree)
        layer = ctx.layer_for(rel_path)

        for stmt in ast.walk(tree):
            if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for call in decorator_calls(stmt):
                target = dotted(call.func)
                if "." not in target:
                    continue
                obj, _, verb = target.rpartition(".")
                if verb not in HTTP_VERBS or obj.split(".")[-1] not in ROUTER_HINTS:
                    continue
                path = literal_str(call.args[0]) if call.args else ""
                if not path.startswith("/"):
                    continue
                method = "WS" if verb == "websocket" else ("ANY" if verb == "route" else verb.upper())
                full_path = _join(prefix, path)
                route_id = make_id(KIND_ROUTE, f"{method} {full_path}")
                result.nodes.append(
                    Node(
                        id=route_id,
                        kind=KIND_ROUTE,
                        title=f"{method} {full_path}",
                        origin=rel_path,
                        summary=first_docline(stmt),
                        layer=layer or "web",
                        tags=["http", method.lower()],
                        attrs={
                            "method": method,
                            "path": full_path,
                            "handler": stmt.name,
                            "line": stmt.lineno,
                            "module": module_name,
                        },
                    )
                )
                result.edges.append(Edge(src=module_id, kind=EDGE_CONTAINS, dst=route_id, origin=rel_path))
                result.edges.append(
                    Edge(
                        src=route_id,
                        kind=EDGE_HANDLED_BY,
                        dst=module_id,
                        origin=rel_path,
                        attrs={"handler": stmt.name},
                    )
                )
        return result


def _router_prefix(tree: ast.Module) -> str:
    """Return the ``prefix=`` passed to a module-level ``APIRouter(...)``.

    Routers that carry their prefix in the constructor would otherwise produce
    paths that do not match the ones the service actually serves.

    Args:
        tree (ast.Module): Parsed module.

    Returns:
        str: The prefix, or ``""`` when there is none.
    """
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign) or not isinstance(stmt.value, ast.Call):
            continue
        if dotted(stmt.value.func).split(".")[-1] != "APIRouter":
            continue
        for keyword in stmt.value.keywords:
            if keyword.arg == "prefix":
                return literal_str(keyword.value)
    return ""


def _join(prefix: str, path: str) -> str:
    """Join a router prefix and a route path into one clean path."""
    if not prefix:
        return path
    return f"{prefix.rstrip('/')}/{path.lstrip('/')}".rstrip("/") or "/"
