"""
test_check_docstrings_extended_stress.py
────────────────────────────────────────
Extended stress testing and oracle verification for scripts/check_docstrings.py.
Deeply probes edge cases:
- Positional-only args, keyword-only args, *args, **kwargs
- Property getters, setters, classmethods, staticmethods
- Self/cls parameter filtering
- Return statements in nested functions vs outer function
- Empty / whitespace-only docstrings
- Multi-style docstrings (Google, NumPy, Sphinx)
- Complex Go receivers, multi-line comment styles, compiler directives
- Non-UTF8 or empty files
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.check_docstrings import run_docstring_check, CoverageStats, Violation


def test_posonly_and_kwonly_args(tmp_path: Path) -> None:
    """Verify posonly, kwonly, *args, and **kwargs require parameter docstrings."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    # Function with all arg types missing in docstring (using names not appearing in summary)
    (py_dir / "args_test.py").write_text(
        '"""Module docstring."""\n\n'
        'def complex_func(alpha, /, beta, *args, gamma=1, **kwargs) -> int:\n'
        '    """Process things."""\n'
        '    return 42\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    param_violations = [v for v in violations if v.category == "PARAMETER"]
    param_names = {v.symbol_name for v in param_violations}

    assert "complex_func.alpha" in param_names
    assert "complex_func.beta" in param_names
    assert "complex_func.args" in param_names
    assert "complex_func.gamma" in param_names
    assert "complex_func.kwargs" in param_names
    assert any(v.category == "RETURN" and v.symbol_name == "complex_func" for v in violations)


def test_self_cls_never_required(tmp_path: Path) -> None:
    """Verify self and cls are never reported as missing parameters."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "methods.py").write_text(
        '"""Module docstring."""\n\n'
        'class Handler:\n'
        '    """Handles requests."""\n'
        '    def handle(self) -> None:\n'
        '        """Handle single request."""\n'
        '        pass\n\n'
        '    @classmethod\n'
        '    def create(cls) -> "Handler":\n'
        '        """Create handler instance.\n\n'
        '        Returns:\n'
        '            Handler: new instance.\n'
        '        """\n'
        '        return cls()\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert len(violations) == 0
    assert stats.coverage_percentage == 100.0


def test_nested_function_return_isolation(tmp_path: Path) -> None:
    """Verify an outer function without return does not falsely require return if an inner function returns."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "nested.py").write_text(
        '"""Module docstring."""\n\n'
        'def outer_action(callback: str) -> None:\n'
        '    """Perform outer action.\n\n'
        '    Args:\n'
        '        callback: Callback name.\n'
        '    """\n'
        '    def _inner_helper() -> int:\n'
        '        return 123\n'
        '    _inner_helper()\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert len(violations) == 0


def test_whitespace_only_docstring_rejected(tmp_path: Path) -> None:
    """Verify whitespace-only docstrings are rejected for module, class, and function."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "spaces.py").write_text(
        '   \n\n'
        'class EmptyClass:\n'
        '    """   """\n'
        '    def empty_func(self) -> None:\n'
        '        """   """\n'
        '        pass\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    categories = {v.category for v in violations}
    assert "MODULE" in categories
    assert "CLASS" in categories
    assert "FUNCTION" in categories


def test_docstring_formats_google_numpy_sphinx(tmp_path: Path) -> None:
    """Verify Google, NumPy, and Sphinx docstring styles are recognized."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "styles.py").write_text(
        '"""Module docstring."""\n\n'
        'def sphinx_style(name: str) -> str:\n'
        '    """:param name: User name.\n'
        '    :return: Formatted string.\n'
        '    """\n'
        '    return f"Hello {name}"\n\n'
        'def numpy_style(value: int) -> int:\n'
        '    """Compute square.\n\n'
        '    Parameters\n'
        '    ----------\n'
        '    value : int\n'
        '        Input number.\n\n'
        '    Returns\n'
        '    -------\n'
        '    int\n'
        '        Squared number.\n'
        '    """\n'
        '    return value * value\n\n'
        'def google_style(item: str) -> bool:\n'
        '    """Check item validity.\n\n'
        '    Args:\n'
        '        item: Item key.\n\n'
        '    Returns:\n'
        '        bool: Validity status.\n'
        '    """\n'
        '    return len(item) > 0\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert len(violations) == 0
    assert stats.functions_covered == 3
    assert stats.params_covered == 3
    assert stats.returns_covered == 3


def test_go_complex_receivers_and_block_comments(tmp_path: Path) -> None:
    """Verify Go methods with value/pointer receivers and standard asterisk block comments are recognized."""
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()

    (go_dir / "server.go").write_text(
        '// Package server provides HTTP daemon.\n'
        'package server\n\n'
        '/*\n'
        ' * Server manages HTTP listener and routing.\n'
        ' */\n'
        'type Server struct{}\n\n'
        '/*\n'
        ' * Listen opens port and processes requests.\n'
        ' */\n'
        'func (s *Server) Listen(port int) error {\n'
        '    return nil\n'
        '}\n\n'
        '// Close gracefully stops the server.\n'
        'func (s Server) Close() {}\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, [], ["go_src"])
    assert len(violations) == 0
    assert stats.go_symbols_covered == 4  # package + Server + Listen + Close


def test_go_compiler_directives_do_not_break_comments(tmp_path: Path) -> None:
    """Verify compiler directives (//go:build, // +build) do not erase doc comments."""
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()

    (go_dir / "build_test.go").write_text(
        '//go:build linux || darwin\n'
        '// +build linux darwin\n\n'
        '// Package platform provides OS-specific operations.\n'
        'package platform\n\n'
        '// SysCall executes raw kernel syscall.\n'
        'func SysCall() int {\n'
        '    return 0\n'
        '}\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, [], ["go_src"])
    assert len(violations) == 0
    assert stats.go_symbols_covered == 2
