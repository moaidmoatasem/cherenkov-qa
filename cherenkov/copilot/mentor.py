from __future__ import annotations

from cherenkov.core.config import Config
from cherenkov.core.contracts import Idiom
from cherenkov.core.errors import get_logger
from cherenkov.reflector.store import VerdictStore

# Default minimum confirmations before an idiom is surfaced
_DEFAULT_MIN_CONFIRMATIONS = 2


class Mentor:
    """E13 Mentor — Surfaces accumulated senior QA idioms based on context.

    Helps junior testers author tests or triage failures using the team's
    historical findings. Idioms require N confirmations before being surfaced
    (C13 #128: 'require N-confirmations before surfacing').
    """

    def __init__(self, store: VerdictStore | None = None, run_id: str | None = None):
        self.store = store or VerdictStore(run_id=run_id)
        self.log = get_logger("MENTOR", run_id)

    def get_suggestions(
        self,
        endpoint: str | None = None,
        divergence_class: str | None = None,
        min_decay: float = 0.3,
        min_confirmations: int | None = None,
    ) -> list[Idiom]:
        """Surface relevant senior idioms based on context.

        Args:
            endpoint: Filter idioms matching this endpoint.
            divergence_class: Filter idioms matching this divergence class.
            min_decay: Minimum decay score threshold (default: 0.3).
            min_confirmations: Minimum confirmations required before surfacing.
                Defaults to Config value or 2.

        Returns:
            Ranked list of Idioms meeting the confirmation threshold.
        """
        if not Config.COPILOT_MENTOR_ENABLED:
            self.log.info("mentor is disabled in config")
            return []

        min_conf = min_confirmations if min_confirmations is not None else getattr(Config, "COPILOT_MENTOR_MIN_CONFIRMATIONS", _DEFAULT_MIN_CONFIRMATIONS)
        all_active = self.store.get_idioms(min_decay=min_decay)
        relevant: list[Idiom] = []

        for idiom in all_active:
            if idiom.confirm_count < min_conf:
                continue

            match = False
            if endpoint and idiom.endpoint and (idiom.endpoint.lower() in endpoint.lower() or endpoint.lower() in idiom.endpoint.lower()):
                match = True

            if divergence_class and idiom.divergence_class == divergence_class:
                match = True

            if endpoint is None and divergence_class is None:
                match = True

            if match:
                relevant.append(idiom)

        relevant.sort(key=lambda x: (x.decay_score, x.confirm_count), reverse=True)
        self.log.info("surfaced idioms for context", endpoint=endpoint, count=len(relevant),
                      min_confirmations=min_conf)
        return relevant
