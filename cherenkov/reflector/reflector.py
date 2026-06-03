"""
CHERENKOV reflector/reflector.py — E7 Reflector core.

Consumes verdicts (accept/reject/escaped-defect) from:
  - divergence/witness.py  (Skeptic hypothesis test results)
  - healing/diagnose.py    (FailureClass from failed test runs)

Then:
  1. Reranks Skeptic hypotheses (rejected ones stop re-surfacing)
  2. Accumulates per-system Idioms (patterns that keep being confirmed)
  3. Surfaces ranked Idioms for future Mentor consumption
"""
from __future__ import annotations

import hashlib
import re
import time
import uuid
from typing import Any

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    Idiom,
    ReflectorConfig,
    ReproductionResult,
    VerdictOutcome,
    VerdictRecord,
)
from cherenkov.core.errors import get_logger
from cherenkov.reflector.store import VerdictStore


def _divergence_class_from_str(s: str | None) -> DivergenceClass | None:
    if s is None:
        return None
    try:
        return DivergenceClass(s)
    except ValueError:
        return None


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def fingerprint_of(hypothesis: DivergenceHypothesis) -> str:
    """Stable SEMANTIC identity of a finding, independent of its random id.

    Two hypotheses with the same class + endpoint + (normalized) claims share a
    fingerprint — so a rejected finding stays rejected across Skeptic runs even
    though each run mints a fresh hypothesis.id. (E7 behavioural-exit fix.)
    """
    cls = hypothesis.divergence_class.value if hypothesis.divergence_class else ""
    basis = "|".join(
        [cls, _norm(hypothesis.endpoint), _norm(hypothesis.claim_a), _norm(hypothesis.claim_b)]
    )
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


class Reflector:
    """E7 Reflector — verdict-driven learning loop.

    Typical usage:
        store = VerdictStore()
        reflector = Reflector(store)
        # After each witness reproduction:
        reflector.ingest(hypothesis, result)
        # Before the next skeptic round:
        filtered = reflector.rerank(hypotheses)
    """

    def __init__(
        self,
        store: VerdictStore | None = None,
        config: ReflectorConfig | None = None,
        run_id: str | None = None,
    ):
        self.store = store or VerdictStore(run_id=run_id)
        self.config = config or ReflectorConfig()
        self.log = get_logger("REFLECTOR", run_id)

    # ── ingest ────────────────────────────────────────────────────────────

    def ingest_from_reproduction(
        self,
        hypothesis: DivergenceHypothesis,
        result: ReproductionResult,
    ) -> VerdictRecord:
        """Record a verdict from a Witness reproduction attempt.

        Args:
            hypothesis: The hypothesis that was tested.
            result:     The reproduction result.

        Returns:
            The VerdictRecord that was persisted.
        """
        outcome = (
            VerdictOutcome.ACCEPT
            if result.reproduced
            else VerdictOutcome.REJECT
        )
        record = VerdictRecord(
            id=str(uuid.uuid4()),
            hypothesis_id=hypothesis.id,
            outcome=outcome,
            divergence_class=hypothesis.divergence_class,
            endpoint=hypothesis.endpoint,
            source="skeptic",
            detail=(
                result.evidence.request_summary
                if result.evidence
                else (result.rejection_reason or "No evidence captured")
            ),
            timestamp=int(time.time()),
        )
        self.store.record_verdict(record)
        self.log.info(
            "recorded verdict",
            hypothesis_id=hypothesis.id,
            outcome=outcome.value,
            endpoint=hypothesis.endpoint,
        )

        if outcome == VerdictOutcome.ACCEPT:
            # strengthen or create an Idiom
            self._reinforce_idiom(hypothesis)
        elif outcome == VerdictOutcome.REJECT:
            # suppress by semantic fingerprint so it cannot resurface (E7 fix)
            self.store.record_rejected_fingerprint(
                fingerprint_of(hypothesis),
                hypothesis.endpoint,
                hypothesis.divergence_class.value if hypothesis.divergence_class else None,
            )

        return record

    def ingest_from_healing(
        self,
        hypothesis_id: str,
        failure_class: str,
        detail: str = "",
        endpoint: str | None = None,
    ) -> VerdictRecord:
        """Record a verdict derived from a healing diagnosis.

        Args:
            hypothesis_id: ID of the hypothesis (or scenario_id).
            failure_class: The FailureClass from Diagnoser (e.g. "AUTH_EXPIRY").
            detail:        Human-readable detail.
            endpoint:      API endpoint if applicable.

        Returns:
            The VerdictRecord that was persisted.
        """
        record = VerdictRecord(
            id=str(uuid.uuid4()),
            hypothesis_id=hypothesis_id,
            outcome=VerdictOutcome.ESCAPED_DEFECT,
            endpoint=endpoint,
            failure_class=failure_class,
            source="healing",
            detail=detail,
            timestamp=int(time.time()),
        )
        self.store.record_verdict(record)
        self.log.info(
            "recorded healing verdict",
            hypothesis_id=hypothesis_id,
            failure_class=failure_class,
        )
        return record

    def ingest_human_verdict(
        self,
        hypothesis_id: str,
        outcome: VerdictOutcome,
        detail: str = "",
        endpoint: str | None = None,
        hypothesis: DivergenceHypothesis | None = None,
    ) -> VerdictRecord:
        """Record a human-supplied verdict (overrides automated ones).

        Pass the full `hypothesis` when rejecting so the rejection is recorded
        as a semantic fingerprint and stays suppressed across runs (E7 fix).
        """
        record = VerdictRecord(
            id=str(uuid.uuid4()),
            hypothesis_id=hypothesis_id,
            outcome=outcome,
            endpoint=endpoint or (hypothesis.endpoint if hypothesis else None),
            source="human",
            detail=detail,
            timestamp=int(time.time()),
        )
        self.store.record_verdict(record)
        if outcome == VerdictOutcome.REJECT and hypothesis is not None:
            self.store.record_rejected_fingerprint(
                fingerprint_of(hypothesis),
                hypothesis.endpoint,
                hypothesis.divergence_class.value if hypothesis.divergence_class else None,
            )
        self.log.info(
            "recorded human verdict",
            hypothesis_id=hypothesis_id,
            outcome=outcome.value,
        )
        return record

    # ── rerank (E7-2) ─────────────────────────────────────────────────────

    def rerank(
        self,
        hypotheses: list[DivergenceHypothesis],
        endpoint: str | None = None,
    ) -> list[DivergenceHypothesis]:
        """Filter and reorder hypotheses based on accumulated verdict memory.

        1. Remove hypotheses whose IDs were previously rejected.
        2. Boost hypotheses matching active Idioms.

        Args:
            hypotheses: Raw hypotheses from SkepticAgent.
            endpoint:   Current endpoint being probed.

        Returns:
            Reranked (filtered + reordered) hypotheses.
        """
        if not hypotheses:
            return hypotheses

        # 1. Suppress previously rejected hypotheses — by ephemeral id (legacy)
        #    AND by semantic fingerprint (E7 fix: survives id re-minting).
        rejected = self.store.get_rejected_hypothesis_ids(endpoint)
        rejected_fps = self.store.rejected_fingerprints(endpoint)
        filtered = [
            h for h in hypotheses
            if h.id not in rejected and fingerprint_of(h) not in rejected_fps
        ]

        if len(filtered) < len(hypotheses):
            self.log.info(
                "suppressed rejected hypotheses",
                count=len(hypotheses) - len(filtered),
                endpoint=endpoint,
            )

        # 2. Boost hypotheses that match active idioms
        active_idioms = self.store.get_idioms(min_decay=0.3)

        def _boost_key(h: DivergenceHypothesis) -> float:
            score = 0.0
            for idiom in active_idioms:
                if idiom.endpoint and idiom.endpoint == h.endpoint:
                    score += idiom.decay_score * 0.5
                if idiom.divergence_class == h.divergence_class:
                    score += idiom.decay_score * 0.3
                if idiom.pattern in (h.claim_a + h.claim_b):
                    score += idiom.decay_score * 0.2
            return score

        # Sort: boosted hypotheses first, then by original order
        filtered.sort(key=_boost_key, reverse=True)

        return filtered

    # ── idioms (E7-3) ─────────────────────────────────────────────────────

    def _reinforce_idiom(self, hypothesis: DivergenceHypothesis) -> None:
        """Strengthen or create an Idiom from a confirmed hypothesis.

        Uses claim_b (the divergence pattern) as the idiom pattern.
        """
        pattern = hypothesis.claim_b[:200]  # keep it concise
        existing = self.store.get_idiom_by_pattern(pattern)

        now = int(time.time())
        if existing:
            existing.confirm_count += 1
            existing.last_confirmed = now
            existing.decay_score = min(1.0, existing.decay_score + 0.1)
            self.store.upsert_idiom(existing)
            self.log.info(
                "reinforced idiom",
                pattern=pattern[:60],
                confirm_count=existing.confirm_count,
            )
        else:
            idiom = Idiom(
                id=str(uuid.uuid4()),
                pattern=pattern,
                divergence_class=hypothesis.divergence_class,
                endpoint=hypothesis.endpoint,
                confirm_count=1,
                last_confirmed=now,
                decay_score=1.0,
            )
            self.store.upsert_idiom(idiom)
            self.log.info(
                "created idiom",
                pattern=pattern[:60],
                endpoint=hypothesis.endpoint,
            )

    def get_top_idioms(
        self, min_decay: float = 0.3, limit: int = 20
    ) -> list[Idiom]:
        """Surface ranked Idioms for Mentor (E13) or CLI inspection."""
        return self.store.get_idioms(min_decay=min_decay, limit=limit)

    def get_stats(self) -> dict[str, Any]:
        """Return high-level reflector statistics."""
        self.store.decay_all_idioms(self.config.decay_half_life_hours)
        return {
            "verdict_count": self.store.verdict_count(),
            "idiom_count": self.store.idiom_count(),
            "enabled": self.config.enabled,
            "store_path": self.store.db_path,
        }
