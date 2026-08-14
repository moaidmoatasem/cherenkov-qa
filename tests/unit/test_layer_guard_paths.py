"""Structural checks on the layer-guard workflow's wiring.

This file used to assert the *shell plumbing* of the previous gate — that
``CHANGED_FILES`` was exported, that the inline Python read it from
``os.environ``, and (in ``test_mixed_pr_is_a_violation``) that a PR touching core
and infra together tripped the gate. That last one encoded the gate's central
mistake as a requirement: the old workflow classified changes by *which files a
PR touched*, which blocked legitimate vertical slices while never checking the
rule it named. Tests that pin an implementation's plumbing outlive the
implementation and then hold the wrong design in place.

The gate now parses imports (``scripts/check_layer_imports.py``). Behavioural
coverage — violation detected, legal direction allowed, missing layer fails
loudly — lives in ``tests/unit/test_layer_imports.py``. What remains here is the
wiring: the workflow must actually invoke the checker, and the layer prefixes
must keep describing the real tree.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "layer-guard.yml"
CHECKER = REPO_ROOT / "scripts" / "check_layer_imports.py"

CORE_LAYERS = ("cherenkov/core", "cherenkov/ports")
INFRA_LAYERS = ("cherenkov/adapters", "cherenkov/web", "cherenkov/cli")


def _all_cherenkov_files() -> list[str]:
    """Every Python file under ``cherenkov/``, repo-relative with POSIX separators."""
    return [
        str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        for p in (REPO_ROOT / "cherenkov").rglob("*.py")
    ]


def test_workflow_file_exists():
    """The gate must exist to enforce anything."""
    assert WORKFLOW.is_file(), f"layer-guard workflow missing at {WORKFLOW}"


def test_checker_script_exists():
    """The workflow delegates to a script; a missing script is a silent no-op."""
    assert CHECKER.is_file(), f"layer import checker missing at {CHECKER}"


def test_workflow_invokes_the_checker():
    """Guards against a rewrite that drops the enforcement step but keeps the job.

    A green job that runs nothing is worse than no job: it reports safety.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/check_layer_imports.py" in text, (
        "layer-guard must invoke scripts/check_layer_imports.py — otherwise the "
        "workflow passes without checking any boundary"
    )


def test_workflow_uses_real_paths_not_src():
    """The historical ``src/`` mismatch made every prefix resolve to nothing."""
    text = WORKFLOW.read_text(encoding="utf-8")
    for stale in ("src/core/", "src/ports/", "src/adapters/", "src/use_cases/", "src/api/"):
        assert stale not in text, f"stale prefix {stale!r} in layer-guard workflow"


def test_checker_layer_constants_match_this_file():
    """The checker's layers and this file's expectations must not drift apart."""
    text = CHECKER.read_text(encoding="utf-8")
    for prefix in CORE_LAYERS + INFRA_LAYERS:
        assert f'"{prefix}"' in text, (
            f"layer prefix {prefix!r} is absent from {CHECKER.name}; "
            "the checker and this test disagree about the layout"
        )


def test_every_core_prefix_resolves_to_a_file():
    """A core prefix matching nothing would turn the gate into a no-op."""
    tree = _all_cherenkov_files()
    for prefix in CORE_LAYERS:
        assert any(f.startswith(prefix) for f in tree), (
            f"core layer prefix {prefix!r} resolves to no files — "
            "the gate would scan an empty set and pass"
        )


def test_every_infra_prefix_resolves_to_a_file():
    """An infra prefix matching nothing would make violations undetectable."""
    tree = _all_cherenkov_files()
    for prefix in INFRA_LAYERS:
        assert any(f.startswith(prefix) for f in tree), (
            f"infra layer prefix {prefix!r} resolves to no files — "
            "no import could ever be classified as a violation"
        )


def test_no_file_matches_both_core_and_infra():
    """Overlapping prefixes would make a file's layer ambiguous."""
    tree = _all_cherenkov_files()
    for f in tree:
        core = any(f.startswith(p) for p in CORE_LAYERS)
        infra = any(f.startswith(p) for p in INFRA_LAYERS)
        assert not (core and infra), (
            f"file {f} matches both a core layer and an infra layer — "
            "classification is ambiguous"
        )
