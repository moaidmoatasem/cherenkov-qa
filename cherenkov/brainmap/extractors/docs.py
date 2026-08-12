"""Docs extractor — markdown notes, the links between them, and code mentions.

This is the extractor that makes the map *Obsidian-shaped*. Three link forms
are read:

* ``[label](other.md)`` — the markdown link, resolved relative to the file.
* ``[[Wikilink]]`` — Obsidian's own form, so a hand-authored note in the vault
  participates in the same graph as generated notes.
* Inline mentions of code — ``cherenkov/web/api.py`` or ``cherenkov.web.api``
  in prose or backticks — which become ``mentions`` edges to the code nodes.

That third form is what lets reconciliation answer the question docs always
lose track of: which prose still describes code that exists, and which code
nobody has ever written about.
"""

from __future__ import annotations

import posixpath
import re

from cherenkov.brainmap.domain.models import (
    EDGE_LINKS,
    EDGE_MENTIONS,
    KIND_ADR,
    KIND_DOC,
    Edge,
    ExtractionResult,
    Node,
    make_id,
)
from cherenkov.brainmap.extractors.base import register
from cherenkov.brainmap.ports import ExtractContext

_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
_CODE_PATH = re.compile(r"(?<![\w/])((?:[a-zA-Z_][\w\-]*/)+[a-zA-Z_][\w\-]*\.(?:py|ts|tsx|js|jsx))")
_DOTTED = re.compile(r"`([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*){1,6})`")
_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_ADR = re.compile(r"(?:^|/)ADR-\d+", re.IGNORECASE)


class DocsExtractor:
    """Maps markdown files to doc/ADR nodes and their outgoing links."""

    name = "docs"

    def claims(self, rel_path: str) -> bool:
        """Whether ``rel_path`` is a markdown document."""
        return rel_path.endswith((".md", ".markdown", ".mdx"))

    def extract(self, rel_path: str, text: str, ctx: ExtractContext) -> ExtractionResult:
        """Parse one markdown file into a node and its link edges.

        Args:
            rel_path (str): Repo-relative path.
            text (str): File contents.
            ctx (ExtractContext): Project context.

        Returns:
            ExtractionResult: The doc node plus ``links`` and ``mentions``
            edges, all unresolved for the reconciler to join.
        """
        result = ExtractionResult()
        is_adr = bool(_ADR.search(rel_path))
        kind = KIND_ADR if is_adr else KIND_DOC
        doc_id = make_id(kind, rel_path)
        heading = _H1.search(text)
        title = heading.group(1).strip() if heading else posixpath.basename(rel_path)
        body = _FENCE.sub(" ", text)

        result.nodes.append(
            Node(
                id=doc_id,
                kind=kind,
                title=title,
                origin=rel_path,
                summary=_summary(body),
                layer=ctx.layer_for(rel_path) or "docs",
                weight=float(text.count("\n") + 1),
                tags=["doc"] + (["adr"] if is_adr else []),
                attrs={"path": rel_path, "words": len(body.split())},
            )
        )

        # Links are read from the body with inline code spans removed: a
        # document that *quotes* link syntax — `[[Some Note]]` in a paragraph
        # explaining wikilinks — is describing the syntax, not using it, and
        # reporting the quote as a broken link is how a findings list stops
        # being worth reading. Mentions still scan the full body, because a
        # path in backticks is a real reference to real code.
        link_body = _INLINE_CODE.sub(" ", body)

        for match in _MD_LINK.finditer(link_body):
            href = match.group(1)
            if not _is_local_link(href):
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(rel_path), href))
            result.edges.append(Edge(src=doc_id, kind=EDGE_LINKS, target_hint=target, origin=rel_path))

        for match in _WIKILINK.finditer(link_body):
            result.edges.append(
                Edge(src=doc_id, kind=EDGE_LINKS, target_hint=match.group(1).strip(), origin=rel_path)
            )

        seen: set[str] = set()
        for match in _CODE_PATH.finditer(body):
            hint = match.group(1)
            if hint in seen:
                continue
            seen.add(hint)
            result.edges.append(
                Edge(src=doc_id, kind=EDGE_MENTIONS, target_hint=hint, origin=rel_path, attrs={"soft": True})
            )
        for match in _DOTTED.finditer(body):
            hint = match.group(1)
            if hint in seen or hint.endswith((".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt")):
                continue
            seen.add(hint)
            result.edges.append(
                Edge(src=doc_id, kind=EDGE_MENTIONS, target_hint=hint, origin=rel_path, attrs={"soft": True})
            )
        return result


def _is_local_link(href: str) -> bool:
    """Whether a markdown link target is a file inside this project.

    Rejects URLs, anchors and — the case that actually bites — prose that
    merely looks like a link. A regex printed in documentation
    (``[a-zA-Z0-9._-]*(...)``) matches the markdown link grammar exactly, and
    reporting it as a broken link would fill the findings list with noise from
    the very documents the map is meant to make trustworthy.

    Args:
        href (str): The raw link target.

    Returns:
        bool: True when the target should be resolved as a project path.
    """
    if not href or "://" in href or href.startswith(("mailto:", "#", "<", "$")):
        return False
    if any(char in href for char in "*?|\\^+"):
        return False
    return "." in href.rsplit("/", 1)[-1] or href.endswith("/")


def _summary(text: str, limit: int = 200) -> str:
    """Return the first prose line of a markdown body.

    Args:
        text (str): Fence-stripped markdown.
        limit (int): Maximum characters to keep.

    Returns:
        str: The first line that is not a heading, badge, front-matter fence
        or list bullet — i.e. the first line that reads like a sentence.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "---", ">", "|", "!", "*", "-", "=")):
            continue
        return stripped[:limit]
    return ""


register("docs", DocsExtractor)
