"""
CHERENKOV ai/accounting.py — per-request cost & latency accounting.
Authority: v3.1 + delta. E1-5.
"""
from __future__ import annotations

from cherenkov.core.contracts import CostEntry, AccountingReport, CacheStats


def _estimate_tokens(text: object) -> int:
    """Approximate token count from response payload.

    Uses ~4 characters per token as a rough heuristic for code and JSON output.
    For Ollama the actual eval_count should be preferred when available.
    """
    raw = str(text)
    return max(1, len(raw) // 4)


_COST_PER_TOKEN = {
    "ollama": 0.0,
    "openai": 0.000015,
    "anthropic": 0.00003,
}


class CostAccountant:
    """Tracks cost and latency per inference request, aggregated per run.

    Records each call (cache-hit or cache-miss) with duration, token estimate,
    and computed cost. Provides a summary AccountingReport on demand.
    """

    def __init__(self) -> None:
        self._entries: list[CostEntry] = []

    def record(
        self,
        model: str,
        duration_ms: int,
        tokens: int = 0,
        cache_hit: bool = False,
        provider: str = "ollama",
    ) -> None:
        cost_per_token = _COST_PER_TOKEN.get(provider, 0.0)
        cost = 0.0 if cache_hit else tokens * cost_per_token
        self._entries.append(
            CostEntry(
                model=model,
                provider=provider,
                duration_ms=duration_ms,
                tokens=tokens,
                cost=round(cost, 6),
                cache_hit=cache_hit,
            )
        )

    def record_json(
        self,
        model: str,
        duration_ms: int,
        output: dict,
        cache_hit: bool = False,
        provider: str = "ollama",
    ) -> None:
        import json as _json
        tokens = _estimate_tokens(_json.dumps(output, default=str))
        self.record(model, duration_ms, tokens, cache_hit, provider)

    def record_code(
        self,
        model: str,
        duration_ms: int,
        output: str,
        cache_hit: bool = False,
        provider: str = "ollama",
    ) -> None:
        tokens = _estimate_tokens(output)
        self.record(model, duration_ms, tokens, cache_hit, provider)

    @property
    def report(self) -> AccountingReport:
        entries = list(self._entries)
        return AccountingReport(
            entries=entries,
            total_duration_ms=sum(e.duration_ms for e in entries),
            total_tokens=sum(e.tokens for e in entries),
            total_cost=round(sum(e.cost for e in entries), 6),
            request_count=len(entries),
        )

    def clear(self) -> None:
        self._entries.clear()

    def get_governance_kpis(self) -> dict[str, float | int]:
        from cherenkov.reflector.store import VerdictStore
        from cherenkov.core.contracts import VerdictOutcome
        import sqlite3

        store = VerdictStore()
        db_path = store.db_path
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT outcome, COUNT(*) FROM verdicts GROUP BY outcome")
            counts = dict(cursor.fetchall())
        except sqlite3.OperationalError:
            counts = {}
        finally:
            conn.close()

        accepts = counts.get(VerdictOutcome.ACCEPT.value, 0)
        rejects = counts.get(VerdictOutcome.REJECT.value, 0)
        escaped = counts.get(VerdictOutcome.ESCAPED_DEFECT.value, 0)
        
        total = accepts + rejects + escaped
        total_skeptic = accepts + rejects

        false_positive_rate = (rejects / total_skeptic) if total_skeptic > 0 else 0.0
        maintenance_efficiency = ((accepts + escaped) / total) if total > 0 else 1.0

        return {
            "defect_escape_count": escaped,
            "false_positive_rate": round(false_positive_rate, 4),
            "maintenance_efficiency": round(maintenance_efficiency, 4),
            "total_verdicts": total,
        }

