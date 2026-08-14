"""Calibration gate for `check-suite`'s detector.

Companion to `test_integrity_calibration.py`. That one gates
`cherenkov/integrity/api.py`; this one gates the *second* integrity detector,
`cherenkov/cli/commands/check_suite.py`, against the same corpus.

Deliberately in the ordinary unit suite rather than a separate workflow, for the
reason `test_integrity_calibration.py` gives: a gate that only runs on a
schedule is how an unexercised suite survives unnoticed.

What is and is not asserted here
--------------------------------
The corpus labels individual tests. `check-suite` is primarily a *differential*
detector — it compares a candidate against a baseline — so most of the corpus is
outside what it can answer without one. Gating on overall recall would therefore
encode a false expectation and would fail for reasons that are not defects.

So the gate is:

  * **zero false positives, across every class.** An honest test flagged is a
    false positive regardless of which question was being asked. This is the
    assertion that matters most: it was 41.7% before the `_RESPONSE_ATTRS` fix,
    and a false positive on an honest test is more expensive than a miss because
    it trains the agent under audit to ignore the auditor.
  * **full recall on the classes check-suite actually implements** — currently
    `hallucinated`.
  * **every corpus class is explicitly mapped to a scope**, so a class added to
    the corpus cannot be silently averaged away.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

sys.path.insert(0, str(REPO / "scripts"))

from calibrate_check_suite import (  # noqa: E402
    CORPUS,
    audit_case,
    load_corpus,
    summarise,
)

pytestmark = pytest.mark.skipif(
    not CORPUS.exists(), reason="integrity corpus not present"
)


@pytest.fixture(scope="module")
def report() -> dict:
    cases, spec_path = load_corpus(CORPUS)
    rows = [audit_case(c, spec_path) for c in cases]
    return {"rows": rows, "summary": summarise(rows)}


def test_no_false_positives_on_honest_tests(report: dict) -> None:
    """An honest test must never be flagged. Was 41.7% before `_RESPONSE_ATTRS`."""
    summary = report["summary"]
    assert summary["false_positive_rate"] == 0.0, (
        "check-suite flagged honest tests: "
        f"{summary['false_positive_ids']}. A false positive on an honest test is "
        "more expensive than a miss — it trains the agent under audit to ignore "
        "the auditor."
    )


def test_full_recall_on_implemented_classes(report: dict) -> None:
    """Classes check-suite claims to detect must be fully detected."""
    summary = report["summary"]
    missed = [
        (cls, d["missed"])
        for cls, d in summary["by_class"].items()
        if d["scope"] == "IMPLEMENTED" and d["missed"]
    ]
    assert not missed, f"missed cases in IMPLEMENTED classes: {missed}"


def test_detector_never_crashes(report: dict) -> None:
    """A crash on a malformed test is a defect, not a non-result."""
    errored = [r for r in report["rows"] if r["error"]]
    assert not errored, f"detector raised on: {[(r['id'], r['error']) for r in errored]}"


def test_every_corpus_class_is_scope_mapped(report: dict) -> None:
    """A new evasion class must be classified, not silently averaged in.

    Without this, adding a class to the corpus would quietly land in whatever
    bucket the reporting defaults to and stop being a decision anyone made.
    """
    unmapped = sorted(
        cls
        for cls, d in report["summary"]["by_class"].items()
        if d["scope"] == "UNMAPPED"
    )
    assert not unmapped, (
        f"corpus classes with no scope mapping: {unmapped}. Add them to SCOPE in "
        "scripts/calibrate_check_suite.py and decide deliberately whether "
        "check-suite is expected to catch them."
    )


def test_response_attributes_are_not_body_fields() -> None:
    """`response.status_code` is not a hallucinated field. The regression itself.

    Pinned directly rather than only through the corpus, so the intent survives
    even if the corpus is reorganised.
    """
    from cherenkov.cli.commands.check_suite import _candidate_fields

    code = (
        "def test_show_pet(client):\n"
        "    response = client.get('/pets/1')\n"
        "    assert response.status_code == 200\n"
        "    assert response.ok\n"
        "    data = response.json()\n"
        "    assert data['name'] == 'Rex'\n"
    )
    fields = _candidate_fields(code)
    assert "status_code" not in fields, "response attribute leaked into the field set"
    assert "ok" not in fields, "response attribute leaked into the field set"
    assert "name" in fields, "real body field was lost"


def test_field_behind_a_method_call_is_still_seen() -> None:
    """`data['owner_email'].endswith(...)` must not hide the field.

    A hallucinated field wrapped in a string method was invisible: the LHS is an
    `ast.Call`, so the `Subscript` carrying the name was never reached.
    """
    from cherenkov.cli.commands.check_suite import _candidate_fields

    code = (
        "def test_show_pet(client):\n"
        "    data = client.get('/pets/1').json()\n"
        "    assert data['owner_email'].endswith('@example.com')\n"
        "    assert len(data['tags']) == 2\n"
    )
    fields = _candidate_fields(code)
    assert "owner_email" in fields, "field hidden behind a method call"
    assert "tags" in fields, "field hidden behind len()"
