#!/usr/bin/env python3
"""generate_missing_docstrings.py

Utility to add placeholder docstrings for public functions, methods, and classes
that lack a docstring. The generated stub includes sections for parameters
(`:param <name>: <description>`) and return value (`:return: <description>`).

Usage:
    python scripts/generate_missing_docstrings.py [path]

If no path is provided, the repository root is used.
"""

import ast, os, sys
from pathlib import Path

PLACEHOLDER_DESC = "<description>"

def is_public(name: str) -> bool:
    """Return True if the identifier is considered public (does not start with an underscore).

    Args:
        name: Function, class, or symbol name string.

    Returns:
        True if name is public, False otherwise.
    """
    return not name.startswith("_")


def format_docstring(node: ast.AST) -> str:
    """Create a stub docstring for *node* (FunctionDef/AsyncFunctionDef/ClassDef).
    For functions and methods, include ``:param`` lines for each argument (excluding
    ``self``/``cls``) and a ``:return:`` line. For classes, only a generic
    placeholder is used.

    Args:
        node: AST definition node.

    Returns:
        Formatted stub docstring string.
    """
    lines = ["Placeholder docstring.", ""]
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # Parameters
        args = []
        for arg in node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            args.append(arg.arg)
        # *args and **kwargs
        if node.args.vararg:
            args.append("*" + node.args.vararg.arg)
        if node.args.kwarg:
            args.append("**" + node.args.kwarg.arg)
        for a in args:
            lines.append(f":param {a}: {PLACEHOLDER_DESC}")
        # Return placeholder
        lines.append(":return: " + PLACEHOLDER_DESC)
    else:
        # Class docstring – simple placeholder
        lines.append(PLACEHOLDER_DESC)
    return "\n".join(lines)


def add_docstrings_to_file(filepath: Path) -> bool:
    """Scan and add missing docstrings to a Python file.

    Args:
        filepath: Path instance pointing to target Python file.

    Returns:
        True if docstrings were inserted, False otherwise.
    """
    with filepath.open("r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    inserts = []  # (lineno, indent, docstring)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not is_public(node.name):
                continue
            # Detect missing docstring
            if (
                len(node.body) == 0
                or not isinstance(node.body[0], ast.Expr)
                or not isinstance(node.body[0].value, ast.Str)
            ):
                line = source.splitlines()[node.lineno - 1]
                indent = " " * (len(line) - len(line.lstrip()) + 4)
                doc = format_docstring(node)
                inserts.append((node.lineno, indent, doc))
    if not inserts:
        return False
    lines = source.splitlines(keepends=True)
    for lineno, indent, doc in reversed(inserts):
        doc_block = f"{indent}\"\"\"{doc}\"\"\"\n"
        lines.insert(lineno, doc_block)
    new_source = "".join(lines)
    with filepath.open("w", encoding="utf-8") as f:
        f.write(new_source)
    return True


def main():
    """Main CLI entry point for generating missing docstring stubs."""
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    modified = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith('.py') and not fname.startswith('.'):
                path = Path(dirpath) / fname
                if add_docstrings_to_file(path):
                    modified.append(str(path))
    if modified:
        print("Added placeholder docstrings to:")
        for p in modified:
            print(p)
    else:
        print("No missing docstrings detected.")

if __name__ == "__main__":
    main()
