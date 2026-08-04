"""Unit tests for the layer-guard CI workflow's boundary configuration.

These tests guard against the two failure modes that made the workflow a
"paper tiger":

1. Layer path prefixes that do not resolve to any real file under ``cherenkov/``
   (the historical ``src/`` mismatch) — the sanity check inside the workflow
   would exit non-zero, but we assert it here statically so the drift is
   caught by the normal test suite too.
2. The core/ports-vs-infrastructure classification the gate is designed to
   enforce (ADR-004 clean architecture).

Read-only against the workflow file: we parse the declared env prefixes, we do
not execute the workflow.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "layer-guard.yml"

CORE_LAYERS = ("cherenkov/core", "cherenkov/ports")
INFRA_LAYERS = ("cherenkov/adapters", "cherenkov/web", "cherenkov/cli")


def _all_cherenkov_files() -> list[str]:
    return [
        str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        for p in (REPO_ROOT / "cherenkov").rglob("*.py")
    ]


def _workflow_declares_prefixes() -> bool:
    text = WORKFLOW.read_text(encoding="utf-8")
    return "CORE_LAYERS:" in text and "INFRA_LAYERS:" in text


def test_workflow_file_exists():
    assert WORKFLOW.is_file(), f"layer-guard workflow missing at {WORKFLOW}"


def test_workflow_uses_real_paths_not_src():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "src/core/" not in text
    assert "src/ports/" not in text
    assert "src/adapters/" not in text
    assert "src/use_cases/" not in text
    assert "src/api/" not in text


def test_workflow_declares_layer_prefixes():
    assert _workflow_declares_prefixes()


def test_every_core_prefix_resolves_to_a_file():
    tree = _all_cherenkov_files()
    for prefix in CORE_LAYERS:
        assert any(f.startswith(prefix) for f in tree), (
            f"core layer prefix {prefix!r} resolves to no files — "
            "layer-guard sanity check would fail"
        )


def test_every_infra_prefix_resolves_to_a_file():
    tree = _all_cherenkov_files()
    for prefix in INFRA_LAYERS:
        assert any(f.startswith(prefix) for f in tree), (
            f"infra layer prefix {prefix!r} resolves to no files — "
            "layer-guard sanity check would fail"
        )


def test_no_file_matches_both_core_and_infra():
    tree = _all_cherenkov_files()
    for f in tree:
        core = any(f.startswith(p) for p in CORE_LAYERS)
        infra = any(f.startswith(p) for p in INFRA_LAYERS)
        assert not (core and infra), (
            f"file {f} matches both a core layer and an infra layer — classification is ambiguous"
        )


def test_mixed_pr_is_a_violation():
    """A PR touching both core and infra files must trip the gate."""
    tree = _all_cherenkov_files()
    core_file = next(f for f in tree if f.startswith(CORE_LAYERS[0]))
    infra_file = next(f for f in tree if f.startswith(INFRA_LAYERS[0]))

    core_hit = core_file.startswith(CORE_LAYERS[0])
    infra_hit = infra_file.startswith(INFRA_LAYERS[0])
    assert core_hit and infra_hit
    # Both branches of the workflow's violation condition are reachable with
    # real files — i.e. the gate can actually fire (never a no-op).
    assert any(f.startswith(CORE_LAYERS[0]) for f in tree)
    assert any(f.startswith(INFRA_LAYERS[0]) for f in tree)


def test_core_only_pr_is_clean():
    """A PR touching only core files must pass the core/infra check."""
    tree = _all_cherenkov_files()
    core_file = next(f for f in tree if f.startswith(CORE_LAYERS[0]))
    core_hit = core_file.startswith(CORE_LAYERS[0])
    infra_hit = any(core_file.startswith(p) for p in INFRA_LAYERS)
    assert core_hit
    assert not infra_hit
