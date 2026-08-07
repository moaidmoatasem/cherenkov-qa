"""Agent-discoverability surface: `cherenkov agent init` and `cherenkov docs`.

These two commands exist so a coding agent that has never heard of CHERENKOV can
find it and parse it. The contracts worth protecting are therefore: the AGENTS.md
write is idempotent and non-destructive, and the JSON is shaped the same every
time. Both are easy to break with an innocuous edit, and neither breaks loudly.
"""

from __future__ import annotations

import json
import re
import shlex

import pytest
from click.testing import CliRunner

from cherenkov.cli.commands.agent_cmd import (
    BLOCK_END,
    BLOCK_START,
    agent_cmd,
    upsert_agents_block,
)
from cherenkov.cli.commands.docs_cmd import TOPICS, docs_cmd


# --------------------------------------------------------------------------- #
# AGENTS.md block
# --------------------------------------------------------------------------- #

def test_creates_block_when_no_file_exists():
    out = upsert_agents_block(None)
    assert out.startswith(BLOCK_START)
    assert out.rstrip().endswith(BLOCK_END)


def test_rerun_is_idempotent():
    once = upsert_agents_block(None)
    assert upsert_agents_block(once) == once, "re-running must not append a second block"


def test_block_is_replaced_in_place_not_appended():
    stale = f"# House rules\n\nBe careful.\n\n{BLOCK_START}\nold and wrong\n{BLOCK_END}\n"
    out = upsert_agents_block(stale)
    assert out.count(BLOCK_START) == 1
    assert "old and wrong" not in out
    assert "# House rules" in out, "surrounding content must survive"
    assert "Be careful." in out


def test_existing_content_is_preserved_when_block_is_added():
    out = upsert_agents_block("# House rules\n\nBe careful.\n")
    assert out.startswith("# House rules")
    assert BLOCK_START in out


def test_content_after_the_block_survives_replacement():
    stale = f"before\n\n{BLOCK_START}\nold\n{BLOCK_END}\n\nafter\n"
    out = upsert_agents_block(stale)
    assert "before" in out and "after" in out
    assert "old" not in out


def test_block_names_the_integrity_check():
    """The block is the only thing an agent reads before deciding to use the tool,
    so it must carry the differentiator, not just a command list."""
    out = upsert_agents_block(None)
    assert "check-suite" in out
    assert "eject" in out, "the exit path is part of the pitch, not a footnote"


# --------------------------------------------------------------------------- #
# agent init
# --------------------------------------------------------------------------- #

def test_agent_init_writes_file_and_reports_json(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        agent_cmd, ["init", "--path", str(tmp_path), "--skip-skills", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["agents_md"]["status"] == "created"
    assert payload["skills"]["status"] == "skipped"
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8").startswith(BLOCK_START)


def test_agent_init_second_run_reports_unchanged(tmp_path):
    runner = CliRunner()
    args = ["init", "--path", str(tmp_path), "--skip-skills", "--json"]
    runner.invoke(agent_cmd, args)
    result = runner.invoke(agent_cmd, args)
    assert json.loads(result.output)["agents_md"]["status"] == "unchanged"


def test_agent_init_skip_agents_md_leaves_no_file(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        agent_cmd,
        ["init", "--path", str(tmp_path), "--skip-skills", "--skip-agents-md", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["agents_md"]["status"] == "skipped"
    assert not (tmp_path / "AGENTS.md").exists()


def test_agent_init_survives_a_missing_npx(tmp_path, monkeypatch):
    """Discovery must not hinge on Node being installed."""
    monkeypatch.setattr("cherenkov.cli.commands.agent_cmd.shutil.which", lambda _: None)
    runner = CliRunner()
    result = runner.invoke(agent_cmd, ["init", "--path", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["skills"]["status"] == "skipped"
    assert payload["skills"]["fallback"].startswith("npx skills add")
    assert payload["agents_md"]["status"] == "created", "AGENTS.md still gets written"


# --------------------------------------------------------------------------- #
# docs
# --------------------------------------------------------------------------- #

def test_docs_lists_every_topic_without_arguments():
    result = CliRunner().invoke(docs_cmd, [])
    assert result.exit_code == 0
    for name in TOPICS:
        assert name in result.output


def test_docs_json_carries_every_topic_with_a_stable_shape():
    result = CliRunner().invoke(docs_cmd, ["--json"])
    assert result.exit_code == 0
    topics = json.loads(result.output)["topics"]
    assert len(topics) == len(TOPICS)
    for entry in topics:
        assert set(entry) == {"topic", "summary", "commands", "notes"}
        assert entry["commands"], f"{entry['topic']} lists no commands"
        assert entry["notes"], f"{entry['topic']} carries no notes — the notes are the point"


@pytest.mark.parametrize("name", sorted(TOPICS))
def test_single_topic_json_round_trips(name):
    result = CliRunner().invoke(docs_cmd, [name, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["topic"] == name


def test_unknown_topic_exits_nonzero_and_lists_the_real_ones():
    result = CliRunner().invoke(docs_cmd, ["definitely-not-a-topic"])
    assert result.exit_code != 0
    assert "quickstart" in result.output


def test_every_documented_command_starts_with_a_real_invocation():
    """Guards against a topic drifting into prose or a stale binary name."""
    for name, entry in TOPICS.items():
        for command in entry["commands"]:
            assert command.startswith(("cherenkov ", "cd ", "curl ", "cat ")), (
                f"topic {name} lists a non-command: {command!r}"
            )


def _resolve(root, parts):
    """Walk `parts` down the Click tree until the first flag."""
    cmd, i = root, 0
    while i < len(parts) and not parts[i].startswith("-"):
        nxt = getattr(cmd, "commands", {}).get(parts[i])
        if nxt is None:
            return cmd, parts[i], i
        cmd, i = nxt, i + 1
    return cmd, None, i


def test_documented_commands_and_flags_all_exist():
    """The whole point of `docs --json` is that an agent can run what it reads.

    A topic that cites a flag which does not exist is worse than no docs: the
    agent burns a turn on a usage error and has no way to tell a typo from a
    version skew. This resolves every documented invocation against the real
    Click tree — the same contract `scripts/check_cli_flags.py` enforces for the
    reference doc, applied to the machine-readable surface.
    """
    from cherenkov.cli.core import _register_commands, cli

    _register_commands()

    problems: list[str] = []
    for topic, entry in TOPICS.items():
        for line in entry["commands"]:
            if not line.startswith("cherenkov "):
                continue
            parts = shlex.split(line)[1:]
            cmd, missing, idx = _resolve(cli, parts)
            if missing:
                problems.append(f"{topic}: no such command {missing!r} — {line}")
                continue
            known = {
                opt
                for param in cmd.params
                for opt in (*getattr(param, "opts", []), *getattr(param, "secondary_opts", []))
            }
            for token in parts[idx:]:
                if token.startswith("--") and token not in known:
                    problems.append(f"{topic}: `{cmd.name}` has no {token} — {line}")

    assert not problems, "docs topics cite flags that do not exist:\n" + "\n".join(problems)


def test_agents_md_block_cites_only_real_flags():
    """The block is copied verbatim into strangers' repositories.

    It is the single artifact an agent reads before deciding whether to run
    anything, so a wrong flag here is the most expensive kind: the agent's first
    ever CHERENKOV command fails, and it has no prior to tell noise from a real
    incompatibility. Same contract as the docs topics, applied to the block.
    """
    from cherenkov.cli.core import _register_commands, cli

    _register_commands()

    problems: list[str] = []
    for match in re.finditer(r"`(cherenkov [^`]+)`", upsert_agents_block(None)):
        if "<" in match.group(1):
            continue  # `cherenkov docs <topic>` is a form, not an invocation
        parts = shlex.split(match.group(1))[1:]
        cmd, missing, idx = _resolve(cli, parts)
        if missing:
            problems.append(f"no such command {missing!r} — {match.group(1)}")
            continue
        known = {
            opt
            for param in cmd.params
            for opt in (*getattr(param, "opts", []), *getattr(param, "secondary_opts", []))
        }
        for token in parts[idx:]:
            if token.startswith("--") and token not in known:
                problems.append(f"`{cmd.name}` has no {token} — {match.group(1)}")

    assert not problems, "AGENTS.md block cites flags that do not exist:\n" + "\n".join(problems)
