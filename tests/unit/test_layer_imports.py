"""The layer gate must fail on a real violation, and pass on a legitimate slice.

The gate this replaces failed neither: it flagged PRs by which files they
touched, so it blocked vertical slices that were architecturally fine and waved
through a `cherenkov/core` module importing `cherenkov.web`. Both directions are
asserted here so a future rewrite cannot quietly regress into a no-op.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "check_layer_imports.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_layer_imports", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_layer_imports"] = module
    spec.loader.exec_module(module)
    return module


mod = _load()


def _tree(root: Path, files: dict[str, str]) -> Path:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


class TestLayerImports:
    def test_real_repository_is_clean(self) -> None:
        """The invariant the workflow claims to enforce holds today."""
        assert mod.check(REPO) == []

    @pytest.mark.parametrize(
        "statement",
        [
            "from cherenkov.web import app",
            "from cherenkov.web.routes import thing",
            "import cherenkov.adapters",
            "import cherenkov.cli.core",
        ],
    )
    def test_core_importing_infrastructure_is_a_violation(
        self, tmp_path: Path, statement: str
    ) -> None:
        root = _tree(
            tmp_path,
            {
                "cherenkov/core/thing.py": f"{statement}\n",
                "cherenkov/ports/__init__.py": "",
            },
        )
        problems = mod.check(root)
        assert len(problems) == 1
        assert "cherenkov/core/thing.py" in problems[0]

    def test_infrastructure_importing_core_is_allowed(self, tmp_path: Path) -> None:
        """Dependencies point inward — this direction is the whole design."""
        root = _tree(
            tmp_path,
            {
                "cherenkov/core/thing.py": "VALUE = 1\n",
                "cherenkov/ports/__init__.py": "",
                "cherenkov/web/app.py": "from cherenkov.core.thing import VALUE\n",
            },
        )
        assert mod.check(root) == []

    def test_vertical_slice_is_not_a_violation(self, tmp_path: Path) -> None:
        """A domain concept plus the adapter exposing it is fine.

        The previous gate failed exactly this shape, which is why it was routinely
        bypassed rather than obeyed.
        """
        root = _tree(
            tmp_path,
            {
                "cherenkov/core/order.py": "class Order: ...\n",
                "cherenkov/ports/__init__.py": "",
                "cherenkov/cli/order_cmd.py": "from cherenkov.core.order import Order\n",
            },
        )
        assert mod.check(root) == []

    def test_missing_layer_fails_loudly(self, tmp_path: Path) -> None:
        """A renamed layer must break the gate, not silently disable it."""
        root = _tree(tmp_path, {"cherenkov/core/thing.py": "VALUE = 1\n"})
        problems = mod.check(root)
        assert any(p.startswith("CONFIG") and "cherenkov/ports" in p for p in problems)

    def test_unparseable_source_is_reported_not_skipped(self, tmp_path: Path) -> None:
        root = _tree(
            tmp_path,
            {
                "cherenkov/core/broken.py": "def (:\n",
                "cherenkov/ports/__init__.py": "",
            },
        )
        with pytest.raises(SystemExit):
            mod.check(root)
