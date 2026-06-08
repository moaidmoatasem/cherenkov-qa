from __future__ import annotations

from typing import Any


def query_verdicts(endpoint: str | None = None, status_code: int | None = None, limit: int = 10) -> dict:
    try:
        from cherenkov.reflector.reflector import get_reflector
        r = get_reflector()
        stats = r.get_stats()
        return {"verdicts": stats.get("recent_verdicts", [])[:limit], "total": stats.get("total_verdicts", 0)}
    except Exception as e:
        return {"error": str(e), "verdicts": []}


def query_idioms(pattern: str | None = None, limit: int = 10) -> dict:
    try:
        from cherenkov.reflector.reflector import get_reflector
        r = get_reflector()
        stats = r.get_stats()
        return {"idioms": stats.get("recent_idioms", [])[:limit], "total": stats.get("total_idioms", 0)}
    except Exception as e:
        return {"error": str(e), "idioms": []}


def explain_divergence(endpoint: str, method: str = "GET") -> dict:
    try:
        from cherenkov.knowledge.graph_rag import GraphRAG
        from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
        repo = SQLiteKnowledgeRepository()
        graph = GraphRAG(repo)
        result = graph.explain_divergence(endpoint, method)
        return result.data
    except Exception as e:
        return {"error": str(e)}


def run_test(endpoint: str, method: str = "GET", spec_path: str | None = None) -> dict:
    try:
        from cherenkov.core.orchestrator import Orchestrator
        o = Orchestrator()
        plan = o.create_plan(spec_path or "stub/openapi.yaml")
        result = o.run_pipeline(plan)
        return {"status": "completed" if result else "failed", "scenarios": len(plan.scenarios) if hasattr(plan, "scenarios") else 0}
    except Exception as e:
        return {"error": str(e), "status": "error"}


TOOL_REGISTRY: dict[str, callable] = {
    "query_verdicts": query_verdicts,
    "query_idioms": query_idioms,
    "explain_divergence": explain_divergence,
    "run_test": run_test,
}


def execute_tool(name: str, **kwargs) -> dict:
    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return {"error": f"Unknown tool '{name}'"}
    return tool(**kwargs)
