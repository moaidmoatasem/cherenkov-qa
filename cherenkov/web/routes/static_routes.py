import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["static"])

_ui_dist = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")


@router.get("/")
async def serve_index():
    index = os.path.join(_ui_dist, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "UI not built. Run `npm run build` in cherenkov/web/ui/."}


@router.get("/assets/{path:path}")
async def serve_assets(path: str):
    asset = os.path.join(_ui_dist, "assets", path)
    if os.path.exists(asset):
        return FileResponse(asset)
    raise HTTPException(status_code=404, detail="Asset not found")
