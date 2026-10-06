"""The catch-the-AI-cheating fixtures shipped in stub/generated_tests/.

These files are tracked, demo-critical artefacts (the `demo` beats, golden
corpus and the password_too_short drift case). Nothing in the pipeline may
modify or delete them (invariant D7), and default `validate` runs skip them.
"""
from __future__ import annotations

import os

SHIPPED_FIXTURE_PREFIXES: tuple[str, ...] = ("demo_", "golden_", "password_too_short")


def is_shipped_fixture(path_or_name: str) -> bool:
    """True when the file name belongs to the shipped fixture corpus."""
    return os.path.basename(path_or_name).startswith(SHIPPED_FIXTURE_PREFIXES)
