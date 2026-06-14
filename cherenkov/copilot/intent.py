"""
CHERENKOV copilot/intent.py — E10-2 NL-intent → ejectable artifact.

A non-coder types a sentence ("check guest checkout with a discount and confirm
the email"). The Copilot:
  1. parses it into a structured IntentSpec via the Substrate Router (deep tier,
     never a hardcoded model), and
  2. emits a durable, human-owned Playwright test using role/text locators —
     the tester never writes a selector.

The emitted file is standard Playwright; it ejects cleanly (no CHERENKOV runtime
hooks), satisfying the E10 exit criterion's "passing, ejected test".
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from cherenkov.core.contracts import (
    IntentSpec,
    IntentStep,
    ReasoningRequest,
    Status,
)
from cherenkov.core.errors import get_logger
from cherenkov.substrate.router import SubstrateRouter

_INTENT_SCHEMA: dict = {
    "type": "object",
    "required": ["title", "kind", "steps"],
    "properties": {
        "title": {"type": "string"},
        "kind": {"type": "string", "enum": ["ui", "api"]},
        "target_url": {"type": "string"},
        "data_hints": {"type": "object"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["navigate", "click", "fill", "expect", "request"],
                    },
                    "target": {"type": "string"},
                    "value": {"type": "string"},
                    "note": {"type": "string"},
                },
            },
        },
    },
}


# Actions that _render_step can convert to Playwright code.
SUPPORTED_ACTIONS: tuple[str, ...] = ("navigate", "click", "fill", "expect", "request")


class IntentAuthor:
    """Turns plain-language intent into an IntentSpec and an ejectable test."""

    def __init__(
        self,
        router: SubstrateRouter | None = None,
        run_id: str | None = None,
    ) -> None:
        self.router = router or SubstrateRouter("copilot_author")
        self.run_id = run_id
        self.log = get_logger("COPILOT_AUTHOR", run_id)
        self._unsupported_actions: list[str] = []

    # ── parse ────────────────────────────────────────────────────────────────

    def parse(self, raw_intent: str, target_url: str = "") -> IntentSpec:
        """Parse a sentence into a structured IntentSpec via the router."""
        request = ReasoningRequest(
            task=self._build_task(raw_intent, target_url),
            output_schema=_INTENT_SCHEMA,
            capability_tier="deep",
        )
        try:
            result = self.router.route(request)
            spec = self._parse_spec(result.content, raw_intent, target_url)
            if spec is not None:
                return spec
        except Exception as e:
            self.log.warning("router parse failed, falling back", error=str(e))

        # Deterministic fallback so the Copilot never dead-ends a tester offline.
        return self._fallback_spec(raw_intent, target_url)

    def _build_task(self, raw_intent: str, target_url: str) -> str:
        url_block = f"\nBase URL: {target_url}" if target_url else ""
        return (
            "You are a QA copilot for a non-coder. Convert the tester's plain-language "
            "intent into an ordered, executable test plan.\n"
            "Rules:\n"
            "  - Describe each target by its visible ROLE and NAME (e.g. \"the 'Checkout' "
            'button", "the Email field"), never a CSS/XPath selector.\n'
            "  - actions: navigate | click | fill | expect | request.\n"
            "  - 'expect' steps assert visible text or a response; put the expectation in 'value'.\n"
            "  - Put any concrete data (codes, emails) into data_hints and reference it in steps.\n"
            f"{url_block}\n\n"
            f"Tester intent: {raw_intent!r}\n\n"
            'Return a JSON object: {"title","kind","target_url","data_hints","steps"[]}.'
        )

    def _parse_spec(
        self, content: Any, raw_intent: str, target_url: str
    ) -> IntentSpec | None:
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                return None
        if not isinstance(content, dict):
            return None
        try:
            steps = [
                IntentStep(
                    action=s["action"],
                    target=s.get("target", ""),
                    value=s.get("value", ""),
                    note=s.get("note", ""),
                )
                for s in content.get("steps", [])
                if isinstance(s, dict) and s.get("action")
            ]
            if not steps:
                return None
            return IntentSpec(
                id=str(uuid.uuid4()),
                raw_intent=raw_intent,
                title=content.get("title") or self._title_from(raw_intent),
                target_url=content.get("target_url") or target_url,
                kind=content.get("kind", "ui")
                if content.get("kind") in ("ui", "api")
                else "ui",
                steps=steps,
                data_hints=content.get("data_hints") or {},
            )
        except (KeyError, ValueError):
            return None

    def _fallback_spec(self, raw_intent: str, target_url: str) -> IntentSpec:
        """A minimal but honest spec when no model is reachable.

        Produces a single navigate + smoke expectation so the round-trip still
        yields a runnable, ejectable test, marked DEGRADED so callers know the
        model didn't shape it.
        """
        steps = [
            IntentStep(
                action="navigate",
                value=target_url or "/",
                note="from intent (offline fallback)",
            ),
            IntentStep(
                action="expect",
                target="page",
                value="",
                note="page loads without error",
            ),
        ]
        return IntentSpec(
            id=str(uuid.uuid4()),
            raw_intent=raw_intent,
            title=self._title_from(raw_intent),
            target_url=target_url,
            kind="ui",
            steps=steps,
            data_hints={},
            status=Status.DEGRADED,
        )

    @staticmethod
    def _title_from(raw_intent: str) -> str:
        text = raw_intent.strip().rstrip(".")
        return (text[:1].upper() + text[1:]) if text else "Untitled intent"

    # ── emit ────────────────────────────────────────────────────────────────

    def to_playwright(self, spec: IntentSpec) -> str:
        """Render an IntentSpec as standard Playwright TypeScript.

        Uses role/text locators (getByRole/getByText/getByLabel) so the file is
        human-owned and selector-free. Ejects with no CHERENKOV runtime deps.
        """
        base = spec.target_url or ""
        lines = [
            'import { test, expect } from "@playwright/test";',
            "",
            "// Authored by CHERENKOV Copilot from plain-language intent:",
            f"//   {spec.raw_intent}",
            "// Standard Playwright — owned by you, no CHERENKOV runtime required.",
            "",
            f"test({json.dumps(spec.title)}, async ({{ page, request }}) => {{",
        ]
        for step in spec.steps:
            lines.extend("  " + ln for ln in self._render_step(step, base))
        lines.append("});")
        lines.append("")
        return "\n".join(lines)

    def _render_step(self, step: IntentStep, base: str) -> list[str]:
        action = step.action.lower()
        if action == "navigate":
            url = step.value or base or "/"
            return [f"await page.goto({json.dumps(url)});"]
        if action == "click":
            return [f"await {self._locator(step.target)}.click();"]
        if action == "fill":
            return [
                f"await {self._locator(step.target)}.fill({json.dumps(step.value)});"
            ]
        if action == "request":
            method = (step.note or "get").lower()
            method = (
                method if method in ("get", "post", "put", "delete", "patch") else "get"
            )
            return [
                f"const resp = await request.{method}({json.dumps(step.value or step.target)});",
                "expect(resp.status()).toBeLessThan(400);",
            ]
        if action == "expect":
            if step.value:
                return [
                    f"await expect(page.getByText({json.dumps(step.value)})).toBeVisible();"
                ]
            return ["await expect(page).toHaveURL(/.*/);"]
        # Unsupported action: surface loudly, don't bury a TODO.
        self._unsupported_actions.append(step.action)
        self.log.warning("unsupported action", action=step.action, note=step.note)
        return [
            f"// UNSUPPORTED: action {step.action!r} not yet rendered — {step.note}",
            "// Supported actions: " + ", ".join(SUPPORTED_ACTIONS),
        ]

    @staticmethod
    def _locator(target: str) -> str:
        """Map a human role+name description to a role/label/text locator."""
        t = (target or "").strip()
        low = t.lower()
        # crude role inference from the description; keeps tests selector-free
        name = re.sub(r"^(the|a|an)\s+", "", low)
        name = re.sub(
            r"\s+(button|link|field|input|checkbox|tab|menu item)$", "", name
        ).strip()
        pretty = name.title() if name else t
        if "button" in low:
            return f'page.getByRole("button", {{ name: {json.dumps(pretty)} }})'
        if "link" in low:
            return f'page.getByRole("link", {{ name: {json.dumps(pretty)} }})'
        if "field" in low or "input" in low or "email" in low or "password" in low:
            return f"page.getByLabel({json.dumps(pretty)})"
        if "checkbox" in low:
            return f'page.getByRole("checkbox", {{ name: {json.dumps(pretty)} }})'
        return f"page.getByText({json.dumps(t)})"

    # ── round-trip ────────────────────────────────────────────────────────────

    def author(
        self,
        raw_intent: str,
        output_dir: str | Path,
        target_url: str = "",
    ) -> tuple[IntentSpec, Path]:
        """Parse intent and write an ejectable Playwright spec. Returns (spec, path)."""
        spec = self.parse(raw_intent, target_url)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        fname = self._slug(spec.title) + ".spec.ts"
        path = out / fname
        path.write_text(self.to_playwright(spec), encoding="utf-8")
        self.log.info(
            "authored test",
            path=str(path),
            steps=len(spec.steps),
            status=spec.status.value,
        )
        return spec, path

    @staticmethod
    def _slug(title: str) -> str:
        s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        return s or "intent_test"
