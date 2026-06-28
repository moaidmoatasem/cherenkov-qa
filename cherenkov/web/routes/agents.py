"""API routes for Multi-Agent Conductor SSE streams (CC-2)."""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from cherenkov.mcp.mesh_router import get_registry

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
_log = logging.getLogger(__name__)


async def event_generator() -> AsyncGenerator[str, None]:
    """Generate SSE events for agent status updates.

    In a real implementation, this would yield events from an EventBus.
    For now, it polls the MCPRegistry to yield active server status.
    """
    registry = get_registry()
    while True:
        # Simulate an event stream by polling registry status periodically
        try:
            servers = registry.get_all_servers()
            # We wrap it in SSE format
            payload = {
                "active_agents": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "status": s.status,
                        "tools": s.supported_tools,
                    }
                    for s in servers
                ]
            }
            yield f"data: {json.dumps(payload)}\n\n"
        except Exception as e:
            _log.error("Error in SSE stream: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        await asyncio.sleep(2.0)


@router.get("/stream")
async def stream_agent_status() -> StreamingResponse:
    """SSE endpoint for real-time agent status."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )
