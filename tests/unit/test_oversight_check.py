"""The oversight script: plan files must agree, and the online report logic is pure."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("oversight_check", ROOT / "scripts" / "oversight_check.py")
oc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oc)

NOW = datetime(2026, 10, 6, tzinfo=timezone.utc)


def test_repo_plan_files_are_consistent():
    """This is the drift gate: it fails the PR that reintroduces a stale plan file."""
    assert oc.offline_findings() == []


def test_missing_banner_and_forbidden_reference_are_reported(tmp_path):
    (tmp_path / "docs").mkdir()
    for rel in oc.CANONICAL:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x")
    (tmp_path / "docs/STATUS.md").write_text("no banner")
    (tmp_path / "docs/other.md").write_text("The source of truth is ROADMAP_RECONCILIATION.md")
    found = oc.offline_findings(tmp_path)
    assert any("STATUS.md" in f and "banner" in f for f in found)
    assert any("other.md" in f and "ROADMAP_RECONCILIATION" in f for f in found)


def test_online_findings_flags_untracked_stale_and_red():
    issues = [{"number": 5, "title": "tracked", "label_names": []},
              {"number": 9, "title": "untracked", "label_names": []},
              {"number": 3, "title": "Oversight report", "label_names": ["oversight"]},
              {"number": 4, "title": "a pr", "label_names": [], "pull_request": {}}]
    prs = [{"number": 11, "title": "old", "updated_at": "2026-08-01T00:00:00Z"},
           {"number": 12, "title": "fresh", "updated_at": "2026-10-05T00:00:00Z"}]
    found = oc.online_findings(issues, prs, {"ci.yml": "failure", "x.yml": "success"},
                               "2026-09-01T00:00:00Z", "Now: #5 and #77", NOW)
    text = "\n".join(found)
    assert "#9 is not in docs/ROADMAP.md" in text
    assert "#77" in text and "#5 " not in text
    assert "PR #11 untouched" in text and "PR #12" not in text
    assert "ci.yml" in text and "x.yml" not in text
    assert "no commit to main for 35 days" in text
    assert "#3" not in text  # the oversight issue itself is not "untracked"


def test_digest_is_stable_and_content_sensitive():
    assert oc.digest("a") == oc.digest("a") != oc.digest("b")


def test_done_and_struck_through_mentions_are_not_stale_refs():
    """Finished work is recorded in ROADMAP on purpose; only live references can go stale."""
    roadmap = "\n".join([
        "| ~~Fixed thing~~ — fixed | #101 |",
        "| Redesign — **done, merged in #102/#103:** more | #5 |",
        "Done in #104: #105, #106.",
        "- Rebase draft PR #107 (still open item)",
        "- Live item #108",
    ])
    found = oc.online_findings([{"number": 5, "title": "t", "label_names": []}], [], {}, None, roadmap, NOW)
    text = "\n".join(found)
    for n in (101, 102, 103, 104, 105, 106):
        assert f"#{n}," not in text and f"#{n} " not in text
    assert "#107" in text and "#108" in text  # live mentions of non-open numbers still flagged
