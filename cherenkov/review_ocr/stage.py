from __future__ import annotations

import json
import os
import subprocess
import time
import tempfile
import re
from typing import Optional

from cherenkov.core.contracts import GateResult
from cherenkov.core.errors import get_logger
from cherenkov.core.settings import get_settings
from cherenkov.review_ocr.models import OCRFinding, OCRReviewOutput, OCRSeverity
from cherenkov.review_ocr.rules import OCRRuleEngine


class ReviewStageOCR:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.log = get_logger("OCR_REVIEW", run_id)
        self.rule_engine = OCRRuleEngine(repo_root=os.getcwd())

    def _get_ocr_binary(self) -> str:
        which = os.environ.get("OCR_BINARY", "")
        if which and os.path.isfile(which):
            return which
        for candidate in ["ocr", "opencodereview"]:
            try:
                subprocess.run([candidate, "--version"], capture_output=True, text=True, timeout=5)
                return candidate
            except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
                continue
        return "ocr"

    def _check_ocr_installed(self) -> bool:
        binary = self._get_ocr_binary()
        try:
            result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
            return False

    def _parse_ocr_json(self, raw: str) -> OCRReviewOutput:
        output = OCRReviewOutput()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            output.passed = False
            output.error = f"OCR output was not valid JSON: {raw[:200]}"
            return output

        findings_raw = data if isinstance(data, list) else data.get("findings", [])
        if not isinstance(findings_raw, list):
            findings_raw = data.get("issues", [])

        for f in findings_raw:
            severity_str = f.get("severity", "info")
            try:
                severity = OCRSeverity(severity_str)
            except ValueError:
                severity = OCRSeverity.INFO
            finding = OCRFinding(
                file=f.get("file", ""),
                line=f.get("line", 0) or f.get("start_line", 0),
                column=f.get("column", 0),
                severity=severity,
                rule=f.get("rule", f.get("type", "")),
                message=f.get("message", f.get("description", "")),
                suggestion=f.get("suggestion", ""),
            )
            output.findings.append(finding)

        output.agent_summary = data.get("summary", data.get("agent_summary", ""))
        output.llm_model = data.get("model", "")
        output.llm_provider = data.get("provider", "")
        output.tokens_used = data.get("tokens", data.get("tokens_used", 0))

        critical_count = sum(1 for f in output.findings if f.severity == OCRSeverity.CRITICAL)
        high_count = sum(1 for f in output.findings if f.severity == OCRSeverity.HIGH)
        medium_count = sum(1 for f in output.findings if f.severity == OCRSeverity.MEDIUM)

        output.score_deduction = (critical_count * 0.15) + (high_count * 0.10) + (medium_count * 0.05)
        output.passed = critical_count == 0
        return output

    def _parse_ocr_text(self, raw: str) -> OCRReviewOutput:
        output = OCRReviewOutput()
        if not raw.strip():
            output.passed = True
            return output

        severity_map = {
            "critical": OCRSeverity.CRITICAL,
            "error": OCRSeverity.HIGH,
            "warn": OCRSeverity.MEDIUM,
            "info": OCRSeverity.INFO,
        }
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            match = re.match(r"\[(critical|error|warn|info)\]\s+(.*)", line, re.IGNORECASE)
            if match:
                sev = severity_map.get(match.group(1).lower(), OCRSeverity.INFO)
                msg = match.group(2)
                file_match = re.match(r"(\S+):(\d+):?\s*(.*)", msg)
            else:
                file_match = re.match(r"(\S+):(\d+):?\s*(.*)", line)
                if file_match:
                    sev = OCRSeverity.INFO
                    msg = file_match.group(3)
                else:
                    continue

            if file_match:
                finding = OCRFinding(
                    file=file_match.group(1),
                    line=int(file_match.group(2)),
                    severity=sev,
                    message=msg,
                )
            else:
                finding = OCRFinding(message=line, severity=sev)
            output.findings.append(finding)

        critical_count = sum(1 for f in output.findings if f.severity == OCRSeverity.CRITICAL)
        high_count = sum(1 for f in output.findings if f.severity == OCRSeverity.HIGH)
        output.score_deduction = (critical_count * 0.15) + (high_count * 0.10)
        output.passed = critical_count == 0
        return output

    def run_on_file(self, filepath: str, test_code: str) -> OCRReviewOutput:
        t0 = time.time()
        binary = self._get_ocr_binary()

        ext = os.path.splitext(filepath)[1].lower()
        if ext and ext not in self.rule_engine.SUPPORTED_EXTENSIONS:
            err_msg = f"Unsupported file type '{ext}' — OCR review only supports: {', '.join(sorted(self.rule_engine.SUPPORTED_EXTENSIONS))}"
            self.log.warning("ocr_unsupported_type", file=filepath, ext=ext)
            return OCRReviewOutput(passed=True, score_deduction=0.0, error=err_msg, duration_ms=0)

        if self.rule_engine.is_excluded(filepath):
            self.log.info("ocr_file_excluded", file=filepath)
            return OCRReviewOutput(passed=True, score_deduction=0.0, error="File excluded by OCR rule engine", duration_ms=0)

        tmpdir = tempfile.mkdtemp(prefix="cherenkov_ocr_")
        rel_path = os.path.relpath(filepath, os.getcwd())

        try:
            os.makedirs(os.path.dirname(os.path.join(tmpdir, rel_path)), exist_ok=True)
            with open(os.path.join(tmpdir, rel_path), "w", encoding="utf-8") as f:
                f.write(test_code)

            rule = self.rule_engine.resolve_rule(filepath)
            cmd = [binary, "review", "--repo", tmpdir, "--file", rel_path, "--format", "json"]
            if rule:
                rule_file = os.path.join(tmpdir, ".opencodereview", "rule.json")
                os.makedirs(os.path.dirname(rule_file), exist_ok=True)
                with open(rule_file, "w", encoding="utf-8") as f:
                    json.dump({"rules": [{"path": rel_path, "rule": rule}]}, f)
                cmd.extend(["--rule", rule_file])

            self.log.info("ocr_review_start", file=rel_path, binary=binary)
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=get_settings().OCR_TIMEOUT_SECONDS
            )
            dt = int((time.time() - t0) * 1000)
            self.log.info("ocr_review_done", returncode=result.returncode, duration_ms=dt)

            combined_output = (result.stdout or "") + (result.stderr or "")
            if "does not support image" in combined_output or "image.png" in combined_output:
                self.log.warning("ocr_llm_image_rejected")
                return OCRReviewOutput(passed=True, score_deduction=0.0, error="OCR LLM does not support image input", duration_ms=dt)

            if result.returncode != 0:
                output = self._parse_ocr_text(result.stdout or result.stderr)
            else:
                output = self._parse_ocr_json(result.stdout)

            output.duration_ms = dt
            return output

        except subprocess.TimeoutExpired:
            dt = int((time.time() - t0) * 1000)
            self.log.warning("ocr_review_timeout", duration_ms=dt)
            return OCRReviewOutput(passed=True, score_deduction=0.0, error="OCR review timed out", duration_ms=dt)
        except FileNotFoundError:
            dt = int((time.time() - t0) * 1000)
            self.log.warning("ocr_binary_not_found")
            return OCRReviewOutput(passed=True, score_deduction=0.0, error="OCR binary not found", duration_ms=dt)
        except Exception as e:
            dt = int((time.time() - t0) * 1000)
            err_str = str(e)
            if "does not support image" in err_str or "image.png" in err_str:
                self.log.warning("ocr_llm_image_rejected", error=err_str)
                return OCRReviewOutput(passed=True, score_deduction=0.0, error="OCR LLM rejected file (does not support image input)", duration_ms=dt)
            self.log.error("ocr_review_error", error=err_str)
            return OCRReviewOutput(passed=True, score_deduction=0.0, error=err_str, duration_ms=dt)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def run(self, test_code: str, filepath: Optional[str] = None, scenario_id: str = "") -> GateResult:
        if not self._check_ocr_installed():
            return GateResult(
                gate="ocr",
                passed=True,
                detail="OCR binary not installed. Gate skipped.",
                skipped=True,
            )

        fp = filepath or os.path.join(os.getcwd(), "stub", "generated_tests", f"{scenario_id}.spec.ts")
        output = self.run_on_file(fp, test_code)

        if output.error and not output.findings:
            return GateResult(
                gate="ocr",
                passed=True,
                detail=f"OCR gate skipped: {output.error}",
                skipped=True,
            )

        detail_parts = []
        if output.findings:
            for f in output.findings[:5]:
                detail_parts.append(f"[{f.severity.value}] {f.file}:{f.line} - {f.message[:120]}")
        if output.score_deduction > 0:
            detail_parts.append(f"Score deduction: {output.score_deduction:.2f}")

        detail = "; ".join(detail_parts) if detail_parts else "No issues found by OCR review."

        return GateResult(
            gate="ocr",
            passed=output.passed,
            detail=detail,
            skipped=False,
        )
