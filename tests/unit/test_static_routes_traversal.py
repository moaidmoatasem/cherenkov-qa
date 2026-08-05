"""Regression tests: the SPA/static routes must not serve files outside dist/."""

import asyncio
import os

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse

from cherenkov.web.routes import static_routes


@pytest.fixture()
def dist(tmp_path, monkeypatch):
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "assets" / "app.js").write_text("console.log(1)")
    (d / "index.html").write_text("<html></html>")
    (tmp_path / "secret.txt").write_text("TOP SECRET")
    monkeypatch.setattr(static_routes, "_ui_dist", str(d))
    return d


def test_asset_inside_dist_is_served(dist):
    resp = asyncio.run(static_routes.serve_assets("app.js"))
    assert isinstance(resp, FileResponse)
    assert resp.path == os.path.join(str(dist), "assets", "app.js")


@pytest.mark.parametrize(
    "path",
    ["../secret.txt", "../../secret.txt", "sub/../../../secret.txt", "/etc/passwd"],
)
def test_asset_traversal_is_rejected(dist, path):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(static_routes.serve_assets(path))
    assert exc.value.status_code == 404


@pytest.mark.parametrize("path", ["../secret.txt", "../../secret.txt", "/etc/passwd"])
def test_spa_fallback_traversal_falls_back_to_index(dist, path):
    resp = asyncio.run(static_routes.serve_spa_fallback(path))
    assert isinstance(resp, FileResponse)
    assert resp.path == os.path.join(str(dist), "index.html")


def test_resolve_within_dist(dist):
    assert static_routes._resolve_within_dist("assets", "../../etc/passwd") is None
    assert static_routes._resolve_within_dist("index.html") == os.path.join(str(dist), "index.html")
