"""HTTP tests for ``/api/v1/brainmap/*``.

The engine is swapped for one pointed at a temp project, so these tests
exercise the real routes and the real store without depending on whether the
repository's own map has been built.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cherenkov.brainmap.api import routes as brainmap_routes
from cherenkov.brainmap.use_cases.sync import build_engine
from cherenkov.web.api import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    """A client whose brain-map engine maps a two-file temp project."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "core.py").write_text('"""Core."""\n\n\nclass Engine:\n    """Runs."""\n')
    (tmp_path / "README.md").write_text("# Demo\n\nUses `pkg.core`.\n")

    engine = build_engine(tmp_path, {"db_path": str(tmp_path / ".brainmap" / "map.db")})
    engine.sync(full=True)
    monkeypatch.setattr(brainmap_routes, "_engine", lambda: engine)
    return TestClient(app)


def test_status_reports_a_built_map(client: TestClient):
    body = client.get("/api/v1/brainmap/status").json()

    assert body["exists"] is True
    assert body["stats"]["nodes"] > 0
    assert body["profile"]["extractors"]


def test_graph_returns_nodes_and_edges(client: TestClient):
    body = client.get("/api/v1/brainmap/graph?limit=10").json()

    assert body["nodes"]
    node_ids = {node["id"] for node in body["nodes"]}
    assert all(edge["src"] in node_ids and edge["dst"] in node_ids for edge in body["edges"])
    assert body["truncated"]["limit"] == 10


def test_graph_filters_by_kind(client: TestClient):
    body = client.get("/api/v1/brainmap/graph?kinds=module").json()
    assert {node["kind"] for node in body["nodes"]} == {"module"}


def test_neighborhood_returns_the_focus_node(client: TestClient):
    body = client.get("/api/v1/brainmap/neighborhood?node_id=module:pkg.core&depth=1").json()

    assert body["focus"]["id"] == "module:pkg.core"
    assert body["depth"] == 1


def test_neighborhood_404s_on_an_unknown_node(client: TestClient):
    response = client.get("/api/v1/brainmap/neighborhood?node_id=module:nope")
    assert response.status_code == 404


def test_findings_expose_facet_counts(client: TestClient):
    body = client.get("/api/v1/brainmap/findings?limit=5").json()

    assert "by_code" in body
    assert len(body["findings"]) <= 5
    assert body["total"] >= len(body["findings"])


def test_sync_runs_and_reports(client: TestClient):
    body = client.post("/api/v1/brainmap/sync?full=false&delta=false").json()

    assert body["busy"] is False
    assert body["scanned"] >= 3
    assert body["parsed"] == 0  # nothing changed since the fixture's build


def test_export_writes_the_configured_vault(client: TestClient):
    body = client.post("/api/v1/brainmap/export").json()

    assert body["notes_written"] > 0
    assert Path(body["vault"]).is_dir()
    assert (Path(body["vault"]) / "Brain Map.md").exists()
