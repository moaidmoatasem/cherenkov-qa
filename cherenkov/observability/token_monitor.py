"""
CHERENKOV observability/token_monitor.py — persistent token-consumption monitor.

Tracks prompt/completion tokens per inference call, aggregates across runs,
analyses utilisation trends, and emits actionable cost-reduction recommendations.

Supports: Ollama (free, local), OpenAI, Anthropic.
Pricing table follows provider public pricing pages (per-1K tokens, USD).
"""
from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_DB = os.path.join(".cherenkov", "token_usage.db")
_BUSY_TIMEOUT_S = 10

# ── Pricing (per 1K tokens, USD) ──────────────────────────────────────────────
# Format: {provider: {model_prefix: {input, output}}}  — longest prefix wins.
# "default" applies when no model prefix matches.

_PRICE_TABLE: dict[str, dict[str, dict[str, float]]] = {
    "ollama": {
        "default": {"input": 0.0, "output": 0.0},
    },
    "openai": {
        "gpt-4o-mini":    {"input": 0.000150, "output": 0.000600},
        "gpt-4o":         {"input": 0.005000, "output": 0.015000},
        "gpt-4-turbo":    {"input": 0.010000, "output": 0.030000},
        "gpt-3.5-turbo":  {"input": 0.000500, "output": 0.001500},
        "default":        {"input": 0.010000, "output": 0.030000},
    },
    "anthropic": {
        "claude-haiku":   {"input": 0.000250, "output": 0.001250},
        "claude-sonnet":  {"input": 0.003000, "output": 0.015000},
        "claude-opus":    {"input": 0.015000, "output": 0.075000},
        "default":        {"input": 0.003000, "output": 0.015000},
    },
}

# ── Recommendation thresholds ─────────────────────────────────────────────────
_LOW_CACHE_THRESHOLD   = 0.10   # cache hit rate below 10% → caching underused
_HIGH_PROMPT_THRESHOLD = 2_000  # avg prompt tokens per call → prompt bloat
_REPROMPT_THRESHOLD    = 0.15   # >15% calls needed a reprompt → schema issue
_GROWTH_THRESHOLD      = 0.20   # week-over-week token growth > 20%
_PAID_SPEND_THRESHOLD  = 0.05   # >$0.05 daily avg on paid provider → expensive


def _price_for(provider: str, model: str) -> dict[str, float]:
    """Return {input, output} per-1K-token pricing for a provider/model pair."""
    table = _PRICE_TABLE.get(provider.lower(), _PRICE_TABLE["openai"])
    # Longest prefix match first
    for prefix in sorted(table.keys(), key=len, reverse=True):
        if prefix == "default":
            continue
        if model.lower().startswith(prefix):
            return table[prefix]
    return table.get("default", {"input": 0.0, "output": 0.0})


def compute_cost(
    provider: str, model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """Compute cost in USD for a single inference call."""
    p = _price_for(provider, model)
    return round(
        (prompt_tokens / 1_000) * p["input"]
        + (completion_tokens / 1_000) * p["output"],
        8,
    )


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class TokenRecord:
    run_id: str
    model: str
    provider: str
    stage: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    cache_hit: bool
    reprompts: int = 0
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class TokenUsageReport:
    """Returned by TokenMonitor.get_report()."""
    period_days: int
    total_tokens: int
    total_cost_usd: float
    total_requests: int
    cache_hit_rate: float
    avg_prompt_tokens: float
    avg_completion_tokens: float
    by_provider: list[dict]          # [{provider, model, requests, tokens, cost_usd}]
    by_stage: list[dict]             # [{stage, requests, tokens, cost_usd}]
    daily_trend: list[dict]          # [{date, tokens, cost_usd}]
    recommendations: list[dict]      # [{severity, code, title, detail, action}]
    reprompt_rate: float = 0.0


# ── Monitor ───────────────────────────────────────────────────────────────────

class TokenMonitor:
    """Persistent, cross-run token consumption tracker and analyser.

    Usage:
        monitor = TokenMonitor()
        monitor.record(TokenRecord(...))
        report  = monitor.get_report(days=30)
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _DEFAULT_DB
        if self.db_path == ":memory:":
            self._mem_conn: Optional[sqlite3.Connection] = sqlite3.connect(
                ":memory:", check_same_thread=False
            )
            self._mem_conn.row_factory = sqlite3.Row
        else:
            self._mem_conn = None
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id            TEXT    NOT NULL,
                model             TEXT    NOT NULL,
                provider          TEXT    NOT NULL DEFAULT 'ollama',
                stage             TEXT    NOT NULL DEFAULT '',
                prompt_tokens     INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens      INTEGER NOT NULL DEFAULT 0,
                cost_usd          REAL    NOT NULL DEFAULT 0.0,
                cache_hit         INTEGER NOT NULL DEFAULT 0,
                reprompts         INTEGER NOT NULL DEFAULT 0,
                timestamp         INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tu_run  ON token_usage(run_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tu_ts   ON token_usage(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tu_prov ON token_usage(provider)")
        conn.commit()
        if self._mem_conn is None:
            conn.close()

    def record(self, rec: TokenRecord) -> None:
        try:
            conn = self._connect()
            conn.execute(
                "INSERT INTO token_usage "
                "(run_id, model, provider, stage, prompt_tokens, completion_tokens, "
                " total_tokens, cost_usd, cache_hit, reprompts, timestamp) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    rec.run_id, rec.model, rec.provider, rec.stage,
                    rec.prompt_tokens, rec.completion_tokens, rec.total_tokens,
                    rec.cost_usd, int(rec.cache_hit), rec.reprompts, rec.timestamp,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_report(self, days: int = 30) -> TokenUsageReport:
        since = int(time.time()) - days * 86_400
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM token_usage WHERE timestamp >= ?", (since,)
            ).fetchall()
        finally:
            if self._mem_conn is None:
                conn.close()

        if not rows:
            return TokenUsageReport(
                period_days=days, total_tokens=0, total_cost_usd=0.0,
                total_requests=0, cache_hit_rate=0.0, avg_prompt_tokens=0.0,
                avg_completion_tokens=0.0, by_provider=[], by_stage=[],
                daily_trend=[], recommendations=self._recommendations([], days),
            )

        records = [dict(r) for r in rows]
        total_tokens = sum(r["total_tokens"] for r in records)
        total_cost   = round(sum(r["cost_usd"] for r in records), 6)
        total_req    = len(records)
        cache_hits   = sum(1 for r in records if r["cache_hit"])
        total_reprompts = sum(r["reprompts"] for r in records)

        avg_prompt = sum(r["prompt_tokens"] for r in records) / total_req
        avg_completion = sum(r["completion_tokens"] for r in records) / total_req

        # by_provider / by_model breakdown
        provider_agg: dict[str, dict] = {}
        for r in records:
            key = f"{r['provider']}::{r['model']}"
            if key not in provider_agg:
                provider_agg[key] = {
                    "provider": r["provider"],
                    "model": r["model"],
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }
            agg = provider_agg[key]
            agg["requests"] += 1
            agg["prompt_tokens"] += r["prompt_tokens"]
            agg["completion_tokens"] += r["completion_tokens"]
            agg["total_tokens"] += r["total_tokens"]
            agg["cost_usd"] = round(agg["cost_usd"] + r["cost_usd"], 6)
        by_provider = sorted(
            provider_agg.values(), key=lambda x: x["cost_usd"], reverse=True
        )

        # by_stage breakdown
        stage_agg: dict[str, dict] = {}
        for r in records:
            s = r["stage"] or "unknown"
            if s not in stage_agg:
                stage_agg[s] = {
                    "stage": s, "requests": 0, "total_tokens": 0, "cost_usd": 0.0
                }
            stage_agg[s]["requests"] += 1
            stage_agg[s]["total_tokens"] += r["total_tokens"]
            stage_agg[s]["cost_usd"] = round(stage_agg[s]["cost_usd"] + r["cost_usd"], 6)
        by_stage = sorted(stage_agg.values(), key=lambda x: x["cost_usd"], reverse=True)

        # daily trend (last `days` days)
        day_agg: dict[str, dict] = {}
        for r in records:
            date = time.strftime("%Y-%m-%d", time.gmtime(r["timestamp"]))
            if date not in day_agg:
                day_agg[date] = {"date": date, "tokens": 0, "cost_usd": 0.0, "requests": 0}
            day_agg[date]["tokens"] += r["total_tokens"]
            day_agg[date]["cost_usd"] = round(
                day_agg[date]["cost_usd"] + r["cost_usd"], 6
            )
            day_agg[date]["requests"] += 1
        daily_trend = sorted(day_agg.values(), key=lambda x: x["date"])

        reprompt_rate = total_reprompts / total_req if total_req else 0.0

        recs = self._recommendations(
            records,
            days,
            cache_hit_rate=cache_hits / total_req,
            avg_prompt_tokens=avg_prompt,
            reprompt_rate=reprompt_rate,
            daily_trend=daily_trend,
        )

        return TokenUsageReport(
            period_days=days,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            total_requests=total_req,
            cache_hit_rate=round(cache_hits / total_req, 4),
            avg_prompt_tokens=round(avg_prompt, 1),
            avg_completion_tokens=round(avg_completion, 1),
            by_provider=by_provider,
            by_stage=by_stage,
            daily_trend=daily_trend,
            recommendations=recs,
            reprompt_rate=round(reprompt_rate, 4),
        )

    # ── Recommendation engine ─────────────────────────────────────────────────

    def _recommendations(
        self,
        records: list[dict],
        days: int,
        *,
        cache_hit_rate: float = 0.0,
        avg_prompt_tokens: float = 0.0,
        reprompt_rate: float = 0.0,
        daily_trend: list[dict] | None = None,
    ) -> list[dict]:
        recs: list[dict] = []

        if not records:
            recs.append({
                "severity": "info",
                "code": "NO_DATA",
                "title": "No token data yet",
                "detail": "Run cherenkov against a real server to populate token usage.",
                "action": "cherenkov validate --target <url>",
            })
            return recs

        # R1 — Cache underused
        if cache_hit_rate < _LOW_CACHE_THRESHOLD:
            recs.append({
                "severity": "warning",
                "code": "CACHE_UNDERUSED",
                "title": "Response cache hit rate is low "
                         f"({cache_hit_rate*100:.1f}%)",
                "detail": "Identical (system_prompt, user_prompt, model) tuples are "
                          "re-evaluated instead of served from cache. "
                          f"Current hit rate: {cache_hit_rate*100:.1f}% "
                          f"(threshold: {_LOW_CACHE_THRESHOLD*100:.0f}%).",
                "action": "Ensure CachedInferenceClient wraps all providers. "
                          "Set CHERENKOV_CACHE_TTL in config (default: 3600s).",
            })

        # R2 — Prompt bloat
        if avg_prompt_tokens > _HIGH_PROMPT_THRESHOLD:
            monthly_prompt_tokens = avg_prompt_tokens * len(records) * (30 / max(days, 1))
            recs.append({
                "severity": "warning",
                "code": "PROMPT_BLOAT",
                "title": f"System prompts are large "
                         f"(avg {avg_prompt_tokens:.0f} prompt tokens/call)",
                "detail": f"Average prompt is {avg_prompt_tokens:.0f} tokens. "
                          "Spec context, few-shot examples, or schema repetition "
                          "may be inflating the prompt. "
                          f"Estimated {monthly_prompt_tokens/1_000:.0f}K monthly prompt tokens.",
                "action": "Compress system prompts: strip comments from schema, "
                          "remove duplicate examples. "
                          "Target: ≤1500 tokens/call for local models.",
            })

        # R3 — High reprompt rate
        if reprompt_rate > _REPROMPT_THRESHOLD:
            recs.append({
                "severity": "error",
                "code": "HIGH_REPROMPT_RATE",
                "title": f"High reprompt rate ({reprompt_rate*100:.1f}%)",
                "detail": f"{reprompt_rate*100:.1f}% of calls needed at least one "
                          "reprompt to produce valid JSON. "
                          "Each reprompt doubles token consumption for that call.",
                "action": "Tighten system prompt: add explicit JSON schema, "
                          "reduce output field count, use format=json mode (Ollama). "
                          "Check model — qwen2.5-coder:7b is better than deepseek for JSON.",
            })

        # R4 — Paid provider expensive
        paid_total = sum(r["cost_usd"] for r in records if r["provider"] != "ollama")
        if paid_total > 0:
            daily_avg = paid_total / max(days, 1)
            monthly_est = daily_avg * 30
            if daily_avg > _PAID_SPEND_THRESHOLD:
                recs.append({
                    "severity": "warning",
                    "code": "PAID_PROVIDER_SPEND",
                    "title": f"Paid API spend: ${paid_total:.4f} "
                             f"(~${monthly_est:.2f}/month estimated)",
                    "detail": f"Daily average: ${daily_avg:.4f}. "
                              "Most test-generation workloads run equivalently "
                              "on Ollama (qwen2.5-coder:7b) at $0/month.",
                    "action": "Run 'cherenkov doctor' to check Ollama availability. "
                              "Set CHERENKOV_PROVIDER=ollama to switch. "
                              "Use paid providers only for planning stage if needed.",
                })

        # R5 — Model tier mismatch (expensive model for cheap work)
        expensive_json_calls = [
            r for r in records
            if r["provider"] in ("openai", "anthropic")
            and any(m in r["model"] for m in ("gpt-4-turbo", "gpt-4o", "claude-opus"))
            and r["stage"] in ("GENERATE", "REVIEW")
        ]
        if len(expensive_json_calls) > 5:
            wasted_cost = sum(r["cost_usd"] for r in expensive_json_calls)
            recs.append({
                "severity": "info",
                "code": "MODEL_TIER_MISMATCH",
                "title": f"Premium model used for routine JSON extraction "
                         f"({len(expensive_json_calls)} calls, ${wasted_cost:.4f})",
                "detail": "GENERATE and REVIEW stages do structured JSON extraction. "
                          "Premium models (GPT-4o, Claude Opus) offer minimal benefit "
                          "over cheaper tiers for this task.",
                "action": "Route GENERATE/REVIEW to gpt-4o-mini or claude-haiku. "
                          "Reserve premium models for PLAN stage only.",
            })

        # R6 — Token growth trend
        if daily_trend and len(daily_trend) >= 14:
            first_week  = sum(d["tokens"] for d in daily_trend[:7])
            second_week = sum(d["tokens"] for d in daily_trend[-7:])
            if first_week > 0 and second_week / first_week > (1 + _GROWTH_THRESHOLD):
                growth_pct = (second_week / first_week - 1) * 100
                recs.append({
                    "severity": "info",
                    "code": "TOKEN_GROWTH",
                    "title": f"Token consumption grew {growth_pct:.0f}% week-over-week",
                    "detail": f"Week 1: {first_week:,} tokens → Week 2: {second_week:,} tokens. "
                              "This may indicate spec growth, more endpoints, "
                              "or increasing reprompt frequency.",
                    "action": "Run 'cherenkov tokens breakdown --stage' to find "
                              "which stage is growing. "
                              "Check if spec added many new endpoints or schemas.",
                })

        # R7 — All Ollama, no cost (positive ack)
        if all(r["provider"] == "ollama" for r in records):
            recs.append({
                "severity": "ok",
                "code": "LOCAL_ONLY",
                "title": "Running 100% on local Ollama — $0 API cost",
                "detail": "All inference is local. Your spec never leaves your machine.",
                "action": None,
            })

        return recs

    def get_dashboard_data(self, days: int = 7) -> dict:
        """Compact payload for the dashboard token widget."""
        report = self.get_report(days=days)
        return {
            "period_days": report.period_days,
            "summary": {
                "total_tokens": report.total_tokens,
                "total_cost_usd": report.total_cost_usd,
                "total_requests": report.total_requests,
                "cache_hit_rate": report.cache_hit_rate,
                "reprompt_rate": report.reprompt_rate,
                "avg_prompt_tokens": report.avg_prompt_tokens,
                "avg_completion_tokens": report.avg_completion_tokens,
            },
            "by_provider": report.by_provider,
            "by_stage": report.by_stage,
            "daily_trend": report.daily_trend,
            "recommendations": report.recommendations,
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_MONITOR: TokenMonitor | None = None


def get_monitor(db_path: str | None = None) -> TokenMonitor:
    global _MONITOR
    if _MONITOR is None:
        _MONITOR = TokenMonitor(db_path)
    return _MONITOR
