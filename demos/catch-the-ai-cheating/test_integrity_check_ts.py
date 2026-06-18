"""Proves the TS-edition integrity checker catches each canonical cheat in
Playwright `.spec.ts` suites (CHERENKOV's real artifact format)."""
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))

from integrity_check_ts import check  # noqa: E402

SPEC = HERE / "openapi.yaml"
TS = HERE / "ts"
BASE = TS / "suite_good.spec.ts"


def _findings(name):
    return check(SPEC, BASE, TS / name)


def test_control_is_clean():
    assert _findings("suite_good.spec.ts") == []


def test_weakened_caught():
    r = _findings("suite_cheat_weakened.spec.ts")
    assert any("WEAKENED" in x for x in r), r


def test_deleted_caught():
    r = _findings("suite_cheat_deleted.spec.ts")
    assert any("DELETED" in x for x in r), r


def test_hallucinated_caught():
    r = _findings("suite_cheat_hallucinated.spec.ts")
    assert any("HALLUCINATED" in x for x in r), r


def test_every_cheat_fails_overall():
    for name in (
        "suite_cheat_weakened.spec.ts",
        "suite_cheat_deleted.spec.ts",
        "suite_cheat_hallucinated.spec.ts",
    ):
        assert _findings(name), f"{name} slipped through uncaught"
