from __future__ import annotations

from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeQueryResult
from cherenkov.knowledge.ports.repository import KnowledgeRepository


class GraphRAG:
    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    def query(
        self, query: str, sources: list[str] | None = None, limit: int = 10
    ) -> list[KnowledgeQueryResult]:
        if sources is None:
            sources = ["verdicts", "idioms", "incidents", "hitl", "feedback", "agent_memory"]
        per_source = max(1, limit // len(sources))
        results = []
        for source in sources:
            q = KnowledgeQuery(query=query, source=source, limit=per_source)
            result = self.repository.query(q)
            if result.data:
                results.append(result)
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:limit]

    def explain_divergence(self, endpoint: str, method: str) -> KnowledgeQueryResult:
        verdicts = self.query(f"{endpoint} {method}", sources=["verdicts"], limit=5)
        idioms = self.query(f"{endpoint} {method}", sources=["idioms"], limit=5)
        incidents = self.query(f"{endpoint} {method}", sources=["incidents"], limit=5)
        explanation = {
            "endpoint": endpoint,
            "method": method,
            "verdicts": [v.data for v in verdicts],
            "idioms": [i.data for i in idioms],
            "incidents": [inc.data for inc in incidents],
        }
        return KnowledgeQueryResult(
            data=explanation,
            source="graph_rag",
            confidence=1.0,
            metadata={
                "verdicts_count": len(verdicts),
                "idioms_count": len(idioms),
                "incidents_count": len(incidents),
            },
        )
