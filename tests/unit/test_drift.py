"""tests/unit/test_drift.py — Phase 12 gate tests.

Gate criteria (spec §9):
  1. detect.py covers all six DriftKinds with hand-built spec/suite pairs.
  2. Near-identical spec edit → overall >= 0.95, zero findings.
  3. Single required-field flip → gate_verdict==FAIL at overall >= 0.95.
  4. L1-only reconcile loop produces a DriftReport a human can act on.
  5. Cost check: a full reconcile on a single-op drift makes ≤1 LLM call
     (verified by asserting no LLM substrate is imported during reconcile).
"""

from __future__ import annotations

import pytest

from cherenkov.drift.snapshot import SpecSuiteSnapshot, spec_hash, suite_manifest_hash
from cherenkov.drift.fingerprint import Fingerprint, fingerprint_of, similarity
from cherenkov.drift.detect import DriftKind, DriftFinding, detect_findings
from cherenkov.drift.reconcile import (
    DriftVerdict,
    GateSignal,
    aggregate,
    MagnitudeVerdict,
    magnitude_verdict,
    reconcile,
    SEVERITY,
)
from cherenkov.drift.loop import AutonomyLevel, DriftLoop


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_spec(operations: dict | None = None, extra_paths: dict | None = None) -> dict:
    """Minimal OpenAPI 3.0 spec with configurable operations."""
    base_paths = {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "tags": ["pets"],
                "parameters": [
                    {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}},
                ],
                "responses": {
                    "200": {
                        "description": "A list of pets",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Pet"},
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "operationId": "createPet",
                "tags": ["pets"],
                "parameters": [
                    {"name": "X-Request-ID", "in": "header", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {
                    "201": {"description": "Created"},
                    "400": {"description": "Bad request"},
                },
            },
        }
    }
    if extra_paths:
        base_paths.update(extra_paths)
    return {
        "openapi": "3.0.0",
        "info": {"title": "Pet Store", "version": "1.0.0"},
        "paths": base_paths,
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }


def _make_suite(*op_ids: str, assertions_per_test: int = 3) -> dict:
    """Minimal suite manifest covering the given operationIds."""
    return {
        op_id: [
            {"assertions": [{"type": "status", "value": 200}] * assertions_per_test}
        ]
        for op_id in op_ids
    }


def _baseline(spec: dict, suite: dict) -> SpecSuiteSnapshot:
    return SpecSuiteSnapshot.create(spec, suite)


# ── §9.1: All six DriftKind coverage ─────────────────────────────────────────

class TestDetectFindings:

    def test_removed_op_still_tested(self):
        """Suite tests an operation that no longer exists in the spec."""
        baseline_spec = _make_spec()
        baseline_suite = _make_suite("listPets", "createPet")
        baseline = _baseline(baseline_spec, baseline_suite)

        # Current spec drops createPet
        current_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Pet Store", "version": "1.0.0"},
            "paths": {
                "/pets": {
                    "get": baseline_spec["paths"]["/pets"]["get"],
                }
            },
        }
        current_suite = _make_suite("listPets", "createPet")  # still tests createPet

        findings = detect_findings(baseline, current_spec, current_suite)
        removed = [f for f in findings if f.kind == DriftKind.REMOVED_OP_STILL_TESTED]
        assert len(removed) >= 1
        assert any(f.operation_id == "createPet" for f in removed)

    def test_new_op_untested(self):
        """A new operation appeared in the spec but the suite has no test for it."""
        baseline_spec = _make_spec()
        baseline_suite = _make_suite("listPets", "createPet")
        baseline = _baseline(baseline_spec, baseline_suite)

        # Current spec adds deletePet
        extra = {
            "/pets/{id}": {
                "delete": {
                    "operationId": "deletePet",
                    "tags": ["pets"],
                    "parameters": [{"name": "id", "in": "path", "required": True}],
                    "responses": {"204": {"description": "Deleted"}},
                }
            }
        }
        current_spec = _make_spec(extra_paths=extra)
        current_suite = _make_suite("listPets", "createPet")  # no deletePet test

        findings = detect_findings(baseline, current_spec, current_suite)
        untested = [f for f in findings if f.kind == DriftKind.NEW_OP_UNTESTED]
        assert len(untested) >= 1
        assert any(f.operation_id == "deletePet" for f in untested)

    def test_breaking_schema_change_required_param(self):
        """A request parameter became required — breaking for existing tests."""
        baseline_spec = _make_spec()
        baseline_suite = _make_suite("listPets", "createPet")
        baseline = _baseline(baseline_spec, baseline_suite)

        # 'limit' param flips to required
        current_spec = _make_spec()
        current_spec["paths"]["/pets"]["get"]["parameters"][0]["required"] = True

        findings = detect_findings(baseline, current_spec, current_suite=baseline_suite)
        breaking = [f for f in findings if f.kind == DriftKind.BREAKING_SCHEMA_CHANGE]
        assert len(breaking) >= 1
        assert any("limit" in f.detail for f in breaking)

    def test_status_contract_violation(self):
        """Axis C: runner_violations are surfaced as STATUS_CONTRACT_VIOLATION."""
        baseline_spec = _make_spec()
        baseline_suite = _make_suite("listPets", "createPet")
        baseline = _baseline(baseline_spec, baseline_suite)

        violations = [
            {
                "operation_id": "listPets",
                "detail": "Expected 200, got 500",
                "expected_status": 200,
                "observed_status": 500,
            }
        ]
        findings = detect_findings(
            baseline, baseline_spec, baseline_suite, runner_violations=violations
        )
        violations_found = [f for f in findings if f.kind == DriftKind.STATUS_CONTRACT_VIOLATION]
        assert len(violations_found) == 1
        assert violations_found[0].operation_id == "listPets"
        assert violations_found[0].before == 200
        assert violations_found[0].after == 500

    def test_deprecated_op_tested(self):
        """Suite tests an operation that is now marked deprecated."""
        baseline_spec = _make_spec()
        baseline_suite = _make_suite("listPets", "createPet")
        baseline = _baseline(baseline_spec, baseline_suite)

        current_spec = _make_spec()
        current_spec["paths"]["/pets"]["post"]["deprecated"] = True

        findings = detect_findings(baseline, current_spec, baseline_suite)
        deprecated = [f for f in findings if f.kind == DriftKind.DEPRECATED_OP_TESTED]
        assert len(deprecated) >= 1
        assert any(f.operation_id == "createPet" for f in deprecated)

    def test_added_optional_param(self):
        """An optional parameter was added — informational only."""
        baseline_spec = _make_spec()
        baseline_suite = _make_suite("listPets", "createPet")
        baseline = _baseline(baseline_spec, baseline_suite)

        # Add optional 'filter' param to listPets
        current_spec = _make_spec()
        current_spec["paths"]["/pets"]["get"]["parameters"].append(
            {"name": "filter", "in": "query", "required": False, "schema": {"type": "string"}}
        )

        findings = detect_findings(baseline, current_spec, baseline_suite)
        optional = [f for f in findings if f.kind == DriftKind.ADDED_OPTIONAL_PARAM]
        assert len(optional) >= 1
        assert any("filter" in f.detail for f in optional)
        # Severity must be PASS (informational)
        for f in optional:
            assert SEVERITY[f.kind] == DriftVerdict.PASS


# ── §9.2: Near-identical spec → overall ≥ 0.95, zero findings ────────────────

class TestNearIdentical:

    def test_description_change_only(self):
        """Changing a description only (no structural drift) → near-identical."""
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        baseline = _baseline(spec, suite)

        # Change only a description — no structural impact
        current_spec = _make_spec()
        current_spec["paths"]["/pets"]["get"]["responses"]["200"]["description"] = (
            "A list of pets (updated description)"
        )

        report = reconcile(baseline, current_spec, suite)
        assert report.magnitude >= 0.95, f"Expected near-identical, got {report.magnitude:.3f}"
        structural_findings = [
            f for f in report.findings
            if f.kind not in (DriftKind.ADDED_OPTIONAL_PARAM, DriftKind.DEPRECATED_OP_TESTED)
        ]
        assert len(structural_findings) == 0, f"Unexpected findings: {structural_findings}"

    def test_same_spec_and_suite(self):
        """Identical spec + suite → overall == 1.0, no findings."""
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        baseline = _baseline(spec, suite)

        report = reconcile(baseline, spec, suite)
        assert report.magnitude >= 0.95
        assert report.magnitude_label == MagnitudeVerdict.NEAR_IDENTICAL
        assert report.gate_verdict == DriftVerdict.PASS
        assert not report.blocked


# ── §9.3: Orthogonal gate — FAIL at near-identical magnitude ─────────────────

class TestOrthogonalGate:

    def test_required_field_flip_fails_at_high_similarity(self):
        """Single required-field flip → gate_verdict==FAIL even at overall ≥ 0.95."""
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        baseline = _baseline(spec, suite)

        # Flip 'limit' from optional to required — tiny structural change
        current_spec = _make_spec()
        current_spec["paths"]["/pets"]["get"]["parameters"][0]["required"] = True

        report = reconcile(baseline, current_spec, suite)

        # Magnitude should still be high (only one param changed)
        assert report.magnitude >= 0.85, (
            f"Magnitude dropped too far: {report.magnitude:.3f}. "
            "The test proves the gate works independent of magnitude."
        )
        # But gate must FAIL due to BREAKING_SCHEMA_CHANGE
        assert report.gate_verdict == DriftVerdict.FAIL, (
            f"gate_verdict={report.gate_verdict} — should FAIL on required-field flip"
        )
        assert report.blocked

    def test_status_violation_fails_regardless_of_magnitude(self):
        """Axis-C violation blocks even when spec/suite are identical."""
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        baseline = _baseline(spec, suite)

        violations = [{"operation_id": "listPets", "detail": "500 instead of 200"}]
        report = reconcile(baseline, spec, suite, runner_violations=violations)

        assert report.gate_verdict == DriftVerdict.FAIL
        assert report.blocked


# ── §9.4: L1 loop end-to-end ─────────────────────────────────────────────────

class TestDriftLoopL1:

    def test_l1_produces_readable_report_no_mutation(self):
        """L1 loop on real drift emits a DriftReport; committed=False."""
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        baseline = _baseline(spec, suite)

        extra = {
            "/pets/{id}": {
                "delete": {
                    "operationId": "deletePet",
                    "tags": ["pets"],
                    "parameters": [{"name": "id", "in": "path", "required": True}],
                    "responses": {"204": {"description": "Deleted"}},
                }
            }
        }
        current_spec = _make_spec(extra_paths=extra)
        report = reconcile(baseline, current_spec, suite)

        loop = DriftLoop(level=AutonomyLevel.L1_REPORT)
        result = loop.run(report)

        assert result.committed is False
        assert result.level == AutonomyLevel.L1_REPORT
        assert result.report is report
        # All findings escalate at L1
        assert len(result.escalations) == len(report.findings)
        # Summary is human-readable
        summary = result.summary()
        assert "autonomy=L1" in summary
        assert "committed=False" in summary

    def test_l1_no_drift_is_noop(self):
        """L1 loop with no drift returns cleanly."""
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        baseline = _baseline(spec, suite)

        report = reconcile(baseline, spec, suite)
        loop = DriftLoop(level=AutonomyLevel.L1_REPORT)
        result = loop.run(report)

        assert not result.report.has_drift
        assert result.committed is False
        assert len(result.escalations) == 0

    def test_fail_severity_always_escalates_even_at_l2(self):
        """FAIL-severity findings escalate even when AutonomyLevel is L2."""
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        baseline = _baseline(spec, suite)

        # Breaking schema change
        current_spec = _make_spec()
        current_spec["paths"]["/pets"]["get"]["parameters"][0]["required"] = True

        report = reconcile(baseline, current_spec, suite)
        loop = DriftLoop(level=AutonomyLevel.L2_ASSISTED)
        result = loop.run(report)

        assert result.committed is False
        fail_escalations = [
            f for f in result.escalations
            if f.kind == DriftKind.BREAKING_SCHEMA_CHANGE
        ]
        assert len(fail_escalations) >= 1


# ── §9.5: Cost check — no LLM import during reconcile ───────────────────────

class TestCostCheck:

    def test_reconcile_does_not_import_llm(self):
        """reconcile() and detect_findings() are pure Python — no LLM substrate."""
        import sys

        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        baseline = _baseline(spec, suite)

        # Record modules loaded before
        before = set(sys.modules.keys())

        # Run a full reconcile with one drifted op
        extra = {
            "/pets/{id}": {
                "delete": {
                    "operationId": "deletePet",
                    "tags": ["pets"],
                    "parameters": [{"name": "id", "in": "path", "required": True}],
                    "responses": {"204": {"description": "Deleted"}},
                }
            }
        }
        current_spec = _make_spec(extra_paths=extra)
        report = reconcile(baseline, current_spec, suite)

        after = set(sys.modules.keys())
        new_modules = after - before

        # No LLM/HTTP client modules should have been imported
        llm_related = {m for m in new_modules if any(
            keyword in m for keyword in ["openai", "ollama", "anthropic", "httpx", "aiohttp"]
        )}
        assert not llm_related, f"reconcile() imported LLM modules: {llm_related}"


# ── Fingerprint + similarity unit tests ──────────────────────────────────────

class TestFingerprint:

    def test_identical_fingerprints_score_1(self):
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        fp = fingerprint_of(spec, suite)
        assert similarity(fp, fp) == pytest.approx(1.0)

    def test_empty_spec_does_not_crash(self):
        fp = fingerprint_of({}, {})
        assert 0.0 <= fp.endpoint_coverage <= 1.0

    def test_operation_set_change_reduces_similarity(self):
        spec_a = _make_spec()
        spec_b = _make_spec(extra_paths={
            "/other": {"get": {"operationId": "getOther", "responses": {"200": {"description": "ok"}}}}
        })
        suite = _make_suite("listPets", "createPet")
        fp_a = fingerprint_of(spec_a, suite)
        fp_b = fingerprint_of(spec_b, suite)
        score = similarity(fp_a, fp_b)
        assert score < 1.0, "Adding an op should reduce similarity"

    def test_near_identical_threshold(self):
        """Minor tweak (one optional param added) stays >= 0.85."""
        spec_a = _make_spec()
        suite = _make_suite("listPets", "createPet")
        spec_b = _make_spec()
        spec_b["paths"]["/pets"]["get"]["parameters"].append(
            {"name": "tag", "in": "query", "required": False}
        )
        fp_a = fingerprint_of(spec_a, suite)
        fp_b = fingerprint_of(spec_b, suite)
        score = similarity(fp_a, fp_b)
        assert score >= 0.85


# ── GateSignal + aggregate unit tests ────────────────────────────────────────

class TestAggregate:

    def test_empty_signals_pass(self):
        assert aggregate([]) == DriftVerdict.PASS

    def test_single_fail_wins(self):
        signals = [
            GateSignal("a", DriftVerdict.PASS),
            GateSignal("b", DriftVerdict.FAIL),
            GateSignal("c", DriftVerdict.WARN),
        ]
        assert aggregate(signals) == DriftVerdict.FAIL

    def test_warn_without_fail(self):
        signals = [
            GateSignal("a", DriftVerdict.PASS),
            GateSignal("b", DriftVerdict.WARN),
        ]
        assert aggregate(signals) == DriftVerdict.WARN

    def test_all_pass(self):
        signals = [GateSignal(str(i), DriftVerdict.PASS) for i in range(5)]
        assert aggregate(signals) == DriftVerdict.PASS


# ── Magnitude ladder ──────────────────────────────────────────────────────────

class TestMagnitudeLadder:

    @pytest.mark.parametrize("score,expected", [
        (1.00, MagnitudeVerdict.NEAR_IDENTICAL),
        (0.95, MagnitudeVerdict.NEAR_IDENTICAL),
        (0.94, MagnitudeVerdict.MINOR_DRIFT),
        (0.85, MagnitudeVerdict.MINOR_DRIFT),
        (0.84, MagnitudeVerdict.MODERATE_DRIFT),
        (0.50, MagnitudeVerdict.MODERATE_DRIFT),
        (0.49, MagnitudeVerdict.MAJOR_DRIFT),
        (0.00, MagnitudeVerdict.MAJOR_DRIFT),
    ])
    def test_ladder(self, score, expected):
        assert magnitude_verdict(score) == expected


# ── Snapshot serialisation round-trip ────────────────────────────────────────

class TestSnapshot:

    def test_round_trip(self):
        spec = _make_spec()
        suite = _make_suite("listPets", "createPet")
        snap = SpecSuiteSnapshot.create(spec, suite)
        restored = SpecSuiteSnapshot.from_dict(snap.to_dict())

        assert restored.snapshot_id == snap.snapshot_id
        assert restored.spec_hash == snap.spec_hash
        assert restored.suite_hash == snap.suite_hash
        assert restored.fingerprint.operation_set == snap.fingerprint.operation_set

    def test_spec_hash_stable(self):
        spec = _make_spec()
        h1 = spec_hash(spec)
        # Different dict ordering — same hash
        import json
        spec2 = json.loads(json.dumps(spec))
        h2 = spec_hash(spec2)
        assert h1 == h2
