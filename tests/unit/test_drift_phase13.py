"""tests/unit/test_drift_phase13.py — Phase 13 gate tests.

Covers: maker, checker, commit, L2 loop round-trip.
No LLM calls — maker is schema-driven.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cherenkov.drift.detect import DriftFinding, DriftKind
from cherenkov.drift.loop import (
    AutonomyLevel,
    DriftLoop,
    ReconciliationProposal,
)
from cherenkov.drift.maker import build_test_skeleton, make_proposal, patch_suite
from cherenkov.drift.checker import check_proposal, is_meaningful_assertion
from cherenkov.drift.reconcile import (
    DriftReport,
    DriftVerdict,
    GateSignal,
    MagnitudeVerdict,
    SEVERITY,
)


# ── fixtures ───────────────────────────────────────────────────────────────────

_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "1.0"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "parameters": [
                    {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "ok"}},
            },
            "post": {
                "operationId": "createPet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "age":  {"type": "integer"},
                                },
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "created"}},
            },
        },
        "/pets/{id}": {
            "get": {
                "operationId": "getPet",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {
                    "200": {"description": "ok"},
                    "404": {"description": "not found"},
                },
            }
        },
    },
}


def _new_op_finding(op_id: str = "createPet") -> DriftFinding:
    return DriftFinding(
        kind=DriftKind.NEW_OP_UNTESTED,
        operation_id=op_id,
        detail=f"New operation '{op_id}' in spec has no test",
        after=op_id,
    )


def _optional_param_finding(op_id: str = "listPets") -> DriftFinding:
    return DriftFinding(
        kind=DriftKind.ADDED_OPTIONAL_PARAM,
        operation_id=op_id,
        detail=f"New optional parameter 'limit' added to '{op_id}'",
        after="limit",
    )


def _drift_report(findings=None, magnitude=0.75) -> DriftReport:
    from cherenkov.drift.reconcile import MagnitudeVerdict, aggregate, GateSignal, SEVERITY

    findings = findings or [_new_op_finding()]
    signals = [GateSignal(name=f.kind.value, verdict=SEVERITY[f.kind], detail=f) for f in findings]
    gate = aggregate(signals)
    return DriftReport(
        magnitude=magnitude,
        magnitude_label=MagnitudeVerdict.MODERATE_DRIFT,
        findings=findings,
        gate_verdict=gate,
    )


# ── maker tests ────────────────────────────────────────────────────────────────

def test_maker_new_op_untested_builds_skeleton():
    finding = _new_op_finding("createPet")
    proposal = make_proposal(finding, _SPEC)

    assert proposal.operation_id == "createPet"
    assert proposal.drift_kind == DriftKind.NEW_OP_UNTESTED
    assert proposal.patch["op"] == "add_test"
    test = proposal.patch["test"]
    assert test["request"]["method"] == "POST"
    assert test["request"]["path"] == "/pets"
    # Required field 'name' should be in body
    assert "name" in test["request"]["body"]
    # Assertions target 201 (the only 2xx response)
    assert test["assertions"][0]["expected"] == [201]


def test_maker_handles_path_params():
    finding = _new_op_finding("getPet")
    proposal = make_proposal(finding, _SPEC)

    test = proposal.patch["test"]
    assert test["request"]["method"] == "GET"
    assert test["request"]["path"] == "/pets/{id}"
    assert "id" in test["request"].get("path_params", {})


def test_maker_added_optional_param_returns_annotate_patch():
    finding = _optional_param_finding("listPets")
    proposal = make_proposal(finding, _SPEC)

    assert proposal.patch["op"] == "annotate_param"
    assert proposal.patch["param"] == "limit"
    assert proposal.patch["suite_key"] == "listPets"


def test_maker_unknown_op_id_returns_fallback():
    finding = _new_op_finding("doesNotExist")
    proposal = make_proposal(finding, _SPEC)

    assert proposal.patch["op"] == "add_test"
    # Fallback skeleton still has assertions
    assert len(proposal.patch["test"]["assertions"]) >= 1


# ── checker tests ──────────────────────────────────────────────────────────────

def test_checker_accepts_valid_status_assertion():
    ok, reason = is_meaningful_assertion({"type": "status", "expected": [200, 201]})
    assert ok


def test_checker_rejects_empty_assertion():
    ok, reason = is_meaningful_assertion({})
    assert not ok
    assert "empty" in reason


def test_checker_rejects_missing_type():
    ok, reason = is_meaningful_assertion({"expected": [200]})
    assert not ok


def test_checker_rejects_status_with_no_expected():
    ok, reason = is_meaningful_assertion({"type": "status", "expected": []})
    assert not ok


def test_checker_rejects_tautological_self_comparison():
    ok, reason = is_meaningful_assertion(
        {"type": "equals", "field": "status_code", "expected": "status_code"}
    )
    assert not ok


def test_checker_rejects_proposal_with_no_assertions():
    proposal = ReconciliationProposal(
        operation_id="listPets",
        drift_kind=DriftKind.NEW_OP_UNTESTED,
        action="Add test",
        patch={
            "op": "add_test",
            "suite_key": "listPets",
            "test": {
                "name": "smoke",
                "request": {"method": "GET", "path": "/pets"},
                "assertions": [],  # empty!
            },
        },
    )
    assert not check_proposal(proposal)


def test_checker_accepts_valid_maker_output():
    finding = _new_op_finding("createPet")
    proposal = make_proposal(finding, _SPEC)
    assert check_proposal(proposal)


def test_checker_accepts_annotate_param_proposal():
    finding = _optional_param_finding()
    proposal = make_proposal(finding, _SPEC)
    assert check_proposal(proposal)


# ── commit tests ───────────────────────────────────────────────────────────────

def test_patch_suite_adds_test_to_file():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"listPets": [{"name": "existing_test"}]}, f)
        path = Path(f.name)

    try:
        finding = _new_op_finding("createPet")
        proposal = make_proposal(finding, _SPEC)
        proposal.verified = True

        patch_suite([proposal], path)

        suite = json.loads(path.read_text())
        assert "createPet" in suite
        assert suite["createPet"][0]["name"] == "smoke_createPet"
        assert suite["listPets"][0]["name"] == "existing_test"
    finally:
        path.unlink(missing_ok=True)


def test_patch_suite_is_idempotent():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({}, f)
        path = Path(f.name)

    try:
        finding = _new_op_finding("createPet")
        proposal = make_proposal(finding, _SPEC)
        patch_suite([proposal], path)
        patch_suite([proposal], path)  # second call — should not duplicate

        suite = json.loads(path.read_text())
        assert len(suite["createPet"]) == 1
    finally:
        path.unlink(missing_ok=True)


# ── L2 loop round-trip ─────────────────────────────────────────────────────────

def test_l2_round_trip_auto_approve_commits():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({}, f)
        suite_path = Path(f.name)

    try:
        report = _drift_report(
            findings=[_new_op_finding("createPet")],
        )
        loop = DriftLoop.l2_interactive(
            spec=_SPEC,
            suite_path=suite_path,
            auto_approve=True,
        )
        result = loop.run(report)

        assert result.committed
        assert len(result.proposals) == 1
        assert result.proposals[0].operation_id == "createPet"

        # Suite file was updated
        suite = json.loads(suite_path.read_text())
        assert "createPet" in suite
    finally:
        suite_path.unlink(missing_ok=True)


def test_l2_fail_findings_always_escalate():
    from cherenkov.drift.reconcile import aggregate

    fail_finding = DriftFinding(
        kind=DriftKind.BREAKING_SCHEMA_CHANGE,
        operation_id="createPet",
        detail="Parameter 'name' became required",
        before=False,
        after=True,
    )
    report = _drift_report(findings=[fail_finding])
    loop = DriftLoop.l2_interactive(spec=_SPEC, auto_approve=True)
    result = loop.run(report)

    # FAIL findings must never be auto-committed
    assert not result.committed
    assert len(result.escalations) == 1
    assert result.escalations[0].kind == DriftKind.BREAKING_SCHEMA_CHANGE


def test_l2_no_drift_returns_empty_result():
    report = DriftReport(
        magnitude=1.0,
        magnitude_label=MagnitudeVerdict.NEAR_IDENTICAL,
        findings=[],
        gate_verdict=DriftVerdict.PASS,
    )
    loop = DriftLoop.l2_interactive(spec=_SPEC, auto_approve=True)
    result = loop.run(report)

    assert not result.committed
    assert not result.proposals
    assert not result.escalations
