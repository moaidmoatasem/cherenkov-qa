"""Tests for cherenkov/bench/report.py — bench report rendering."""

from __future__ import annotations

import json

import pytest

import cherenkov.bench.report as report_module
from cherenkov.bench.metrics import BenchReport, GateSummary, SpecBenchResult
from cherenkov.bench.report import (
    _rate_str,
    _verdict_str,
    print_report,
    write_json,
)


def _spec_result(
    spec_path: str = "specs/petstore.json",
    scenario_count: int = 10,
    tsc_pass: int = 9,
    tsc_fail: int = 1,
    tsc_skip: int = 0,
    avg_quality_score: float = 0.92,
    verdicts: dict[str, int] | None = None,
    errors: list[str] | None = None,
) -> SpecBenchResult:
    return SpecBenchResult(
        spec_path=spec_path,
        scenario_count=scenario_count,
        gate_summaries={
            "tsc": GateSummary("tsc", pass_count=tsc_pass, fail_count=tsc_fail, skip_count=tsc_skip)
        },
        avg_quality_score=avg_quality_score,
        verdict_distribution=verdicts if verdicts is not None else {"auto_approve": 8, "hitl": 2},
        elapsed_s=12.34,
        errors=errors or [],
    )


def _bench_report(results=None, thresholds=None) -> BenchReport:
    return BenchReport(
        results=results if results is not None else [_spec_result()],
        thresholds=thresholds
        if thresholds is not None
        else {"compile_rate": 0.9, "quality_score": 0.85},
    )


# ── _rate_str ──────────────────────────────────────────────────────────────────


class TestRateStr:
    """Placeholder docstring.

<description>"""
    def test_none_is_not_available(self):
        """Placeholder docstring.

:return: <description>"""
        assert _rate_str(None) == "N/A"

    @pytest.mark.parametrize(
        ("rate", "expected"),
        [
            (1.0, "[green]100.0%[/green]"),
            (0.9, "[green]90.0%[/green]"),
            (0.899, "[yellow]89.9%[/yellow]"),
            (0.7, "[yellow]70.0%[/yellow]"),
            (0.699, "[red]69.9%[/red]"),
            (0.0, "[red]0.0%[/red]"),
        ],
    )
    def test_colour_band_follows_the_rate(self, rate, expected):
        """Placeholder docstring.

:param rate: <description>
:param expected: <description>
:return: <description>"""
        assert _rate_str(rate) == expected


# ── _verdict_str ───────────────────────────────────────────────────────────────
    """Placeholder docstring.

<description>"""

class TestVerdictStr:
    def test_empty_distribution_is_a_dash(self):
        """Placeholder docstring.

:return: <description>"""
        assert _verdict_str({}) == "—"
        assert _verdict_str({"auto_approve": 0, "hitl": 0}) == "—"

    def test_renders_only_non_zero_buckets_in_order(self):
        """Placeholder docstring.

:return: <description>"""
        assert (
            _verdict_str({"auto_approve": 3, "regenerate": 1}) == "[green]✓3[/green] [red]✗1[/red]"
        )

    def test_renders_all_three_buckets(self):
        """Placeholder docstring.

:return: <description>"""
        out = _verdict_str({"auto_approve": 1, "hitl": 2, "regenerate": 3})
        assert out == "[green]✓1[/green] [yellow]↑2[/yellow] [red]✗3[/red]"

    def test_unknown_keys_only_count_toward_the_total(self):
        """Placeholder docstring.

:return: <description>"""
        assert _verdict_str({"mystery": 4}) == ""
    """Placeholder docstring.

<description>"""


# ── print_report (Rich) ────────────────────────────────────────────────────────


class TestPrintReportRich:
    @pytest.fixture(autouse=True)
    def _requires_rich(self):
        if not report_module._RICH:
            pytest.skip("rich is an optional dependency and is not installed")

    def test_includes_spec_gates_and_summary(self, capsys):
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        print_report(_bench_report())
        out = capsys.readouterr().out
        assert "CHERENKOV bench report" in out
        assert "specs/petstore.json" in out
        assert "elapsed:" in out and "12.3s" in out
        assert "tsc" in out and "90.0%" in out
        assert "Total tests" in out and "10" in out
        assert "BENCH PASSED" in out

    def test_failing_thresholds_are_called_out(self, capsys):
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        report = _bench_report([_spec_result(tsc_pass=1, tsc_fail=9, avg_quality_score=0.2)])
        print_report(report)
        assert "BENCH FAILED" in capsys.readouterr().out

    def test_errors_are_hidden_unless_verbose(self, capsys):
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        report = _bench_report([_spec_result(errors=["tsc crashed"])])
        print_report(report)
        assert "tsc crashed" not in capsys.readouterr().out
        print_report(report, verbose=True)
        out = capsys.readouterr().out
        assert "Errors (1)" in out and "tsc crashed" in out

    def test_thresholds_come_from_the_report(self, capsys):
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        print_report(_bench_report(thresholds={"compile_rate": 0.5, "quality_score": 0.4}))
        out = capsys.readouterr().out
        assert "50%" in out and "40%" in out

    def test_multiple_specs_are_all_rendered(self, capsys):
    """Placeholder docstring.

<description>"""
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        report = _bench_report([_spec_result(spec_path="a.json"), _spec_result(spec_path="b.json")])
        print_report(report)
        out = capsys.readouterr().out
        assert "a.json" in out and "b.json" in out


# ── print_report (plain fallback) ──────────────────────────────────────────────


class TestPrintReportPlain:
    @pytest.fixture(autouse=True)
    def _no_rich(self, monkeypatch):
        monkeypatch.setattr(report_module, "_RICH", False)

    def test_plain_output_has_no_markup(self, capsys):
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        print_report(_bench_report())
        out = capsys.readouterr().out
        assert "[green]" not in out
        assert "Spec: specs/petstore.json" in out
        assert "[tsc] pass=9 fail=1 skip=0 rate=90.0%" in out
        assert "Overall compile rate : 90.0%" in out
        assert "BENCH PASSED" in out

    def test_skipped_gate_rate_is_not_available(self, capsys):
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        report = _bench_report([_spec_result(tsc_pass=0, tsc_fail=0, tsc_skip=5)])
        print_report(report)
        out = capsys.readouterr().out
        assert "rate=N/A" in out
        assert "Overall compile rate : N/A" in out
    """Placeholder docstring.

<description>"""
    def test_verdict_counts_default_to_zero(self, capsys):
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        print_report(_bench_report([_spec_result(verdicts={})]))
        assert "Verdicts: approve=0 hitl=0 regenerate=0" in capsys.readouterr().out

    def test_failure_is_reported(self, capsys):
        """Placeholder docstring.

:param capsys: <description>
:return: <description>"""
        print_report(_bench_report([_spec_result(avg_quality_score=0.1)]))
        assert "BENCH FAILED" in capsys.readouterr().out


# ── write_json ─────────────────────────────────────────────────────────────────


class TestWriteJson:
    def test_writes_the_serialised_report(self, tmp_path):
        """Placeholder docstring.

:param tmp_path: <description>
:return: <description>"""
        report = _bench_report()
        path = tmp_path / "bench_report.json"
        write_json(report, str(path))
        assert json.loads(path.read_text(encoding="utf-8")) == report.to_dict()

    def test_overwrites_an_existing_file(self, tmp_path):
        """Placeholder docstring.

:param tmp_path: <description>
:return: <description>"""
        path = tmp_path / "bench_report.json"
        path.write_text("stale", encoding="utf-8")
        write_json(_bench_report(), str(path))
        assert json.loads(path.read_text(encoding="utf-8"))["total_scenarios"] == 10
