"""Unit tests for cherenkov/oracle/consensus_oracle.py — CANDOR consensus oracle."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cherenkov.core.contracts import Claim, Provenance, ProvenanceType
from cherenkov.oracle.consensus_oracle import ConsensusOracle


# ── fixtures ──────────────────────────────────────────────────────────────────


def _make_claim(claim_id: str = "test-claim") -> Claim:
    return Claim(
        id=claim_id,
        category="mutation",
        subject="POST /users",
        value={"expected_status": 201},
        provenance=Provenance(
            source_type=ProvenanceType.SPEC,
            source_uri="openapi.yaml",
        ),
    )


_SAMPLE_TEST = """
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user happy path', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'pass123' }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});
"""

_SAMPLE_SLICE = {
    "path": "/users",
    "method": "POST",
    "operation": {
        "summary": "Create a new user",
        "responses": {"201": {"description": "Created"}, "400": {"description": "Bad Request"}},
    },
    "schemas": {},
}


# ── constructor ───────────────────────────────────────────────────────────────


def test_passes_clamped_to_2_min():
    oracle = ConsensusOracle(passes=0)
    assert oracle.passes == 2


def test_passes_clamped_to_4_max():
    oracle = ConsensusOracle(passes=99)
    assert oracle.passes == 4


def test_default_passes_and_threshold():
    oracle = ConsensusOracle()
    assert oracle.passes == 3
    assert oracle.consensus_threshold == 0.6


# ── evaluate with no test code ────────────────────────────────────────────────


def test_evaluate_empty_test_code():
    oracle = ConsensusOracle()
    claim = _make_claim()
    result = oracle.evaluate(claim, test_code="", endpoint_slice=_SAMPLE_SLICE)
    assert result.is_correct is False
    assert result.confidence == 0.0
    assert "no test code" in result.detail.lower()


# ── _single_pass fallback ────────────────────────────────────────────────────


def test_single_pass_fallback_on_client_error():
    oracle = ConsensusOracle(run_id="test-run")
    with patch("cherenkov.oracle.consensus_oracle.ConsensusOracle._single_pass") as mock_pass:
        mock_pass.return_value = {
            "verdict": "incorrect",
            "confidence": 0.3,
            "reason": "pass evaluation failed",
        }
        result = oracle.evaluate(
            _make_claim(), test_code=_SAMPLE_TEST, endpoint_slice=_SAMPLE_SLICE
        )
    # All passes return incorrect → is_correct should be False
    assert result.is_correct is False


# ── consensus logic ───────────────────────────────────────────────────────────


def _mock_passes(verdicts: list[str], confidences: list[float]):
    """Return a side_effect list for _single_pass mock."""
    return [
        {"verdict": v, "confidence": c, "reason": f"reason for {v}"}
        for v, c in zip(verdicts, confidences)
    ]


def test_unanimous_correct_returns_correct():
    oracle = ConsensusOracle(passes=3, consensus_threshold=0.6)
    side_effects = _mock_passes(["correct", "correct", "correct"], [0.9, 0.85, 0.9])
    with patch.object(oracle, "_single_pass", side_effect=side_effects):
        result = oracle.evaluate(
            _make_claim(), test_code=_SAMPLE_TEST, endpoint_slice=_SAMPLE_SLICE
        )
    assert result.is_correct is True
    assert result.confidence > 0.7


def test_unanimous_incorrect_returns_incorrect():
    oracle = ConsensusOracle(passes=3, consensus_threshold=0.6)
    side_effects = _mock_passes(["incorrect", "incorrect", "incorrect"], [0.8, 0.7, 0.8])
    with patch.object(oracle, "_single_pass", side_effect=side_effects):
        result = oracle.evaluate(
            _make_claim(), test_code=_SAMPLE_TEST, endpoint_slice=_SAMPLE_SLICE
        )
    assert result.is_correct is False


def test_split_vote_below_threshold_returns_incorrect():
    # 1/3 agree (0.33) < threshold 0.6 → incorrect
    oracle = ConsensusOracle(passes=3, consensus_threshold=0.6)
    side_effects = _mock_passes(
        ["correct", "incorrect", "incorrect"], [0.9, 0.6, 0.7]
    )
    with patch.object(oracle, "_single_pass", side_effect=side_effects):
        result = oracle.evaluate(
            _make_claim(), test_code=_SAMPLE_TEST, endpoint_slice=_SAMPLE_SLICE
        )
    assert result.is_correct is False


def test_split_vote_at_threshold_returns_correct():
    # 2/3 agree (0.67) >= threshold 0.6 → correct
    oracle = ConsensusOracle(passes=3, consensus_threshold=0.6)
    side_effects = _mock_passes(
        ["correct", "correct", "incorrect"], [0.8, 0.85, 0.6]
    )
    with patch.object(oracle, "_single_pass", side_effect=side_effects):
        result = oracle.evaluate(
            _make_claim(), test_code=_SAMPLE_TEST, endpoint_slice=_SAMPLE_SLICE
        )
    assert result.is_correct is True


def test_two_pass_majority_correct():
    oracle = ConsensusOracle(passes=2, consensus_threshold=0.5)
    side_effects = _mock_passes(["correct", "correct"], [0.8, 0.9])
    with patch.object(oracle, "_single_pass", side_effect=side_effects):
        result = oracle.evaluate(
            _make_claim(), test_code=_SAMPLE_TEST, endpoint_slice=_SAMPLE_SLICE
        )
    assert result.is_correct is True


def test_detail_contains_pass_count():
    oracle = ConsensusOracle(passes=3, consensus_threshold=0.6)
    side_effects = _mock_passes(["correct", "correct", "correct"], [0.9, 0.9, 0.9])
    with patch.object(oracle, "_single_pass", side_effect=side_effects):
        result = oracle.evaluate(
            _make_claim(), test_code=_SAMPLE_TEST, endpoint_slice=_SAMPLE_SLICE
        )
    assert "3/3" in result.detail


def test_confidence_is_zero_when_all_passes_fail():
    oracle = ConsensusOracle(passes=2, consensus_threshold=0.6)
    # agree_ratio=0, avg_confidence=0.3 → combined = 0
    side_effects = _mock_passes(["incorrect", "incorrect"], [0.3, 0.3])
    with patch.object(oracle, "_single_pass", side_effect=side_effects):
        result = oracle.evaluate(
            _make_claim(), test_code=_SAMPLE_TEST, endpoint_slice=_SAMPLE_SLICE
        )
    assert result.confidence == 0.0


# ── oracle __init__ export ────────────────────────────────────────────────────


def test_consensus_oracle_importable_from_package():
    from cherenkov.oracle import ConsensusOracle as CO  # noqa: F401

    assert CO is ConsensusOracle
