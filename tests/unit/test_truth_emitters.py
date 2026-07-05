"""tests/unit/test_truth_emitters.py — SpecPatchEmitter / PRCommentEmitter contract.

Both emitters used a stale DivergenceReport schema (nonexistent `endpoint_id`,
`description` fields and a nonexistent `DivergenceClass.D4_SPEC_DB` member) and
crashed with AttributeError on any non-empty divergence list. The only prior
coverage lived in tests/standalone/, which unit CI never runs — these tests
exercise the real contracts.py models so schema drift fails here.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)
from cherenkov.truth.emitters.pr_comment import PRCommentEmitter
from cherenkov.truth.emitters.spec_patch import SpecPatchEmitter


def _report(divergence_class: DivergenceClass, endpoint: str | None = "/pets") -> DivergenceReport:
    return DivergenceReport(
        id="div-1",
        divergence_class=divergence_class,
        claim_a="spec says 422",
        claim_b="server returns 400",
        evidence=DivergenceEvidence(
            request_summary="POST /pets → 400 (12ms)",
            response_actual={"error": "bad request"},
            response_expected={"detail": "validation error"},
            diff="status: 422 != 400",
        ),
        repro_steps=["POST /pets with missing name"],
        severity=Severity.HIGH,
        endpoint=endpoint,
        metadata=StageMeta(stage="DIVERGENCE"),
    )


@pytest.fixture
def truth_model():
    return MagicMock()  # neither emitter reads the truth model


def test_spec_patch_emits_for_spec_divergences(truth_model, tmp_path):
    out = tmp_path / "patch.diff"
    result = SpecPatchEmitter().emit(
        truth_model,
        out,
        divergences=[
            _report(DivergenceClass.D1_SPEC_CODE),
            _report(DivergenceClass.D4_DB_CODE, endpoint=None),
        ],
    )
    text = result.read_text(encoding="utf-8")
    assert "--- a/spec divergence: /pets" in text
    assert "--- a/spec divergence: unknown" in text
    assert "spec says 422 → server returns 400" in text


def test_spec_patch_filters_non_spec_divergences(truth_model, tmp_path):
    out = tmp_path / "patch.diff"
    SpecPatchEmitter().emit(
        truth_model, out, divergences=[_report(DivergenceClass.D2_CODE_PROD)]
    )
    assert out.read_text(encoding="utf-8") == ""


def test_spec_patch_empty_list_writes_empty_file(truth_model, tmp_path):
    out = tmp_path / "patch.diff"
    SpecPatchEmitter().emit(truth_model, out, divergences=[])
    assert out.read_text(encoding="utf-8") == ""


def test_pr_comment_renders_divergence_row(truth_model, tmp_path):
    out = tmp_path / "comment.md"
    PRCommentEmitter().emit(
        truth_model, out, divergences=[_report(DivergenceClass.D1_SPEC_CODE)]
    )
    text = out.read_text(encoding="utf-8")
    assert "| /pets | D1_spec_code | high | spec says 422 → server returns 400 |" in text


def test_pr_comment_escapes_pipes_and_handles_missing_endpoint(truth_model, tmp_path):
    report = _report(DivergenceClass.D5_SPEC_PROD, endpoint=None)
    report = report.model_copy(update={"claim_a": "a|b"})
    out = tmp_path / "comment.md"
    PRCommentEmitter().emit(truth_model, out, divergences=[report])
    text = out.read_text(encoding="utf-8")
    assert "| unknown |" in text
    assert "a\\|b" in text


def test_pr_comment_empty_list_renders_placeholder(truth_model, tmp_path):
    out = tmp_path / "comment.md"
    PRCommentEmitter().emit(truth_model, out, divergences=None)
    assert "_No divergences detected_" in out.read_text(encoding="utf-8")
