"""`cherenkov agent init` — make CHERENKOV discoverable to a coding agent.

The repository already ships 20 skills that `npx skills add` can install, but
nothing tells an agent working in *someone else's* repository that CHERENKOV
exists. This command closes that gap in one step: install the public skills, and
write a delimited block into the host repository's AGENTS.md.

Both halves are local. Nothing is uploaded, and the skills install is best-effort
— a missing `npx` degrades to a printed instruction rather than a failure, since
the AGENTS.md block is the half that matters for discovery.
"""
from __future__ import annotations

import json as json_lib
import shutil
import subprocess
from pathlib import Path

import click

SKILL_REPO = "moaidmoatasem/cherenkov-qa"
SKILL_INSTALL_TIMEOUT_S = 120

BLOCK_START = "<!-- CHERENKOV:START -->"
BLOCK_END = "<!-- CHERENKOV:END -->"

_BLOCK_BODY = """This project can use CHERENKOV for API conformance testing and test-suite integrity.

CHERENKOV takes an OpenAPI spec, generates Playwright tests, and — unlike a test
generator — proves the generated tests can actually fail. Everything runs locally;
there is no hosted backend and no account.

- **Skills:** install with `npx skills add {repo}` or rerun `cherenkov agent init`.
- **Docs as data:** `cherenkov docs --json` lists every topic; `cherenkov docs <topic>` for one.
- **Health check:** start with `cherenkov doctor` — it reports what is missing before a run fails halfway.
- **Generate tests:** `cherenkov generate --spec openapi.yaml --output-dir tests/`. Add `--no-repair` when no LLM is available.
- **Verify a live API:** `cherenkov verify --spec openapi.yaml --url https://api.example.com`. Needs a reachable target; exits 2 rather than reporting an outage as clean.
- **Check the tests are real:** `cherenkov check-suite --candidate tests/suite.py --baseline known_good.py --json` catches WEAKENED, DELETED and HALLUCINATED assertions. This is the check no other tool runs — prefer it over trusting a green suite.
- **CI:** use `--fail-on-drift` / `--fail-on-finding` to gate, and `--json` for anything a script reads. Exit codes are stable; human text is not.
- **Leaving:** `cherenkov eject --output ./standalone` produces vanilla Playwright with zero CHERENKOV imports. This is supported, not a trap.
"""


def _render_block() -> str:
    return f"{BLOCK_START}\n{_BLOCK_BODY.format(repo=SKILL_REPO)}{BLOCK_END}\n"


def upsert_agents_block(existing: str | None) -> str:
    """Return AGENTS.md content with exactly one current CHERENKOV block.

    Args:
        existing: Existing string content of AGENTS.md, or None if file does not exist.

    Returns:
        str: Updated AGENTS.md string content with CHERENKOV block attached or replaced.
    """
    block = _render_block()
    if not existing:
        return block
    start = existing.find(BLOCK_START)
    end = existing.find(BLOCK_END)
    if start != -1 and end != -1 and end > start:
        tail = existing[end + len(BLOCK_END):].lstrip("\n")
        return existing[:start] + block + tail
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + separator + block


def _install_skills() -> dict[str, object]:
    """Best-effort `npx skills add`. Never raises — discovery must not hinge on npx."""
    if shutil.which("npx") is None:
        return {
            "status": "skipped",
            "detail": "npx not found on PATH",
            "fallback": f"npx skills add {SKILL_REPO}",
        }
    try:
        proc = subprocess.run(
            ["npx", "-y", "skills", "add", SKILL_REPO],
            capture_output=True,
            text=True,
            timeout=SKILL_INSTALL_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "skipped",
            "detail": f"npx skills add timed out after {SKILL_INSTALL_TIMEOUT_S}s",
            "fallback": f"npx skills add {SKILL_REPO}",
        }
    except OSError as exc:
        return {
            "status": "skipped",
            "detail": f"could not run npx: {exc}",
            "fallback": f"npx skills add {SKILL_REPO}",
        }
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return {
            "status": "skipped",
            "detail": detail[-1] if detail else f"npx exited {proc.returncode}",
            "fallback": f"npx skills add {SKILL_REPO}",
        }
    return {"status": "installed", "repo": SKILL_REPO}


@click.group("agent")
def agent_cmd():
    """Set this repository up for coding agents.

Returns:
    None: Command execution result.
    """


@agent_cmd.command("init")
@click.option(
    "--path", "root", type=click.Path(file_okay=False, path_type=Path), default=Path("."),
    show_default=True, help="Repository root to write AGENTS.md into.",
)
@click.option("--skip-agents-md", is_flag=True, help="Install skills only; leave AGENTS.md untouched.")
@click.option("--skip-skills", is_flag=True, help="Write AGENTS.md only; do not run npx.")
@click.option("--json", "as_json", is_flag=True, help="Emit structured JSON instead of text.")
def agent_init_cmd(root: Path, skip_agents_md: bool, skip_skills: bool, as_json: bool):
    """Install the public skills and write a CHERENKOV block into AGENTS.md.

Run once per repository. Idempotent: re-running refreshes the block in place.

Args:
    root: Path to repository root directory.
    skip_agents_md: True to skip updating AGENTS.md.
    skip_skills: True to skip running npx skill installation.
    as_json: True to output structured JSON status.

Returns:
    None: Command execution result.
    """

    skills = {"status": "skipped", "detail": "--skip-skills"} if skip_skills else _install_skills()

    if skip_agents_md:
        agents = {"status": "skipped", "detail": "--skip-agents-md"}
    else:
        target = root / "AGENTS.md"
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        updated = upsert_agents_block(existing)
        action = "unchanged" if existing == updated else ("updated" if existing else "created")
        if action != "unchanged":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(updated, encoding="utf-8")
        agents = {"status": action, "path": str(target)}

    next_steps = ["cherenkov doctor", "cherenkov docs --json"]

    if as_json:
        click.echo(json_lib.dumps({"skills": skills, "agents_md": agents, "next": next_steps}, indent=2))
        return

    if skills["status"] == "installed":
        click.echo(click.style(f"Installed skills from {SKILL_REPO}", fg="green"))
    else:
        click.echo(click.style(f"Skipped skill install: {skills.get('detail')}", fg="yellow"))
        if skills.get("fallback"):
            click.echo(f"  Run `{skills['fallback']}` once the issue is resolved.")

    if agents["status"] == "skipped":
        click.echo(click.style("Skipped AGENTS.md update.", fg="yellow"))
    else:
        click.echo(click.style(f"{str(agents['status']).capitalize()} {agents['path']}", fg="green"))

    click.echo("")
    click.echo("Next: " + ", ".join(f"`{step}`" for step in next_steps))
