"""Script to validate internal Markdown link targets across repository documentation."""
import os
import re
import sys
from pathlib import Path

docs_dir = Path("docs")
repo_root = Path(".")

# Match [label](url)
link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
broken_links = []

for md_path in docs_dir.glob("**/*.md"):
    try:
        content = md_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        continue
    for match in link_pattern.finditer(content):
        label, url = match.group(1), match.group(2).strip()
        if url.startswith("http://") or url.startswith("https://") or url.startswith("mailto:") or url.startswith("#"):
            continue
        # Strip anchor
        url_target = url.split("#")[0]
        if not url_target:
            continue
        # Avoid code-block or formatting artifacts like (**tool_args)
        if url_target.startswith("**") or " " in url_target:
            broken_links.append((str(md_path), url, "invalid format"))
            continue
        
        target_path = (md_path.parent / url_target).resolve()
        if not target_path.exists():
            broken_links.append((str(md_path), url, str(target_path)))

print(f"Total broken relative links found: {len(broken_links)}")
for source, url, resolved in broken_links:
    print(f"File: {source} -> Link: {url}")
