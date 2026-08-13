"""End-to-end tests for the brain map engine, store, reconciler and exporters.

Every test builds a small real project on disk and runs the real pipeline over
it. Nothing here mocks the store or the walker: incremental sync and vault
pruning are exactly the behaviours that only fail against a real filesystem.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cherenkov.brainmap.adapters.json_export import graph_payload
from cherenkov.brainmap.adapters.obsidian_vault import GENERATED_KEY, MANIFEST_NAME, ObsidianVaultExporter
from cherenkov.brainmap.adapters.sqlite_store import SQLiteBrainMapStore
from cherenkov.brainmap.config import load_profile
from cherenkov.brainmap.domain.models import (
    BrainMap,
    Edge,
    ExtractionResult,
    Node,
    dedupe_edges,
    make_id,
)
from cherenkov.brainmap.extractors.base import (
    BUILTIN_EXTRACTORS,
    _REGISTRY,
    build_extractors,
    register,
    registered_names,
)
from cherenkov.brainmap.reconcile import ReconcileOptions, Reconciler, diff_maps
from cherenkov.brainmap.use_cases.sync import build_engine


class ShoutExtractor:
    """A minimal out-of-tree extractor, used to prove the extension path."""

    name = "shout"

    def claims(self, rel_path: str) -> bool:
        """Claim nothing — this exists only to be loaded."""
        return False

    def extract(self, rel_path: str, text: str, ctx) -> ExtractionResult:
        """Return nothing; loading is the behaviour under test."""
        return ExtractionResult()

APP_PY = '''"""The service."""
from fastapi import APIRouter

from app.store import Store

router = APIRouter(prefix="/api/v1")


@router.get("/widgets")
async def list_widgets():
    """List widgets."""
    return Store().all()
'''

STORE_PY = '''"""Persistence."""


class Store:
    """Keeps widgets."""

    def all(self):
        return []
'''

UI_TS = """
export const API_BASE = '/api/v1';

export async function listWidgets() {
  return fetch(`${API_BASE}/widgets`);
}
export async function listGhosts() {
  return fetch(`${API_BASE}/ghosts`);
}
"""

DOC_MD = """# Widgets

How widgets work.

The endpoint is served by `app.service`. See [the store notes](store.md) and [[Missing Note]].
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A miniature multi-language project on disk."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text('"""App package."""\n')
    (tmp_path / "app" / "service.py").write_text(APP_PY)
    (tmp_path / "app" / "store.py").write_text(STORE_PY)
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "api.ts").write_text(UI_TS)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "widgets.md").write_text(DOC_MD)
    (tmp_path / "docs" / "store.md").write_text("# Store\n\nNotes.\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_store.py").write_text("from app.store import Store\n\n\ndef test_all():\n    assert Store().all() == []\n")
    return tmp_path


def engine_for(root: Path):
    """Build an engine whose store lives inside the temp project."""
    return build_engine(root, {"db_path": str(root / ".brainmap" / "map.db")})


# ── build & incremental sync ────────────────────────────────────────────────
def test_build_maps_every_layer(project: Path):
    report = engine_for(project).sync(full=True)
    by_kind = report.stats["by_kind"]

    assert by_kind["module"] >= 2
    assert by_kind["route"] == 1
    assert by_kind["doc"] == 2
    assert by_kind["test"] == 1
    assert by_kind["class"] >= 1
    assert report.parsed == report.scanned


def test_sync_reparses_only_changed_files(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)

    unchanged = engine.sync()
    assert unchanged.parsed == 0
    assert unchanged.skipped == unchanged.scanned

    (project / "app" / "store.py").write_text(STORE_PY + "\n\nclass Cache:\n    pass\n")
    changed = engine.sync()
    assert changed.parsed == 1
    assert "class:app.store.Cache" in engine.graph().nodes


def test_sync_forgets_deleted_files(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    assert "module:app.store" in engine.graph().nodes

    (project / "app" / "store.py").unlink()
    report = engine.sync()

    assert report.removed == 1
    assert "module:app.store" not in engine.graph().nodes


def test_sync_reports_a_delta_when_asked(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    (project / "app" / "extra.py").write_text('"""Extra."""\n')

    report = engine.sync(with_delta=True)

    assert report.delta["empty"] is False
    assert "module:app.extra" in report.delta["added_nodes"]
    assert "app/extra.py" in report.delta["changed_files"]


def test_profile_excludes_are_honoured(project: Path):
    (project / "vendor").mkdir()
    (project / "vendor" / "huge.py").write_text("x = 1\n")
    engine = build_engine(
        project, {"db_path": str(project / ".brainmap" / "map.db"), "excludes": ["vendor/**"]}
    )
    engine.sync(full=True)
    assert "module:vendor.huge" not in engine.graph().nodes


# ── reconciliation ──────────────────────────────────────────────────────────
def test_reconciler_joins_the_frontend_to_the_backend_route(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    map_ = engine.graph()
    route_id = make_id("route", "GET /api/v1/widgets")

    calls = [e for e in map_.edges if e.kind == "calls"]
    assert any(e.dst == route_id for e in calls)


def test_reconciler_reports_a_ui_call_with_no_route(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    codes = {f.code for f in engine.graph().findings}
    ghost = [f for f in engine.graph().findings if f.code == "ui_calls_missing_route"]

    assert "ui_calls_missing_route" in codes
    assert any("/api/v1/ghosts" in f.detail.get("path", "") for f in ghost)


def test_reconciler_reports_a_wikilink_to_nothing(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    dangling = [f for f in engine.graph().findings if f.code == "dangling_link"]
    assert any("Missing Note" in f.message for f in dangling)


def test_reconciler_does_not_report_links_to_unmapped_but_real_files(project: Path):
    (project / "run.sh").write_text("echo hi\n")
    (project / "docs" / "widgets.md").write_text(DOC_MD + "\nRun [the script](../run.sh).\n")
    engine = engine_for(project)
    engine.sync(full=True)

    assert not any("run.sh" in f.message for f in engine.graph().findings)


def test_reconciler_keeps_stdlib_out_of_the_map(project: Path):
    (project / "app" / "uses_stdlib.py").write_text("import json\nimport os\n")
    engine = engine_for(project)
    engine.sync(full=True)
    map_ = engine.graph()

    assert "external:json" not in map_.nodes
    assert not any(f.code == "dangling_link" and "json" in f.message for f in map_.findings)


def test_reconciler_maps_third_party_dependencies(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    assert "external:fastapi" in engine.graph().nodes


def test_reconciler_can_be_told_to_skip_externals(project: Path):
    engine = build_engine(
        project,
        {"db_path": str(project / ".brainmap" / "map.db")},
        ReconcileOptions(detect_externals=False),
    )
    engine.sync(full=True)
    assert not [n for n in engine.graph().nodes if n.startswith("external:")]


def test_reconciler_links_tests_to_their_subject(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    map_ = engine.graph()

    tests_edges = [e for e in map_.edges if e.kind == "tests"]
    assert any(e.dst == "module:app.store" for e in tests_edges)
    untested = {f.node_id for f in map_.findings if f.code == "untested_module"}
    assert "module:app.store" not in untested
    assert "module:app.service" in untested


def test_reconciler_drops_edges_to_nodes_that_disappeared(project: Path):
    map_ = BrainMap(project="p")
    map_.add_node(Node(id="module:a", kind="module", title="a", tags=["python"]))
    map_.add_edge(Edge(src="module:a", kind="imports", dst="module:gone"))

    Reconciler().reconcile(map_)

    assert map_.edges == []


def test_diff_maps_names_what_moved():
    before = BrainMap(project="p")
    before.add_node(Node(id="module:a", kind="module", title="a"))
    after = BrainMap(project="p")
    after.add_node(Node(id="module:b", kind="module", title="b"))

    delta = diff_maps(before, after)

    assert delta.added_nodes == ["module:b"]
    assert delta.removed_nodes == ["module:a"]
    assert not delta.empty


def test_dedupe_edges_sums_weights():
    edges = dedupe_edges(
        [
            Edge(src="a", kind="mentions", dst="b", weight=1.0),
            Edge(src="a", kind="mentions", dst="b", weight=2.0),
            Edge(src="a", kind="imports", dst="b", weight=1.0),
        ]
    )
    assert len(edges) == 2
    assert next(e for e in edges if e.kind == "mentions").weight == 3.0


# ── store ───────────────────────────────────────────────────────────────────
def test_store_neighborhood_expands_by_depth(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)

    one_hop = engine.neighborhood("module:app.service", depth=1)
    two_hops = engine.neighborhood("module:app.service", depth=2)

    assert "module:app.store" in one_hop.nodes
    assert len(two_hops.nodes) >= len(one_hop.nodes)
    assert all(edge.dst in two_hops.nodes for edge in two_hops.edges)


def test_store_survives_a_reopen(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)

    reopened = SQLiteBrainMapStore(project / ".brainmap" / "map.db")
    map_ = reopened.load(engine.profile.project, resolved=True)

    assert map_.nodes
    assert map_.edges
    assert map_.built_at


def test_store_drop_project_clears_everything(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    engine.store.drop_project(engine.profile.project)

    assert engine.graph().nodes == {}
    assert engine.store.known_files(engine.profile.project) == {}


# ── payload shaping ─────────────────────────────────────────────────────────
def test_graph_payload_ranks_then_truncates(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    map_ = engine.graph()

    payload = graph_payload(map_, limit=3)

    assert len(payload["nodes"]) == 3
    assert payload["truncated"]["nodes_hidden"] == len(map_.nodes) - 3
    degrees = [node["degree"] for node in payload["nodes"]]
    assert degrees == sorted(degrees, reverse=True)
    assert all(edge["src"] in {n["id"] for n in payload["nodes"]} for edge in payload["edges"])


def test_graph_payload_filters_by_kind_and_query(project: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    map_ = engine.graph()

    only_routes = graph_payload(map_, kinds=["route"])
    assert {n["kind"] for n in only_routes["nodes"]} == {"route"}

    searched = graph_payload(map_, query="store")
    assert searched["nodes"]
    assert all("store" in n["title"].lower() or "store" in n["summary"].lower() for n in searched["nodes"])


# ── Obsidian vault ──────────────────────────────────────────────────────────
def test_vault_export_writes_linked_notes(project: Path, tmp_path: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    vault = tmp_path / "vault"

    summary = ObsidianVaultExporter().export(engine.graph(), vault)

    assert summary["notes_written"] == len(engine.graph().nodes)
    assert (vault / "Brain Map.md").exists()
    assert (vault / "Findings.md").exists()
    assert json.loads((vault / "Brain Map.canvas").read_text())["nodes"]

    note = next((vault / "Modules").glob("app.service.md"))
    body = note.read_text()
    assert f"{GENERATED_KEY}: true" in body
    assert "[[" in body
    assert "app/service.py" in body


def test_vault_export_prunes_notes_for_deleted_code(project: Path, tmp_path: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    vault = tmp_path / "vault"
    exporter = ObsidianVaultExporter()
    exporter.export(engine.graph(), vault)
    assert (vault / "Modules" / "app.store.md").exists()

    (project / "app" / "store.py").unlink()
    engine.sync()
    summary = exporter.export(engine.graph(), vault)

    assert not (vault / "Modules" / "app.store.md").exists()
    assert summary["stale_removed"] >= 1


def test_vault_export_never_deletes_hand_written_notes(project: Path, tmp_path: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    vault = tmp_path / "vault"
    exporter = ObsidianVaultExporter()
    exporter.export(engine.graph(), vault)

    mine = vault / "My Thoughts.md"
    mine.write_text("# My Thoughts\n\nNot generated.\n")
    adopted = vault / "Modules" / "app.store.md"
    adopted.write_text("# app.store\n\nI rewrote this by hand.\n")

    (project / "app" / "store.py").unlink()
    engine.sync()
    exporter.export(engine.graph(), vault)

    assert mine.exists()
    assert "I rewrote this by hand." in adopted.read_text()


def test_vault_manifest_records_what_was_generated(project: Path, tmp_path: Path):
    engine = engine_for(project)
    engine.sync(full=True)
    vault = tmp_path / "vault"
    ObsidianVaultExporter().export(engine.graph(), vault)

    manifest = json.loads((vault / MANIFEST_NAME).read_text())
    assert manifest["project"] == engine.profile.project
    assert "Brain Map.md" in manifest["extras"]
    assert manifest["notes"]


def test_fixture_corpora_do_not_report_broken_links(project: Path):
    # A generated-suite fixture imports a client module that only exists once
    # the suite is ejected. That is correct, not broken — but only where the
    # profile says the tree is a corpus.
    (project / "corpus").mkdir()
    (project / "corpus" / "generated.spec.ts").write_text("import { client } from './client';\n")
    (project / "app" / "real.ts").write_text("import { thing } from './missing';\n")

    engine = build_engine(
        project,
        {"db_path": str(project / ".brainmap" / "map.db"), "fixture_roots": ["corpus"]},
    )
    engine.sync(full=True)
    dangling = [f for f in engine.graph().findings if f.code == "dangling_link"]

    assert not [f for f in dangling if f.origin == "corpus/generated.spec.ts"]
    assert [f for f in dangling if f.origin == "app/real.ts"]


def test_fixture_roots_default_to_empty(project: Path):
    engine = engine_for(project)
    assert engine.profile.fixture_roots == []
    assert not engine.profile.is_fixture("anything/at/all.ts")


# ── extractor resolution ────────────────────────────────────────────────────
def test_builtin_extractors_all_resolve():
    built = build_extractors(list(BUILTIN_EXTRACTORS))
    assert len(built) == len(BUILTIN_EXTRACTORS)
    assert {e.name for e in built} == set(BUILTIN_EXTRACTORS)


def test_a_third_party_extractor_loads_from_a_dotted_spec():
    # The class is resolved by import path, so another project ships its own
    # extractor in its own package without patching this one.
    built = build_extractors(["tests.unit.test_brainmap_engine:ShoutExtractor"])

    assert len(built) == 1
    assert built[0].name == "shout"


def test_an_unresolvable_extractor_is_skipped_not_raised():
    built = build_extractors(["python", "no.such.module:Nope", "not-a-name"])
    assert [e.name for e in built] == ["python"]


def test_a_runtime_registered_extractor_wins():
    register("shout", ShoutExtractor)
    try:
        assert build_extractors(["shout"])[0].name == "shout"
        assert "shout" in registered_names()
    finally:
        _REGISTRY.pop("shout", None)


# ── profile ─────────────────────────────────────────────────────────────────
def test_profile_reads_a_brainmap_toml(tmp_path: Path):
    (tmp_path / "brainmap.toml").write_text(
        '[brainmap]\nproject = "custom"\nsymbol_depth = "module"\nexcludes = ["skip/**"]\n'
    )
    profile = load_profile(tmp_path)

    assert profile.project == "custom"
    assert profile.symbol_depth == "module"
    assert profile.is_excluded("skip/thing.py")
    # Configured excludes extend the defaults rather than replacing them.
    assert profile.is_excluded("node_modules/pkg/index.js")


def test_profile_handles_a_src_layout(tmp_path: Path):
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "__init__.py").write_text("")
    profile = load_profile(tmp_path)

    assert profile.source_roots == ["src"]
    assert profile.module_name("src/pkg/mod.py") == "pkg.mod"


def test_profile_maps_paths_to_layers(tmp_path: Path):
    profile = load_profile(tmp_path, {"layers": {"a": "one", "a/b": "two"}})
    assert profile.layer_for("a/x.py") == "one"
    assert profile.layer_for("a/b/x.py") == "two"
    assert profile.layer_for("z.py") == ""
