"""`cherenkov check` — the integrity gate for AI-written tests.

A thin front door over the `check-suite` analysis (no LLM, no server, no Node):

    cherenkov check --baseline origin/main          # tests/ auto-detected
    cherenkov check ./e2e --baseline HEAD~1 --format md

Differences from `check-suite`: the baseline can be a git ref, the test
directory is auto-detected, findings always fail the command (exit 1), and
`--format md` renders a sticky PR-comment body. Exit codes: 0 clean,
1 violations found, 2 usage error.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import click

from cherenkov.cli.commands.check_suite import (
    _check_one_file,
    _collect_suite_files,
    _not_checked_reasons,
    _pair_baseline,
    _print_findings,
)

COMMENT_MARKER = "<!-- cherenkov-check -->"
_TEST_DIR_CANDIDATES = ("tests", "test", "e2e", "__tests__", "spec")


def _detect_tests_dir(cwd: Path) -> Path | None:
    for name in _TEST_DIR_CANDIDATES:
        if (cwd / name).is_dir():
            return cwd / name
    return None


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def materialise_baseline(ref: str, tests: Path, dest: Path) -> Path:
    """Write the `.py`/`.ts` files of `tests` as they were at git `ref` into `dest`.

    Returns the baseline root (a directory when `tests` is one, else a file).
    Raises click.UsageError when `ref` or the repo cannot be resolved.
    """
    anchor = tests if tests.is_dir() else tests.parent
    top = _git(["rev-parse", "--show-toplevel"], anchor)
    if top.returncode != 0:
        raise click.UsageError(
            f"--baseline {ref!r} is not an existing path and {anchor} is not inside a git repository."
        )
    toplevel = Path(top.stdout.strip()).resolve()
    rel = tests.resolve().relative_to(toplevel).as_posix()
    if not _git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], toplevel).returncode == 0:
        raise click.UsageError(f"--baseline {ref!r} is neither an existing path nor a git ref.")

    listing = _git(["ls-tree", "-r", "--name-only", ref, "--", rel], toplevel)
    names = [n for n in listing.stdout.splitlines() if n.endswith((".py", ".ts"))]
    if tests.is_file():
        if rel not in names:
            raise click.UsageError(f"{rel} does not exist at {ref}.")
        out = dest / tests.name
        out.write_text(_git(["show", f"{ref}:{rel}"], toplevel).stdout, encoding="utf-8")
        return out
    for name in names:
        target = dest / Path(name).relative_to(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_git(["show", f"{ref}:{name}"], toplevel).stdout, encoding="utf-8")
    return dest


def _markdown(payload: dict) -> str:
    findings = payload["findings"]
    verdict = "FAIL" if findings else "PASS"
    lines = [COMMENT_MARKER, f"### Cherenkov integrity check — **{verdict}**", ""]
    if findings:
        lines += [f"{len(findings)} integrity violation(s) in AI-modified tests:", ""]
        lines += [f"- `{f.split()[0]}` {f[len(f.split()[0]):].strip()}" for f in findings]
    else:
        n, total = len(payload["checks_run"]), 3
        scope = "" if n == total else f" in the {n}/{total} checks that ran"
        lines.append(f"No integrity violations found{scope}.")
    lines += ["", f"Checked {len(payload['files_checked'])} suite file(s); checks run: "
              f"{', '.join(payload['checks_run']) or 'none'}."]
    if payload["checks_not_run"]:
        lines += ["", "**Not checked:**"]
        lines += [f"- `{e['check']}` — {e['reason']}" for e in payload["checks_not_run"]]
    return "\n".join(lines) + "\n"


@click.command("check")
@click.argument("tests", required=False, type=click.Path(exists=True))
@click.option("--baseline", "-b", default=None,
              help="Known-honest suite to compare against: a git ref (origin/main, HEAD~1, a SHA) "
                   "or a path. Needed for WEAKENED and DELETED detection.")
@click.option("--spec", "-s", default=None, type=click.Path(exists=True),
              help="OpenAPI spec (YAML/JSON). Needed for HALLUCINATED detection.")
@click.option("--format", "fmt", type=click.Choice(["text", "json", "md"]), default="text",
              show_default=True, help="Output format; md is a sticky PR-comment body.")
@click.option("--output", "-o", default=None, help="Also write the output to this file.")
def check_cmd(tests: str | None, baseline: str | None, spec: str | None, fmt: str, output: str | None) -> None:
    """Prove an AI's change to your tests did not weaken them.

    Runs fast static analysis (no LLM, no server) and exits 1 when it finds a
    WEAKENED, DELETED or HALLUCINATED assertion. Every verdict states which of
    the three checks actually ran.

    \b
    Examples:
      cherenkov check --baseline origin/main
      cherenkov check ./e2e --baseline HEAD~1 --spec openapi.yaml
      cherenkov check --baseline $BASE_SHA --format md > comment.md
    """
    cwd = Path.cwd()
    cand_path = Path(tests) if tests else _detect_tests_dir(cwd)
    if cand_path is None:
        raise click.UsageError(
            f"No tests path given and none of {', '.join(_TEST_DIR_CANDIDATES)} exists in {cwd}."
        )
    cand_files = _collect_suite_files(cand_path) if cand_path.is_dir() else [cand_path]
    if not cand_files:
        click.echo(f"[ERROR] No .py or .ts test suites found under {cand_path}.", err=True)
        sys.exit(2)

    with tempfile.TemporaryDirectory(prefix="cherenkov-baseline-") as tmp:
        base_path: Path | None = None
        if baseline:
            base_path = Path(baseline) if Path(baseline).exists() else materialise_baseline(
                baseline, cand_path, Path(tmp))
        if base_path is not None and base_path.is_dir() and not cand_path.is_dir():
            raise click.UsageError("--baseline is a directory but the tests path is a single file.")

        findings: list[str] = []
        per_file: list[dict] = []
        ran = {"WEAKENED": False, "DELETED": False, "HALLUCINATED": False}
        skipped: dict[str, str] = {}
        for cand_file in cand_files:
            base_file = _pair_baseline(cand_file, cand_path, base_path)
            file_findings = _check_one_file(cand_file, base_file, spec, ran, skipped)
            if len(cand_files) > 1:
                file_findings = [f"{cand_file.relative_to(cand_path)}: {f}" for f in file_findings]
            per_file.append({"file": str(cand_file), "findings": file_findings})
            findings.extend(file_findings)

    checks_run = sorted(k for k, v in ran.items() if v)
    not_checked = _not_checked_reasons(ran, skipped)
    payload = {
        "tests": str(cand_path),
        "baseline": baseline,
        "findings": findings,
        "clean": not findings,
        "files_checked": [str(p) for p in cand_files],
        "per_file": per_file,
        "checks_run": checks_run,
        "checks_not_run": not_checked,
    }
    if fmt == "json":
        rendered = json.dumps(payload, indent=2)
        click.echo(rendered)
    elif fmt == "md":
        rendered = _markdown(payload)
        click.echo(rendered, nl=False)
    else:
        label = cand_path.name if len(cand_files) == 1 else f"{cand_path} ({len(cand_files)} suites)"
        _print_findings(label, findings, checks_run, not_checked)
        rendered = json.dumps(payload, indent=2)
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    if findings:
        sys.exit(1)
