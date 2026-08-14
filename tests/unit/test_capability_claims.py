"""Bind CHERENKOV's published detection claims to what the detector actually does.

CHERENKOV's thesis is that a quality verdict must be independent of the thing
being judged. That principle had no gate pointed at CHERENKOV itself, and the
result was a `check-suite` run that printed

    "HALLUCINATED is NOT IMPLEMENTED for TypeScript"

immediately before printing a HALLUCINATED finding — with README.md carrying the
same dead claim. Nothing failed, because no test connected a documented
capability to the code implementing it. The drift happened to point at modesty;
nothing structural made that the direction.

This module closes that class of gap. Every cell of the README's "Detection depth
by language" table is:

  1. **executed** — a fixture proves the capability is really there, and
  2. **parsed out of README.md** — so the table and the behaviour cannot diverge.

A capability that regresses fails `test_claimed_capabilities_are_real`. A README
that overstates *or understates* fails `test_readme_table_matches_reality`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from cherenkov.cli.commands.check_suite import (
    _check_typescript,
    check_integrity,
    check_suite_cmd,
)

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
SPEC = REPO / "petstore.json"

# ── Fixtures: one honest baseline and one cheat per capability ────────────────

PY_BASELINE = """
def test_get_pet():
    resp = client.get("/pet/1")
    body = resp.json()
    assert body["id"] == 1 and body["name"] == "doggie"
    assert body["status"] == "available"

def test_list_inventory():
    body = client.get("/store/inventory").json()
    assert body["id"] == 7
"""

# `== 1` -> `in (...)`, and the second half of the compound `and` is dropped.
PY_WEAKENED = """
def test_get_pet():
    resp = client.get("/pet/1")
    body = resp.json()
    assert body["id"] in (1, 2, 3)
    assert body["status"] == "available"

def test_list_inventory():
    body = client.get("/store/inventory").json()
    assert body["id"] == 7
"""

PY_DELETED = """
def test_get_pet():
    resp = client.get("/pet/1")
    body = resp.json()
    assert body["id"] == 1 and body["name"] == "doggie"
    assert body["status"] == "available"
"""

# `shipDate` is an Order field. It exists in the spec, but not on /pet/{petId}.
PY_HALLUCINATED = """
def test_get_pet():
    resp = client.get("/pet/1")
    body = resp.json()
    assert body["shipDate"] == "2020-01-01"
"""

TS_BASELINE = """
test('get pet by id', async ({ request }) => {
  const res = await request.get('/pet/1');
  const data = await res.json();
  expect(data.id).toBe(1);
  expect(data.name).toBe('doggie');
});
test('list inventory', async ({ request }) => {
  const res = await request.get('/store/inventory');
  const data = await res.json();
  expect(data.id).toBe(7);
});
"""

TS_WEAKENED = """
test('get pet by id', async ({ request }) => {
  const res = await request.get('/pet/1');
  const data = await res.json();
  expect(data.id).toBeTruthy();
  expect(data.name).toBe('doggie');
});
test('list inventory', async ({ request }) => {
  const res = await request.get('/store/inventory');
  const data = await res.json();
  expect(data.id).toBe(7);
});
"""

TS_DELETED = """
test('get pet by id', async ({ request }) => {
  const res = await request.get('/pet/1');
  const data = await res.json();
  expect(data.id).toBe(1);
});
test('list inventory', async ({ request }) => {
  const res = await request.get('/store/inventory');
  const data = await res.json();
  expect(data.id).toBe(7);
});
"""

TS_HALLUCINATED = """
test('get pet by id', async ({ request }) => {
  const res = await request.get('/pet/1');
  const data = await res.json();
  expect(data.shipDate).toBe('2020-01-01');
});
"""


def _py(candidate: str, baseline: str = PY_BASELINE) -> list[str]:
    return check_integrity(SPEC, baseline, candidate)


def _ts(candidate: str, baseline: str | None = TS_BASELINE) -> list[str]:
    return _check_typescript(candidate, baseline, SPEC)


def _tags(findings: list[str]) -> set[str]:
    return {f.split()[0] for f in findings}


# ── The claim matrix ──────────────────────────────────────────────────────────
#
# Each entry is (language, capability) -> a probe returning True when the
# capability is genuinely present. These probes are the *definition* of what the
# README is allowed to claim.

def _py_weakened() -> bool:
    """Per-assertion and baseline-relative: one half of a compound `and`, only."""
    findings = _py(PY_WEAKENED)
    return any(
        f.startswith("WEAKENED") and "test_get_pet" in f and "body['id']" in f
        for f in findings
    )


def _py_deleted() -> bool:
    """Both a whole test and a single assertion inside a surviving test."""
    whole_test = any(
        f.startswith("DELETED") and "test_list_inventory" in f
        for f in _py(PY_DELETED)
    )
    single_assertion = any(
        f.startswith("DELETED") and "body['name']" in f for f in _py(PY_WEAKENED)
    )
    return whole_test and single_assertion


def _py_hallucinated() -> bool:
    """Scoped to the endpoint: `shipDate` is in the spec, but not on /pet/{petId}."""
    return any(f.startswith("HALLUCINATED") and "shipDate" in f for f in _py(PY_HALLUCINATED))


def _ts_weakened() -> bool:
    findings = _ts(TS_WEAKENED)
    return any(
        f.startswith("WEAKENED") and "get pet by id" in f and "data.id" in f
        for f in findings
    )


def _ts_deleted() -> bool:
    return any(
        f.startswith("DELETED") and "data.name" in f and "get pet by id" in f
        for f in _ts(TS_DELETED)
    )


def _ts_hallucinated() -> bool:
    return any(f.startswith("HALLUCINATED") and "shipDate" in f for f in _ts(TS_HALLUCINATED))


CLAIMS = {
    ("Python", "Weakened"): _py_weakened,
    ("Python", "Deleted"): _py_deleted,
    ("Python", "Hallucinated"): _py_hallucinated,
    ("TypeScript", "Weakened"): _ts_weakened,
    ("TypeScript", "Deleted"): _ts_deleted,
    ("TypeScript", "Hallucinated"): _ts_hallucinated,
}


class TestClaimedCapabilitiesAreReal:
    @pytest.mark.parametrize(("language", "capability"), sorted(CLAIMS))
    def test_claimed_capabilities_are_real(self, language: str, capability: str) -> None:
        probe = CLAIMS[(language, capability)]
        assert probe(), (
            f"README claims {capability} detection for {language}, but the "
            f"detector did not produce it. Either fix the detector or downgrade "
            f"the claim in README.md — do not leave them disagreeing."
        )

    def test_honest_suite_is_not_flagged(self) -> None:
        """The counterweight: none of the above may be bought with false positives."""
        assert _py(PY_BASELINE) == []
        assert _ts(TS_BASELINE) == []


# ── README parity ─────────────────────────────────────────────────────────────

_MARK = re.compile(r"[✅⚠️❌]")


def _readme_detection_table() -> dict[tuple[str, str], str]:
    """Parse the "Detection depth by language" table into `{(lang, cap): mark}`."""
    text = README.read_text(encoding="utf-8")
    rows = [
        line for line in text.splitlines()
        if line.startswith("|") and ("**Python**" in line or "**TypeScript**" in line)
    ]
    assert len(rows) == 2, (
        "Could not find both language rows of the detection table in README.md. "
        "If the table moved or was renamed, update this test — the point is that "
        "the claims stay bound to the code, not that they live at a fixed line."
    )
    out: dict[tuple[str, str], str] = {}
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        language = "Python" if "**Python**" in cells[0] else "TypeScript"
        # cells: [suite, engine, weakened, deleted, hallucinated]
        for capability, cell in zip(("Weakened", "Deleted", "Hallucinated"), cells[2:5]):
            found = _MARK.search(cell)
            assert found, f"No status mark in the {language}/{capability} cell: {cell!r}"
            out[(language, capability)] = found.group(0)
    return out


class TestReadmeMatchesReality:
    @pytest.mark.parametrize(("language", "capability"), sorted(CLAIMS))
    def test_readme_table_matches_reality(self, language: str, capability: str) -> None:
        """A ✅ must be earned, and a capability that works must not be marked ❌.

        Both directions are failures. Understating is the friendlier error, but it
        is the same defect — the table is not being maintained against the code —
        and it is what actually happened here.
        """
        mark = _readme_detection_table()[(language, capability)]
        works = CLAIMS[(language, capability)]()
        if works:
            assert mark == "✅", (
                f"{language}/{capability} detection works, but README marks it "
                f"{mark!r}. Understating is still drift: upgrade the table."
            )
        else:
            assert mark != "✅", (
                f"README marks {language}/{capability} as shipped (✅), but the "
                f"detector did not produce that finding."
            )


class TestCliDisclosureIsTrue:
    """The banner is a claim too, and it is the one users actually read."""

    def _ts_run(self, tmp_path: Path) -> str:
        candidate = tmp_path / "cand.spec.ts"
        candidate.write_text(TS_HALLUCINATED, encoding="utf-8")
        result = CliRunner().invoke(
            check_suite_cmd, ["-c", str(candidate), "-s", str(SPEC)]
        )
        return result.output

    def test_banner_does_not_deny_a_capability_it_then_demonstrates(
        self, tmp_path: Path
    ) -> None:
        output = self._ts_run(tmp_path)
        assert "HALLUCINATED" in output, "fixture no longer exercises the path"
        assert "NOT IMPLEMENTED" not in output.upper(), (
            "The TypeScript banner denies a capability that the same run "
            "demonstrates. This exact contradiction shipped once; it is the "
            "reason this file exists."
        )

    def test_json_output_carries_the_findings(self, tmp_path: Path) -> None:
        """`--json` owns stdout, so the banner must not corrupt the document."""
        candidate = tmp_path / "cand.spec.ts"
        candidate.write_text(TS_HALLUCINATED, encoding="utf-8")
        # Click >= 8.2 separates stdout/stderr by default; the warning banner
        # goes to stderr precisely so it cannot corrupt this document.
        result = CliRunner().invoke(
            check_suite_cmd, ["-c", str(candidate), "-s", str(SPEC), "--json"]
        )
        payload = json.loads(result.stdout)
        assert payload["clean"] is False
        assert any("HALLUCINATED" in f for f in payload["findings"])
