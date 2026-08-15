#!/usr/bin/env python3
"""
Test suite for scripts/check_docs_markdown.py
Verifies detection of:
- GFM checkboxes and empty brackets (NOT flagged as placeholders)
- Uppercase URL schemes like HTTPS:// (recognized as external)
- Empty files (detected)
- Placeholders TODO, TBD, FIXME, XXX (detected)
- Broken relative links (detected)
- Invalid heading anchors (detected)
"""
import json
import pathlib
import subprocess
import sys
import tempfile

def main():
    temp_dir = pathlib.Path(tempfile.mkdtemp())
    script_path = pathlib.Path(__file__).parent / "check_docs_markdown.py"

    def run_check(target_dir):
        cmd = [
            sys.executable,
            str(script_path),
            "--root",
            str(target_dir),
            "--dirs",
            ".",
            "--no-root-md",
            "--json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode, json.loads(res.stdout) if res.stdout else {}

    # Test 1: Clean markdown with valid GFM checklists, empty brackets, and uppercase HTTPS
    d1 = temp_dir / "test1"
    d1.mkdir()
    (d1 / "doc.md").write_text(
        "# Title\n\n"
        "Here is a task list:\n"
        "- [ ] Task 1\n"
        "- [x] Task 2\n"
        "* [ ] Task 3\n"
        "1. [ ] Task 4\n\n"
        "Here are code snippets and types:\n"
        "`const arr: string[] = [];`\n"
        "`data = []`\n\n"
        "External links:\n"
        "[Google](HTTPS://google.com)\n"
        "[Secure](https://example.com/test)\n",
        encoding="utf-8",
    )
    rc1, out1 = run_check(d1)
    print(f"Test 1 (Clean + Checkboxes + [] + HTTPS): RC={rc1}, violations={out1.get('metrics', {}).get('total_violations')}")
    assert rc1 == 0, f"Expected RC 0, got {rc1}"
    assert out1["metrics"]["total_violations"] == 0, "Expected 0 violations"

    # Test 2: Empty file detection
    d2 = temp_dir / "test2"
    d2.mkdir()
    (d2 / "empty.md").write_text("", encoding="utf-8")
    rc2, out2 = run_check(d2)
    print(f"Test 2 (Empty File): RC={rc2}, violations={out2.get('metrics', {}).get('total_violations')}")
    assert rc2 == 1, f"Expected RC 1, got {rc2}"
    assert out2["metrics"]["empty_files"] == 1, "Expected 1 empty file"

    # Test 3: TODO / TBD / FIXME / XXX placeholder detection
    d3 = temp_dir / "test3"
    d3.mkdir()
    (d3 / "todo.md").write_text(
        "# Doc\n"
        "TODO: write this\n"
        "[TBD] more details\n"
        "FIXME: broken feature\n"
        "XXX: review needed\n",
        encoding="utf-8",
    )
    rc3, out3 = run_check(d3)
    print(f"Test 3 (Placeholders TODO/TBD/FIXME/XXX): RC={rc3}, placeholders={out3.get('metrics', {}).get('placeholders_found')}")
    assert rc3 == 1, f"Expected RC 1, got {rc3}"
    assert out3["metrics"]["placeholders_found"] == 4, "Expected 4 placeholders"

    # Test 4: Broken link detection
    d4 = temp_dir / "test4"
    d4.mkdir()
    (d4 / "broken.md").write_text(
        "# Doc\n"
        "[Nonexistent](does_not_exist.md)\n",
        encoding="utf-8",
    )
    rc4, out4 = run_check(d4)
    print(f"Test 4 (Broken Link): RC={rc4}, broken_links={out4.get('metrics', {}).get('broken_links_found')}")
    assert rc4 == 1, f"Expected RC 1, got {rc4}"
    assert out4["metrics"]["broken_links_found"] == 1, "Expected 1 broken link"

    # Test 5: Invalid anchor detection
    d5 = temp_dir / "test5"
    d5.mkdir()
    (d5 / "anchor.md").write_text(
        "# Doc\n"
        "## Real Section\n"
        "[Link to missing](#missing-section)\n",
        encoding="utf-8",
    )
    rc5, out5 = run_check(d5)
    print(f"Test 5 (Invalid Anchor): RC={rc5}, invalid_anchors={out5.get('metrics', {}).get('invalid_anchors_found')}")
    assert rc5 == 1, f"Expected RC 1, got {rc5}"
    assert out5["metrics"]["invalid_anchors_found"] == 1, "Expected 1 invalid anchor"

    print("\n=== ALL 5 TEST HARNESS SUITES PASSED SUCCESSFULLY ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
