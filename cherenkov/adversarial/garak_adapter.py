from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def is_garak_available() -> bool:
    return shutil.which("garak") is not None


def run_garak(spec_path: str, probes: list[str] | None = None) -> dict[str, Any]:
    if not is_garak_available():
        return {
            "available": False,
            "error": "garak not installed (pip install garak)",
            "findings": [],
        }

    if probes is None:
        probes = ["promptinject", "lmrc", "realtoxicityprompts"]

    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "garak_report.jsonl"
        cmd = [
            "garak",
            "--model_type",
            "rest",
            "--model_name",
            spec_path,
            "--probes",
            ",".join(probes),
            "--report_prefix",
            str(report_path),
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            findings = _parse_garak_output(report_path)
            return {
                "available": True,
                "returncode": result.returncode,
                "stdout_lines": result.stdout.splitlines()[-10:]
                if result.stdout
                else [],
                "stderr_lines": result.stderr.splitlines()[-5:]
                if result.stderr
                else [],
                "findings": findings,
            }
        except subprocess.TimeoutExpired:
            return {
                "available": True,
                "error": "garak timed out after 120s",
                "findings": [],
            }
        except Exception as e:
            return {"available": True, "error": str(e), "findings": []}


def _parse_garak_output(report_path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not report_path.exists():
        for candidate in report_path.parent.glob("*.jsonl"):
            report_path = candidate
            break
    if not report_path.exists():
        return findings
    try:
        for line in report_path.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("entry_type") == "attempt":
                findings.append(
                    {
                        "probe": entry.get("probe", "unknown"),
                        "detector": entry.get("detector", "unknown"),
                        "prompt": entry.get("prompt", "")[:200],
                        "output": entry.get("output", "")[:200],
                        "passed": entry.get("passed", False),
                    }
                )
    except Exception:
        pass
    return findings
