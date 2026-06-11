"""
Artifact classification — pure heuristics, no I/O.

Infers what kind of artifact we were handed and how mature it looks, so
the workflow strategy can pick an appropriate variant when the caller
does not state these explicitly.
"""
from __future__ import annotations

import re

from cherenkov.reasoning.domain.models import Artifact, ArtifactKind, Maturity

_DRAFT_MARKERS = re.compile(r"\b(draft|wip|tbd|tba|to be defined|proposal)\b", re.IGNORECASE)
_TODO_MARKERS = re.compile(r"\b(todo|fixme|xxx|\?\?\?)\b", re.IGNORECASE)


def classify_kind(uri: str = "", content: str = "", parsed: dict | None = None) -> ArtifactKind:
    """Infer artifact kind from its URI and content."""
    parsed = parsed or {}
    if "openapi" in parsed or "swagger" in parsed:
        return ArtifactKind.OPENAPI_SPEC
    lowered_uri = uri.lower()
    if "figma.com" in lowered_uri:
        return ArtifactKind.FIGMA_DESIGN
    if lowered_uri.startswith(("http://", "https://")):
        return ArtifactKind.LIVE_APP
    if lowered_uri.endswith((".yaml", ".yml", ".json")) and re.search(
        r'["\']?(openapi|swagger)["\']?\s*:', content
    ):
        return ArtifactKind.OPENAPI_SPEC
    if lowered_uri.endswith((".py", ".ts", ".tsx", ".js", ".go", ".rs")) or "/src/" in lowered_uri:
        return ArtifactKind.CODEBASE
    return ArtifactKind.REQUIREMENTS_DOC


def infer_maturity(artifact: Artifact) -> Maturity:
    """Infer maturity from version markers and draft/TODO density."""
    text = artifact.content
    if artifact.kind == ArtifactKind.OPENAPI_SPEC:
        version = str(artifact.parsed.get("info", {}).get("version", ""))
        if version.startswith("0."):
            return Maturity.IN_DEVELOPMENT
        if version:
            return Maturity.STABILIZING
    if _DRAFT_MARKERS.search(text):
        return Maturity.CONCEPT
    if text and _todo_density(text) > 0.02:
        return Maturity.IN_DEVELOPMENT
    if artifact.kind == ArtifactKind.LIVE_APP:
        return Maturity.PRODUCTION
    return Maturity.IN_DEVELOPMENT


def _todo_density(text: str) -> float:
    words = max(len(text.split()), 1)
    return len(_TODO_MARKERS.findall(text)) / words
