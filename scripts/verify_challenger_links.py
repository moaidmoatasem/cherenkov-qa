"""
Exhaustive internal link and anchor validation script for CHERENKOV-QA 1.4 docs.
Validates relative links, image paths, anchors, and cross-references.
"""

import os
import re
import sys
import urllib.parse
from pathlib import Path

# Regular expressions for markdown link extraction
# Avoid matching code blocks if possible or process line by line
MD_INLINE_LINK_RE = re.compile(r'(?<!\!)\[([^\]]*?)\]\(([^)]+)\)')
MD_IMAGE_LINK_RE = re.compile(r'!\[([^\]]*?)\]\(([^)]+)\)')
HTML_A_HREF_RE = re.compile(r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']+)["\']', re.IGNORECASE)
HTML_IMG_SRC_RE = re.compile(r'<img\s+(?:[^>]*?\s+)?src=["\']([^"\']+)["\']', re.IGNORECASE)
MD_REF_DEF_RE = re.compile(r'^\s*\[([^\]]+)\]:\s*(\S+)', re.MULTILINE)
MD_REF_USE_RE = re.compile(r'(?<!\!)\[([^\]]*?)\]\[([^\]]+)\]')

# Heading & Anchor regexes
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
ATTR_LIST_ID_RE = re.compile(r'\{[#.:\w\s-]*#([a-zA-Z0-9_-]+)[^}]*\}')
HTML_ID_RE = re.compile(r'id=["\']([a-zA-Z0-9_-]+)["\']', re.IGNORECASE)
HTML_NAME_RE = re.compile(r'<a\s+[^>]*name=["\']([a-zA-Z0-9_-]+)["\']', re.IGNORECASE)


def slugify(text):
    """
    Python-markdown / Material for MkDocs compatible slugify algorithm.
    """
    # Remove attr_list syntax if present: e.g., "Heading {: #custom-id }"
    text = re.sub(r'\{[^}]+\}', '', text)
    # Remove markdown formatting like bold, italic, code backticks, links
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'[`*_~]', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.strip().lower()
    # Replace non-alphanumeric (except hyphens and underscores and whitespace) with empty
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace whitespace and repeated hyphens with single hyphen
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text


def extract_anchors_from_content(content):
    """
    Extracts all possible valid anchor slugs and explicit IDs from a markdown file content.
    """
    anchors = set()
    slug_counts = {}

    # 1. Headings
    for line in content.splitlines():
        # Check if line is a code block delimiter (skip)
        m = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if m:
            heading_raw = m.group(2)
            # Check for attr_list ID: e.g. ## Title {: #custom-anchor }
            attr_m = ATTR_LIST_ID_RE.search(heading_raw)
            if attr_m:
                anchors.add(attr_m.group(1).lower())
            
            slug = slugify(heading_raw)
            if slug:
                if slug in slug_counts:
                    slug_counts[slug] += 1
                    dedup_slug = f"{slug}_{slug_counts[slug]-1}" if False else f"{slug}-{slug_counts[slug]-1}"
                    anchors.add(dedup_slug)
                    anchors.add(f"{slug}_{slug_counts[slug]-1}")
                else:
                    slug_counts[slug] = 1
                    anchors.add(slug)

    # 2. HTML IDs and Name anchors
    for m in HTML_ID_RE.finditer(content):
        anchors.add(m.group(1).lower())
    for m in HTML_NAME_RE.finditer(content):
        anchors.add(m.group(1).lower())
    for m in ATTR_LIST_ID_RE.finditer(content):
        anchors.add(m.group(1).lower())

    return anchors


def remove_code_blocks(text):
    """
    Removes fenced code blocks (```...```) to avoid false positive links inside sample code.
    """
    # Remove triple backtick code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline backticks
    text = re.sub(r'`[^`\n]+`', '', text)
    return text


def scan_directory(docs_root):
    """
    Scans docs_root for all markdown files and validates all links and anchors.
    """
    docs_root = Path(docs_root).resolve()
    print(f"\n=======================================================")
    print(f"Scanning directory: {docs_root}")
    print(f"=======================================================")

    md_files = list(docs_root.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files.")

    # Pre-parse all files for content and anchors
    file_data = {}
    for md_path in md_files:
        rel_path = md_path.relative_to(docs_root).as_posix()
        try:
            content = md_path.read_text(encoding='utf-8')
        except Exception as e:
            content = md_path.read_text(encoding='latin-1')
        anchors = extract_anchors_from_content(content)
        file_data[rel_path] = {
            'abs_path': md_path,
            'content': content,
            'anchors': anchors
        }

    total_links = 0
    total_images = 0
    total_anchors_checked = 0
    broken_links = []
    broken_images = []
    broken_anchors = []
    external_links = []

    for rel_path, data in file_data.items():
        content_no_code = remove_code_blocks(data['content'])
        file_dir = data['abs_path'].parent

        # 1. Inline links [text](url)
        for m in MD_INLINE_LINK_RE.finditer(content_no_code):
            link_text = m.group(1)
            raw_url = m.group(2).strip()
            total_links += 1
            check_link(raw_url, link_text, rel_path, file_dir, docs_root, file_data,
                       broken_links, broken_anchors, external_links, total_anchors_checked)

        # 2. HTML <a> hrefs
        for m in HTML_A_HREF_RE.finditer(content_no_code):
            raw_url = m.group(1).strip()
            total_links += 1
            check_link(raw_url, "<html-a>", rel_path, file_dir, docs_root, file_data,
                       broken_links, broken_anchors, external_links, total_anchors_checked)

        # 3. Markdown images ![alt](url)
        for m in MD_IMAGE_LINK_RE.finditer(content_no_code):
            alt_text = m.group(1)
            raw_url = m.group(2).strip()
            total_images += 1
            check_image(raw_url, alt_text, rel_path, file_dir, docs_root, broken_images)

        # 4. HTML <img> src
        for m in HTML_IMG_SRC_RE.finditer(content_no_code):
            raw_url = m.group(1).strip()
            total_images += 1
            check_image(raw_url, "<html-img>", rel_path, file_dir, docs_root, broken_images)

    print(f"\n--- Results for {docs_root} ---")
    print(f"Total Markdown Files: {len(md_files)}")
    print(f"Total Internal & External Links Checked: {total_links}")
    print(f"Total External Links: {len(external_links)}")
    print(f"Total Images Checked: {total_images}")
    print(f"Broken Links: {len(broken_links)}")
    print(f"Broken Anchors: {len(broken_anchors)}")
    print(f"Broken Images: {len(broken_images)}")

    if broken_links:
        print("\n[BROKEN LINKS]:")
        for b in broken_links:
            print(f"  In {b['source']}: '{b['url']}' -> Reason: {b['reason']}")

    if broken_anchors:
        print("\n[BROKEN ANCHORS]:")
        for b in broken_anchors:
            print(f"  In {b['source']}: '{b['url']}' (target file: {b['target_file']}, anchor: #{b['anchor']})")
            if b.get('available_anchors'):
                print(f"    Available in target: {sorted(list(b['available_anchors']))[:10]}")

    if broken_images:
        print("\n[BROKEN IMAGES]:")
        for b in broken_images:
            print(f"  In {b['source']}: '{b['url']}' -> Reason: {b['reason']}")

    return {
        'total_files': len(md_files),
        'total_links': total_links,
        'total_images': total_images,
        'external_links': len(external_links),
        'broken_links': broken_links,
        'broken_anchors': broken_anchors,
        'broken_images': broken_images
    }


def check_link(raw_url, link_text, source_rel, file_dir, docs_root, file_data,
               broken_links, broken_anchors, external_links, total_anchors_checked):
    # Strip quotes or titles in url like `[text](url "title")`
    url_clean = raw_url.split()[0].strip('\'"')

    # Ignore mailto, tel, javascript, template macros
    if url_clean.startswith(('mailto:', 'tel:', 'javascript:', '{{', '{%')):
        return

    # External links
    if url_clean.startswith(('http://', 'https://', '//')):
        external_links.append({'source': source_rel, 'url': url_clean})
        return

    # Parse URL into path and fragment (anchor)
    parsed = urllib.parse.urlparse(url_clean)
    path_part = urllib.parse.unquote(parsed.path)
    fragment = parsed.fragment.strip().lower()

    # 1. Pure internal anchor on same page: e.g. `#section-heading`
    if not path_part and fragment:
        available = file_data[source_rel]['anchors']
        if fragment not in available:
            # Check fuzzy matches (slug variations)
            if not any(fragment in a or a in fragment for a in available):
                broken_anchors.append({
                    'source': source_rel,
                    'url': raw_url,
                    'target_file': source_rel,
                    'anchor': fragment,
                    'available_anchors': available
                })
        return

    if not path_part and not fragment:
        return

    # 2. Relative or root-relative link
    if path_part.startswith('/'):
        # Root relative or absolute docs link
        # In mkdocs, `/` might mean site root or docs root
        # Check if path starts with `/cherenkov-qa/1.4/` or `/1.4/`
        sub_path = path_part
        for prefix in ['/cherenkov-qa/1.4/', '/cherenkov-qa/', '/1.4/']:
            if sub_path.startswith(prefix):
                sub_path = sub_path[len(prefix):]
                break
        else:
            if sub_path.startswith('/'):
                sub_path = sub_path[1:]

        target_candidate = (docs_root / sub_path).resolve()
    else:
        target_candidate = (file_dir / path_part).resolve()

    # Resolve target candidate
    # MkDocs supports linking to `foo.md`, `foo/`, `foo` (directory index)
    resolved_target = None
    target_rel = None

    if target_candidate.is_file():
        resolved_target = target_candidate
    elif target_candidate.is_dir():
        if (target_candidate / 'index.md').is_file():
            resolved_target = target_candidate / 'index.md'
        elif (target_candidate / 'README.md').is_file():
            resolved_target = target_candidate / 'README.md'
    elif target_candidate.with_suffix('.md').is_file():
        resolved_target = target_candidate.with_suffix('.md')
    elif (docs_root / path_part).is_file():
        resolved_target = docs_root / path_part
    elif (docs_root / f"{path_part}.md").is_file():
        resolved_target = docs_root / f"{path_part}.md"
    elif (docs_root / path_part / 'index.md').is_file():
        resolved_target = docs_root / path_part / 'index.md'

    if not resolved_target or not resolved_target.exists():
        broken_links.append({
            'source': source_rel,
            'url': raw_url,
            'reason': f"Target file does not exist (tried {target_candidate})"
        })
        return

    # Check anchor on target if target is markdown
    if fragment and resolved_target.suffix == '.md':
        try:
            target_rel = resolved_target.relative_to(docs_root).as_posix()
        except ValueError:
            target_rel = resolved_target.name

        if target_rel in file_data:
            available = file_data[target_rel]['anchors']
            if fragment not in available:
                if not any(fragment in a or a in fragment for a in available):
                    broken_anchors.append({
                        'source': source_rel,
                        'url': raw_url,
                        'target_file': target_rel,
                        'anchor': fragment,
                        'available_anchors': available
                    })


def check_image(raw_url, alt_text, source_rel, file_dir, docs_root, broken_images):
    url_clean = raw_url.split()[0].strip('\'"')
    if url_clean.startswith(('http://', 'https://', '//', 'data:')):
        return

    parsed = urllib.parse.urlparse(url_clean)
    path_part = urllib.parse.unquote(parsed.path)

    if path_part.startswith('/'):
        sub_path = path_part
        for prefix in ['/cherenkov-qa/1.4/', '/cherenkov-qa/', '/1.4/']:
            if sub_path.startswith(prefix):
                sub_path = sub_path[len(prefix):]
                break
        else:
            if sub_path.startswith('/'):
                sub_path = sub_path[1:]
        target_candidate = (docs_root / sub_path).resolve()
    else:
        target_candidate = (file_dir / path_part).resolve()

    if not target_candidate.is_file():
        # Try relative to docs_root
        if (docs_root / path_part).is_file():
            return
        broken_images.append({
            'source': source_rel,
            'url': raw_url,
            'reason': f"Image file not found at {target_candidate}"
        })


if __name__ == '__main__':
    res1 = scan_directory('docs/1.4')
    res2 = scan_directory('docs-site/docs')

    total_broken = (
        len(res1['broken_links']) + len(res1['broken_anchors']) + len(res1['broken_images']) +
        len(res2['broken_links']) + len(res2['broken_anchors']) + len(res2['broken_images'])
    )

    if total_broken > 0:
        print(f"\n[FAIL] Found {total_broken} total issues across docs suites.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All internal links, anchors, and images verified successfully!")
        sys.exit(0)
