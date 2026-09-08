"""The dashboard must request nothing off-origin, and the CSP must say so.

README's headline claim is *"100% private. No telemetry, no cloud calls"*, and
`SecurityHeadersMiddleware` encodes it as `default-src 'self'`. Those two were
never tied together by a test.

They drifted. `index.css` shipped from 2026-08-11 (b462f6b) opening with

    @import url('https://fonts.googleapis.com/css2?family=Inter...')

against a policy of `style-src 'self'` and `font-src 'self'`. The browser
blocked the stylesheet and the gstatic font files on every page load, so the
dashboard rendered in fallback faces while calling out to a third party — both
halves of the claim broken at once. It was removed on 2026-09-07 (#1012).

Nothing caught it for four weeks, and the reason is worth recording. The single
test watching for failed network requests
(`ui/tests/qa/nonfunctional-suite.spec.ts:452`) excludes `fonts.gstatic.com` and
`fonts.googleapis.com` from what it reports — it was taught to ignore exactly
this defect. It would not have mattered either way: `qa-headless.yml` runs only
`headless-qa-user.spec.ts`, so that suite never executes in CI at all.

Hence a Python unit test. It runs in the `unit-tests` job on every pull request,
needs no browser and no server, and asserts against the **shipped** `dist/`
artifacts rather than the sources they are built from.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cherenkov.web.api import app

# Package-relative, never cwd-relative: pytest is invoked from several
# directories in this repo and a cwd-relative path silently resolves to
# nothing when it is not the root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DIST = _REPO_ROOT / "cherenkov" / "web" / "ui" / "dist"

client = TestClient(app)


# ── Off-origin URL extraction ────────────────────────────────────────────────
#
# Only the positions a browser actually fetches. A bare mention of a hostname in
# a CSS comment is not a request — index.css names fonts.googleapis.com in the
# comment explaining why it no longer imports it, and flagging that would make
# the guard unhonest in the opposite direction.

# A URL may be double-quoted, single-quoted, or bare. The quoted forms must be
# read to their closing quote rather than to the first delimiter: a real Google
# Fonts URL carries `;` and `&` inside the quotes (`wght@300;400;500`), and a
# scanner that stops at `;` captures a fragment and still looks like it works.
_QUOTED_OR_BARE = r"""(?:"([^"]*)"|'([^']*)'|([^)\s;]+))"""

_CSS_IMPORT = re.compile(rf"@import\s+(?:url\(\s*)?{_QUOTED_OR_BARE}", re.IGNORECASE)
_CSS_URL = re.compile(rf"url\(\s*{_QUOTED_OR_BARE}", re.IGNORECASE)
_HTML_REF = re.compile(
    r"""<(?:link|script|img|source)\b[^>]*?\b(?:href|src)\s*=\s*["']([^"']+)""",
    re.IGNORECASE,
)

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# Protocol-relative `//host/x` counts: the browser resolves it to the page scheme
# and fetches off-origin just the same.
_OFF_ORIGIN = re.compile(r"^(?:https?:)?//", re.IGNORECASE)


def _off_origin_refs(text: str, patterns) -> list[str]:
    # Deduplicated, first-seen order: `@import url(...)` matches both the import
    # and the url() pattern, and one blocked request should be reported once.
    found: dict[str, None] = {}
    for pattern in patterns:
        for match in pattern.findall(text):
            # Alternation groups yield a tuple; exactly one branch is non-empty.
            url = next((g for g in match if g), "") if isinstance(match, tuple) else match
            if _OFF_ORIGIN.match(url.strip()):
                found[url.strip()] = None
    return list(found)


def _css_refs(text: str) -> list[str]:
    """Off-origin URLs a browser would fetch. Comments are prose, not requests."""
    return _off_origin_refs(_CSS_COMMENT.sub("", text), (_CSS_IMPORT, _CSS_URL))


def _html_refs(text: str) -> list[str]:
    return _off_origin_refs(_HTML_COMMENT.sub("", text), (_HTML_REF,))


# ── The extractor itself must not be vacuous ─────────────────────────────────
#
# Every assertion below is worthless if the scanner cannot see the thing it is
# looking for. These pin it against the exact defect that shipped.

_THE_DEFECT = (
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;"
    "500;600;700&family=JetBrains+Mono:ital,wght@0,300&display=swap');"
)


def test_scanner_catches_the_import_that_actually_shipped():
    """The literal first line of index.css as of b462f6b."""
    assert _css_refs(_THE_DEFECT) == [
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700"
        "&family=JetBrains+Mono:ital,wght@0,300&display=swap"
    ]


@pytest.mark.parametrize(
    "snippet",
    [
        "@import url(https://fonts.googleapis.com/css2?family=Inter);",  # unquoted
        '@import "https://fonts.googleapis.com/css2";',                  # no url()
        "@font-face { src: url('//fonts.gstatic.com/s/inter.woff2'); }",  # protocol-relative
        "body { background: url(https://cdn.example.com/bg.png); }",     # any third party
    ],
)
def test_scanner_catches_off_origin_css_variants(snippet):
    assert _css_refs(snippet), f"scanner blind to: {snippet}"


@pytest.mark.parametrize(
    "snippet",
    [
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">',
        '<script src="//cdn.example.com/analytics.js"></script>',
    ],
)
def test_scanner_catches_off_origin_html_variants(snippet):
    assert _html_refs(snippet), f"scanner blind to: {snippet}"


@pytest.mark.parametrize(
    "snippet",
    [
        '@import "./styles/design-system.css";',                  # relative, fine
        '@import "tailwindcss";',                                 # bare specifier
        "div { background: url(\"data:image/svg+xml,%3csvg/%3e\"); }",  # inlined
        "/* used to @import https://fonts.googleapis.com/css2 */",  # a comment, not a request
    ],
)
def test_scanner_does_not_flag_same_origin_or_prose(snippet):
    assert _css_refs(snippet) == [], f"false positive on: {snippet}"


# ── The shipped dashboard ────────────────────────────────────────────────────


def test_dist_is_present():
    """dist/ is tracked in git; its absence means the guards below check nothing."""
    assert _DIST.is_dir(), f"{_DIST} missing — the offline guards would pass vacuously"


def test_shipped_stylesheets_fetch_nothing_off_origin():
    stylesheets = sorted(_DIST.rglob("*.css"))
    assert stylesheets, "no built stylesheet found — guard would be vacuous"

    offenders = {
        css.relative_to(_REPO_ROOT).as_posix(): refs
        for css in stylesheets
        if (refs := _css_refs(css.read_text(encoding="utf-8", errors="replace")))
    }
    assert not offenders, (
        f"shipped CSS requests off-origin resources: {offenders}. "
        "Self-host the asset under public/ — the CSP (font-src/style-src 'self') "
        "blocks these, so they fail silently and break the offline guarantee."
    )


def test_shipped_index_html_fetches_nothing_off_origin():
    index = _DIST / "index.html"
    assert index.is_file(), f"{index} missing"

    refs = _html_refs(index.read_text(encoding="utf-8"))
    assert not refs, f"dist/index.html references off-origin resources: {refs}"


def test_index_css_source_has_no_external_import():
    """The source too — dist can lag, and this is the file that regressed."""
    source = _REPO_ROOT / "cherenkov" / "web" / "ui" / "src" / "index.css"
    assert source.is_file(), f"{source} missing"

    refs = _css_refs(source.read_text(encoding="utf-8"))
    assert not refs, f"src/index.css imports off-origin resources: {refs}"


# ── The policy that is supposed to enforce all of the above ──────────────────


def _csp() -> str:
    response = client.get("/api/v1/health")
    assert response.status_code == 200, response.text
    header = response.headers.get("Content-Security-Policy")
    assert header, "no Content-Security-Policy header on the response"
    return header


def _csp_directives() -> dict[str, str]:
    """Parse the policy into {directive: sources}.

    Substring matching is not good enough here. `"font-src 'self'" in csp` stays
    true when the policy is widened to `font-src 'self' https://fonts.gstatic.com`
    — the exact loosening this test exists to catch — so the value is compared
    whole.
    """
    directives = {}
    for part in _csp().split(";"):
        if tokens := part.split():
            directives[tokens[0]] = " ".join(tokens[1:])
    return directives


def test_csp_header_is_actually_sent():
    assert _csp_directives()["default-src"] == "'self'"


@pytest.mark.parametrize(
    ("directive", "sources"),
    [
        ("default-src", "'self'"),
        ("script-src", "'self'"),
        ("font-src", "'self'"),
        ("frame-ancestors", "'none'"),
    ],
)
def test_csp_confines_the_dashboard_to_its_own_origin(directive, sources):
    directives = _csp_directives()
    assert directive in directives, f"{directive} absent from the policy"
    assert directives[directive] == sources


def test_csp_permits_no_third_party_host():
    """No directive may name an external origin.

    The tempting repair for the font breakage was widening the policy to
    `font-src 'self' https://fonts.gstatic.com` — which would have kept the
    cloud call and merely stopped the browser complaining. Removing the
    dependency was the fix; this pins that choice.
    """
    csp = _csp()
    hosts = re.findall(r"(?:https?:)?//[^\s;]+", csp)
    assert not hosts, f"CSP allow-lists third-party origins: {hosts}"


def test_csp_does_not_allow_unsafe_eval():
    assert "unsafe-eval" not in _csp()
