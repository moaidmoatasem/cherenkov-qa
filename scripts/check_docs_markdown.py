#!/usr/bin/env python3
"""
check_docs_markdown.py
──────────────────────
Automated Markdown Integrity & Placeholder Inspector for CHERENKOV QA.
Scans docs/ and root Markdown files for empty files, unresolved placeholders
(TODO, TBD, []), broken relative links, and invalid GitHub heading anchor slugs.

Usage:
    python scripts/check_docs_markdown.py
    python scripts/check_docs_markdown.py --json
    python scripts/check_docs_markdown.py --root . --verbose
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote, urlparse

# Reconfigure stdout to UTF-8 for Windows console safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Directories to exclude from scanning
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "target",
    ".agents", "build", "dist", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".freebuff", ".qwen", "eject-e2e-output"
}

# Regex patterns
PLACEHOLDER_REGEX = re.compile(r'(\bTODO\b|\bTBD\b|\[\s*\])')
MD_INLINE_LINK_REGEX = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
MD_REF_LINK_REGEX = re.compile(r'^\s*\[([^\]]+)\]:\s*(\S+)', re.MULTILINE)


class MarkdownViolation(NamedTuple):
    """Represents a single Markdown structural or content violation."""
    file_path: str
    line: int
    category: str  # EMPTY_FILE, PLACEHOLDER, BROKEN_LINK, INVALID_ANCHOR
    symbol: str
    message: str


class MarkdownStats:
    """Maintains statistics across scanned Markdown files."""

    def __init__(self) -> None:
        """Initialize counters to zero."""
        self.files_scanned: int = 0
        self.empty_files: int = 0
        self.placeholders_found: int = 0
        self.broken_links_found: int = 0
        self.invalid_anchors_found: int = 0

    @property
    def total_violations(self) -> int:
        """Calculate total violation count.

        Returns:
            int: Sum of empty files, placeholders, broken links, and invalid anchors.
        """
        return (
            self.empty_files
            + self.placeholders_found
            + self.broken_links_found
            + self.invalid_anchors_found
        )


def _heading_to_slug(text: str) -> str:
    """Convert heading text to a GitHub-compatible anchor slug.

    Args:
        text: Raw heading text line without leading '#' characters.

    Returns:
        str: Generated anchor slug string.
    """
    # 1. Remove markdown inline links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 2. Strip formatting backticks, asterisks, underscores
    text = re.sub(r'[`*_]', '', text)
    # 3. Convert to lowercase and strip whitespace
    text = text.lower().strip()
    # 4. Remove punctuation characters (keep word chars, spaces, hyphens)
    text = re.sub(r'[^\w\s-]', '', text)
    # 5. Replace spaces with hyphens
    slug = text.replace(' ', '-')
    return slug


def _extract_file_anchors(content: str) -> set[str]:
    """Extract all heading anchor slugs and HTML element IDs/names from Markdown content.

    Args:
        content: Full text of the Markdown file.

    Returns:
        set[str]: Set of all valid anchor slugs and HTML IDs in the file.
    """
    anchors: set[str] = set()
    slug_counts: dict[str, int] = {}

    for line in content.splitlines():
        line_str = line.strip()
        if line_str.startswith("#"):
            heading_text = line_str.lstrip("#").strip()
            slug_base = _heading_to_slug(heading_text)
            if slug_base:
                count = slug_counts.get(slug_base, 0)
                slug_counts[slug_base] = count + 1
                final_slug = slug_base if count == 0 else f"{slug_base}-{count}"
                anchors.add(final_slug)
                # Also record normalized multi-hyphen variants
                norm_slug = re.sub(r'-+', '-', final_slug)
                anchors.add(norm_slug)

    # HTML anchor tags: <a id="..."> or <div id="...">
    html_anchors = re.findall(r'(?:id|name)=["\']([^"\']+)["\']', content, re.IGNORECASE)
    for a in html_anchors:
        anchors.add(a)

    return anchors


def scan_markdown_files(
    root_dir: Path, dirs: list[str], include_root_md: bool = True, ignore_code_blocks: bool = False
) -> tuple[MarkdownStats, list[MarkdownViolation]]:
    """Scan Markdown files for empty content, placeholders, broken links, and invalid anchors.

    Args:
        root_dir: Root repository directory path.
        dirs: Directory names containing Markdown files to scan (e.g. ['docs']).
        include_root_md: Whether to include root directory *.md files.
        ignore_code_blocks: If True, ignore placeholder checks inside code blocks.

    Returns:
        tuple[MarkdownStats, list[MarkdownViolation]]: Calculated statistics and list of violations.
    """
    stats = MarkdownStats()
    violations: list[MarkdownViolation] = []

    # 1. Collect all target Markdown files
    md_files: list[Path] = []

    if include_root_md:
        for p in root_dir.glob("*.md"):
            if p.is_file() and not any(part in EXCLUDE_DIRS for part in p.parts):
                md_files.append(p)

    for d in dirs:
        dir_path = root_dir / d
        if dir_path.is_file() and dir_path.suffix == ".md":
            if dir_path not in md_files:
                md_files.append(dir_path)
        elif dir_path.is_dir():
            for p in dir_path.rglob("*.md"):
                if not any(part in EXCLUDE_DIRS for part in p.parts):
                    if p not in md_files:
                        md_files.append(p)

    # Map file path to content and extracted anchors
    file_cache: dict[Path, tuple[str, list[str], set[str]]] = {}

    for md_file in md_files:
        stats.files_scanned += 1
        rel_path = str(md_file.relative_to(root_dir))
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            violations.append(MarkdownViolation(rel_path, 1, "FILE_ERROR", md_file.name, f"Failed to read file: {e}"))
            continue

        lines = content.splitlines()

        # Check 1: Empty file check
        if len(content.strip()) == 0:
            stats.empty_files += 1
            violations.append(MarkdownViolation(
                file_path=rel_path,
                line=1,
                category="EMPTY_FILE",
                symbol=md_file.name,
                message="Markdown file is empty (0 non-whitespace bytes)"
            ))

        # Check 2: Unresolved placeholders check
        in_code_block = False
        for lineno, line in enumerate(lines, start=1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block

            if ignore_code_blocks and in_code_block:
                continue

            matches = PLACEHOLDER_REGEX.findall(line)
            if matches:
                for match in matches:
                    stats.placeholders_found += 1
                    snippet = line.strip()[:80]
                    violations.append(MarkdownViolation(
                        file_path=rel_path,
                        line=lineno,
                        category="PLACEHOLDER",
                        symbol=match,
                        message=f"Unresolved placeholder pattern '{match}' found in line: `{snippet}`"
                    ))

        anchors = _extract_file_anchors(content)
        file_cache[md_file.resolve()] = (content, lines, anchors)

    # Check 3: Links and Anchor resolution
    for md_file, (content, lines, anchors) in file_cache.items():
        rel_path = str(md_file.relative_to(root_dir))

        for lineno, line in enumerate(lines, start=1):
            # Extract inline links [text](url) and reference links
            found_links: list[str] = []

            for m in MD_INLINE_LINK_REGEX.finditer(line):
                url = m.group(2).strip()
                found_links.append(url)

            for m in MD_REF_LINK_REGEX.finditer(line):
                url = m.group(2).strip()
                found_links.append(url)

            for url in found_links:
                # Exclude external links and file:// URIs
                if url.startswith(("http://", "https://", "mailto:", "ftp://", "tel:", "file://")):
                    continue

                # Local anchor on same file e.g. #section-name
                if url.startswith("#"):
                    fragment = unquote(url.lstrip("#"))
                    if fragment and fragment not in anchors:
                        norm_frag = re.sub(r'-+', '-', fragment)
                        if norm_frag not in anchors:
                            stats.invalid_anchors_found += 1
                            violations.append(MarkdownViolation(
                                file_path=rel_path,
                                line=lineno,
                                category="INVALID_ANCHOR",
                                symbol=f"#{fragment}",
                                message=f"Local anchor '#{fragment}' not found in current file '{md_file.name}'"
                            ))
                    continue

                # Relative link e.g. path/to/file.md or path/to/file.md#anchor
                parsed = urlparse(url)
                path_str = unquote(parsed.path)
                fragment = unquote(parsed.fragment)

                if not path_str:
                    target_file = md_file
                else:
                    target_file = (md_file.parent / path_str).resolve()

                if not target_file.exists():
                    stats.broken_links_found += 1
                    try:
                        rel_target = str(target_file.relative_to(root_dir))
                    except ValueError:
                        rel_target = str(target_file)
                    violations.append(MarkdownViolation(
                        file_path=rel_path,
                        line=lineno,
                        category="BROKEN_LINK",
                        symbol=url,
                        message=f"Link target file does not exist: '{url}' -> '{rel_target}'"
                    ))
                    continue

                # If target is a Markdown file in our cache and fragment is specified
                if fragment and target_file in file_cache:
                    target_anchors = file_cache[target_file][2]
                    norm_frag = re.sub(r'-+', '-', fragment)
                    if fragment not in target_anchors and norm_frag not in target_anchors:
                        stats.invalid_anchors_found += 1
                        violations.append(MarkdownViolation(
                            file_path=rel_path,
                            line=lineno,
                            category="INVALID_ANCHOR",
                            symbol=f"#{fragment}",
                            message=f"Anchor '#{fragment}' not found in target file '{target_file.name}'"
                        ))

    return stats, violations


def main() -> int:
    """CLI entry point for check_docs_markdown.py.

    Returns:
        int: 0 if 100% compliant, 1 if any violations detected.
    """
    parser = argparse.ArgumentParser(
        description="Automated Markdown Integrity & Placeholder Inspector for CHERENKOV QA"
    )
    parser.add_argument("--root", type=str, default=".", help="Root repository directory (default: .)")
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=["docs"],
        help="Directories containing Markdown files to scan (default: docs)",
    )
    parser.add_argument(
        "--no-root-md",
        action="store_true",
        help="Do not include *.md files in repository root directory",
    )
    parser.add_argument(
        "--ignore-code-blocks",
        action="store_true",
        help="Ignore placeholder tags located inside code blocks",
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    root_path = Path(args.root).resolve()

    include_root_md = not args.no_root_md

    stats, violations = scan_markdown_files(
        root_dir=root_path,
        dirs=args.dirs,
        include_root_md=include_root_md,
        ignore_code_blocks=args.ignore_code_blocks,
    )

    passed = stats.total_violations == 0

    if args.json:
        payload = {
            "tool": "check_docs_markdown.py",
            "status": "PASSED" if passed else "FAILED",
            "exit_code": 0 if passed else 1,
            "metrics": {
                "files_scanned": stats.files_scanned,
                "empty_files": stats.empty_files,
                "placeholders_found": stats.placeholders_found,
                "broken_links_found": stats.broken_links_found,
                "invalid_anchors_found": stats.invalid_anchors_found,
                "total_violations": stats.total_violations,
            },
            "violations": [
                {
                    "file": v.file_path,
                    "line": v.line,
                    "category": v.category,
                    "symbol": v.symbol,
                    "message": v.message,
                }
                for v in violations
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0 if passed else 1

    # Terminal Summary Output
    print("=" * 80)
    print("CHERENKOV QA - Markdown Integrity & Link Validation Report")
    print("=" * 80)
    print(f"Target Root:     {root_path}")
    print(f"Files Scanned:   {stats.files_scanned}")
    print(f"Total Issues:    {stats.total_violations}")
    print("-" * 80)

    if violations:
        print("[FAIL] VIOLATIONS FOUND:\n")
        for v in violations:
            print(f"  [{v.category:14s}] {v.file_path}:{v.line}")
            print(f"                 └─ {v.message}")
        print("-" * 80)
    else:
        print("[OK] ZERO VIOLATIONS DETECTED!\n")
        print("-" * 80)

    print("SUMMARY STATISTICS:")
    print(f"  - Files Scanned:           {stats.files_scanned}")
    print(f"  - Empty Files (0-byte):    {stats.empty_files}")
    print(f"  - Placeholders (TODO/TBD): {stats.placeholders_found}")
    print(f"  - Broken Links:            {stats.broken_links_found}")
    print(f"  - Invalid Heading Anchors: {stats.invalid_anchors_found}")

    print("-" * 80)
    status_str = "PASSED" if passed else "FAILED"
    indicator = "[OK]" if passed else "[FAIL]"
    print(f"OVERALL INTEGRITY: {status_str} ({stats.total_violations} issues found)")
    print(f"STATUS: {indicator} {status_str} (Exit Code: {0 if passed else 1})")
    print("=" * 80)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
