"""Unit tests for cherenkov/core/certificate.py — E3.1 / E3.2."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cherenkov.core.certificate import (
    CertSubject,
    CertSummary,
    VerificationCertificate,
    issue_certificate,
    load_certificate,
)
from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceReport,
    Severity,
    StageMeta,
)


# ── fixtures ───────────────────────────────────────────────────────────────────

def _make_report(sev: Severity = Severity.HIGH) -> DivergenceReport:
    ev = DivergenceEvidence(
        request_summary="POST /pet → 500",
        diff="status: expected=400 actual=500",
        response_actual="500",
        response_expected="400",
    )
    return DivergenceReport(
        id="test-001",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="spec says 400",
        claim_b="impl returns 500",
        severity=sev,
        endpoint="POST /pet",
        evidence=ev,
        repro_steps=["POST /pet"],
        metadata=StageMeta(stage="proof_run"),
    )


_KEY = bytes.fromhex("a" * 64)  # 32-byte key


# ── E3.1: certificate format ───────────────────────────────────────────────────

class TestCertificateFormat:
    def test_fields_populated(self):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        assert cert.cert_id
        assert cert.issued_at
        assert cert.version == "1.0"
        assert cert.subject.base_url == "http://localhost"

    def test_empty_run_is_pass(self):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        assert cert.verdict == "PASS"
        assert cert.summary.total == 0

    def test_high_divergence_is_fail(self):
        cert = issue_certificate(
            reports=[_make_report(Severity.HIGH)],
            base_url="http://localhost",
        )
        assert cert.verdict == "FAIL"
        assert cert.summary.high == 1

    def test_medium_only_is_warn(self):
        cert = issue_certificate(
            reports=[_make_report(Severity.MEDIUM)],
            base_url="http://localhost",
        )
        assert cert.verdict == "WARN"
        assert cert.summary.medium == 1

    def test_low_only_is_pass(self):
        cert = issue_certificate(
            reports=[_make_report(Severity.LOW)],
            base_url="http://localhost",
        )
        assert cert.verdict == "PASS"
        assert cert.summary.low == 1

    def test_multiple_severities_verdict(self):
        reports = [
            _make_report(Severity.LOW),
            _make_report(Severity.MEDIUM),
            _make_report(Severity.HIGH),
        ]
        cert = issue_certificate(reports=reports, base_url="http://localhost")
        assert cert.verdict == "FAIL"
        assert cert.summary.total == 3

    def test_spec_hash_included_when_spec_provided(self):
        spec = {"openapi": "3.0.0", "info": {"title": "test"}}
        cert = issue_certificate(reports=[], base_url="http://localhost", spec=spec)
        assert cert.subject.spec_hash is not None
        assert len(cert.subject.spec_hash) == 16  # truncated to 16 hex chars

    def test_spec_hash_none_when_no_spec(self):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        assert cert.subject.spec_hash is None

    def test_divergences_serialised(self):
        cert = issue_certificate(
            reports=[_make_report()],
            base_url="http://localhost",
        )
        assert len(cert.divergences_json) == 1
        assert cert.divergences_json[0]["endpoint"] == "POST /pet"


# ── E3.1: fingerprint / tamper detection ──────────────────────────────────────

class TestFingerprint:
    def test_fingerprint_computed_on_seal(self):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        assert len(cert.fingerprint) == 64  # SHA-256 hex

    def test_verify_passes_on_fresh_cert(self):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        assert cert.verify() is True

    def test_verify_detects_tampered_verdict(self):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        cert.verdict = "FAIL"  # tamper
        assert cert.verify() is False

    def test_verify_detects_tampered_summary(self):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        cert.summary.high = 99  # tamper
        assert cert.verify() is False

    def test_signed_cert_verifies_with_correct_key(self):
        cert = issue_certificate(
            reports=[], base_url="http://localhost", signing_key=_KEY
        )
        assert cert.signature != ""
        assert cert.verify(signing_key=_KEY) is True

    def test_signed_cert_fails_with_wrong_key(self):
        cert = issue_certificate(
            reports=[], base_url="http://localhost", signing_key=_KEY
        )
        wrong_key = bytes.fromhex("b" * 64)
        assert cert.verify(signing_key=wrong_key) is False

    def test_unsigned_cert_ignores_key_on_verify(self):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        # No signature was set — verify should still pass (fingerprint only)
        assert cert.verify(signing_key=_KEY) is True


# ── roundtrip: JSON serialise + deserialise ────────────────────────────────────

class TestRoundtrip:
    def test_json_roundtrip_preserves_all_fields(self):
        cert = issue_certificate(
            reports=[_make_report()],
            base_url="http://api.example.com",
            signing_key=_KEY,
        )
        raw = json.dumps(cert.model_dump(), default=str)
        loaded = load_certificate(json.loads(raw))
        assert loaded.cert_id == cert.cert_id
        assert loaded.verdict == cert.verdict
        assert loaded.fingerprint == cert.fingerprint
        assert loaded.signature == cert.signature
        assert loaded.verify(signing_key=_KEY) is True

    def test_file_roundtrip(self, tmp_path: Path):
        cert = issue_certificate(reports=[], base_url="http://localhost")
        p = tmp_path / "cert.json"
        p.write_text(json.dumps(cert.model_dump(), default=str))
        loaded = load_certificate(json.loads(p.read_text()))
        assert loaded.cert_id == cert.cert_id
        assert loaded.verify() is True


# ── E3.2: CLI command ─────────────────────────────────────────────────────────

class TestCertifyCmd:
    def test_help(self):
        from cherenkov.cli.commands.certify import certify_cmd
        runner = CliRunner()
        result = runner.invoke(certify_cmd, ["--help"])
        assert result.exit_code == 0
        assert "--url" in result.output
        assert "--output" in result.output

    def test_zero_config_uses_petstore(self):
        from cherenkov.cli.commands.certify import certify_cmd
        from cherenkov.divergence.proof_run import PETSTORE_BASE_URL
        runner = CliRunner()
        with patch("cherenkov.cli.commands.certify.run_proof", return_value=[]) as mock:
            result = runner.invoke(certify_cmd, [])
        assert result.exit_code == 0
        assert "demo mode" in result.output
        mock.assert_called_once_with(
            base_url=PETSTORE_BASE_URL, spec=None, use_llm=False
        )

    def test_pass_verdict_exit_0(self):
        from cherenkov.cli.commands.certify import certify_cmd
        runner = CliRunner()
        with patch("cherenkov.cli.commands.certify.run_proof", return_value=[]):
            result = runner.invoke(certify_cmd, ["--url", "http://localhost:9"])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_fail_verdict_shown(self):
        from cherenkov.cli.commands.certify import certify_cmd
        runner = CliRunner()
        reports = [_make_report(Severity.HIGH)]
        with patch("cherenkov.cli.commands.certify.run_proof", return_value=reports):
            result = runner.invoke(certify_cmd, ["--url", "http://localhost:9"])
        assert result.exit_code == 0
        assert "FAIL" in result.output

    def test_fail_on_fail_exits_1(self):
        from cherenkov.cli.commands.certify import certify_cmd
        runner = CliRunner()
        reports = [_make_report(Severity.HIGH)]
        with patch("cherenkov.cli.commands.certify.run_proof", return_value=reports):
            result = runner.invoke(
                certify_cmd,
                ["--url", "http://localhost:9", "--fail-on-fail"],
            )
        assert result.exit_code == 1

    def test_fail_on_fail_exits_0_when_clean(self):
        from cherenkov.cli.commands.certify import certify_cmd
        runner = CliRunner()
        with patch("cherenkov.cli.commands.certify.run_proof", return_value=[]):
            result = runner.invoke(
                certify_cmd,
                ["--url", "http://localhost:9", "--fail-on-fail"],
            )
        assert result.exit_code == 0

    def test_output_writes_json_cert(self, tmp_path: Path):
        from cherenkov.cli.commands.certify import certify_cmd
        out = tmp_path / "cert.json"
        runner = CliRunner()
        with patch("cherenkov.cli.commands.certify.run_proof", return_value=[]):
            result = runner.invoke(
                certify_cmd,
                ["--url", "http://localhost:9", "--output", str(out)],
            )
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["verdict"] == "PASS"
        assert len(data["fingerprint"]) == 64

    def test_verify_mode_valid_cert(self, tmp_path: Path):
        from cherenkov.cli.commands.certify import certify_cmd
        cert = issue_certificate(reports=[], base_url="http://localhost")
        p = tmp_path / "cert.json"
        p.write_text(json.dumps(cert.model_dump(), default=str))
        runner = CliRunner()
        result = runner.invoke(certify_cmd, ["--verify", str(p)])
        assert result.exit_code == 0
        assert "VALID" in result.output

    def test_verify_mode_tampered_cert(self, tmp_path: Path):
        from cherenkov.cli.commands.certify import certify_cmd
        cert = issue_certificate(reports=[], base_url="http://localhost")
        data = cert.model_dump()
        data["verdict"] = "FAIL"  # tamper
        p = tmp_path / "cert.json"
        p.write_text(json.dumps(data, default=str))
        runner = CliRunner()
        result = runner.invoke(certify_cmd, ["--verify", str(p)])
        assert result.exit_code == 3
        assert "TAMPERED" in result.output
