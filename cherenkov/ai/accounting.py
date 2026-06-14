"""
CHERENKOV ai/accounting.py — per-request cost & latency accounting.
Authority: v3.1 + delta. E1-5.
"""

from __future__ import annotations

from cherenkov.core.contracts import CostEntry, AccountingReport


def _estimate_tokens(text: object) -> int:
    """Approximate token count from response payload (~4 chars per token)."""
    return max(1, len(str(text)) // 4)


_COST_PER_TOKEN = {
    "ollama": 0.0,
    "openai": 0.000015,
    "anthropic": 0.00003,
}


class CostAccountant:
    """Tracks cost and latency per inference request, aggregated per run.

    Records each call (cache-hit or cache-miss) with duration, token estimate,
    and computed cost. Provides a summary AccountingReport on demand.

    Optionally persists every record to TokenMonitor for cross-run analytics.
    Pass monitor=None (default) to keep behaviour purely in-memory.
    """

    def __init__(self, monitor=None) -> None:
        self._entries: list[CostEntry] = []
        self._monitor = (
            monitor  # TokenMonitor | None — injected to avoid hard import cycle
        )

    def record(
        self,
        model: str,
        duration_ms: int,
        tokens: int = 0,
        cache_hit: bool = False,
        provider: str = "ollama",
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        stage: str = "",
        run_id: str = "",
        reprompts: int = 0,
    ) -> None:
        # Use split counts when available; fall back to total estimate
        if prompt_tokens or completion_tokens:
            actual_tokens = prompt_tokens + completion_tokens
        else:
            actual_tokens = tokens or 0

        from cherenkov.observability.token_monitor import compute_cost

        if prompt_tokens or completion_tokens:
            cost = (
                0.0
                if cache_hit
                else compute_cost(provider, model, prompt_tokens, completion_tokens)
            )
        else:
            cost_per_token = _COST_PER_TOKEN.get(provider, 0.0)
            cost = 0.0 if cache_hit else actual_tokens * cost_per_token

        self._entries.append(
            CostEntry(
                model=model,
                provider=provider,
                duration_ms=duration_ms,
                tokens=actual_tokens,
                cost=round(cost, 8),
                cache_hit=cache_hit,
            )
        )

        if self._monitor is not None and not cache_hit:
            from cherenkov.observability.token_monitor import TokenRecord

            self._monitor.record(
                TokenRecord(
                    run_id=run_id or "unknown",
                    model=model,
                    provider=provider,
                    stage=stage,
                    prompt_tokens=prompt_tokens or (actual_tokens // 2),
                    completion_tokens=completion_tokens or (actual_tokens // 2),
                    total_tokens=actual_tokens,
                    cost_usd=round(cost, 8),
                    cache_hit=cache_hit,
                    reprompts=reprompts,
                )
            )

    def record_json(
        self,
        model: str,
        duration_ms: int,
        output: dict,
        cache_hit: bool = False,
        provider: str = "ollama",
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        stage: str = "",
        run_id: str = "",
        reprompts: int = 0,
    ) -> None:
        import json as _json

        estimated = _estimate_tokens(_json.dumps(output, default=str))
        self.record(
            model,
            duration_ms,
            tokens=estimated,
            cache_hit=cache_hit,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            stage=stage,
            run_id=run_id,
            reprompts=reprompts,
        )

    def record_code(
        self,
        model: str,
        duration_ms: int,
        output: str,
        cache_hit: bool = False,
        provider: str = "ollama",
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        stage: str = "",
        run_id: str = "",
        reprompts: int = 0,
    ) -> None:
        estimated = _estimate_tokens(output)
        self.record(
            model,
            duration_ms,
            tokens=estimated,
            cache_hit=cache_hit,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            stage=stage,
            run_id=run_id,
            reprompts=reprompts,
        )

    @property
    def report(self) -> AccountingReport:
        entries = list(self._entries)
        return AccountingReport(
            entries=entries,
            total_duration_ms=sum(e.duration_ms for e in entries),
            total_tokens=sum(e.tokens for e in entries),
            total_cost=round(sum(e.cost for e in entries), 8),
            request_count=len(entries),
        )

    def clear(self) -> None:
        self._entries.clear()

    def get_governance_kpis(self) -> dict[str, float | int]:
        from cherenkov.reflector.store import VerdictStore
        from cherenkov.core.contracts import VerdictOutcome

        store = VerdictStore()
        conn = store._connect()

        try:
            cursor = conn.execute(
                "SELECT outcome, COUNT(*) FROM verdicts GROUP BY outcome"
            )
            counts = dict(cursor.fetchall())
        except Exception:
            counts = {}

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
