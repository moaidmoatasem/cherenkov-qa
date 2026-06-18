"""Proves the G0 / E0.2 demonstrator catches each canonical cheat.

Self-contained: imports the sibling `integrity_check` module by path so it runs
whether or not `demos/` is on the default pytest path.
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))

from integrity_check import check  # noqa: E402

SPEC = HERE / "openapi.yaml"
BASE = HERE / "suite_good.py"


def _findings(name):
    return check(SPEC, BASE, HERE / name)


def test_control_is_clean():
    assert _findings("suite_good.py") == []


def test_weakened_assertion_caught():
    r = _findings("suite_cheat_weakened.py")
    assert any("WEAKENED" in x for x in r), r


def test_deleted_check_caught():
    r = _findings("suite_cheat_deleted.py")
    assert any("DELETED" in x for x in r), r


def test_hallucinated_oracle_caught():
    r = _findings("suite_cheat_hallucinated.py")
    assert any("HALLUCINATED" in x for x in r), r


def test_every_cheat_fails_overall():
    for name in (
        "suite_cheat_weakened.py",
        "suite_cheat_deleted.py",
        "suite_cheat_hallucinated.py",
    ):
        assert _findings(name), f"{name} slipped through uncaught"
