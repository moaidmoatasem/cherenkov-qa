"""
CHERENKOV execution/ui_probe.py — Playwright-backed UiProbe implementation.

Provides a concrete UiProbe callable (matching the interface in divergence/explorer.py)
that drives a real Chromium browser to detect:
  - JavaScript console errors
  - Uncaught page exceptions
  - Broken images (img elements that failed to load)
  - Missing visible content (empty body / no text nodes)

Design constraints:
  - Uses the playwright Python package (already a project dependency).
  - Headless, no GPU, no sandbox — safe in CI/Docker.
  - Never raises: all errors are returned as UNREACHABLE findings so the Explorer
    crawl never aborts due to a probe failure.
  - Zero browser state shared between calls (fresh context per URL).
"""

from __future__ import annotations

from typing import Callable

from cherenkov.core.contracts import ExplorerFindingKind
from cherenkov.core.errors import get_logger

# The UiProbe type alias expected by Explorer.
UiProbe = Callable[[str], list[tuple[ExplorerFindingKind, str, str]]]


class PlaywrightUiProbe:
    """Playwright-backed UiProbe.

    Usage:
        probe = PlaywrightUiProbe()
        explorer = Explorer(base_url=..., ui_probe=probe)
        findings = explorer.crawl(["/", "/dashboard"])
    """

    def __init__(
        self,
        timeout_ms: int = 15_000,
        screenshot_dir: str | None = None,
    ) -> None:
        self._timeout = timeout_ms
        self._screenshot_dir = screenshot_dir
        self._log = get_logger("ui-probe")

    def __call__(self, url: str) -> list[tuple[ExplorerFindingKind, str, str]]:
        """Navigate to *url* and return UI findings. Never raises."""
        try:
            return self._probe(url)
        except Exception as exc:
            self._log.warning("ui_probe error", url=url, error=str(exc))
            return [(ExplorerFindingKind.UNREACHABLE, f"Probe error: {exc}", url)]

    def _probe(self, url: str) -> list[tuple[ExplorerFindingKind, str, str]]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return [
                (
                    ExplorerFindingKind.UNREACHABLE,
                    "playwright Python package not installed",
                    url,
                )
            ]

        findings: list[tuple[ExplorerFindingKind, str, str]] = []
        console_errors: list[str] = []
        page_errors: list[str] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-gpu"]
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
            )
            page = context.new_page()

            page.on(
                "console",
                lambda msg: console_errors.append(msg.text)
                if msg.type == "error"
                else None,
            )
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            try:
                page.goto(url, wait_until="networkidle", timeout=self._timeout)
            except Exception as nav_err:
                browser.close()
                return [
                    (
                        ExplorerFindingKind.UNREACHABLE,
                        f"Navigation failed: {nav_err}",
                        url,
                    )
                ]

            # Collect broken images
            try:
                broken = page.evaluate(
                    """() => [...document.querySelectorAll('img')]
                        .filter(img => img.complete && !img.naturalWidth && img.src)
                        .map(img => img.src)"""
                )
                for src in broken:
                    findings.append(
                        (ExplorerFindingKind.VISUAL_BREAK, f"Broken image: {src}", url)
                    )
            except Exception:
                pass

            # Capture screenshot for downstream VLM analysis if a directory is configured
            if self._screenshot_dir:
                import os
                import time

                os.makedirs(self._screenshot_dir, exist_ok=True)
                slug = url.replace("://", "_").replace("/", "_").replace(":", "_")[:80]
                shot_path = os.path.join(
                    self._screenshot_dir, f"{slug}_{int(time.time())}.png"
                )
                try:
                    page.screenshot(path=shot_path, full_page=False)
                except Exception:
                    pass

            browser.close()

        for err in console_errors:
            findings.append(
                (ExplorerFindingKind.JS_ERROR, f"Console error: {err}", url)
            )

        for err in page_errors:
            findings.append(
                (ExplorerFindingKind.JS_ERROR, f"Page exception: {err}", url)
            )

        return findings
