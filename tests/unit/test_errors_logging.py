"""Unit tests for cherenkov/core/errors.py — exception hierarchy, StructuredLogger, set_events_file."""

from __future__ import annotations

import io
import json
import threading
from unittest.mock import patch

import pytest

from cherenkov.core.errors import (
    CherenkovError,
    ProviderJSONError,
    OllamaJSONError,
    ContractError,
    RefDepthError,
    SpecTooThinError,
    EgressError,
    AllProvidersFailedError,
    CertificationError,
    StructuredLogger,
    LoggerConfig,
    get_logger,
    set_events_file,
)


# ── Exception hierarchy ──────────────────────────────────────────────────────

class TestExceptionHierarchy:
    def test_all_errors_inherit_from_cherenkov_error(self):
        for cls in (
            ProviderJSONError, OllamaJSONError, ContractError,
            RefDepthError, SpecTooThinError, EgressError,
            AllProvidersFailedError, CertificationError,
        ):
            assert issubclass(cls, CherenkovError)

    def test_cherenkov_error_inherits_exception(self):
        assert issubclass(CherenkovError, Exception)

    def test_ollama_json_error_inherits_provider_json_error(self):
        assert issubclass(OllamaJSONError, ProviderJSONError)

    def test_error_codes_unique(self):
        classes = [
            CherenkovError, ProviderJSONError, OllamaJSONError, ContractError,
            RefDepthError, SpecTooThinError, EgressError,
            AllProvidersFailedError, CertificationError,
        ]
        codes = [c.code for c in classes]
        assert len(codes) == len(set(codes))

    def test_errors_are_catchable_as_cherenkov_error(self):
        for cls in (ContractError, EgressError, CertificationError):
            with pytest.raises(CherenkovError):
                raise cls("test message")

    def test_error_message_preserved(self):
        err = ContractError("stage X returned bad type")
        assert "stage X" in str(err)

    def test_egress_error_code(self):
        assert EgressError.code == "EGRESS_BLOCKED"

    def test_contract_error_code(self):
        assert ContractError.code == "CONTRACT_VIOLATION"

    def test_certification_error_code(self):
        assert CertificationError.code == "CERTIFICATION_FAILED"


# ── StructuredLogger ─────────────────────────────────────────────────────────

class TestStructuredLogger:
    def _logger(self, stage="TEST", run_id="r1"):
        return StructuredLogger(stage=stage, run_id=run_id)

    def _capture_stderr(self, logger, method, msg, **fields):
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            getattr(logger, method)(msg, **fields)
        return buf.getvalue().strip()

    def test_info_emits_json_line(self):
        lg = self._logger()
        line = self._capture_stderr(lg, "info", "hello")
        record = json.loads(line)
        assert record["level"] == "INFO"
        assert record["msg"] == "hello"
        assert record["stage"] == "TEST"
        assert record["run_id"] == "r1"

    def test_warning_level(self):
        lg = self._logger()
        line = self._capture_stderr(lg, "warning", "watch out")
        assert json.loads(line)["level"] == "WARN"

    def test_error_level(self):
        lg = self._logger()
        line = self._capture_stderr(lg, "error", "boom")
        assert json.loads(line)["level"] == "ERROR"

    def test_extra_fields_included(self):
        lg = self._logger()
        line = self._capture_stderr(lg, "info", "stage done", duration_ms=42, provider="ollama")
        record = json.loads(line)
        assert record["duration_ms"] == 42
        assert record["provider"] == "ollama"

    def test_timestamp_present(self):
        lg = self._logger()
        line = self._capture_stderr(lg, "info", "ts check")
        record = json.loads(line)
        assert "ts" in record
        assert isinstance(record["ts"], float)
        assert record["ts"] > 0

    def test_suppress_stderr_suppresses_output(self):
        lg = self._logger()
        buf = io.StringIO()
        LoggerConfig.suppress_stderr = True
        try:
            with patch("sys.stderr", buf):
                lg.info("silent")
        finally:
            LoggerConfig.suppress_stderr = False
        assert buf.getvalue() == ""

    def test_writes_to_events_file_when_set(self):
        lg = self._logger()
        buf = io.StringIO()
        set_events_file(buf)
        try:
            with patch("sys.stderr", io.StringIO()):
                lg.info("to file")
        finally:
            set_events_file(None)
        line = buf.getvalue().strip()
        assert json.loads(line)["msg"] == "to file"

    def test_events_file_per_thread_isolation(self):
        """set_events_file() is thread-local — one thread's file doesn't leak."""
        results = {}

        def worker(name, file_obj):
            set_events_file(file_obj)
            lg = StructuredLogger(stage=name)
            with patch("sys.stderr", io.StringIO()):
                lg.info(f"from {name}")
            results[name] = file_obj.getvalue()
            set_events_file(None)

        bufs = {name: io.StringIO() for name in ("A", "B")}
        threads = [threading.Thread(target=worker, args=(n, bufs[n])) for n in ("A", "B")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert "from A" in results["A"]
        assert "from A" not in results["B"]
        assert "from B" in results["B"]


# ── get_logger factory ───────────────────────────────────────────────────────

class TestGetLogger:
    def test_returns_structured_logger(self):
        lg = get_logger("INGEST", "run-42")
        assert isinstance(lg, StructuredLogger)
        assert lg.stage == "INGEST"
        assert lg.run_id == "run-42"

    def test_no_run_id_defaults_none(self):
        lg = get_logger("PLAN")
        assert lg.run_id is None
