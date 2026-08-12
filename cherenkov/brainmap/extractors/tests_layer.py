"""Tests extractor — what covers what.

Emits no nodes: a Python test file is already a ``test`` node from the Python
extractor, and a Playwright spec is already a frontend module. This extractor
contributes the one relationship neither of them can state on its own —
``tests`` — from two signals:

* every project module a Python test imports, and
* the naming convention, so ``tests/unit/test_coverage_map.py`` points at
  ``coverage_map`` even when the import is indirect.

The payoff is negative space. Once ``tests`` edges exist, "which module has no
test edge" is a query rather than an audit, which for a QA product is the whole
point of having a map at all.
"""

from __future__ import annotations

import ast
import posixpath
import re

from cherenkov.brainmap.domain.models import (
    EDGE_TESTS,
    KIND_TEST,
    Edge,
    ExtractionResult,
    make_id,
)
from cherenkov.brainmap.extractors.python_modules import is_test_path
from cherenkov.brainmap.ports import ExtractContext

_SPEC_IMPORT = re.compile(r"""(?:import|from)\s+['"]([^'"]+)['"]""")
SPEC_SUFFIXES = (".spec.ts", ".spec.tsx", ".test.ts", ".test.tsx", ".spec.js", ".test.js")


class TestsExtractor:
    """Adds ``tests`` edges from test files to the code they exercise."""

    name = "tests"

    def claims(self, rel_path: str) -> bool:
        """Whether ``rel_path`` is a test file in any supported language."""
        if rel_path.endswith(SPEC_SUFFIXES):
            return True
        return rel_path.endswith(".py") and is_test_path(rel_path, [])

    def extract(self, rel_path: str, text: str, ctx: ExtractContext) -> ExtractionResult:
        """Derive coverage edges for one test file.

        Args:
            rel_path (str): Repo-relative path.
            text (str): File contents.
            ctx (ExtractContext): Project context.

        Returns:
            ExtractionResult: ``tests`` edges only, all unresolved. Edges are
            marked soft — a test importing ``pytest`` must not be reported as
            a broken link.
        """
        result = ExtractionResult()
        if rel_path.endswith(SPEC_SUFFIXES):
            return self._spec(rel_path, text, result)
        return self._python(rel_path, text, ctx, result)

    def _python(
        self, rel_path: str, text: str, ctx: ExtractContext, result: ExtractionResult
    ) -> ExtractionResult:
        """Emit coverage edges for a Python test module."""
        module_name = ctx.profile.module_name(rel_path)
        test_id = make_id(KIND_TEST, module_name)
        try:
            tree = ast.parse(text, filename=rel_path)
        except SyntaxError:
            return result

        hints: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                hints.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                hints.append(node.module)

        seen: set[str] = set()
        for hint in hints:
            if hint in seen:
                continue
            seen.add(hint)
            result.edges.append(
                Edge(src=test_id, kind=EDGE_TESTS, target_hint=hint, origin=rel_path, attrs={"soft": True})
            )

        subject = _subject_from_name(rel_path)
        if subject and subject not in seen:
            result.edges.append(
                Edge(
                    src=test_id,
                    kind=EDGE_TESTS,
                    target_hint=subject,
                    origin=rel_path,
                    weight=0.5,
                    attrs={"soft": True, "by": "naming-convention"},
                )
            )
        return result

    def _spec(self, rel_path: str, text: str, result: ExtractionResult) -> ExtractionResult:
        """Emit coverage edges for a TypeScript/JavaScript spec file."""
        stem = rel_path
        for suffix in SPEC_SUFFIXES:
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        test_id = make_id(KIND_TEST, stem)
        for match in _SPEC_IMPORT.finditer(text):
            spec = match.group(1)
            if not spec.startswith("."):
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(rel_path), spec))
            result.edges.append(
                Edge(src=test_id, kind=EDGE_TESTS, target_hint=target, origin=rel_path, attrs={"soft": True})
            )
        return result


def _subject_from_name(rel_path: str) -> str:
    """Return the bare subject name implied by a test filename.

    ``tests/unit/test_coverage_map.py`` → ``coverage_map``. The reconciler
    treats this as a last-resort suffix match, so a wrong guess resolves to
    nothing rather than to the wrong node.

    Args:
        rel_path (str): Repo-relative path to a test file.

    Returns:
        str: Subject name, or ``""`` when the filename carries no hint.
    """
    name = rel_path.rsplit("/", 1)[-1]
    if name.endswith(".py"):
        name = name[:-3]
    if name.startswith("test_"):
        return name[len("test_") :]
    if name.endswith("_test"):
        return name[: -len("_test")]
    return ""
