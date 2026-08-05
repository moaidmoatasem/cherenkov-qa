"""
CHERENKOV substrate/text_utils.py — model-output text handling shared by providers.

Every inference client has to undo the same three habits of chat models:
reasoning blocks, markdown fences, and JSON wrapped in prose. The helpers live
here so provider modules do not each carry their own copy.
"""

from __future__ import annotations

import json
import re

RE_FENCE_START = re.compile(r"^```[a-z]*\n?")
RE_FENCE_END = re.compile(r"\n?```$")
RE_CODE_FENCE = re.compile(r"```(?:typescript|ts|python)?\s*([\s\S]+?)```")
RE_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]+?)```")

_THINK = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL)


def strip_think(text: str) -> str:
    """Remove deepseek <think> blocks. Malformed/unclosed -> return as-is + caller
    logs a warning. We do NOT try to rescue half-open reasoning (Delta)."""
    return _THINK.sub("", text).strip()


def strip_fences(text: str) -> str:
    """Strip a leading/trailing markdown fence from a code block."""
    text = RE_FENCE_START.sub("", text)
    text = RE_FENCE_END.sub("", text)
    return text.strip()


def extract_fenced_code(text: str) -> str:
    """Return the body of the first fenced code block, or the text unchanged."""
    fenced = RE_CODE_FENCE.search(text)
    return fenced.group(1).strip() if fenced else text


def extract_json_text(text: str) -> str:
    """Narrow model output down to the substring most likely to be JSON.

    Prefers a fenced ```json block; otherwise drops any prose before the first
    `{` or `[`.
    """
    fenced = RE_JSON_FENCE.search(text)
    if fenced:
        return fenced.group(1).strip()
    start = next((i for i, c in enumerate(text) if c in "{["), None)
    return text[start:] if start is not None else text


def try_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def json_repair(raw: str) -> dict | None:
    """Extract the last valid JSON object from a string (last is usually the real response)."""
    # Find all {...} blocks and return the last one (most likely the real response)
    matches = list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}", raw, re.DOTALL))
    if matches:
        return try_json(matches[-1].group(0))
    return None
