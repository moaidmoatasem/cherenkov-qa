#!/usr/bin/env python3
"""Agent Sync — CLI tool for Sync Driven Development (SDD).

Usage:
    agent_sync before --task <type> [--budget <n>] [--source <name>]
    agent_sync after --summary <text>
    agent_sync log --type <finding|decision|pitfall|context> <message>
    agent_sync token [--action <type> --count <n> --item <name>]
    agent_sync status [--json]
    agent_sync compact [--force]
    agent_sync experience query <pattern> [--outcome <str>] [--sort <field>]

Environment:
    CHERENKOV_ROOT  — project root (default: auto-detect from script path)
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Path resolution ──────────────────────────────────────────────────


def _project_root() -> Path:
    env = os.environ.get("CHERENKOV_ROOT")
    if env:
        return Path(env).resolve()
    # Auto-detect: this script is at scripts/agent_sync.py
    return Path(__file__).resolve().parent.parent


ROOT = _project_root()
SYNC_DIR = ROOT / "agent_memory" / "sync"
FINDINGS_DIR = SYNC_DIR / "findings"
CONTEXT_FILE = SYNC_DIR / "context.json"
TOKENS_FILE = SYNC_DIR / "tokens.json"
SESSION_FILE = SYNC_DIR / "session.json"
EXPERIENCE_FILE = SYNC_DIR / "experience.json"


# ── JSON helpers ─────────────────────────────────────────────────────


def _read_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ── Session ID ───────────────────────────────────────────────────────


def _new_session_id() -> str:
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"sess_{ts}_{short}"


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── Subcommands ──────────────────────────────────────────────────────


def cmd_before(task_type: str, budget: Optional[int] = None, source: str = "cherenkov"):
    """Start a new agent session: load context, init state."""
    session_id = _new_session_id()
    now = _timestamp()

    # Init session
    session = {
        "session": {
            "id": session_id,
            "status": "open",
            "task": task_type,
            "started_at": now,
            "ended_at": None,
            "findings_count": 0,
            "token_total": 0,
            "summary": None,
            "compacted": False,
            "task_type": task_type,
            "source": source,
        },
        "previous_sessions": [],
        "sessions_since_compact": 0,
    }

    # Carry forward previous sessions from old session.json
    old = _read_json(SESSION_FILE)
    if old.get("session") and old["session"].get("id") != "sess_init":
        session["previous_sessions"] = old.get("previous_sessions", [])
        prev = {
            "id": old["session"]["id"],
            "task": old["session"].get("task"),
            "ended_at": old["session"].get("ended_at"),
            "summary": old["session"].get("summary"),
            "token_total": old["session"].get("token_total", 0),
        }
        session["previous_sessions"].append(prev)
        # Keep last 10
        session["previous_sessions"] = session["previous_sessions"][-10:]
        session["sessions_since_compact"] = old.get("sessions_since_compact", 0) + 1

    _write_json(SESSION_FILE, session)

    # Init token tracker for this session
    tokens = _read_json(TOKENS_FILE)
    if not tokens.get("budget"):
        tokens = {
            "budget": {
                "per_session": budget or 50000,
                "hard_cap": (budget or 50000) * 2,
                "warning_at_pct": 60,
                "compact_at_pct": 80,
                "emergency_at_pct": 95,
            },
            "current_session": {},
            "historical": {
                "total_all_time": 0,
                "sessions_completed": 0,
                "avg_per_session": 0,
                "by_task_type": {},
            },
            "top_consumers": [],
        }
    tokens["current_session"] = {
        "session_id": session_id,
        "prompt": 0,
        "generate": 0,
        "read": 0,
        "search": 0,
        "total": 0,
    }
    _write_json(TOKENS_FILE, tokens)

    # Load context snippets for this task type
    context = _read_json(CONTEXT_FILE)
    snippets = context.get("snippets", [])
    task_map = context.get("task_type_map", {})
    keys_to_load = set(task_map.get("*", []))
    keys_to_load.update(task_map.get(task_type, []))

    loaded = [s for s in snippets if s["key"] in keys_to_load]
    total_est = sum(s["tokens_estimate"] for s in loaded)

    print(f"[SDD] Session started: {session_id}")
    print(f"   Task type: {task_type}")
    print(f"   Context loaded: {len(loaded)} snippets (~{total_est} tokens)")
    for s in loaded:
        print(f"     [{s['key']}] ({s['tokens_estimate']}t) {s['content'][:80]}...")
    print(f"   Budget: {tokens['budget']['per_session']} tokens")
    print(f"   Previous sessions: {len(session['previous_sessions'])}")


def cmd_after(summary: str):
    """Close session: compact findings, update experience, update tokens."""
    session = _read_json(SESSION_FILE)
    if not session.get("session") or session["session"].get("status") != "open":
        print("No open session to close. Run 'agent_sync before' first.")
        sys.exit(1)

    sid = session["session"]["id"]
    session["session"]["status"] = "closed"
    session["session"]["ended_at"] = _timestamp()
    session["session"]["summary"] = summary

    tokens = _read_json(TOKENS_FILE)
    tok = tokens.get("current_session", {})
    total = tok.get("total", 0)
    session["session"]["token_total"] = total
    session["session"]["compacted"] = True

    _write_json(SESSION_FILE, session)

    # Update historical token stats
    hist = tokens.get("historical", {})
    hist["total_all_time"] = hist.get("total_all_time", 0) + total
    hist["sessions_completed"] = hist.get("sessions_completed", 0) + 1
    c = hist["sessions_completed"]
    hist["avg_per_session"] = round(hist["total_all_time"] / c, 1) if c else 0

    tt = session["session"].get("task_type", "unknown")
    by_type = hist.get("by_task_type", {})
    if tt not in by_type:
        by_type[tt] = {"sessions": 0, "total_tokens": 0}
    by_type[tt]["sessions"] += 1
    by_type[tt]["total_tokens"] += total
    hist["by_task_type"] = by_type
    tokens["historical"] = hist

    # Clear current session
    tokens["current_session"] = {
        "session_id": None,
        "prompt": 0,
        "generate": 0,
        "read": 0,
        "search": 0,
        "total": 0,
    }
    _write_json(TOKENS_FILE, tokens)

    # Extract experience from findings
    findings_path = FINDINGS_DIR / f"{sid}.json"
    findings = []
    if findings_path.exists():
        findings = _read_json(findings_path).get("findings", [])

    # Build experience record
    decisions = [f for f in findings if f.get("type") == "decision"]
    pitfall_count = len([f for f in findings if f.get("type") == "pitfall"])
    finding_count = len(findings)

    exp = _read_json(EXPERIENCE_FILE)
    if not exp.get("experiences"):
        exp["experiences"] = []

    for d in decisions[-3:]:  # Max 3 decisions per session
        exp_rec = {
            "id": f"exp_{sid}_{uuid.uuid4().hex[:4]}",
            "timestamp": _timestamp(),
            "task": session["session"].get("task"),
            "action": d.get("message", summary)[:200],
            "rationale": d.get("rationale", ""),
            "outcome": "success",  # optimistic; owner can revise
            "token_cost": total,
            "patterns": session["session"].get("task_type", "unknown").split(","),
            "session_id": sid,
        }
        exp["experiences"].append(exp_rec)

    exp["experience_count"] = len(exp["experiences"])
    exp["sessions_contributing"] = hist["sessions_completed"]
    exp["last_updated"] = _timestamp()

    # Update pattern index
    pidx = exp.get("pattern_index", {})
    for rec in exp["experiences"]:
        for pat in rec.get("patterns", []):
            pat = pat.strip()
            if pat not in pidx:
                pidx[pat] = []
            if rec["id"] not in pidx[pat]:
                pidx[pat].append(rec["id"])
    exp["pattern_index"] = pidx
    _write_json(EXPERIENCE_FILE, exp)

    print(f"Session closed: {sid}")
    print(f"   Summary: {summary}")
    print(f"   Token total: {total}")
    print(f"   Findings logged: {finding_count}")
    print(f"   Decisions captured: {len(decisions)}")
    print(f"   Pitfalls noted: {pitfall_count}")
    print(f"   Total experience records: {exp['experience_count']}")


def cmd_log(log_type: str, message: str):
    """Log a finding during an active session."""
    session = _read_json(SESSION_FILE)
    if not session.get("session") or session["session"].get("status") != "open":
        print("No open session. Run 'agent_sync before' first.")
        sys.exit(1)

    sid = session["session"]["id"]
    findings_path = FINDINGS_DIR / f"{sid}.json"

    findings_data = _read_json(findings_path)
    if "findings" not in findings_data:
        findings_data["session_id"] = sid
        findings_data["findings"] = []

    findings_data["findings"].append(
        {"timestamp": _timestamp(), "type": log_type, "message": message}
    )
    _write_json(findings_path, findings_data)

    # Update session count
    session["session"]["findings_count"] = len(findings_data["findings"])
    _write_json(SESSION_FILE, session)

    print(f"Logged [{log_type}]: {message[:120]}")


def cmd_token(action_type: Optional[str], count: Optional[int], item: Optional[str]):
    """Track token usage for this session."""
    if action_type is None and count is None and item is None:
        # Just show token status
        return cmd_status(json_output=False)

    tokens = _read_json(TOKENS_FILE)
    cur = tokens.get("current_session", {})
    if not cur.get("session_id"):
        print("No active session. Token tracking requires an open session.")
        sys.exit(1)

    if action_type not in ("prompt", "generate", "read", "search"):
        print(
            f"Unknown action type: {action_type}. Use: prompt, generate, read, search"
        )
        sys.exit(1)

    if count is None or count < 0:
        print("Token count must be a positive integer.")
        sys.exit(1)

    cur[action_type] = cur.get(action_type, 0) + count
    total = sum(cur.get(k, 0) for k in ("prompt", "generate", "read", "search"))
    cur["total"] = total
    tokens["current_session"] = cur

    # Track top consumers
    if item:
        consumers = tokens.get("top_consumers", [])
        consumers.append(
            {
                "timestamp": _timestamp(),
                "action": action_type,
                "count": count,
                "item": item,
                "running_total": total,
            }
        )
        # Keep last 50
        tokens["top_consumers"] = consumers[-50:]

    _write_json(TOKENS_FILE, tokens)

    budget = tokens.get("budget", {}).get("per_session", 50000)
    pct = round(total / budget * 100, 1)

    line = f"Token: +{count} {action_type} -> total {total}/{budget} ({pct}%)"
    if item:
        line += f" [{item}]"

    if pct >= 95:
        line += " [EMERGENCY] session will auto-close"
    elif pct >= 80:
        line += " [COMPACT NEEDED]"
    elif pct >= 60:
        line += " [near budget]"
    print(line)


def cmd_status(json_output: bool = False):
    """Show current sync state."""
    session = _read_json(SESSION_FILE)
    tokens = _read_json(TOKENS_FILE)
    exp = _read_json(EXPERIENCE_FILE)

    if json_output:
        data = {
            "session": session.get("session"),
            "tokens": tokens.get("current_session"),
            "budget": tokens.get("budget"),
            "historical": tokens.get("historical"),
            "experience_count": exp.get("experience_count", 0),
        }
        print(json.dumps(data, indent=2))
        return

    s = session.get("session", {})
    sid = s.get("id", "none")
    status = s.get("status", "unknown")

    print("=== SDD Status ===")
    print(f"Session:    {sid} [{status}]")
    if s.get("task"):
        print(f"Task:       {s['task']}")
    if s.get("started_at"):
        print(f"Started:    {s['started_at']}")
    if s.get("ended_at"):
        print(f"Ended:      {s['ended_at']}")
    if s.get("summary"):
        print(f"Summary:    {s['summary']}")
    print(f"Findings:   {s.get('findings_count', 0)}")

    tok = tokens.get("current_session", {})
    budget = tokens.get("budget", {})
    per_session = budget.get("per_session", 50000)
    total = tok.get("total", 0)
    pct = round(total / per_session * 100, 1) if per_session else 0
    print(f"Tokens:     {total}/{per_session} ({pct}%)")
    print(f"  Prompt:   {tok.get('prompt', 0)}")
    print(f"  Generate: {tok.get('generate', 0)}")
    print(f"  Read:     {tok.get('read', 0)}")
    print(f"  Search:   {tok.get('search', 0)}")

    hist = tokens.get("historical", {})
    print(
        f"History:    {hist.get('sessions_completed', 0)} sessions, "
        f"{hist.get('total_all_time', 0)} total tokens, "
        f"avg {hist.get('avg_per_session', 0)}/session"
    )

    print(f"Experience: {exp.get('experience_count', 0)} records")
    prev = session.get("previous_sessions", [])
    if prev:
        print(
            f"Last session: {prev[-1].get('id')} - {prev[-1].get('summary', 'no summary')[:80]}"
        )


def cmd_compact(force: bool = False):
    """Compact session context: promote high-value, prune stale."""
    context = _read_json(CONTEXT_FILE)
    snippets = context.get("snippets", [])

    # Count how many sessions each snippet was used
    session = _read_json(SESSION_FILE)
    sessions_since = session.get("sessions_since_compact", 0)

    if sessions_since < 3 and not force:
        print(
            f"Only {sessions_since} sessions since last compact. Use --force to override."
        )
        return

    # Auto-promote: if a task type has been used 3+ sessions, ensure its context is loaded
    exp = _read_json(EXPERIENCE_FILE)
    by_type = {}
    for rec in exp.get("experiences", []):
        for pat in rec.get("patterns", []):
            by_type[pat] = by_type.get(pat, 0) + 1

    # Check if any high-frequency task types are missing from task_type_map
    ttm = context.get("task_type_map", {})
    promoted = 0
    for pat, count in by_type.items():
        if count >= 3 and pat not in ttm:
            # Find snippets with this pattern
            matching = [s for s in snippets if pat in s.get("key", "")]
            if matching:
                ttm[pat] = [matching[0]["key"]]
                promoted += 1

    if promoted:
        context["task_type_map"] = ttm
        print(f"Promoted {promoted} task types to auto-load context")

    # Reset compact counter
    session["sessions_since_compact"] = 0
    _write_json(SESSION_FILE, session)
    context["last_refreshed"] = _timestamp()
    _write_json(CONTEXT_FILE, context)

    print(f"Context compacted. {len(snippets)} snippets, {len(ttm)} task mappings.")


def cmd_experience_query(
    pattern: str, outcome: Optional[str] = None, sort: Optional[str] = None
):
    """Query past experiences by pattern."""
    exp = _read_json(EXPERIENCE_FILE)
    results = []

    for rec in exp.get("experiences", []):
        pats = " ".join(rec.get("patterns", []))
        if (
            pattern.lower() in pats.lower()
            or pattern.lower() in rec.get("action", "").lower()
        ):
            if outcome and rec.get("outcome") != outcome:
                continue
            results.append(rec)

    if sort == "cost":
        results.sort(key=lambda r: r.get("token_cost", 0), reverse=True)
    elif sort == "date":
        results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

    if not results:
        print(f"No experiences match pattern '{pattern}'.")
        return

    print(f"Found {len(results)} experience(s) for '{pattern}':")
    for r in results:
        print(f"\n  [{r['id']}] {r['action'][:100]}")
        print(
            f"  Outcome: {r['outcome']} | Tokens: {r['token_cost']} | Patterns: {', '.join(r.get('patterns', []))}"
        )
        if r.get("rationale"):
            print(f"  Rationale: {r['rationale'][:150]}")
        print(f"  Session: {r['session_id']} | {r['timestamp']}")


# ── CLI Entry Point ──────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "before":
        task = None
        budget = None
        source = "cherenkov"
        for i, arg in enumerate(sys.argv[2:], start=3):
            if arg == "--task" and i < len(sys.argv):
                task = sys.argv[i]
            elif arg == "--budget" and i < len(sys.argv):
                budget = int(sys.argv[i])
            elif arg == "--source" and i < len(sys.argv):
                source = sys.argv[i]
        if not task:
            print("Usage: agent_sync before --task <type> [--source <name>]")
            sys.exit(1)
        cmd_before(task, budget, source)

    elif cmd == "after":
        summary = None
        for i, arg in enumerate(sys.argv[2:], start=3):
            if arg == "--summary" and i < len(sys.argv):
                summary = sys.argv[i]
        if not summary:
            print("Usage: agent_sync after --summary <text>")
            sys.exit(1)
        cmd_after(summary)

    elif cmd == "log":
        log_type = "finding"
        message_parts = []
        for i, arg in enumerate(sys.argv[2:], start=3):
            if arg == "--type" and i < len(sys.argv):
                log_type = sys.argv[i]
            elif arg.startswith("--"):
                continue
            else:
                message_parts.append(arg)
        if not message_parts:
            print("Usage: agent_sync log --type <type> <message>")
            sys.exit(1)
        cmd_log(log_type, " ".join(message_parts))

    elif cmd == "token":
        action = None
        count = None
        item = None
        for i, arg in enumerate(sys.argv[2:], start=3):
            if arg == "--action" and i < len(sys.argv):
                action = sys.argv[i]
            elif arg == "--count" and i < len(sys.argv):
                count = int(sys.argv[i])
            elif arg == "--item" and i < len(sys.argv):
                item = sys.argv[i]
        cmd_token(action, count, item)

    elif cmd == "status":
        json_mode = "--json" in sys.argv
        cmd_status(json_output=json_mode)

    elif cmd == "compact":
        force = "--force" in sys.argv
        cmd_compact(force=force)

    elif cmd == "experience" and len(sys.argv) >= 4 and sys.argv[2] == "query":
        pattern = None
        outcome = None
        sort = None
        for i, arg in enumerate(sys.argv[3:], start=4):
            if arg == "--outcome" and i < len(sys.argv):
                outcome = sys.argv[i]
            elif arg == "--sort" and i < len(sys.argv):
                sort = sys.argv[i]
            elif not arg.startswith("--"):
                pattern = arg
        if not pattern:
            print(
                "Usage: agent_sync experience query <pattern> [--outcome <str>] [--sort <field>]"
            )
            sys.exit(1)
        cmd_experience_query(pattern, outcome, sort)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__.strip())
        sys.exit(1)


if __name__ == "__main__":
    main()
