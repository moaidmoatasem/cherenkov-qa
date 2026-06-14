"""
cherenkov/execution/demo_mode.py

Provides a demo path that produces real-looking findings (cached from generate+validate on the bundled petstore)
without requiring a GPU or Ollama instance. This allows the Horizon V review UI to be demonstrated purely on cached data.
"""

from __future__ import annotations

import logging
from cherenkov.hitl.store import HitlQueue
from cherenkov.hitl.contracts import HitlItem

logger = logging.getLogger(__name__)

MOCK_FINDINGS = [
    {
        "id": "demo-hitl-1",
        "endpoint": "POST /pets",
        "method": "POST",
        "mutation_id": "mut_missing_name",
        "status": "pending",
        "diff": "- Expected 400 Bad Request\n+ Received 201 Created",
        "rationale": "Spec dictates name is required for POST /pets, but the server accepted a request without it.",
    },
    {
        "id": "demo-hitl-2",
        "endpoint": "GET /pets/{petId}",
        "method": "GET",
        "mutation_id": "mut_invalid_id",
        "status": "pending",
        "diff": "- Expected 404 Not Found\n+ Received 400 Bad Request",
        "rationale": "Spec says invalid petId format should be 400, but an unknown valid-format petId should be 404. Server returned 400 for unknown valid id.",
    },
    {
        "id": "demo-hitl-3",
        "endpoint": "POST /pets",
        "method": "POST",
        "mutation_id": "mut_extra_fields",
        "status": "pending",
        "diff": "- Expected 201 Created\n+ Received 500 Internal Server Error",
        "rationale": "Spec allows extra properties, but server crashed with 500 when extra fields were sent.",
    },
]


def generate_demo_findings() -> None:
    """Populates the HITL queue with cached demo findings."""
    queue = HitlQueue()
    logger.info("Demo mode engaged: inserting cached findings into HITL queue.")

    for mf in MOCK_FINDINGS:
        # Instead of directly messing with SQL, use the HitlQueue enqueue method if possible,
        # but since we mock, let's just use raw enqueue.
        try:
            item = HitlItem(
                id=mf["id"],
                endpoint=mf["endpoint"],
                method=mf["method"],
                mutation_id=mf["mutation_id"],
                diff=mf["diff"],
                rationale=mf["rationale"],
            )
            queue.enqueue(item)
            logger.info(f"Enqueued demo item {mf['id']}")
        except Exception as e:
            logger.error(f"Failed to enqueue demo item {mf['id']}: {e}")
