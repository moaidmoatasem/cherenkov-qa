"""Extractor-level tests for the brain map.

Each test feeds one file to one extractor and asserts on the fragments it
emits, so a failure names the extractor rather than the pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cherenkov.brainmap.config import BrainMapProfile
from cherenkov.brainmap.domain.models import (
    EDGE_CALLS,
    EDGE_CONTAINS,
    EDGE_DEFINES,
    EDGE_IMPORTS,
    EDGE_LINKS,
    EDGE_MENTIONS,
    EDGE_TESTS,
    KIND_CLASS,
    KIND_CLI_COMMAND,
    KIND_COMPONENT,
    KIND_DOC,
    KIND_MODULE,
    KIND_ROUTE,
    KIND_TEST,
)
from cherenkov.brainmap.extractors.cli_commands import CliExtractor
from cherenkov.brainmap.extractors.docs import DocsExtractor
from cherenkov.brainmap.extractors.frontend import FrontendExtractor
from cherenkov.brainmap.extractors.http_routes import RouteExtractor
from cherenkov.brainmap.extractors.python_modules import PythonExtractor
from cherenkov.brainmap.extractors.tests_layer import TestsExtractor
from cherenkov.brainmap.ports import ExtractContext


@pytest.fixture
def ctx() -> ExtractContext:
    """A context for a project rooted at ``/proj`` with default settings."""
    return ExtractContext(Path("/proj"), BrainMapProfile(project="proj", root=Path("/proj")))


def kinds(result) -> set[str]:
    """Return the set of node kinds in an extraction result."""
    return {node.kind for node in result.nodes}


def hints(result, kind: str) -> set[str]:
    """Return the target hints of every edge of one kind."""
    return {edge.target_hint for edge in result.edges if edge.kind == kind}


# ── Python ──────────────────────────────────────────────────────────────────
def test_python_extractor_maps_module_classes_and_imports(ctx):
    source = '''"""Widget factory."""
import os
from pkg.sub import helper
from . import sibling


class Widget:
    """A widget."""


def _private():
    pass
'''
    result = PythonExtractor().extract("pkg/widget.py", source, ctx)

    module = next(n for n in result.nodes if n.kind == KIND_MODULE)
    assert module.title == "pkg.widget"
    assert module.summary == "Widget factory."
    assert KIND_CLASS in kinds(result)
    assert {"os", "pkg.sub", "pkg.sub.helper"} <= hints(result, EDGE_IMPORTS)
    # ``from . import sibling`` inside pkg.widget must rebase onto ``pkg``.
    assert "pkg.sibling" in hints(result, EDGE_IMPORTS)
    assert any(e.kind == EDGE_DEFINES for e in result.edges)


def test_python_extractor_skips_private_symbols(ctx):
    result = PythonExtractor().extract("m.py", "def _hidden():\n    pass\n", ctx)
    assert not [n for n in result.nodes if n.title == "_hidden"]


def test_python_extractor_maps_test_files_as_tests(ctx):
    result = PythonExtractor().extract("tests/test_widget.py", "def test_x():\n    pass\n", ctx)
    # The file itself is a test; the extra node is its parent package.
    assert KIND_TEST in kinds(result)
    assert KIND_MODULE not in kinds(result)


def test_python_extractor_reports_syntax_errors_instead_of_dropping_the_file(ctx):
    result = PythonExtractor().extract("broken.py", "def oops(:\n", ctx)
    node = result.nodes[0]
    assert "unparseable" in node.tags
    assert node.attrs["parse_error"]


def test_python_extractor_respects_symbol_depth(ctx):
    ctx.profile.symbol_depth = "module"
    result = PythonExtractor().extract("m.py", "class Thing:\n    pass\n", ctx)
    assert kinds(result) == {KIND_MODULE}


# ── Routes ──────────────────────────────────────────────────────────────────
def test_route_extractor_joins_router_prefix(ctx):
    source = '''from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/things")


@router.get("/{thing_id}")
async def read_thing(thing_id: str):
    """Read one thing."""
'''
    result = RouteExtractor().extract("app/things.py", source, ctx)
    route = next(n for n in result.nodes if n.kind == KIND_ROUTE)
    assert route.attrs["path"] == "/api/v1/things/{thing_id}"
    assert route.attrs["method"] == "GET"
    assert route.summary == "Read one thing."
    assert any(e.kind == EDGE_CONTAINS for e in result.edges)


def test_route_extractor_ignores_non_router_decorators(ctx):
    source = '@some_cache.get("/not-a-route")\ndef f():\n    pass\n'
    assert not RouteExtractor().extract("m.py", source, ctx).nodes


# ── CLI ─────────────────────────────────────────────────────────────────────
def test_cli_extractor_nests_subcommands_under_their_group(ctx):
    source = '''import click


@click.group("brain")
def brain_cmd():
    """Group help."""


@brain_cmd.command("sync")
@click.option("--full", is_flag=True)
def sync(full):
    """Sync help."""
'''
    result = CliExtractor().extract("cli/brain.py", source, ctx)
    titles = {n.title for n in result.nodes if n.kind == KIND_CLI_COMMAND}
    assert titles == {"brain", "brain sync"}
    sub = next(n for n in result.nodes if n.title == "brain sync")
    assert sub.attrs["options"] == ["--full"]
    # Ids slugify whitespace, so the group→subcommand edge lands on
    # ``cli_command:brain-sync``.
    assert any(e.kind == EDGE_CONTAINS and e.dst == "cli_command:brain-sync" for e in result.edges)


# ── Frontend ────────────────────────────────────────────────────────────────
def test_frontend_extractor_maps_components_and_relative_imports(ctx):
    source = """
import { Card } from '../ui/Card';
import helper from './helper';

export const Widget: React.FC = () => null;
export function Sidebar() { return null; }
"""
    result = FrontendExtractor().extract("src/views/Widget.tsx", source, ctx)
    component = next(n for n in result.nodes if n.kind == KIND_COMPONENT)
    assert component.title == "Widget"
    assert {"src/ui/Card", "src/views/helper"} == hints(result, EDGE_IMPORTS)
    assert "Sidebar" in {n.title for n in result.nodes}


def test_frontend_extractor_resolves_api_base_interpolation(ctx):
    source = """
export const API_BASE = '/api/v1';

export async function getRun(id) {
  return fetch(`${API_BASE}/runs/${id}`);
}
export async function ping() {
  return fetch('/api/v1/health');
}
export async function unknownBase() {
  return fetch(`${SOMETHING_ELSE}/nope`);
}
"""
    result = FrontendExtractor().extract("src/lib/api.ts", source, ctx)
    calls = hints(result, EDGE_CALLS)
    assert "/api/v1/runs/{}" in calls
    assert "/api/v1/health" in calls
    assert not any("nope" in call for call in calls)


def test_frontend_extractor_ignores_imports_quoted_inside_template_literals(ctx):
    # The dashboard's pipeline mock embeds a *sample* of generated test code in
    # a backtick string. Those are quotations, not this file's dependencies.
    source = """
import { real } from './real-module';

export const SAMPLE = `
import { client } from '../clients/api';
test('x', async () => {});
`;
"""
    result = FrontendExtractor().extract("src/mocks.ts", source, ctx)
    assert hints(result, EDGE_IMPORTS) == {"src/real-module"}


def test_frontend_extractor_still_reads_api_paths_inside_template_literals(ctx):
    # The same blanking must not hide real call sites, which are template
    # literals by construction.
    source = """
const API_BASE = '/api/v1';
fetch(`${API_BASE}/runs`);
"""
    result = FrontendExtractor().extract("src/api.ts", source, ctx)
    assert "/api/v1/runs" in hints(result, EDGE_CALLS)


def test_frontend_extractor_ignores_package_imports(ctx):
    result = FrontendExtractor().extract("src/a.ts", "import React from 'react';\n", ctx)
    assert not hints(result, EDGE_IMPORTS)


# ── Docs ────────────────────────────────────────────────────────────────────
def test_docs_extractor_reads_links_wikilinks_and_code_mentions(ctx):
    source = """# Title

Intro sentence.

See [the guide](guides/setup.md) and [[Another Note]].
The handler lives in `cherenkov.web.api` and `docs/other.py`.
"""
    result = DocsExtractor().extract("docs/index.md", source, ctx)
    doc = result.nodes[0]
    assert doc.kind == KIND_DOC
    assert doc.title == "Title"
    assert doc.summary == "Intro sentence."
    assert {"docs/guides/setup.md", "Another Note"} == hints(result, EDGE_LINKS)
    assert {"cherenkov.web.api", "docs/other.py"} <= hints(result, EDGE_MENTIONS)


def test_docs_extractor_ignores_regexes_that_look_like_markdown_links(ctx):
    source = "Names match [a-zA-Z0-9._-]*(x) in the parser.\n"
    result = DocsExtractor().extract("docs/spec.md", source, ctx)
    assert not hints(result, EDGE_LINKS)


def test_docs_extractor_ignores_fenced_code(ctx):
    source = "# T\n\n```\n[link](inside/code.md)\n```\n"
    result = DocsExtractor().extract("docs/t.md", source, ctx)
    assert not hints(result, EDGE_LINKS)


def test_docs_extractor_ignores_link_syntax_quoted_in_inline_code(ctx):
    source = "# T\n\nObsidian writes them as `[[Some Note]]` and `[label](target.md)`.\n"
    result = DocsExtractor().extract("docs/t.md", source, ctx)
    assert not hints(result, EDGE_LINKS)


def test_docs_extractor_still_reads_code_paths_in_backticks(ctx):
    source = "# T\n\nSee `cherenkov/web/api.py`.\n"
    result = DocsExtractor().extract("docs/t.md", source, ctx)
    assert "cherenkov/web/api.py" in hints(result, EDGE_MENTIONS)


def test_docs_extractor_marks_adr_paths(ctx):
    result = DocsExtractor().extract("docs/adr/ADR-006-thing.md", "# ADR 6\n", ctx)
    assert "adr" in result.nodes[0].tags


# ── Tests layer ─────────────────────────────────────────────────────────────
def test_tests_extractor_emits_edges_only(ctx):
    source = "from cherenkov.web import api\n\n\ndef test_it():\n    assert api\n"
    result = TestsExtractor().extract("tests/unit/test_api.py", source, ctx)
    assert result.nodes == []
    assert "cherenkov.web" in hints(result, EDGE_TESTS)
    # The filename convention contributes a lower-weight guess.
    assert "api" in hints(result, EDGE_TESTS)
    assert all(e.attrs.get("soft") for e in result.edges)


def test_tests_extractor_claims_spec_files(ctx):
    extractor = TestsExtractor()
    assert extractor.claims("ui/tests/thing.spec.ts")
    assert extractor.claims("tests/test_x.py")
    assert not extractor.claims("src/index.ts")
