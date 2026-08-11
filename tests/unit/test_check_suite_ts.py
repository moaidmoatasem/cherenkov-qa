"""TypeScript integrity path for `cherenkov check-suite` (E0.6 / M0b).

`.spec.ts` is CHERENKOV's own primary output format — the artifact
`ReviewStage` writes and `eject` ships. Until 2026-07-31 it had the weakest
analysis of any supported language:

  * WEAKENED was a whole-file heuristic ("no `.toBe()` anywhere") that never
    consulted the baseline, so weakening nine of ten assertions passed clean
    if a single strong matcher survived somewhere in the file.
  * DELETED compared only `test('...')` names, so an assertion dropped from a
    test that still exists was invisible.
  * HALLUCINATED was dead code — a `pass` statement under a loop, unreachable
    by any input — while `--spec --help` advertised it.

No test covered `_check_typescript`, which is why the dead code survived. This
module is that coverage, using the labelled corpus the demo already shipped.
"""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from cherenkov.cli.commands.check_suite import _check_typescript, check_suite_cmd

DEMO = Path(__file__).parents[2] / "demos" / "catch-the-ai-cheating"
SPEC = DEMO / "openapi.yaml"
TS = DEMO / "ts"
TS_GOOD = TS / "suite_good.spec.ts"
TS_WEAKENED = TS / "suite_cheat_weakened.spec.ts"
TS_DELETED = TS / "suite_cheat_deleted.spec.ts"
TS_HALLUCINATED = TS / "suite_cheat_hallucinated.spec.ts"


def _findings(candidate: Path, baseline: Path | None = TS_GOOD) -> list[str]:
    return _check_typescript(
        candidate.read_text(encoding="utf-8"),
        baseline.read_text(encoding="utf-8") if baseline else None,
        SPEC,
    )


class TestTypeScriptIntegrity:
    """Placeholder docstring.

<description>"""
    def test_honest_suite_is_clean(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        assert _findings(TS_GOOD) == []

    def test_weakened_is_caught_and_names_the_subject(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        findings = _findings(TS_WEAKENED)
        assert any(f.startswith("WEAKENED") for f in findings)
        # Must identify which subject was loosened, not just flag the file.
        assert any("response.status" in f for f in findings)

    def test_weakening_caught_despite_a_surviving_strong_matcher(self) -> None:
        """The old whole-file heuristic passed this suite clean.

        suite_cheat_weakened retains an exact check on total, so "does the file
        contain toBe?" answers yes and the cheat went undetected.
        """
        assert "toBe(99.5)" in TS_WEAKENED.read_text(encoding="utf-8")
        assert any(f.startswith("WEAKENED") for f in _findings(TS_WEAKENED))

    def test_assertion_dropped_from_a_surviving_test_is_caught(self) -> None:
        """Name-only comparison could not see this — the test still exists."""
        dropped = [f for f in _findings(TS_DELETED) if f.startswith("DELETED")]
        assert dropped
        assert any("no longer checked" in f for f in dropped)

    def test_hallucinated_is_implemented(self) -> None:
        """Regression guard: this detection used to return nothing, ever."""
        findings = _findings(TS_HALLUCINATED)
        assert any(f.startswith("HALLUCINATED") for f in findings), (
            "HALLUCINATED detection for TypeScript has regressed to dead code"
        )

    def test_hallucination_check_runs_without_a_baseline(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        findings = _findings(TS_HALLUCINATED, baseline=None)
        assert any(f.startswith("HALLUCINATED") for f in findings)

    def test_no_spec_means_no_hallucination_findings(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        findings = _check_typescript(
            TS_HALLUCINATED.read_text(encoding="utf-8"),
            TS_GOOD.read_text(encoding="utf-8"),
            None,
        )
        assert not any(f.startswith("HALLUCINATED") for f in findings)

    def test_subject_normalisation_treats_casts_as_the_same_subject(self) -> None:
        """`(data as any).total` and `data.total` must not read as two subjects,
        or every cast would look like a dropped assertion."""
        baseline = (
            "test('t', async () => {\n"
            "  expect(data.total).toBe(99.5);\n"
            "});\n"
        )
        candidate = (
            "test('t', async () => {\n"
            "  expect((data as any).total).toBe(99.5);\n"
            "});\n"
        )
    """Placeholder docstring.

<description>"""
        assert _check_typescript(candidate, baseline, None) == []


class TestTypeScriptDisclosure:
    def test_cli_warns_typescript_is_not_ast(self) -> None:
        """The honest warning existed but was unreachable for `.ts` inputs."""
        result = CliRunner().invoke(
            check_suite_cmd,
            ["-c", str(TS_WEAKENED), "-b", str(TS_GOOD), "-s", str(SPEC)],
        )
        assert "regex-based detection" in result.output
        assert "NOT IMPLEMENTED" in result.output

    def test_python_path_does_not_emit_the_typescript_warning(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        result = CliRunner().invoke(
            check_suite_cmd,
            [
                "-c", str(DEMO / "suite_cheat_weakened.py"),
                "-b", str(DEMO / "suite_good.py"),
                "-s", str(SPEC),
            ],
        )
        assert "regex-based detection" not in result.output
