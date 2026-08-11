"""FastAPI routes for serving static frontend UI bundle and SPA fallback."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["static"])

_ui_dist = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "ui", "dist"))


def _resolve_within_dist(*parts: str) -> str | None:
    """Resolve a client-supplied path inside the built UI directory.

    Returns the real path, or None when it escapes `_ui_dist` (``..``
    segments, absolute paths, symlinks pointing outside).
    """
    candidate = os.path.realpath(os.path.join(_ui_dist, *parts))
    if candidate != _ui_dist and not candidate.startswith(_ui_dist + os.sep):
        return None
    return candidate


@router.get("/")
async def serve_index():
    """Serve the root dashboard index.html page or build status message.

    Returns:
        FileResponse containing index.html or dictionary build instruction message.
    """
    index = os.path.join(_ui_dist, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "UI not built. Run `npm run build` in cherenkov/web/ui/."}


@router.get("/assets/{path:path}")
async def serve_assets(path: str):
    """Serve static asset files (JS, CSS, images) from the UI build directory.

    Args:
        path: Relative asset file path string.

    Returns:
        FileResponse containing requested static asset.

    Raises:
        HTTPException: 404 Not Found if asset path does not exist or escapes distribution root.
    """
    asset = _resolve_within_dist("assets", path)
    if asset and os.path.isfile(asset):
        return FileResponse(asset)
    raise HTTPException(status_code=404, detail="Asset not found")


@router.get("/{full_path:path}")
async def serve_spa_fallback(full_path: str):
    """Fallback route for SPA client-side routing.

    Args:
        full_path: Requested URL path string.

    Returns:
        FileResponse containing static file or index.html fallback, or JSON status dictionary.

    Raises:
        HTTPException: 404 Not Found if path starts with 'api/'.
    """
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    file_path = _resolve_within_dist(full_path)
    if file_path and os.path.isfile(file_path):
        return FileResponse(file_path)

    index = os.path.join(_ui_dist, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "UI not built. Run `npm run build` in cherenkov/web/ui/."}
