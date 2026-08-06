"""Tests for divergence finding persistence (#903).

Before this, DivergenceReport objects were computed by run_proof, printed, and
dropped — RunStore kept only the scalar divergence_count — so /api/v1/divergences
had nothing real to serve and returned a hardcoded fixture.
"""
from __future__ import annotations

import os

os.environ.setdefault("CHERENKOV_ENV", "development")

import pytest

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)
from cherenkov.persistence.divergence_store import DivergenceStore


def _report(
    report_id: str = "DIV-1",
    endpoint: str = "GET /pet/findByStatus",
    severity: Severity = Severity.HIGH,
) -> DivergenceReport:
    return DivergenceReport(
        id=report_id,
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="spec: status must be one of [available, pending, sold]",
        claim_b="server accepts arbitrary status strings and returns 200",
        evidence=DivergenceEvidence(
            request_summary="GET /pet/findByStatus?status=XYZ → 200 (41ms)",
            response_actual="[]",
            response_expected="400 Bad Request",
            diff="expected 400, got 200",
        ),
        repro_steps=["curl -s '.../pet/findByStatus?status=XYZ'", "# Expected 400, got 200"],
        severity=severity,
        endpoint=endpoint,
        metadata=StageMeta(stage="verify"),
    )


@pytest.fixture
def store(tmp_path):
    return DivergenceStore(db_path=tmp_path / "runs.db")


class TestPersistence:
    def test_save_reports_round_trips_every_field(self, store):
        assert store.save_reports("run-a", [_report()]) == 1

        (rec,) = store.list_for_run("run-a")
        assert rec.finding_key == "run-a:DIV-1"
        assert rec.run_id == "run-a"
        assert rec.endpoint == "GET /pet/findByStatus"
        assert rec.severity == "high"
        assert rec.divergence_class == "D1_spec_code"
        assert "arbitrary status strings" in rec.claim_b
        # The rich fields RunStore threw away are what make this worth storing.
        assert "expected 400, got 200" in rec.evidence_json
        assert "curl" in rec.repro_steps_json

    def test_empty_report_list_writes_nothing(self, store):
        assert store.save_reports("run-a", []) == 0
        assert store.count() == 0
        assert store.list_latest() == []

    def test_findings_are_scoped_to_their_run(self, store):
        store.save_reports("run-old", [_report("OLD-1")])
        store.save_reports("run-new", [_report("NEW-1"), _report("NEW-2")])

        assert {r.report_id for r in store.list_for_run("run-old")} == {"OLD-1"}
        assert {r.report_id for r in store.list_for_run("run-new")} == {"NEW-1", "NEW-2"}

    def test_same_report_id_across_runs_does_not_collide(self, store):
        store.save_reports("run-a", [_report("DIV-1")])
        store.save_reports("run-b", [_report("DIV-1")])
        # Two distinct findings, not one overwritten row.
        assert store.count() == 2

    def test_resaving_the_same_run_is_idempotent(self, store):
        store.save_reports("run-a", [_report("DIV-1")])
        store.save_reports("run-a", [_report("DIV-1")])
        assert store.count() == 1


class TestTriageStatus:
    def test_findings_default_to_reproduced(self, store):
        store.save_reports("run-a", [_report()])
        assert store.list_for_run("run-a")[0].status == "reproduced"

    def test_set_status_persists(self, store):
        store.save_reports("run-a", [_report()])
        assert store.set_status("run-a:DIV-1", "rejected") is True
        assert store.list_for_run("run-a")[0].status == "rejected"

    def test_set_status_on_unknown_finding_returns_false(self, store):
        assert store.set_status("nope:missing", "rejected") is False

    def test_set_status_rejects_values_outside_the_ui_union(self, store):
        store.save_reports("run-a", [_report()])
        with pytest.raises(ValueError):
            store.set_status("run-a:DIV-1", "banana")


class TestApiMapping:
    """The stored row must render into the frontend `Divergence` interface."""

    def test_record_maps_onto_the_frontend_shape(self, store, monkeypatch):
        from cherenkov.web import divergences as mod

        store.save_reports("run-a", [_report()])
        monkeypatch.setattr(mod, "_stored_divergences", lambda: [
            mod._record_to_api(r) for r in store.list_for_run("run-a")
        ])

        (item,) = mod.list_divergences()
        assert set(item) >= {
            "id", "divergenceClass", "endpoint", "severity",
            "status", "claimA", "claimB", "evidence", "reproSteps",
        }
        # types.ts narrows divergenceClass to 'D1'..'D5', not the enum value.
        assert item["divergenceClass"] == "D1"
        assert item["severity"] == "high"
        assert "expected 400, got 200" in item["evidence"]
        assert item["reproSteps"].startswith("curl")

    def test_short_class_handles_every_divergence_class(self):
        from cherenkov.web.divergences import _short_class

        for cls in DivergenceClass.__members__.values():
            assert _short_class(cls.value) in {"D1", "D2", "D3", "D4", "D5"}

    def test_short_class_falls_back_on_junk(self):
        from cherenkov.web.divergences import _short_class

        assert _short_class("") == "D1"
        assert _short_class("nonsense") == "D1"

    def test_format_evidence_skips_absent_fields(self):
        from cherenkov.web.divergences import _format_evidence

        assert _format_evidence({}) == ""
        out = _format_evidence({"request_summary": "GET /x → 500", "diff": ""})
        assert out == "Request: GET /x → 500"


class TestCorpusFallback:
    def test_corpus_is_served_when_no_findings_exist(self, monkeypatch):
        from cherenkov.web import divergences as mod

        monkeypatch.setattr(mod, "_stored_divergences", lambda: [])
        out = mod.list_divergences()
        # Demo seed data for a fresh install that has never run verify.
        assert out and out[0]["id"] == "D-01"

    def test_real_findings_take_precedence_over_the_corpus(self, monkeypatch):
        from cherenkov.web import divergences as mod

        real = [{"id": "run-a:DIV-1", "divergenceClass": "D1", "endpoint": "GET /real",
                 "severity": "high", "status": "reproduced", "claimA": "a",
                 "claimB": "b", "evidence": "e", "reproSteps": "s"}]
        monkeypatch.setattr(mod, "_stored_divergences", lambda: real)

        out = mod.list_divergences()
        assert [d["id"] for d in out] == ["run-a:DIV-1"]
        assert not any(d["id"].startswith("D-0") for d in out)

    def test_store_failure_degrades_to_the_corpus(self, monkeypatch):
        """A broken/absent DB must not 500 the dashboard."""
        from cherenkov.web import divergences as mod

        def _boom():
            raise RuntimeError("db is gone")

        monkeypatch.setattr(
            "cherenkov.persistence.divergence_store.get_divergence_store", _boom
        )
        assert mod._stored_divergences() == []
        assert mod.list_divergences()[0]["id"] == "D-01"


class TestActions:
    def test_action_on_a_real_finding_persists_to_the_store(self, store, monkeypatch):
        from cherenkov.web import divergences as mod

        store.save_reports("run-a", [_report()])
        monkeypatch.setattr(
            "cherenkov.persistence.divergence_store.get_divergence_store", lambda: store
        )
        monkeypatch.setattr(mod, "_stored_divergences", lambda: [
            mod._record_to_api(r) for r in store.list_for_run("run-a")
        ])

        assert mod.apply_action("run-a:DIV-1", "reject") == "rejected"
        # Survives process restart, unlike the in-memory override.
        assert store.list_for_run("run-a")[0].status == "rejected"

    def test_log_sanitiser_strips_newlines(self):
        """A forged id must not be able to inject extra log lines."""
        from cherenkov.web.divergences import _safe_for_log

        assert _safe_for_log("ok-id") == "ok-id"
        assert _safe_for_log("id\nINFO: forged entry") == "idINFO: forged entry"
        assert _safe_for_log("id\r\nfoo") == "idfoo"
        assert len(_safe_for_log("x" * 500)) == 120

    def test_unknown_id_still_raises_keyerror(self, monkeypatch):
        from cherenkov.web import divergences as mod

        monkeypatch.setattr(mod, "_stored_divergences", lambda: [])
        with pytest.raises(KeyError):
            mod.apply_action("does-not-exist", "reject")
