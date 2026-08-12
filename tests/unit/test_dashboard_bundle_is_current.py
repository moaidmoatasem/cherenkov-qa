"""The served dashboard bundle must contain the fix that was made to its source.

`cherenkov/web/ui/dist` is committed and is what `web/routes/static_routes.py`
serves. It is generated, so a source-only change leaves the shipped bundle
stale: the repository looks fixed while every user still runs the old code.

That is not hypothetical. When the SLA panel was rewritten to stop fabricating
data (#762), the committed bundle was not rebuilt, and it contained **none** of
the new panel's strings — nor the old panel's, having gone unbuilt for long
enough to predate the Enterprise workspace entirely. The backend was honest,
the source was honest, and the dashboard a user actually loaded was neither.

These tests are deliberately string-based rather than a build: running `vite`
in the unit suite would be slow and would need node. Checking that a marker
from the current source survives into the bundle is cheap and catches the
failure that actually happened.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_UI = _REPO / "cherenkov" / "web" / "ui"
_PANEL = _UI / "src" / "components" / "workspaces" / "EnterpriseWorkspace" / "SlaDashboard.tsx"
_DIST = _UI / "dist" / "assets"


def _bundle_text() -> str:
    if not _DIST.is_dir():
        pytest.skip("no built dashboard bundle in this checkout")
    parts = [
        p.read_text(encoding="utf-8", errors="ignore")
        for p in _DIST.iterdir()
        if p.suffix in (".js", ".css")
    ]
    if not parts:
        pytest.skip("no built dashboard bundle in this checkout")
    return "\n".join(parts)


# Strings the current SLA panel renders. If the panel is redesigned these must
# be updated to markers from the new copy — that is the point: the assertion is
# meant to fail when the source moves and the bundle does not.
_PANEL_MARKERS = ("Conformance pass rate", "Conformance trend")


@pytest.mark.parametrize("marker", _PANEL_MARKERS)
def test_marker_is_present_in_the_panel_source(marker: str):
    """Guard the guard: a stale marker would make the bundle test vacuous."""
    assert marker in _PANEL.read_text(encoding="utf-8"), (
        f"{marker!r} is no longer in SlaDashboard.tsx; update _PANEL_MARKERS to "
        "strings the current panel renders, or this test proves nothing."
    )


@pytest.mark.parametrize("marker", _PANEL_MARKERS)
def test_committed_bundle_contains_the_current_panel(marker: str):
    """The shipped bundle must have been rebuilt after the panel changed."""
    assert marker in _bundle_text(), (
        f"The committed dashboard bundle does not contain {marker!r} from "
        "SlaDashboard.tsx, so cherenkov/web/ui/dist is stale and users are "
        "served the previous build. Rebuild it:\n"
        "    cd cherenkov/web/ui && npx vite build\n"
        "and commit the result alongside the source change."
    )


def test_panel_source_does_not_fabricate_chart_data():
    """The 30-day chart was drawn from Math.random(), re-rolled every render,
    with tooltips asserting a specific uptime per day (#762).

    Comments are stripped first: the panel documents the removed code in a JSX
    block comment, and that mention must not read as a live call.
    """
    import re

    source = _PANEL.read_text(encoding="utf-8")
    without_comments = re.sub(r"\{?/\*.*?\*/\}?", "", source, flags=re.S)
    without_comments = re.sub(r"^\s*//.*$", "", without_comments, flags=re.M)

    assert "Math.random" not in without_comments, (
        "SlaDashboard.tsx fabricates chart data outside of a comment"
    )
    # The mention in the comment is intentional history; confirm the stripping
    # above actually had something to strip, so this test cannot pass vacuously
    # by mis-parsing the file into nothing.
    assert "Math.random" in source
    assert "Conformance trend" in without_comments


def test_shipped_bundle_does_not_fabricate_sla_chart_data():
    """The same check against what is actually served."""
    bundle = _bundle_text()
    # The fabricated bar heights were `Math.random() * 40 + 60`; minifiers keep
    # the numeric literals adjacent to the call.
    assert "Math.random()*40" not in bundle.replace(" ", "")
    assert "% uptime" not in bundle
