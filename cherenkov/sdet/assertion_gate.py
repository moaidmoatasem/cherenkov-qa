"""
CHERENKOV sdet/assertion_gate.py — E11-2 meaningful-assertion gate.

Wraps the adversarial self-play harness (`divergence/self_play.py`) as a gate:
a candidate test is *meaningful* only if it PASSES a spec-conforming mock and
FAILS a deliberately-broken implementation. A test that passes both has vacuous
assertions (true == true) and is rejected — the same anti-reward-hacking check
the divergence engine uses, applied here to gate what counts toward coverage.

This is intentionally a thin adapter over `AdversarialSelfPlay`: it reuses the
broken-impl run rather than reimplementing it, and presents an SDET-shaped
result (`AssertionGateResult`) plus a batch filter.
"""

from __future__ import annotations

from typing import Callable

from cherenkov.core.contracts import AssertionGateResult
from cherenkov.core.errors import get_logger
from cherenkov.divergence.self_play import AdversarialSelfPlay

# run_test(base_url) -> (passed, output)
RunTest = Callable[[str], "tuple[bool, str]"]


class MeaningfulAssertionGate:
    """Gate candidate tests through an adversarial broken-impl run.

    A single `AdversarialSelfPlay` instance backs the gate so kill-rate
    reporting accumulates across every evaluated candidate.
    """

    def __init__(self, run_id: str | None = None) -> None:
        self.log = get_logger("ASSERTION_GATE", run_id)
        self._self_play = AdversarialSelfPlay()

    def evaluate(
        self,
        test_id: str,
        run_test: RunTest,
        correct_mock_url: str,
        broken_mock_url: str,
    ) -> AssertionGateResult:
        """Return whether a candidate test carries meaningful assertions.

        Args mirror `AdversarialSelfPlay.validate`. `meaningful` is True only
        when the test passes the correct mock and fails the broken impl.
        """
        sp = self._self_play.validate(
            test_id=test_id,
            run_test=run_test,
            correct_mock_url=correct_mock_url,
            broken_mock_url=broken_mock_url,
        )
        meaningful = sp.passed_correct and sp.failed_broken
        if not meaningful:
            if not sp.passed_correct:
                reason = "Test does not pass the spec-conforming mock"
            else:
                reason = (
                    sp.kill_reason
                    or "Test passes the broken impl — assertions are vacuous"
                )
        else:
            reason = ""

        self.log.info(
            "assertion gate verdict",
            test_id=test_id,
            meaningful=meaningful,
            passed_correct=sp.passed_correct,
            failed_broken=sp.failed_broken,
        )
        return AssertionGateResult(
            test_id=test_id,
            meaningful=meaningful,
            passed_correct=sp.passed_correct,
            failed_broken=sp.failed_broken,
            reason=reason,
        )

    def filter_meaningful(
        self,
        candidates: list[tuple[str, RunTest]],
        correct_mock_url: str,
        broken_mock_url: str,
    ) -> list[AssertionGateResult]:
        """Evaluate a batch of (test_id, run_test) candidates; return all verdicts."""
        return [
            self.evaluate(test_id, run_test, correct_mock_url, broken_mock_url)
            for test_id, run_test in candidates
        ]

    def kill_rate(self) -> float:
        """Fraction of evaluated candidates rejected as not-meaningful."""
        return self._self_play.kill_rate()

    def report(self) -> str:
        return self._self_play.report()
