"""E1.3 adversarial corpus gate — proves cheating suites are caught.

Each parametrized case loads a corpus file and asserts that scan_test_code
flags at least one detection with the expected threat category.  The clean
reference suite must produce zero detections.

This is the CI-backed audit behind the brand promise: guardrails can't be
weakened without breaking these tests.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cherenkov.adversarial.core import ThreatCategory
from cherenkov.adversarial.detector import has_meaningful_body_assertion, scan_test_code

CORPUS_DIR = Path(__file__).parent.parent / "adversarial" / "corpus"


def _read(name: str) -> str:
    return (CORPUS_DIR / name).read_text()


# ---------------------------------------------------------------------------
# Cheat suites: each must be caught
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename,expected_category", [
    ("cheat_tautological.ts",    ThreatCategory.TAUTOLOGICAL_TEST),
    ("cheat_vacuous_body.ts",    ThreatCategory.TAUTOLOGICAL_TEST),
    ("cheat_empty_catch.ts",     ThreatCategory.TAUTOLOGICAL_TEST),
    ("cheat_exfiltration.ts",    ThreatCategory.DATA_EXFILTRATION),
    ("cheat_eval_injection.ts",  ThreatCategory.COMMAND_INJECTION),
    ("cheat_prompt_injection.ts", ThreatCategory.PROMPT_INJECTION),
])
def test_corpus_cheat_is_caught(filename: str, expected_category: ThreatCategory) -> None:
    code = _read(filename)
    findings = scan_test_code(code)
    categories_found = {f.category for f in findings}
    assert findings, f"{filename}: gate found no issues — cheat slipped through"
    assert expected_category in categories_found, (
        f"{filename}: expected {expected_category.value} to be flagged, "
        f"but only found: {[c.value for c in categories_found]}"
    )


# ---------------------------------------------------------------------------
# Clean reference suite: must NOT be caught
# ---------------------------------------------------------------------------

def test_clean_meaningful_passes() -> None:
    code = _read("clean_meaningful.ts")
    findings = scan_test_code(code)
    assert findings == [], (
        f"clean_meaningful.ts was incorrectly flagged: {[f.detail for f in findings]}"
    )


def test_clean_meaningful_has_body_assertions() -> None:
    code = _read("clean_meaningful.ts")
    assert has_meaningful_body_assertion(code), (
        "clean_meaningful.ts should have meaningful body assertions"
    )


# ---------------------------------------------------------------------------
# Meaningful-assertion gate: cheat suites should fail the body-assertion check
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", [
    "cheat_tautological.ts",
    "cheat_vacuous_body.ts",
    "cheat_empty_catch.ts",
])
def test_cheat_lacks_meaningful_body_assertion(filename: str) -> None:
    code = _read(filename)
    assert not has_meaningful_body_assertion(code), (
        f"{filename}: expected no meaningful body assertions, but gate says it has some"
    )
