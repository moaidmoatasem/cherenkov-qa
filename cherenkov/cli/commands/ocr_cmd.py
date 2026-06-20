"""OCR CLI commands — Alibaba Open Code Review integration."""
from __future__ import annotations

import os
import sys
import subprocess
import json
import click

from cherenkov.review_ocr.provider import OCRProviderManager
from cherenkov.review_ocr.stage import ReviewStageOCR


@click.group("ocr")
def ocr_cmd() -> None:
    """Alibaba Open Code Review integration."""


@ocr_cmd.command("status")
def ocr_status() -> None:
    """Check OCR binary installation status."""
    binary = os.environ.get("OCR_BINARY", "ocr")
    try:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            click.echo(f"OCR binary ({binary}): installed — {version}")
            sys.exit(0)
        click.echo(f"OCR binary ({binary}): found but returned error:\n  {result.stderr[:200]}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo("OCR binary not found in PATH.", err=True)
        click.echo("Install: npm install -g @alibaba-group/open-code-review")
        click.echo("Or download from: https://github.com/alibaba/open-code-review/releases")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        click.echo("OCR binary timed out.", err=True)
        sys.exit(1)


@ocr_cmd.command("test")
def ocr_test() -> None:
    """Test OCR review with a sample Playwright test."""
    ocr_stage = ReviewStageOCR(run_id="cli")
    test_code = (
        'import { test, expect } from "@playwright/test";\n'
        'import client from "../client";\n\n'
        'test("health check", async () => {\n'
        '  const res = await client.GET("/api/health");\n'
        '  expect(res.status).toBe(200);\n'
        "});\n"
    )
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".spec.ts", prefix="ocr_test_", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        output = ocr_stage.run_on_file(tmp_path, test_code)
    finally:
        os.unlink(tmp_path)
    if output.error:
        click.echo(f"OCR test: ISSUE ({output.error})", err=True)
    elif output.passed:
        click.echo("OCR test: PASS")
    else:
        click.echo("OCR test: ISSUES FOUND", err=True)
    for f in output.findings:
        click.echo(f"  [{f.severity.value}] {f.file}:{f.line} - {f.message[:120]}")
    sys.exit(0 if output.passed else 1)


@ocr_cmd.command("review")
@click.option("--file", "-f", "filepath", default="", help="Path to file to review")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format")
def ocr_review(filepath: str, fmt: str) -> None:
    """Run OCR review on generated tests or a specific file."""
    ocr_stage = ReviewStageOCR(run_id="cli")

    if filepath:
        target_path = os.path.abspath(filepath)
        if not os.path.isfile(target_path):
            click.echo(f"File not found: {target_path}", err=True)
            sys.exit(1)
        with open(target_path, "r", encoding="utf-8") as f:
            code = f.read()
        output = ocr_stage.run_on_file(target_path, code)
        _print_output(output, fmt)
        sys.exit(0 if output.passed else 1)
        return

    stub_dir = os.path.join(os.getcwd(), "stub", "generated_tests")
    if not os.path.isdir(stub_dir):
        click.echo("stub/generated_tests/ not found. Use --file to specify a target.", err=True)
        sys.exit(1)

    files = [f for f in os.listdir(stub_dir) if f.endswith(".spec.ts")]
    if not files:
        click.echo("No generated test files found in stub/generated_tests/")
        sys.exit(0)

    all_passed = True
    results = []
    for fname in sorted(files):
        fpath = os.path.join(stub_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()
        output = ocr_stage.run_on_file(fpath, code)
        results.append({"file": fname, "output": output})
        if not output.passed:
            all_passed = False

    if fmt == "json":
        click.echo(json.dumps([
            {"file": r["file"], "passed": r["output"].passed,
             "findings": [{"severity": f.severity.value, "line": f.line, "message": f.message}
                          for f in r["output"].findings],
             "score_deduction": r["output"].score_deduction}
            for r in results
        ], indent=2))
    else:
        for r in results:
            status = "PASS" if r["output"].passed else "FAIL"
            click.echo(f"  {r['file']}: {status}")
            for f in r["output"].findings:
                click.echo(f"    [{f.severity.value}] {f.file}:{f.line} - {f.message[:120]}")
    sys.exit(0 if all_passed else 1)


@ocr_cmd.group("config")
def ocr_config() -> None:
    """Configure OCR provider and models."""


@ocr_config.command("provider")
def ocr_config_provider() -> None:
    """List and set OCR LLM provider."""
    try:
        mgr = OCRProviderManager()
        providers = mgr.list_providers()
        active = mgr.get_active_provider()
        click.echo("Available providers:")
        for p in providers:
            marker = " *" if active and active.name == p else "  "
            click.echo(f"  {marker}{p}")
        click.echo("\nTo set: cherenkov ocr config set provider <name>")
        click.echo("Or: export OCR_LLM_URL / OCR_LLM_TOKEN / OCR_LLM_MODEL")
    except Exception as e:
        click.echo(f"Error reading provider config: {e}", err=True)
        sys.exit(1)


@ocr_config.command("model")
def ocr_config_model() -> None:
    """Show or set OCR LLM model."""
    try:
        mgr = OCRProviderManager()
        active = mgr.get_active_provider()
        click.echo(f"Active provider: {active.name}")
        click.echo(f"Model: {active.model}")
        click.echo(f"URL: {active.base_url}")
        click.echo(f"Protocol: {active.protocol}")
        click.echo("\nTo change: cherenkov ocr config set model <model_name>")
        click.echo("Or: export OCR_LLM_MODEL=<model_name>")
    except Exception as e:
        click.echo(f"Error reading model config: {e}", err=True)
        sys.exit(1)


@ocr_config.command("set")
@click.argument("key")
@click.argument("value")
def ocr_config_set(key: str, value: str) -> None:
    """Set a config key (e.g. provider, model, url, api_key, protocol)."""
    mgr = OCRProviderManager()
    if key == "provider":
        mgr.set_active_provider(value)
    elif key in ("model", "url", "api_key", "protocol"):
        active = mgr.get_active_provider()
        prov_name = active.name if active and active.name != "env" else "default"
        prov_config = {
            "model": value if key == "model" else active.model,
            "url": value if key == "url" else active.base_url,
            "api_key": value if key == "api_key" else active.auth_token,
            "protocol": value if key == "protocol" else active.protocol,
        }
        # carry over existing values for unchanged keys
        if active and active.name != "env":
            prov_config.setdefault("model", active.model)
            prov_config.setdefault("url", active.base_url)
            prov_config.setdefault("api_key", active.auth_token)
            prov_config.setdefault("protocol", active.protocol)
        mgr.set_provider(prov_name, prov_config)
    else:
        mgr.set_llm_config(key, value)
    click.echo(f"Set {key} = {value}")


def _print_output(output, fmt: str = "text") -> None:
    if fmt == "json":
        click.echo(json.dumps({
            "passed": output.passed,
            "findings": [
                {"file": f.file, "line": f.line, "severity": f.severity.value, "message": f.message}
                for f in output.findings
            ],
            "score_deduction": output.score_deduction,
            "duration_ms": output.duration_ms,
        }, indent=2))
        return

    click.echo(f"  OCR Review: {'PASS' if output.passed else 'FAIL'}")
    click.echo(f"  Duration: {output.duration_ms}ms")
    if output.score_deduction > 0:
        click.echo(f"  Score deduction: {output.score_deduction:.2f}")
    if output.findings:
        click.echo(f"  Findings ({len(output.findings)}):")
        for f in output.findings:
            click.echo(f"    [{f.severity.value}] {f.file}:{f.line} - {f.message[:120]}")
    if output.agent_summary:
        click.echo(f"  Summary: {output.agent_summary[:200]}")
