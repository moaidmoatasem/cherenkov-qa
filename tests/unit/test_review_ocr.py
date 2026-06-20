"""Unit tests for cherenkov/review_ocr/ — OCR integration module."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from cherenkov.review_ocr.models import OCRFinding, OCRReviewOutput, OCRProvider, OCRSeverity
from cherenkov.review_ocr.rules import OCRRuleEngine, BUILT_IN_RULES, _glob_match
from cherenkov.review_ocr.provider import OCRProviderManager
from cherenkov.review_ocr.stage import ReviewStageOCR


# ── Model Tests ──────────────────────────────────────────────────────────────

class TestOCRFinding:
    def test_default_severity_is_info(self):
        f = OCRFinding(file="test.ts", message="test")
        assert f.severity == OCRSeverity.INFO

    def test_critical_severity(self):
        f = OCRFinding(file="test.ts", message="critical issue", severity=OCRSeverity.CRITICAL)
        assert f.severity == OCRSeverity.CRITICAL

    def test_with_all_fields(self):
        f = OCRFinding(
            file="test.ts", line=42, column=5, severity=OCRSeverity.HIGH,
            rule="null-safety", message="Missing optional chaining", suggestion="Add ?.",
        )
        assert f.line == 42
        assert f.rule == "null-safety"
        assert f.suggestion == "Add ?."


class TestOCRReviewOutput:
    def test_default_passed(self):
        o = OCRReviewOutput()
        assert o.passed is True
        assert o.findings == []
        assert o.score_deduction == 0.0

    def test_score_deduction_calculation(self):
        findings = [
            OCRFinding(file="a.ts", severity=OCRSeverity.CRITICAL, message="c1"),
            OCRFinding(file="b.ts", severity=OCRSeverity.HIGH, message="h1"),
            OCRFinding(file="c.ts", severity=OCRSeverity.MEDIUM, message="m1"),
            OCRFinding(file="d.ts", severity=OCRSeverity.LOW, message="l1"),
        ]
        expected = (1 * 0.15) + (1 * 0.10) + (1 * 0.05)  # = 0.30
        o = OCRReviewOutput(findings=findings, passed=False)
        assert o.score_deduction == expected  # auto-calculated via __post_init__
        assert len(o.findings) == 4


# ── Rules Engine Tests ──────────────────────────────────────────────────────

class TestGlobMatch:
    def test_exact_match(self):
        assert _glob_match("test.ts", "test.ts")

    def test_double_star_prefix(self):
        assert _glob_match("**/*.ts", "src/test.ts")
        assert _glob_match("**/*.ts", "test.ts")
        assert _glob_match("**/*.spec.ts", "stub/generated_tests/health.spec.ts")

    def test_double_star_middle(self):
        assert _glob_match("src/**/test.ts", "src/a/b/test.ts")
        assert _glob_match("src/**/test.ts", "src/test.ts")

    def test_no_match(self):
        assert not _glob_match("*.py", "test.ts")

    def test_exclude_pattern(self):
        assert _glob_match("**/node_modules/**", "project/node_modules/pkg/index.js")

    def test_brace_expansion(self):
        assert _glob_match("**/*.{ts,tsx}", "file.ts")
        assert not _glob_match("**/*.{ts,tsx}", "file.py")


class TestOCRRuleEngine:
    def test_built_in_rules_as_fallback(self):
        engine = OCRRuleEngine()
        assert len(engine._layers) >= 1
        assert engine._layers[-1]["rules"] == BUILT_IN_RULES

    def test_resolve_rule_dot_spec_ts(self):
        engine = OCRRuleEngine()
        rule = engine.resolve_rule("/tmp/stub/generated_tests/health.spec.ts")
        assert rule is not None
        assert "Playwright" in rule or "openapi-fetch" in rule

    def test_unknown_file_returns_none(self):
        engine = OCRRuleEngine()
        rule = engine.resolve_rule("/tmp/Makefile")
        assert rule is None

    def test_is_excluded_node_modules(self):
        engine = OCRRuleEngine()
        assert engine.is_excluded("/tmp/project/node_modules/pkg/index.js")

    def test_is_excluded_unsupported_extension(self):
        engine = OCRRuleEngine()
        assert engine.is_excluded("/tmp/file.bin")

    def test_project_rules_override_builtin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rule_dir = os.path.join(tmpdir, ".opencodereview")
            os.makedirs(rule_dir)
            custom_rule = "Custom rule for spec files"
            with open(os.path.join(rule_dir, "rule.json"), "w") as f:
                json.dump({"rules": [{"path": "**/*.spec.ts", "rule": custom_rule}]}, f)
            engine = OCRRuleEngine(repo_root=tmpdir)
            test_file = os.path.join(tmpdir, "generated_tests", "test.spec.ts")
            os.makedirs(os.path.dirname(test_file))
            with open(test_file, "w") as f:
                f.write("// test")
            rule = engine.resolve_rule(test_file)
            assert rule is not None

    def test_rule_priority_cli_over_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_rule_path = os.path.join(tmpdir, "cli_rules.json")
            with open(cli_rule_path, "w") as f:
                json.dump({"rules": [{"path": "**/*.spec.ts", "rule": "cli rule"}]}, f)
            project_dir = os.path.join(tmpdir, "project")
            os.makedirs(os.path.join(project_dir, ".opencodereview"))
            with open(os.path.join(project_dir, ".opencodereview", "rule.json"), "w") as f:
                json.dump({"rules": [{"path": "**/*.spec.ts", "rule": "project rule"}]}, f)
            engine = OCRRuleEngine(cli_rule_path=cli_rule_path, repo_root=project_dir)
            test_file = os.path.join(project_dir, "test.spec.ts")
            with open(test_file, "w") as f:
                f.write("// test")
            rule = engine.resolve_rule(test_file)
            assert rule == "cli rule"


# ── Provider Manager Tests ──────────────────────────────────────────────────

class TestOCRProviderManager:
    def test_default_config_path(self):
        mgr = OCRProviderManager()
        assert ".opencodereview" in mgr.config_path
        assert mgr.config_path.endswith("config.json")

    def test_env_vars_take_priority(self):
        with patch.dict(os.environ, {
            "OCR_LLM_URL": "https://test.api/v1",
            "OCR_LLM_TOKEN": "test-token",
            "OCR_LLM_MODEL": "test-model",
            "OCR_USE_ANTHROPIC": "true",
        }):
            mgr = OCRProviderManager()
            provider = mgr.get_active_provider()
            assert provider.base_url == "https://test.api/v1"
            assert provider.model == "test-model"
            assert provider.auth_token == "test-token"

    def test_env_url_uses_anthropic_protocol(self):
        with patch.dict(os.environ, {
            "OCR_LLM_URL": "https://api.anthropic.com/v1/messages",
            "OCR_LLM_TOKEN": "sk-ant-test",
        }):
            mgr = OCRProviderManager()
            provider = mgr.get_active_provider()
            assert provider.protocol == "anthropic"

    def test_set_and_get_provider(self, tmp_path: Path):
        config_path = str(tmp_path / "config.json")
        mgr = OCRProviderManager(config_path=config_path)
        mgr.set_provider("test-provider", {
            "url": "https://test.api/v1",
            "model": "test-model",
            "api_key": "test-key",
            "protocol": "openai",
        })
        provider = mgr.get_provider("test-provider")
        assert provider is not None
        assert provider.name == "test-provider"
        assert provider.model == "test-model"

    def test_list_providers_empty_config(self, tmp_path: Path):
        config_path = str(tmp_path / "config.json")
        mgr = OCRProviderManager(config_path=config_path)
        providers = mgr.list_providers()
        assert "anthropic" in providers
        assert "openai" in providers

    def test_set_llm_config(self, tmp_path: Path):
        config_path = str(tmp_path / "config.json")
        mgr = OCRProviderManager(config_path=config_path)
        mgr.set_llm_config("model", "claude-test")
        assert mgr.get_llm_config("model") == "claude-test"


# ── Stage Tests ─────────────────────────────────────────────────────────────

class TestReviewStageOCR:
    def test_init(self):
        stage = ReviewStageOCR(run_id="test-run")
        assert stage.run_id == "test-run"

    def test_check_ocr_not_installed(self):
        stage = ReviewStageOCR()
        assert not stage._check_ocr_installed()  # no binary in CI

    def test_get_ocr_binary_default(self):
        stage = ReviewStageOCR()
        binary = stage._get_ocr_binary()
        assert binary == "ocr" or binary == "opencodereview"

    def test_run_skipped_when_not_installed(self):
        stage = ReviewStageOCR(run_id="test")
        gate = stage.run("const x = 1;", scenario_id="test_001")
        assert gate.gate == "ocr"
        assert gate.skipped is True  # no binary available

    def test_parse_ocr_json_empty(self):
        stage = ReviewStageOCR()
        output = stage._parse_ocr_json("{}")
        assert output.passed is True
        assert output.findings == []

    def test_parse_ocr_json_with_findings(self):
        stage = ReviewStageOCR()
        raw = json.dumps({
            "findings": [
                {"file": "test.spec.ts", "line": 15, "severity": "high",
                 "message": "Missing null check", "rule": "null-safety"},
                {"file": "test.spec.ts", "line": 30, "severity": "info",
                 "message": "Consider adding timeout", "rule": "best-practice"},
            ]
        })
        output = stage._parse_ocr_json(raw)
        assert output.passed  # high + info passes (only critical fails)
        assert len(output.findings) == 2
        assert output.findings[0].severity == OCRSeverity.HIGH
        assert output.score_deduction > 0

    def test_parse_ocr_json_only_info(self):
        stage = ReviewStageOCR()
        raw = json.dumps({
            "findings": [
                {"file": "test.spec.ts", "line": 5, "severity": "info",
                 "message": "Style suggestion", "rule": "style"},
            ]
        })
        output = stage._parse_ocr_json(raw)
        assert output.passed  # info-only is a pass

    def test_parse_ocr_json_critical_fails(self):
        stage = ReviewStageOCR()
        raw = json.dumps({
            "findings": [
                {"file": "main.ts", "line": 42, "severity": "critical",
                 "message": "SQL injection risk", "rule": "security"},
            ]
        })
        output = stage._parse_ocr_json(raw)
        assert not output.passed

    def test_parse_ocr_text_with_brackets(self):
        stage = ReviewStageOCR()
        raw = "[critical] main.ts:42 - SQL injection risk\n[info] test.ts:10 - Style issue\n"
        output = stage._parse_ocr_text(raw)
        assert len(output.findings) == 2
        assert output.findings[0].severity == OCRSeverity.CRITICAL

    def test_parse_ocr_text_empty(self):
        stage = ReviewStageOCR()
        output = stage._parse_ocr_text("")
        assert output.passed is True
        assert output.findings == []

    def test_parse_ocr_text_no_match(self):
        stage = ReviewStageOCR()
        output = stage._parse_ocr_text("Some random output without structured format")
        assert output.passed is True
        assert output.findings == []

    def test_score_deduction_findings(self):
        stage = ReviewStageOCR()
        raw = json.dumps({
            "findings": [
                {"file": "a.ts", "line": 1, "severity": "critical", "message": "c1"},
                {"file": "b.ts", "line": 2, "severity": "high", "message": "h1"},
                {"file": "c.ts", "line": 3, "severity": "medium", "message": "m1"},
            ]
        })
        output = stage._parse_ocr_json(raw)
        assert output.score_deduction == 0.30  # 0.15 + 0.10 + 0.05

    def test_parse_ocr_json_summary(self):
        stage = ReviewStageOCR()
        raw = json.dumps({
            "summary": "Found 2 potential issues",
            "model": "claude-opus-4",
            "tokens_used": 1250,
            "findings": [],
        })
        output = stage._parse_ocr_json(raw)
        assert output.agent_summary == "Found 2 potential issues"
        assert output.llm_model == "claude-opus-4"
        assert output.tokens_used == 1250


# ── Integration Point: Gate Result from ReviewStage —───────────────────────

class TestOCRGateInPipeline:
    def test_gate_result_structure(self):
        from cherenkov.core.contracts import GateResult
        gate = GateResult(gate="ocr", passed=True, detail="No issues", skipped=False)
        assert gate.gate == "ocr"
        assert gate.passed is True
        assert gate.skipped is False

    def test_gate_result_skipped(self):
        from cherenkov.core.contracts import GateResult
        gate = GateResult(gate="ocr", passed=True, detail="OCR not available", skipped=True)
        assert gate.skipped is True

    def test_gate_result_quality_impact(self):
        from cherenkov.core.contracts import GateResult
        ocr_gate = GateResult(gate="ocr", passed=False, detail="Critical issues found")
        skipped_gate = GateResult(gate="ocr", passed=True, detail="Skipped", skipped=True)
        assert ocr_gate.passed is False
        assert skipped_gate.skipped is True
        assert skipped_gate.passed is True
