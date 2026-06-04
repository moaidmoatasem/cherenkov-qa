"""
CHERENKOV core/errors.py + logging — typed exceptions and structured JSONL logs.
From Week 1, not bolted on later (Non-Negotiable #17).
"""
from __future__ import annotations

  
import json
import sys
import time


# ── typed exceptions (never raise bare Exception in pipeline code) ──────────
class CherenkovError(Exception):
    """Base for all pipeline errors."""
    code = "CHERENKOV_ERROR"


class ProviderJSONError(CherenkovError):
    """Provider output failed JSON validation after the full retry ladder."""
    code = "PROVIDER_JSON_ERROR"


class OllamaJSONError(ProviderJSONError):
    """Ollama-specific model output failed JSON validation after the full retry ladder."""
    code = "INVALID_JSON"


class ContractError(CherenkovError):
    """A stage emitted data that failed its Pydantic contract."""
    code = "CONTRACT_VIOLATION"


class RefDepthError(CherenkovError):
    """$ref resolution hit the depth limit (circular or too deep)."""
    code = "REF_DEPTH"


class SpecTooThinError(CherenkovError):
    """Endpoint richness below the floor and no inference possible."""
    code = "SPEC_TOO_THIN"


class EgressError(CherenkovError):
    """A provider requires egress but the current policy forbids it."""
    code = "EGRESS_BLOCKED"


class AllProvidersFailedError(CherenkovError):
    """All providers (primary + fallback) failed for a request."""
    code = "ALL_PROVIDERS_FAILED"


class CertificationError(CherenkovError):
    """A model tier failed its certification gold set."""
    code = "CERTIFICATION_FAILED"




class LoggerConfig:
    suppress_stderr = False
    events_file = None

# ── structured logging (JSONL, one event per line) ──────────────────────────
class StructuredLogger:
    """Minimal structured logger. One logger per stage. JSONL to stderr (and
    optionally a file). No print() in library code."""

    def __init__(self, stage: str, run_id: str | None = None, file=None):
        self.stage = stage
        self.run_id = run_id
        self._file = file

    def _emit(self, level: str, msg: str, **fields):
        record = {
            "ts": round(time.time(), 3),
            "level": level,
            "stage": self.stage,
            "run_id": self.run_id,
            "msg": msg,
            **fields,
        }
        line = json.dumps(record)
        if not LoggerConfig.suppress_stderr:
            print(line, file=sys.stderr)
        if LoggerConfig.events_file:
            LoggerConfig.events_file.write(line + "\n")
            LoggerConfig.events_file.flush()
        if self._file:
            self._file.write(line + "\n")
            self._file.flush()

    def info(self, msg: str, **f):    self._emit("INFO", msg, **f)
    def warning(self, msg: str, **f): self._emit("WARN", msg, **f)
    def error(self, msg: str, **f):   self._emit("ERROR", msg, **f)


def get_logger(stage: str, run_id: str | None = None, file=None) -> StructuredLogger:
    return StructuredLogger(stage, run_id, file)
