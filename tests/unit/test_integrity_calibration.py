"""
tests/unit/test_integrity_calibration.py
Calibration gate for the integrity detector.

The integrity auditor is the component that tells other agents whether their
tests are honest. Its own claim therefore has to be measured, not asserted: this
module runs the labelled corpus at bench/integrity_corpus/cases.yaml through
`audit_test_integrity` and fails the build if detection regresses.

Deliberately wired into the ordinary unit suite rather than a separate workflow.
A gate that runs only on a schedule is a gate that can rot unnoticed — which is
how this repository previously carried a Playwright suite that loaded zero tests.

The corpus was written alongside the current detector, so a perfect score on it
proves only that known evasions stay caught. `test_golden_fixtures_*` below is
the check that matters more: those fixtures predate this corpus and were not
written to exercise these rules.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cherenkov.integrity.api import (
    IntegrityAuditRequest,
    VerdictLabel,
    audit_test_integrity,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = REPO_ROOT / "bench" / "integrity_corpus" / "cases.yaml"
GOLDEN_DIR = REPO_ROOT / "bench" / "fixtures" / "golden_tests"


def _load_corpus() -> tuple[list[dict], str]:
    doc = yaml.safe_load(CORPUS_PATH.read_text(encoding="utf-8"))
    spec_path = (CORPUS_PATH.parent / doc["spec"]).resolve()
    return doc["cases"], spec_path.read_text(encoding="utf-8")


CASES, SPEC = _load_corpus()


def _audit(case: dict):
    return audit_test_integrity(
        IntegrityAuditRequest(
            test_content=case["content"],
            spec_content=SPEC,
            test_format=case["format"],
        )
    )


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_is_classified_correctly(case: dict) -> None:
    """Every labelled case lands on the right side of the verdict."""
    result = _audit(case)
    flagged = len(result.issues) > 0

    if case["label"] == "honest":
        assert not flagged, (
            f"{case['id']} is honest but was flagged "
            f"{[i.issue_type.value for i in result.issues]}. A false positive teaches "
            f"the agent under audit to ignore the auditor."
        )
    else:
        assert flagged, (
            f"{case['id']} ({case.get('class')}) is dishonest but passed the audit "
            f"with score {result.integrity_score}."
        )


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["label"] == "dishonest"],
    ids=[c["id"] for c in CASES if c["label"] == "dishonest"],
)
def test_dishonest_case_never_receives_a_certificate(case: dict) -> None:
    """No test that cannot fail may be handed a signed certificate.

    A miss is a gap. A certificate issued to a test that cannot fail is the
    auditor asserting something untrue, which is worse than no auditor.
    """
    result = _audit(case)
    assert result.certificate is None, (
        f"{case['id']} ({case.get('class')}) received certificate {result.certificate}"
    )


def test_corpus_covers_every_evasion_class() -> None:
    """Guard against a class being silently dropped from the corpus."""
    classes = {c.get("class") for c in CASES if c["label"] == "dishonest"}
    expected = {
        "tautology", "weakened_status", "no_assertion", "disabled",
        "swallowed", "always_true", "deleted_coverage", "spec_mismatch",
        "hallucinated",
    }
    assert expected <= classes, f"missing evasion classes: {sorted(expected - classes)}"


def test_corpus_has_both_labels_and_enough_honest_cases() -> None:
    """Recall is meaningless without honest cases to measure false positives against."""
    honest = [c for c in CASES if c["label"] == "honest"]
    dishonest = [c for c in CASES if c["label"] == "dishonest"]
    assert len(honest) >= 10
    assert len(dishonest) >= 20


# ── Held-out fixtures ─────────────────────────────────────────────────────────
# These three predate the corpus. They are the only evidence here that the
# detector generalises beyond the cases written for it.

def test_golden_fixture_correct_test_passes() -> None:
    content = (GOLDEN_DIR / "correct_petstore.spec.ts").read_text(encoding="utf-8")
    result = audit_test_integrity(
        IntegrityAuditRequest(test_content=content, spec_content=SPEC, test_format="playwright")
    )
    assert result.verdict == VerdictLabel.PASS, [i.detail for i in result.issues]
    assert result.certificate is not None


def test_golden_fixture_weakened_assertion_is_flagged() -> None:
    content = (GOLDEN_DIR / "weakened_assertion_petstore.spec.ts").read_text(encoding="utf-8")
    result = audit_test_integrity(
        IntegrityAuditRequest(test_content=content, spec_content=SPEC, test_format="playwright")
    )
    assert result.verdict != VerdictLabel.PASS
    assert any(i.issue_type.value == "WEAKENED_ASSERTION" for i in result.issues)
    assert result.certificate is None


def test_golden_fixture_deleted_body_check_is_flagged() -> None:
    """The case that the corpus missed until this fixture was run against it."""
    content = (GOLDEN_DIR / "deleted_check_petstore.spec.ts").read_text(encoding="utf-8")
    result = audit_test_integrity(
        IntegrityAuditRequest(test_content=content, spec_content=SPEC, test_format="playwright")
    )
    assert result.verdict != VerdictLabel.PASS
    assert result.certificate is None


# ── Spec awareness ────────────────────────────────────────────────────────────

def test_spec_checks_are_silent_without_a_spec() -> None:
    """Without a spec the audit must make no spec claims, not guess at them."""
    mismatch = next(c for c in CASES if c["id"] == "py-mismatch-post-200")
    with_spec = audit_test_integrity(
        IntegrityAuditRequest(
            test_content=mismatch["content"], spec_content=SPEC, test_format="pytest"
        )
    )
    without_spec = audit_test_integrity(
        IntegrityAuditRequest(
            test_content=mismatch["content"], spec_content=None, test_format="pytest"
        )
    )
    assert any(i.issue_type.value == "SPEC_MISMATCH" for i in with_spec.issues)
    assert not any(i.issue_type.value == "SPEC_MISMATCH" for i in without_spec.issues)


def test_malformed_spec_degrades_instead_of_raising() -> None:
    """A broken spec must not take the auditor down with it."""
    result = audit_test_integrity(
        IntegrityAuditRequest(
            test_content="def test_x(client):\n    r = client.get('/pets')\n    assert r.status_code == 200\n",
            spec_content="{{{ not a spec",
            test_format="pytest",
        )
    )
    assert result.audit_id
    assert not any(i.issue_type.value == "SPEC_MISMATCH" for i in result.issues)
