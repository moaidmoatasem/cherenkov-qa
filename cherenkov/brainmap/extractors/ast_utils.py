"""Small AST helpers shared by the decorator-driven Python extractors."""

from __future__ import annotations

import ast


def dotted(node: ast.AST) -> str:
    """Render an attribute/name expression as a dotted string.

    Args:
        node (ast.AST): Expression node, e.g. the ``router.get`` in a decorator.

    Returns:
        str: ``"router.get"``, or ``""`` for anything that is not a plain
        name/attribute chain.
    """
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return ""
    return ".".join(reversed(parts))


def literal_str(node: ast.AST | None) -> str:
    """Return a string constant's value, or ``""`` for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def kwarg(call: ast.Call, name: str) -> ast.AST | None:
    """Return the value node of keyword argument ``name``, if present."""
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def decorator_calls(stmt: ast.AST) -> list[ast.Call]:
    """Return the decorators of a def/class that are call expressions."""
    decorators = getattr(stmt, "decorator_list", [])
    return [d for d in decorators if isinstance(d, ast.Call)]


def first_docline(stmt: ast.AST) -> str:
    """Return the first line of a def/class docstring, or ``""``."""
    if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        return ""
    doc = ast.get_docstring(stmt) or ""
    for line in doc.splitlines():
        if line.strip():
            return line.strip()[:160]
    return ""
