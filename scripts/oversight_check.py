#!/usr/bin/env python3
"""Deterministic plan/issue/CI drift check. Zero LLM tokens.

Offline (default for PRs): the plan files in this repo agree with each other.
Online (weekly workflow): the plan agrees with GitHub (issues, PRs, CI).
The online report is upserted into ONE issue labelled ``oversight``, edited only
when its content hash changes, so sessions start from it instead of re-auditing.

    python scripts/oversight_check.py --offline
    GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python scripts/oversight_check.py --upsert
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- plan-status: superseded -->"
SUPERSEDED = [
    "docs/STATUS.md", "docs/PHASE_PLAN.md", "docs/EXECUTION_PLAN.md", "docs/SCOPE_LEDGER.md",
    "docs/MODULE_STATUS.md", "docs/GAP_REPORT.md", "docs/wiki/Roadmap.md",
    "docs/vision/02_ROADMAP.md", "docs/vision/07_MASTER_PLAN.md", "docs/vision/08_DELIVERY_PLAN.md",
    "docs/vision/CHERENKOV-QA_Unified Master Plan.md", "docs/INNOVATION_ROADMAP_V2.md",
    "PROJECT.md", ".agents/BRIEFING.md", ".agents/handoff.md", ".agents/orchestrator/plan.md",
]
CANONICAL = ["HANDOVER.md", "docs/ROADMAP.md", "CLAUDE.md", "AGENTS.md"]
# Files allowed to mention the dead/forbidden plan names (history, warnings).
HISTORY_OK = {"HANDOVER.md", "CLAUDE.md", "CHANGELOG.md", "docs/_archive", "docs/reviews", "agent_memory", "docs/ROADMAP.md"}
BAD_AUTHORITY = ("ROADMAP_RECONCILIATION.md", "ROADMAP_2026H2.md")
AUTHORITY_WORDS = re.compile(r"source of truth|authoritative|refer to|see the unified|forward plan|single source", re.I)
STALE_PR_DAYS = 21
LABEL = "oversight"
TITLE = "Oversight report"


def offline_findings(root: Path = ROOT) -> list[str]:
    out: list[str] = []
    for rel in CANONICAL:
        if not (root / rel).is_file():
            out.append(f"canonical plan file missing: {rel}")
    for rel in SUPERSEDED:
        p = root / rel
        if p.is_file() and MARKER not in p.read_text(encoding="utf-8", errors="replace"):
            out.append(f"{rel}: superseded plan file lacks the `{MARKER}` banner")
    for md in list(root.glob("*.md")) + list((root / "docs").rglob("*.md")):
        rel = md.relative_to(root).as_posix()
        if any(rel == h or rel.startswith(h + "/") for h in HISTORY_OK):
            continue
        for line in md.read_text(encoding="utf-8", errors="replace").splitlines():
            for name in BAD_AUTHORITY:
                # Only flag lines that present it as the thing to follow; plain
                # historical mentions (changelogs, evidence logs) are fine.
                if name in line and AUTHORITY_WORDS.search(line):
                    out.append(f"{rel}: points at {name} (fabricated or deleted) as a plan source")
                    break
    return out


def _api(path: str, token: str, repo: str, method: str = "GET", body: dict | None = None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https host
        return json.loads(resp.read() or b"null")


_STRUCK = re.compile(r"~~.*?~~", re.S)
_DONE_REF = re.compile(r"(?:merged in|fixed in|done in)\s+(?:#\d+[/,\s]*)+", re.I)


def live_mentions(roadmap_text: str) -> set[int]:
    """Issue numbers ROADMAP still treats as live work.

    Struck-through rows and "done/merged in #N" notes record finished work on
    purpose, so they must not be reported as stale references.
    """
    # A row with a struck-through title is finished, including the issue number
    # in its "Where" column, which sits outside the ~~strike~~.
    kept = [ln for ln in roadmap_text.splitlines()
            if not _STRUCK.search(ln) and not re.match(r"\s*done in\b", ln, re.I)]
    text = _DONE_REF.sub(" ", "\n".join(kept))
    return {int(n) for n in re.findall(r"#(\d+)", text)}


def online_findings(issues: list[dict], prs: list[dict], runs: dict[str, str], last_main_commit: str | None,
                    roadmap_text: str, now: datetime | None = None) -> list[str]:
    """Pure function over already-fetched GitHub data (unit-testable without a network)."""
    now = now or datetime.now(timezone.utc)
    out: list[str] = []
    mentioned = {int(n) for n in re.findall(r"#(\d+)", roadmap_text)}
    open_nums = {i["number"] for i in issues if "pull_request" not in i and i.get("label_names", []) != [LABEL]
                 and i.get("title") != TITLE}
    for n in sorted(open_nums - mentioned):
        title = next(i["title"] for i in issues if i["number"] == n)
        out.append(f"open issue #{n} is not in docs/ROADMAP.md: {title}")
    for n in sorted(live_mentions(roadmap_text) - open_nums):
        out.append(f"ROADMAP mentions #{n}, which is not an open issue (closed, a PR, or a typo) — check it")
    for pr in prs:
        updated = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
        if now - updated > timedelta(days=STALE_PR_DAYS):
            out.append(f"PR #{pr['number']} untouched for {(now - updated).days} days: {pr['title']}")
    for name, conclusion in sorted(runs.items()):
        if conclusion not in ("success", "skipped", None):
            out.append(f"workflow '{name}' last conclusion on main: {conclusion}")
    if last_main_commit:
        age = (now - datetime.fromisoformat(last_main_commit.replace("Z", "+00:00"))).days
        if age > 14:
            out.append(f"no commit to main for {age} days")
    return out


def render(offline: list[str], online: list[str] | None) -> str:
    lines = ["# Oversight report", "",
             "Deterministic check (scripts/oversight_check.py, no LLM). Edited only when content changes.", ""]
    lines += ["## Plan files", ""] + ([f"- {f}" for f in offline] or ["- consistent"]) + [""]
    if online is not None:
        lines += ["## GitHub / CI", ""] + ([f"- {f}" for f in online] or ["- consistent"]) + [""]
    return "\n".join(lines)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def run_online(repo: str, token: str) -> tuple[list[str], str]:
    issues = _api("/issues?state=open&per_page=100", token, repo)
    for i in issues:
        i["label_names"] = [lb["name"] for lb in i.get("labels", [])]
    prs = _api("/pulls?state=open&per_page=100", token, repo)
    runs: dict[str, str] = {}
    for wf in ("ci.yml", "dashboard-e2e.yml", "validation-gate.yml", "eval-regression.yml", "qa-headless.yml"):
        try:
            r = _api(f"/actions/workflows/{wf}/runs?branch=main&status=completed&per_page=1", token, repo)
            if r["workflow_runs"]:
                runs[wf] = r["workflow_runs"][0]["conclusion"]
        except Exception as exc:  # noqa: BLE001 - a missing workflow must not hide the rest
            runs[wf] = f"unreadable ({exc.__class__.__name__})"
    commits = _api("/commits?sha=main&per_page=1", token, repo)
    last = commits[0]["commit"]["committer"]["date"] if commits else None
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    return online_findings(issues, prs, runs, last, roadmap), json.dumps({"n": len(issues)})


def upsert(repo: str, token: str, body: str) -> str:
    h = digest(body)
    body = f"{body}\n<!-- oversight-hash: {h} -->\n"
    existing = [i for i in _api(f"/issues?state=open&labels={LABEL}&per_page=5", token, repo) if "pull_request" not in i]
    if not existing:
        try:
            _api("/labels", token, repo, "POST", {"name": LABEL, "color": "5319e7"})
        except Exception:  # noqa: BLE001 - label may already exist
            pass
        _api("/issues", token, repo, "POST", {"title": TITLE, "body": body, "labels": [LABEL]})
        return "created"
    if f"oversight-hash: {h}" in (existing[0].get("body") or ""):
        return "unchanged"
    _api(f"/issues/{existing[0]['number']}", token, repo, "PATCH", {"body": body})
    return "updated"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true", help="plan-file checks only; exit 1 on findings")
    ap.add_argument("--upsert", action="store_true", help="also upsert the oversight issue (needs GITHUB_TOKEN)")
    args = ap.parse_args(argv)
    off = offline_findings()
    if args.offline:
        print(render(off, None))
        return 1 if off else 0
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN and GITHUB_REPOSITORY are required for online mode (use --offline)", file=sys.stderr)
        return 2
    on, _ = run_online(repo, token)
    report = render(off, on)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(report, encoding="utf-8")
    if args.upsert:
        print(f"oversight issue: {upsert(repo, token, report)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
