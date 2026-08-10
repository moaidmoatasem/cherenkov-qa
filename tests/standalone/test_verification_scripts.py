"""
test_verification_scripts.py
─────────────────────────────
Unit tests for verification tooling scripts:
- scripts/check_docstrings.py
- scripts/check_docs_markdown.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_docstrings import run_docstring_check
from scripts.check_docs_markdown import scan_markdown_files


def test_check_docstrings_compliant(tmp_path: Path) -> None:
    """Verify that check_docstrings returns 0 violations on fully compliant code.

    Args:
        tmp_path: Temporary directory fixture.
    """
    py_dir = tmp_path / "cherenkov"
    py_dir.mkdir()

    sample_py = py_dir / "sample.py"
    sample_py.write_text(
        '"""Sample module docstring explaining purpose."""\n\n'
        'class Calculator:\n'
        '    """Calculator class for basic math operations."""\n'
        '    def add(self, x: int, y: int) -> int:\n'
        '        """Add two integers and return the result.\n\n'
        '        Args:\n'
        '            x: First integer.\n'
        '            y: Second integer.\n\n'
        '        Returns:\n'
        '            int: Sum of x and y.\n'
        '        """\n'
        '        return x + y\n',
        encoding="utf-8",
    )

    go_dir = tmp_path / "operator"
    go_dir.mkdir()

    sample_go = go_dir / "main.go"
    sample_go.write_text(
        '// Package main defines the entrypoint.\n'
        'package main\n\n'
        '// Runner handles task execution.\n'
        'type Runner struct{}\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["cherenkov"], ["operator"])
    assert len(violations) == 0
    assert stats.coverage_percentage == 100.0


def test_check_docstrings_violations_detected(tmp_path: Path) -> None:
    """Verify that check_docstrings accurately detects missing docstrings and parameters.

    Args:
        tmp_path: Temporary directory fixture.
    """
    py_dir = tmp_path / "cherenkov"
    py_dir.mkdir()

    bad_py = py_dir / "bad.py"
    bad_py.write_text(
        '# Missing module docstring\n\n'
        'class Foo:\n'
        '    # Missing class docstring\n'
        '    def do_something(self, param1: str) -> str:\n'
        '        """Do something without doc sections."""\n'
        '        return param1\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["cherenkov"], [])
    assert len(violations) > 0
    categories = [v.category for v in violations]
    assert "MODULE" in categories
    assert "CLASS" in categories
    assert "PARAMETER" in categories
    assert "RETURN" in categories


def test_check_docs_markdown_compliant(tmp_path: Path) -> None:
    """Verify that scan_markdown_files passes on clean Markdown files.

    Args:
        tmp_path: Temporary directory fixture.
    """
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    doc_a = docs_dir / "page_a.md"
    doc_a.write_text(
        '# Title A\n\n'
        '## Section One\n\n'
        'This is a valid link to [Page B](page_b.md#heading-b).\n',
        encoding="utf-8",
    )

    doc_b = docs_dir / "page_b.md"
    doc_b.write_text(
        '# Title B\n\n'
        '## Heading B\n\n'
        'Content for heading B.\n',
        encoding="utf-8",
    )

    stats, violations = scan_markdown_files(tmp_path, ["docs"], include_root_md=False)
    assert len(violations) == 0
    assert stats.total_violations == 0


def test_check_docs_markdown_violations_detected(tmp_path: Path) -> None:
    """Verify that scan_markdown_files catches empty files, placeholders, and broken links.

    Args:
        tmp_path: Temporary directory fixture.
    """
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    empty_doc = docs_dir / "empty.md"
    empty_doc.write_text("", encoding="utf-8")

    todo_doc = docs_dir / "todo.md"
    todo_doc.write_text(
        '# Unfinished Page\n\n'
        'TODO: Complete this section.\n'
        'Reference: [Missing](nonexistent.md)\n',
        encoding="utf-8",
    )

    stats, violations = scan_markdown_files(tmp_path, ["docs"], include_root_md=False)
    assert stats.total_violations > 0
    categories = [v.category for v in violations]
    assert "EMPTY_FILE" in categories
    assert "PLACEHOLDER" in categories
    assert "BROKEN_LINK" in categories
