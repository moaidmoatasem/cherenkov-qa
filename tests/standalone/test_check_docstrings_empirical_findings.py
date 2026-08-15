"""
test_check_docstrings_empirical_findings.py
───────────────────────────────────────────
Empirical validation of findings and scanner mechanics for check_docstrings.py.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from scripts.check_docstrings import (
    _check_go_file,
    _check_python_file,
    CoverageStats,
    run_docstring_check,
)


def test_empirical_param_substring_false_negative(tmp_path: Path) -> None:
    """Empirical demonstration: Parameter 'c' is missing from Args, but passes because 'c' is in 'Process'."""
    f = tmp_path / "sample.py"
    f.write_text(
        '"""Module docstring."""\n\n'
        'def process_item(c: int) -> None:\n'
        '    """Process item now."""\n'
        '    pass\n',
        encoding="utf-8",
    )
    stats = CoverageStats()
    violations = _check_python_file(f, tmp_path, stats)
    # Because 'c' is in 'process', violations is 0 (False Negative in AST parameter checker)
    assert len(violations) == 0, "Demonstrates substring false negative"
    assert stats.params_covered == 1


def test_empirical_param_distinct_fails(tmp_path: Path) -> None:
    """Empirical demonstration: Parameter 'xyz' is missing from Args and does not appear in summary, correctly fails."""
    f = tmp_path / "sample2.py"
    f.write_text(
        '"""Module docstring."""\n\n'
        'def process_item(xyz: int) -> None:\n'
        '    """Process item now."""\n'
        '    pass\n',
        encoding="utf-8",
    )
    stats = CoverageStats()
    violations = _check_python_file(f, tmp_path, stats)
    assert len(violations) == 1
    assert violations[0].category == "PARAMETER"
    assert "xyz" in violations[0].symbol_name


def test_empirical_go_multiline_block_comment_behavior(tmp_path: Path) -> None:
    """Empirical demonstration: Go block comments without leading '*' on middle lines get cleared."""
    f = tmp_path / "block.go"
    f.write_text(
        '// Package blockdemo provides block comment test.\n'
        'package blockdemo\n\n'
        '/*\n'
        'Server handles incoming connections.\n'
        '*/\n'
        'type Server struct{}\n',
        encoding="utf-8",
    )
    stats = CoverageStats()
    violations = _check_go_file(f, tmp_path, stats)
    # Demonstrates that Server triggers a violation because middle line lacked '*' or '//'
    assert len(violations) == 1
    assert violations[0].category == "GO_SYMBOL"
    assert "Server" in violations[0].symbol_name


def test_empirical_go_multiline_block_comment_with_asterisk_passes(tmp_path: Path) -> None:
    """Empirical demonstration: Go block comments with leading '*' on middle lines pass."""
    f = tmp_path / "block_star.go"
    f.write_text(
        '// Package blockdemo provides block comment test.\n'
        'package blockdemo\n\n'
        '/*\n'
        ' * Server handles incoming connections.\n'
        ' */\n'
        'type Server struct{}\n',
        encoding="utf-8",
    )
    stats = CoverageStats()
    violations = _check_go_file(f, tmp_path, stats)
    assert len(violations) == 0
    assert stats.go_symbols_covered == 2


def test_empirical_return_detection_annotated_vs_inferred(tmp_path: Path) -> None:
    """Verify return value detection on both return type annotation and AST Return node."""
    f = tmp_path / "ret.py"
    f.write_text(
        '"""Module docstring."""\n\n'
        'def unannotated_return():\n'
        '    """Summary docstring."""\n'
        '    return 100\n\n'
        'def annotated_return() -> int:\n'
        '    """Summary docstring."""\n'
        '    pass\n',
        encoding="utf-8",
    )
    stats = CoverageStats()
    violations = _check_python_file(f, tmp_path, stats)
    assert len(violations) == 2
    assert all(v.category == "RETURN" for v in violations)
