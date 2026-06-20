"""
cherenkov/core/budget.py — Per-run LLM cost budget enforcement.

Tracks accumulated inference cost across a pipeline run and raises
BudgetExceededError before submitting requests that would breach the cap.

Usage:
    from cherenkov.core.budget import RunBudget

    budget = RunBudget(cap_usd=0.10)       # 10 cents per verify run
    budget.charge(cost_usd=0.02, tokens=1200, model="gpt-4o-mini")
    budget.charge(cost_usd=0.05, ...)      # fine
    budget.charge(cost_usd=0.05, ...)      # raises BudgetExceededError

Integration with substrate (cherenkov/substrate/):
    Each substrate provider calls budget.pre_check(estimated_cost) before
    dispatching a request, and budget.charge(actual_cost) after.

Environment override:
    CHERENKOV_BUDGET_USD — float, replaces cap_usd at runtime.
    CHERENKOV_BUDGET_WARN_USD — float, emit a warning log at this threshold.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Callable

_log = logging.getLogger(__name__)

_ENV_CAP = "CHERENKOV_BUDGET_USD"
_ENV_WARN = "CHERENKOV_BUDGET_WARN_USD"

# Sentinel: no cap enforced
_NO_CAP = float("inf")


class BudgetExceededError(Exception):
    """Raised when an inference request would exceed the run budget."""

    def __init__(self, spent: float, cap: float, requested: float) -> None:
        self.spent = spent
        self.cap = cap
        self.requested = requested
        super().__init__(
            f"Budget exceeded: ${spent:.4f} already spent + ${requested:.4f} requested "
            f"> ${cap:.4f} cap. Set CHERENKOV_BUDGET_USD to increase or disable."
        )


@dataclass
class _ChargeRecord:
    model: str
    provider: str
    cost_usd: float
    tokens: int
    cache_hit: bool = False
    org_id: str = "default"
    run_id: str = ""


@dataclass
class RunBudget:
    """Thread-safe per-run cost accumulator with a hard cap.

    Args:
        cap_usd: Maximum USD spend for this run. ``None`` or ``0.0`` means
            no cap (unlimited). Overridden by ``CHERENKOV_BUDGET_USD`` env var.
        warn_fraction: Emit a WARNING log when spend crosses this fraction of
            the cap (default 0.80 = 80 %).
        on_warn: Optional callback called once when the warn threshold is crossed.
    """

    cap_usd: float | None = None
    warn_fraction: float = 0.80
    on_warn: Callable[[float, float], None] | None = None

    _spent: float = field(default=0.0, init=False, repr=False)
    _records: list[_ChargeRecord] = field(default_factory=list, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _warned: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        env_cap = os.getenv(_ENV_CAP)
        if env_cap:
            try:
                self.cap_usd = float(env_cap)
            except ValueError:
                _log.warning("Invalid %s value %r — ignoring", _ENV_CAP, env_cap)

        env_warn = os.getenv(_ENV_WARN)
        if env_warn:
            try:
                warn_val = float(env_warn)
                cap = self._effective_cap()
                if cap != _NO_CAP and cap > 0:
                    self.warn_fraction = warn_val / cap
            except ValueError:
                pass

    def _effective_cap(self) -> float:
        if not self.cap_usd:
            return _NO_CAP
        return self.cap_usd

    @property
    def spent(self) -> float:
        with self._lock:
            return self._spent

    @property
    def remaining(self) -> float:
        cap = self._effective_cap()
        with self._lock:
            return max(0.0, cap - self._spent)

    def pre_check(self, estimated_cost_usd: float) -> None:
        """Raise BudgetExceededError if *estimated_cost_usd* would breach the cap.

        Call before dispatching an inference request.
        """
        cap = self._effective_cap()
        if cap == _NO_CAP:
            return
        with self._lock:
            if self._spent + estimated_cost_usd > cap:
                raise BudgetExceededError(
                    spent=self._spent,
                    cap=cap,
                    requested=estimated_cost_usd,
                )

    def charge(
        self,
        cost_usd: float,
        tokens: int = 0,
        model: str = "unknown",
        provider: str = "unknown",
        cache_hit: bool = False,
        org_id: str = "default",
        run_id: str = "",
    ) -> None:
        """Record actual post-request cost.

        Args:
            cost_usd: Actual USD charged for this inference request.
            tokens: Total tokens consumed (prompt + completion).
            model: Model identifier string.
            provider: Provider name (openai, anthropic, ollama, …).
            cache_hit: Whether the response was served from provider cache.
            org_id: Organisation identifier for cost attribution (enterprise).
            run_id: Run/session identifier for per-run breakdown.
        """
        cap = self._effective_cap()
        with self._lock:
            self._spent += cost_usd
            self._records.append(
                _ChargeRecord(
                    model=model,
                    provider=provider,
                    cost_usd=cost_usd,
                    tokens=tokens,
                    cache_hit=cache_hit,
                    org_id=org_id,
                    run_id=run_id,
                )
            )
            spent = self._spent

        # Warn at threshold (outside lock to avoid deadlock in callback)
        if cap != _NO_CAP and not self._warned and spent >= cap * self.warn_fraction:
            self._warned = True
            _log.warning(
                "Budget warning: $%.4f of $%.4f cap spent (%.0f%%)",
                spent,
                cap,
                (spent / cap) * 100,
            )
            if self.on_warn:
                self.on_warn(spent, cap)

    def summary(self) -> dict:
        """Return a structured cost summary for reports / observability."""
        with self._lock:
            cap = self._effective_cap()
            records = list(self._records)
            spent = self._spent

        by_model: dict[str, dict] = {}
        by_org: dict[str, dict] = {}
        for r in records:
            key = f"{r.provider}/{r.model}"
            if key not in by_model:
                by_model[key] = {"requests": 0, "tokens": 0, "cost_usd": 0.0, "cache_hits": 0}
            by_model[key]["requests"] += 1
            by_model[key]["tokens"] += r.tokens
            by_model[key]["cost_usd"] += r.cost_usd
            if r.cache_hit:
                by_model[key]["cache_hits"] += 1

            org = r.org_id or "default"
            if org not in by_org:
                by_org[org] = {"requests": 0, "tokens": 0, "cost_usd": 0.0}
            by_org[org]["requests"] += 1
            by_org[org]["tokens"] += r.tokens
            by_org[org]["cost_usd"] += r.cost_usd

        return {
            "spent_usd": spent,
            "cap_usd": None if cap == _NO_CAP else cap,
            "remaining_usd": None if cap == _NO_CAP else max(0.0, cap - spent),
            "utilization_pct": None if cap == _NO_CAP else round((spent / cap) * 100, 1),
            "total_requests": len(records),
            "total_tokens": sum(r.tokens for r in records),
            "cache_hits": sum(1 for r in records if r.cache_hit),
            "by_model": by_model,
            "by_org": by_org,
        }

    def reset(self) -> None:
        """Reset accumulated spend (useful for test isolation)."""
        with self._lock:
            self._spent = 0.0
            self._records.clear()
            self._warned = False


# ── Module-level default budget (shared across a process, e.g. CLI run) ─────
_default_budget: RunBudget | None = None
_budget_lock = threading.Lock()


def get_run_budget() -> RunBudget:
    """Return the process-wide RunBudget, creating it from env vars if needed."""
    global _default_budget
    with _budget_lock:
        if _default_budget is None:
            _default_budget = RunBudget()
        return _default_budget


def reset_run_budget() -> None:
    """Reset the process-wide RunBudget (call at the start of each CLI run)."""
    global _default_budget
    with _budget_lock:
        _default_budget = RunBudget()
