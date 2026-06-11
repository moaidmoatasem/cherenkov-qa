from __future__ import annotations

import logging
from typing import Any, Callable

from cherenkov.chat.guard import get_guard

logger = logging.getLogger(__name__)

_guard = get_guard()


@_guard.wrap_tool(name="query_verdicts")
def query_verdicts(endpoint: str | None = None, status_code: int | None = None, limit: int = 10) -> dict[str, Any]:
    try:
        from cherenkov.reflector.reflector import get_reflector
        r = get_reflector()
        stats = r.get_stats()
        return {"verdicts": stats.get("recent_verdicts", [])[:limit], "total": stats.get("total_verdicts", 0)}
    except Exception as e:
        logger.error("query_verdicts failed", exc_info=e)
        return {"error": str(e), "verdicts": []}


@_guard.wrap_tool(name="query_idioms")
def query_idioms(pattern: str | None = None, limit: int = 10) -> dict[str, Any]:
    try:
        from cherenkov.reflector.reflector import get_reflector
        r = get_reflector()
        stats = r.get_stats()
        return {"idioms": stats.get("recent_idioms", [])[:limit], "total": stats.get("total_idioms", 0)}
    except Exception as e:
        logger.error("query_idioms failed", exc_info=e)
        return {"error": str(e), "idioms": []}


@_guard.wrap_tool(name="explain_divergence")
def explain_divergence(endpoint: str, method: str = "GET") -> dict[str, Any]:
    try:
        from cherenkov.knowledge.graph_rag import GraphRAG
        from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
        repo = SQLiteKnowledgeRepository()
        graph = GraphRAG(repo)
        result = graph.explain_divergence(endpoint, method)
        return result.data
    except Exception as e:
        logger.error("explain_divergence failed: endpoint=%s method=%s", endpoint, method, exc_info=e)
        return {"error": str(e)}


@_guard.wrap_tool(name="run_test")
def run_test(endpoint: str, method: str = "GET", spec_path: str | None = None) -> dict[str, Any]:
    try:
        from cherenkov.stages.ingest import IngestStage
        from cherenkov.stages.plan import PlanStage
        import os
        effective_spec = spec_path or "stub/openapi.yaml"
        if not os.path.exists(effective_spec):
            return {"error": f"Spec file not found: {effective_spec}", "status": "error"}
        ingest = IngestStage("chat-tool").run(effective_spec)
        plan = PlanStage("chat-tool").run(ingest)
        matching = [s for s in plan.scenarios if s.endpoint == endpoint and s.method == method]
        return {
            "status": "planned",
            "endpoint": endpoint,
            "method": method,
            "scenarios": len(matching),
            "total_scenarios": len(plan.scenarios),
            "note": "Use the full pipeline to execute. This tool only plans scenarios for the given endpoint.",
        }
    except Exception as e:
        logger.error("run_test failed: endpoint=%s method=%s", endpoint, method, exc_info=e)
        return {"error": str(e), "status": "error"}


TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "query_verdicts": query_verdicts,
    "query_idioms": query_idioms,
    "explain_divergence": explain_divergence,
    "run_test": run_test,
}


def execute_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return {"error": f"Unknown tool '{name}'"}
    guard_result = _guard.check_tool_call(name, kwargs)
    if not guard_result.allowed:
        return {"error": guard_result.reason, "guard": guard_result.to_dict(), "tool": name}
    result = tool(**kwargs)
    _guard.record_tool_call(name, kwargs, result)
    return result
