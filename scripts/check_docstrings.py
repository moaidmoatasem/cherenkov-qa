#!/usr/bin/env python3
"""
check_docstrings.py
───────────────────
Automated Python AST & Go Comment Docstring Coverage Inspector for CHERENKOV QA.
Enforces 100% docstring coverage for public modules, classes, functions,
parameters, and return values in Python (cherenkov/, scripts/, ci/),
and exported Go symbols in operator/.

Usage:
    python scripts/check_docstrings.py
    python scripts/check_docstrings.py --json
    python scripts/check_docstrings.py --root . --verbose
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

# Reconfigure stdout to UTF-8 for Windows console safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Directories to exclude from scanning
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "target",
    ".agents", "build", "dist", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "site-packages"
}


class Violation(NamedTuple):
    """Represents a single docstring violation found during scan."""
    file_path: str
    line: int
    category: str  # MODULE, CLASS, FUNCTION, PARAMETER, RETURN, GO_PACKAGE, GO_SYMBOL
    symbol_name: str
    message: str


class CoverageStats:
    """Maintains coverage statistics across Python and Go source files."""

    def __init__(self) -> None:
        """Initialize all counter metrics to zero."""
        self.files_scanned: int = 0
        self.py_files: int = 0
        self.go_files: int = 0
        self.modules_total: int = 0
        self.modules_covered: int = 0
        self.classes_total: int = 0
        self.classes_covered: int = 0
        self.functions_total: int = 0
        self.functions_covered: int = 0
        self.params_total: int = 0
        self.params_covered: int = 0
        self.returns_total: int = 0
        self.returns_covered: int = 0
        self.go_symbols_total: int = 0
        self.go_symbols_covered: int = 0

    @property
    def total_symbols(self) -> int:
        """Calculate total number of inspected public symbols across all categories.

        Returns:
            int: Sum of module, class, function, parameter, return, and Go symbol counts.
        """
        return (
            self.modules_total
            + self.classes_total
            + self.functions_total
            + self.params_total
            + self.returns_total
            + self.go_symbols_total
        )

    @property
    def total_covered(self) -> int:
        """Calculate total number of covered public symbols across all categories.

        Returns:
            int: Sum of covered module, class, function, parameter, return, and Go symbol counts.
        """
        return (
            self.modules_covered
            + self.classes_covered
            + self.functions_covered
            + self.params_covered
            + self.returns_covered
            + self.go_symbols_covered
        )

    @property
    def coverage_percentage(self) -> float:
        """Calculate total docstring coverage percentage.

        Returns:
            float: Percentage value between 0.0 and 100.0.
        """
        if self.total_symbols == 0:
            return 100.0
        return (self.total_covered / self.total_symbols) * 100.0


def _is_none_node(node: ast.AST) -> bool:
    """Check if an AST node represents a literal None value or None type annotation.

    Args:
        node: AST node to evaluate.

    Returns:
        bool: True if node represents None, False otherwise.
    """
    if isinstance(node, ast.Constant) and node.value is None:
        return True
    if isinstance(node, ast.Name) and node.id == "None":
        return True
    return False


def _check_python_file(file_path: Path, root_path: Path, stats: CoverageStats) -> list[Violation]:
    """Inspect a single Python file using AST parsing for docstrings, parameters, and returns.

    Args:
        file_path: Absolute path to the Python file.
        root_path: Root repository directory for relative path formatting.
        stats: CoverageStats instance to update.

    Returns:
        list[Violation]: List of detected docstring violations.
    """
    violations: list[Violation] = []
    rel_path = str(file_path.relative_to(root_path))
    stats.files_scanned += 1
    stats.py_files += 1

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as se:
        violations.append(Violation(rel_path, se.lineno or 1, "SYNTAX_ERROR", file_path.name, f"Python Syntax Error: {se.msg}"))
        return violations
    except Exception as e:
        violations.append(Violation(rel_path, 1, "FILE_ERROR", file_path.name, f"Failed to read/parse file: {e}"))
        return violations

    # Check Module Docstring
    # Public modules: name does not start with "_" OR is "__init__.py"
    filename = file_path.name
    is_public_module = not filename.startswith("_") or filename == "__init__.py"

    if is_public_module:
        stats.modules_total += 1
        mod_docstring = ast.get_docstring(tree)
        if not mod_docstring or not mod_docstring.strip():
            violations.append(Violation(
                file_path=rel_path,
                line=1,
                category="MODULE",
                symbol_name=filename,
                message=f"Missing module docstring in '{rel_path}'"
            ))
        else:
            stats.modules_covered += 1

    # Traverse AST for Classes and Functions
    class ParentVisitor(ast.NodeVisitor):
        """AST visitor for traversing classes and functions while tracking nesting context."""

        def __init__(self) -> None:
            """Initialize ParentVisitor class stack."""
            self.class_stack: list[tuple[ast.ClassDef, str | None]] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            """Inspect a ClassDef node for class docstrings.

            Args:
                node: AST ClassDef node.
            """
            class_name = node.name
            class_doc = ast.get_docstring(node)
            if not class_name.startswith("_"):
                stats.classes_total += 1
                if not class_doc or not class_doc.strip():
                    violations.append(Violation(
                        file_path=rel_path,
                        line=node.lineno,
                        category="CLASS",
                        symbol_name=class_name,
                        message=f"Missing docstring for public class '{class_name}'"
                    ))
                else:
                    stats.classes_covered += 1

            self.class_stack.append((node, class_doc))
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            """Inspect a FunctionDef node for function docstrings, parameters, and returns.

            Args:
                node: AST FunctionDef node.
            """
            self._handle_function(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            """Inspect an AsyncFunctionDef node for docstrings, parameters, and returns.

            Args:
                node: AST AsyncFunctionDef node.
            """
            self._handle_function(node)
            self.generic_visit(node)

        def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            """Inspect a function or async function node.

            Args:
                node: AST function node.
            """
            func_name = node.name
            # Skip private functions/methods starting with "_" except "__init__"
            if func_name.startswith("_") and func_name != "__init__":
                return

            func_doc = ast.get_docstring(node)
            parent_class_doc = self.class_stack[-1][1] if self.class_stack else None

            if func_name == "__init__":
                params = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
                posonly = getattr(node.args, "posonlyargs", [])
                params.extend([a.arg for a in posonly if a.arg not in ("self", "cls")])
                params.extend([a.arg for a in node.args.kwonlyargs if a.arg not in ("self", "cls")])
                if node.args.vararg and node.args.vararg.arg not in ("self", "cls"):
                    params.append(node.args.vararg.arg)
                if node.args.kwarg and node.args.kwarg.arg not in ("self", "cls"):
                    params.append(node.args.kwarg.arg)

                if params:
                    combined_doc = (func_doc or "") + "\n" + (parent_class_doc or "")
                    combined_doc_lower = combined_doc.lower()
                    for p_name in params:
                        stats.params_total += 1
                        if p_name.lower() in combined_doc_lower:
                            stats.params_covered += 1
                        else:
                            violations.append(Violation(
                                file_path=rel_path,
                                line=node.lineno,
                                category="PARAMETER",
                                symbol_name=f"__init__.{p_name}",
                                message=f"Parameter '{p_name}' is missing description in docstring for '__init__'"
                            ))
                return

            # Regular public function / method
            stats.functions_total += 1
            if not func_doc or not func_doc.strip():
                violations.append(Violation(
                    file_path=rel_path,
                    line=node.lineno,
                    category="FUNCTION",
                    symbol_name=func_name,
                    message=f"Missing docstring for public function/method '{func_name}'"
                ))
                return

            stats.functions_covered += 1
            doc_lower = func_doc.lower()

            # Parameter check
            params = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
            posonly = getattr(node.args, "posonlyargs", [])
            params.extend([a.arg for a in posonly if a.arg not in ("self", "cls")])
            params.extend([a.arg for a in node.args.kwonlyargs if a.arg not in ("self", "cls")])
            if node.args.vararg and node.args.vararg.arg not in ("self", "cls"):
                params.append(node.args.vararg.arg)
            if node.args.kwarg and node.args.kwarg.arg not in ("self", "cls"):
                params.append(node.args.kwarg.arg)

            for p_name in params:
                stats.params_total += 1
                if p_name.lower() in doc_lower:
                    stats.params_covered += 1
                else:
                    violations.append(Violation(
                        file_path=rel_path,
                        line=node.lineno,
                        category="PARAMETER",
                        symbol_name=f"{func_name}.{p_name}",
                        message=f"Parameter '{p_name}' is missing description in docstring of '{func_name}'"
                    ))

            # Return value check
            has_return = False
            if node.returns:
                if not _is_none_node(node.returns):
                    has_return = True
            else:
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value is not None:
                        if not _is_none_node(child.value):
                            has_return = True
                            break
                    elif isinstance(child, (ast.Yield, ast.YieldFrom)):
                        has_return = True
                        break

            if has_return:
                stats.returns_total += 1
                return_keywords = ("return", "returns", "yield", "yields", ":return", ":returns", "@return", "@returns")
                if any(k in doc_lower for k in return_keywords):
                    stats.returns_covered += 1
                else:
                    violations.append(Violation(
                        file_path=rel_path,
                        line=node.lineno,
                        category="RETURN",
                        symbol_name=func_name,
                        message=f"Function '{func_name}' returns a value but lacks return/yield description in docstring"
                    ))

    visitor = ParentVisitor()
    visitor.visit(tree)

    return violations


GO_PKG_DECL = re.compile(r'^\s*package\s+(?P<name>[a-zA-Z0-9_]+)')
GO_EXPORTED_DECL = re.compile(
    r'^\s*(?:type|func|const|var)\s+'
    r'(?:\([^\)]+\)\s+)?'  # optional receiver (r *Type)
    r'(?P<name>[A-Z][a-zA-Z0-9_]*)'  # Exported name starting with uppercase
)

def _check_go_file(file_path: Path, root_path: Path, stats: CoverageStats) -> list[Violation]:
    """Inspect a single Go source file for package and exported symbol doc comments.

    Args:
        file_path: Absolute path to the Go file.
        root_path: Root repository directory for relative path formatting.
        stats: CoverageStats instance to update.

    Returns:
        list[Violation]: List of detected Go doc comment violations.
    """
    violations: list[Violation] = []
    rel_path = str(file_path.relative_to(root_path))
    filename = file_path.name

    # Skip auto-generated Go files (e.g. zz_generated*.go)
    if filename.startswith("zz_generated"):
        return violations

    stats.files_scanned += 1
    stats.go_files += 1

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        violations.append(Violation(rel_path, 1, "GO_FILE", filename, f"Failed to read file: {e}"))
        return violations

    lines = content.splitlines()

    # Check header for generated code markers
    header = "\n".join(lines[:10]).lower()
    if "code generated" in header or "do not edit" in header:
        return violations

    pending_comments: list[str] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Compiler directives
        if stripped.startswith("//go:") or stripped.startswith("// +build"):
            continue

        # Comment line accumulation
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or stripped.endswith("*/"):
            pending_comments.append(stripped)
            continue

        # Blank line resets comment buffer
        if not stripped:
            pending_comments.clear()
            continue

        # Package declaration
        pkg_match = GO_PKG_DECL.match(line)
        if pkg_match:
            pkg_name = pkg_match.group("name")
            stats.go_symbols_total += 1
            if not pending_comments:
                violations.append(Violation(
                    file_path=rel_path,
                    line=idx,
                    category="GO_PACKAGE",
                    symbol_name=f"package {pkg_name}",
                    message=f"Package '{pkg_name}' is missing a doc comment"
                ))
            else:
                comment_text = " ".join(pending_comments).strip()
                if len(comment_text) >= 5:
                    stats.go_symbols_covered += 1
                else:
                    violations.append(Violation(
                        file_path=rel_path,
                        line=idx,
                        category="GO_PACKAGE",
                        symbol_name=f"package {pkg_name}",
                        message=f"Package '{pkg_name}' has empty/invalid doc comment"
                    ))
            pending_comments.clear()
            continue

        # Exported symbol declaration
        decl_match = GO_EXPORTED_DECL.match(line)
        if decl_match:
            symbol_name = decl_match.group("name")
            stats.go_symbols_total += 1
            if not pending_comments:
                violations.append(Violation(
                    file_path=rel_path,
                    line=idx,
                    category="GO_SYMBOL",
                    symbol_name=symbol_name,
                    message=f"Exported Go symbol '{symbol_name}' is missing a doc comment"
                ))
            else:
                comment_text = " ".join(pending_comments).strip()
                if len(comment_text) >= 5:
                    stats.go_symbols_covered += 1
                else:
                    violations.append(Violation(
                        file_path=rel_path,
                        line=idx,
                        category="GO_SYMBOL",
                        symbol_name=symbol_name,
                        message=f"Exported Go symbol '{symbol_name}' has empty/invalid doc comment"
                    ))
            pending_comments.clear()
            continue

        # Non-comment line resets comment buffer
        pending_comments.clear()

    return violations


def run_docstring_check(root_dir: Path, py_dirs: list[str], go_dirs: list[str]) -> tuple[CoverageStats, list[Violation]]:
    """Execute docstring coverage check across specified Python and Go directories.

    Args:
        root_dir: Root directory of the repository.
        py_dirs: List of directories to search for Python files.
        go_dirs: List of directories to search for Go files.

    Returns:
        tuple[CoverageStats, list[Violation]]: Calculated statistics and detected violations.
    """
    stats = CoverageStats()
    all_violations: list[Violation] = []

    # Collect Python files
    py_files: list[Path] = []
    for d in py_dirs:
        dir_path = root_dir / d
        if dir_path.is_file() and dir_path.suffix == ".py":
            py_files.append(dir_path)
        elif dir_path.is_dir():
            for p in dir_path.rglob("*.py"):
                if not any(part in EXCLUDE_DIRS for part in p.parts):
                    py_files.append(p)

    for py_file in py_files:
        violations = _check_python_file(py_file, root_dir, stats)
        all_violations.extend(violations)

    # Collect Go files
    go_files: list[Path] = []
    for d in go_dirs:
        dir_path = root_dir / d
        if dir_path.is_file() and dir_path.suffix == ".go":
            go_files.append(dir_path)
        elif dir_path.is_dir():
            for p in dir_path.rglob("*.go"):
                if not any(part in EXCLUDE_DIRS for part in p.parts):
                    go_files.append(p)

    for go_file in go_files:
        violations = _check_go_file(go_file, root_dir, stats)
        all_violations.extend(violations)

    return stats, all_violations


def main() -> int:
    """CLI entry point for check_docstrings.py.

    Returns:
        int: 0 if 100% compliant, 1 if any violations detected.
    """
    parser = argparse.ArgumentParser(
        description="Automated Python AST & Go Comment Docstring Coverage Inspector for CHERENKOV QA"
    )
    parser.add_argument("--root", type=str, default=".", help="Root repository directory (default: .)")
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=["cherenkov", "scripts", "ci"],
        help="Directories containing Python files to scan",
    )
    parser.add_argument(
        "--go-dirs",
        nargs="+",
        default=["operator"],
        help="Directories containing Go files to scan",
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    root_path = Path(args.root).resolve()

    stats, violations = run_docstring_check(root_path, args.dirs, args.go_dirs)

    passed = len(violations) == 0 and stats.coverage_percentage >= 100.0

    if args.json:
        payload = {
            "tool": "check_docstrings.py",
            "status": "PASSED" if passed else "FAILED",
            "exit_code": 0 if passed else 1,
            "metrics": {
                "files_scanned": stats.files_scanned,
                "py_files": stats.py_files,
                "go_files": stats.go_files,
                "total_symbols": stats.total_symbols,
                "covered_symbols": stats.total_covered,
                "coverage_percentage": round(stats.coverage_percentage, 2),
                "breakdown": {
                    "module_docstrings": {"covered": stats.modules_covered, "total": stats.modules_total},
                    "class_docstrings": {"covered": stats.classes_covered, "total": stats.classes_total},
                    "function_docstrings": {"covered": stats.functions_covered, "total": stats.functions_total},
                    "parameter_descriptions": {"covered": stats.params_covered, "total": stats.params_total},
                    "return_descriptions": {"covered": stats.returns_covered, "total": stats.returns_total},
                    "go_doc_comments": {"covered": stats.go_symbols_covered, "total": stats.go_symbols_total},
                },
            },
            "violations": [
                {
                    "file": v.file_path,
                    "line": v.line,
                    "category": v.category,
                    "symbol": v.symbol_name,
                    "message": v.message,
                }
                for v in violations
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0 if passed else 1

    # Terminal Summary Output
    print("=" * 80)
    print("CHERENKOV QA - Docstring & API Documentation Coverage Report")
    print("=" * 80)
    print(f"Target Root:     {root_path}")
    print(f"Files Scanned:   {stats.files_scanned} ({stats.py_files} Python, {stats.go_files} Go)")
    print(f"Total Symbols:   {stats.total_symbols}")
    print("-" * 80)

    if violations:
        print("[FAIL] VIOLATIONS FOUND:\n")
        for v in violations:
            print(f"  [{v.category:10s}] {v.file_path}:{v.line}")
            print(f"              └─ {v.message}")
        print("-" * 80)
    else:
        print("[OK] ZERO VIOLATIONS DETECTED!\n")
        print("-" * 80)

    print("SUMMARY STATISTICS:")
    def _fmt_stat(label: str, covered: int, total: int) -> str:
        pct = (covered / total * 100.0) if total > 0 else 100.0
        missing = total - covered
        missing_str = f" [{missing} Missing]" if missing > 0 else ""
        return f"  - {label:24s} {pct:5.1f}% ({covered}/{total}){missing_str}"

    print(_fmt_stat("Module Docstrings:", stats.modules_covered, stats.modules_total))
    print(_fmt_stat("Class Docstrings:", stats.classes_covered, stats.classes_total))
    print(_fmt_stat("Function Docstrings:", stats.functions_covered, stats.functions_total))
    print(_fmt_stat("Parameter Descs:", stats.params_covered, stats.params_total))
    print(_fmt_stat("Return Value Descs:", stats.returns_covered, stats.returns_total))
    print(_fmt_stat("Go Doc Comments:", stats.go_symbols_covered, stats.go_symbols_total))

    print("-" * 80)
    cov_pct = stats.coverage_percentage
    status_str = "PASSED" if passed else "FAILED"
    indicator = "[OK]" if passed else "[FAIL]"
    print(f"OVERALL COVERAGE: {cov_pct:.1f}% - {status_str} (Threshold: 100.0%)")
    print(f"STATUS: {indicator} {status_str} (Exit Code: {0 if passed else 1})")
    print("=" * 80)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
