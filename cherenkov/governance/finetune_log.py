"""
CHERENKOV governance/finetune_log.py — fine-tune signal collector.
Authority: v3.1 + delta.

Appends accepted and rejected test-case records to a JSONL file so that
confirmed examples can later feed a fine-tuning dataset for local models.

Research basis: LlamaRestTest's biggest coverage gains came from fine-tuning
on mined API parameter data (arXiv 2501.08598). SpecEnrichStage (added in
the research PR) extracts that context; this module closes the loop by
persisting the generate→review outcome alongside the spec context, creating
a labelled dataset of (spec_context, test_code) → accepted|rejected.

Activation: automatic — ReviewStage calls log_outcome() on AUTO_APPROVE and
REGENERATE verdicts. No config flag needed; the file is append-only and cheap.
Opt out by deleting or symlinking .cherenkov/finetune.jsonl to /dev/null.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class FinetuneLogger:
    """
    Append-only JSONL logger for fine-tune signal collection.

    Each line is a self-contained JSON object:
    {
        "run_id":       str,
        "ts":           int,          # unix timestamp
        "endpoint":     str,          # e.g. "POST /users"
        "case_type":    str,          # "happy_path" | "validation" | ...
        "mutation_id":  str,
        "verdict":      "accepted" | "rejected",
        "quality_score": float,
        "gate_results": [{"gate": str, "passed": bool, "detail": str}],
        "spec_rules":   str,          # rendered SpecRules block (may be "")
        "test_code":    str
    }
    """

    def __init__(self, log_path: str | None = None) -> None:
        default = Path(".cherenkov") / "finetune.jsonl"
        self.log_path = str(Path(log_path) if log_path else default)
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)

    def log_outcome(
        self,
        *,
        run_id: str,
        endpoint: str,
        method: str,
        case_type: str,
        mutation_id: str,
        verdict: str,           # "accepted" | "rejected"
        quality_score: float,
        gate_results: list[dict[str, Any]],
        test_code: str,
        spec_rules: str = "",
    ) -> None:
        """Append one fine-tune signal record. Never raises — write errors are swallowed."""
        record = {
            "run_id": run_id,
            "ts": int(time.time()),
            "endpoint": f"{method.upper()} {endpoint}",
            "case_type": case_type,
            "mutation_id": mutation_id,
            "verdict": verdict,
            "quality_score": round(quality_score, 4),
            "gate_results": gate_results,
            "spec_rules": spec_rules,
            "test_code": test_code,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # never block the pipeline on logging failures

    def tail(self, n: int = 5) -> list[dict[str, Any]]:
        """Return the last N records from the log (for inspection/testing)."""
        try:
            with open(self.log_path, encoding="utf-8") as f:
                lines = f.readlines()
            records = []
            for line in lines[-n:]:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
            return records
        except FileNotFoundError:
            return []
        except Exception:
            return []

    def stats(self) -> dict[str, Any]:
        """Return aggregate accepted/rejected counts from the log."""
        accepted = rejected = 0
        try:
            with open(self.log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        if rec.get("verdict") == "accepted":
                            accepted += 1
                        else:
                            rejected += 1
                    except Exception:
                        pass
        except FileNotFoundError:
            pass
        total = accepted + rejected
        return {
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "accept_rate": round(accepted / total, 4) if total else 0.0,
            "log_path": self.log_path,
        }
