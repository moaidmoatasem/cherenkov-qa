"""
test_proof_run_reflector.py — A7 #114 unit tests.

Verifies:
  - rerank() is called once per PROOF_RUN_PROBE when a Reflector is provided.
  - Hypotheses suppressed by rerank() never enter the Witness loop.
  - The suppressed-count message is printed when hypotheses are removed.
  - When reflector=None, rerank() is never called.

All tests run in offline mode (use_llm=False) — no LLM, no network.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from cherenkov.divergence.proof_run import run_proof, PROOF_RUN_PROBES
from cherenkov.reflector.reflector import Reflector
from cherenkov.reflector.store import VerdictStore


# ── helpers ───────────────────────────────────────────────────────────────────


def _in_memory_reflector() -> Reflector:
    """Reflector backed by an in-memory SQLite (no disk I/O)."""
    store = VerdictStore(db_path=":memory:")
    return Reflector(store=store)


def _mock_reflector_pass_through() -> MagicMock:
    """Reflector mock whose rerank() is a transparent pass-through."""
    mock = MagicMock(spec=Reflector)
    # rerank returns the hypotheses unchanged
    mock.rerank.side_effect = lambda hypotheses, endpoint=None: hypotheses
    return mock


def _mock_reflector_suppress_all() -> MagicMock:
    """Reflector mock whose rerank() suppresses ALL hypotheses (returns [])."""
    mock = MagicMock(spec=Reflector)
    mock.rerank.return_value = []
    return mock


# ── A7 rerank() call count tests ──────────────────────────────────────────────


class TestRerankcalledPerProbe:
    """rerank() must be called exactly once per PROOF_RUN_PROBE."""

    def test_rerank_called_for_every_probe_offline(self, capsys):
        """With use_llm=False, rerank() is called len(PROOF_RUN_PROBES) times."""
        reflector = _mock_reflector_pass_through()

        # Patch witness so we don't hit the network
        with patch(
            "cherenkov.divergence.proof_run.WitnessAgent.reproduce",
            return_value=MagicMock(
                reproduced=False, evidence=None, rejection_reason="mocked"
            ),
        ):
            run_proof(
                base_url="http://localhost:1",
                use_llm=False,
                reflector=reflector,
            )

        assert reflector.rerank.call_count == len(PROOF_RUN_PROBES), (
            f"Expected rerank() called {len(PROOF_RUN_PROBES)} times, "
            f"got {reflector.rerank.call_count}"
        )

    def test_rerank_receives_correct_endpoint_key(self, capsys):
        """Each rerank() call must receive `endpoint='{METHOD} {path}'`."""
        reflector = _mock_reflector_pass_through()

        with patch(
            "cherenkov.divergence.proof_run.WitnessAgent.reproduce",
            return_value=MagicMock(
                reproduced=False, evidence=None, rejection_reason="mocked"
            ),
        ):
            run_proof(
                base_url="http://localhost:1",
                use_llm=False,
                reflector=reflector,
            )

        expected_keys = {
            f"{method} {endpoint}" for endpoint, method, _, _ in PROOF_RUN_PROBES
        }
        actual_keys = {
            c.kwargs.get("endpoint") or c.args[1]
            for c in reflector.rerank.call_args_list
        }
        assert (
            expected_keys == actual_keys
        ), f"Endpoint keys mismatch.\n  Expected: {expected_keys}\n  Got: {actual_keys}"

    def test_no_rerank_when_reflector_is_none(self, capsys):
        """When reflector=None, proof_run must NOT call rerank() on anything."""
        with patch(
            "cherenkov.divergence.proof_run.WitnessAgent.reproduce",
            return_value=MagicMock(
                reproduced=False, evidence=None, rejection_reason="mocked"
            ),
        ):
            # Should not raise; reflector is not used
            run_proof(
                base_url="http://localhost:1",
                use_llm=False,
                reflector=None,
            )
        # No assertions needed – if the code tried to call .rerank() on None it
        # would raise AttributeError and the test would fail.


# ── Suppression tests ─────────────────────────────────────────────────────────


class TestSuppressionPreventsWitnessEntry:
    """Hypotheses removed by rerank() must NEVER reach WitnessAgent.reproduce()."""

    def test_suppressed_hypotheses_skip_witness(self):
        """When rerank() returns [], witness.reproduce() must never be called."""
        reflector = _mock_reflector_suppress_all()

        witness_reproduce = MagicMock(
            return_value=MagicMock(
                reproduced=False, evidence=None, rejection_reason="mocked"
            )
        )
        with patch(
            "cherenkov.divergence.proof_run.WitnessAgent.reproduce",
            witness_reproduce,
        ):
            reports = run_proof(
                base_url="http://localhost:1",
                use_llm=False,
                reflector=reflector,
            )

        assert witness_reproduce.call_count == 0, (
            f"Witness.reproduce() should not be called when all hypotheses are "
            f"suppressed, but it was called {witness_reproduce.call_count} time(s)"
        )
        assert (
            reports == []
        ), "No reports should be emitted when all hypotheses are suppressed"

    def test_partial_suppression_limits_witness_calls(self):
        """When rerank() removes half the hypotheses, witness calls are halved."""
        # Offline mode gives 1 hypothesis per probe (5 probes → 5 total)
        # We'll suppress 3 out of 5 probes' hypotheses.

        probe_count = len(PROOF_RUN_PROBES)

        call_counter = {"n": 0}

        def _selective_rerank(hypotheses, endpoint=None):
            call_counter["n"] += 1
            # Suppress odd-numbered probes (1-indexed)
            if call_counter["n"] % 2 == 1:
                return []  # suppress
            return hypotheses  # pass through

        reflector = MagicMock(spec=Reflector)
        reflector.rerank.side_effect = _selective_rerank

        witness_reproduce = MagicMock(
            return_value=MagicMock(
                reproduced=False, evidence=None, rejection_reason="mocked"
            )
        )
        with patch(
            "cherenkov.divergence.proof_run.WitnessAgent.reproduce",
            witness_reproduce,
        ):
            run_proof(
                base_url="http://localhost:1",
                use_llm=False,
                reflector=reflector,
            )

        # 5 probes; probes 1,3,5 are suppressed → 2 pass through
        expected_witness_calls = probe_count // 2
        assert witness_reproduce.call_count == expected_witness_calls, (
            f"Expected {expected_witness_calls} witness calls, "
            f"got {witness_reproduce.call_count}"
        )


# ── Print message tests ───────────────────────────────────────────────────────


class TestSuppressedCountPrinted:
    """When hypotheses are suppressed, the count must be printed."""

    def test_suppressed_message_printed(self, capsys):
        """'Reflector: suppressed N rejected hypothesis(es)' appears in stdout."""
        reflector = _mock_reflector_suppress_all()

        with patch(
            "cherenkov.divergence.proof_run.WitnessAgent.reproduce",
            return_value=MagicMock(
                reproduced=False, evidence=None, rejection_reason="mocked"
            ),
        ):
            run_proof(
                base_url="http://localhost:1",
                use_llm=False,
                reflector=reflector,
            )

        captured = capsys.readouterr()
        assert (
            "Reflector: suppressed" in captured.out
        ), f"Expected suppression message in stdout.\nGot:\n{captured.out}"

    def test_no_suppressed_message_when_nothing_suppressed(self, capsys):
        """No suppression message when rerank() is a pass-through."""
        reflector = _mock_reflector_pass_through()

        with patch(
            "cherenkov.divergence.proof_run.WitnessAgent.reproduce",
            return_value=MagicMock(
                reproduced=False, evidence=None, rejection_reason="mocked"
            ),
        ):
            run_proof(
                base_url="http://localhost:1",
                use_llm=False,
                reflector=reflector,
            )

        captured = capsys.readouterr()
        assert (
            "Reflector: suppressed" not in captured.out
        ), "Suppression message should NOT appear when nothing was suppressed."

    def test_ingest_called_for_each_witness_result(self):
        """ingest_from_reproduction() must be called once per witness result."""
        reflector = _mock_reflector_pass_through()

        witness_reproduce = MagicMock(
            return_value=MagicMock(
                reproduced=False, evidence=None, rejection_reason="mocked"
            )
        )
        with patch(
            "cherenkov.divergence.proof_run.WitnessAgent.reproduce",
            witness_reproduce,
        ):
            run_proof(
                base_url="http://localhost:1",
                use_llm=False,
                reflector=reflector,
            )

        # 5 probes × 1 offline hypothesis each = 5 results ingested
        assert reflector.ingest_from_reproduction.call_count == len(PROOF_RUN_PROBES), (
            f"Expected ingest_from_reproduction called {len(PROOF_RUN_PROBES)} times, "
            f"got {reflector.ingest_from_reproduction.call_count}"
        )
