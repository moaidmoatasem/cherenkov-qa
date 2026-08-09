"""
cherenkov/cli/commands/audit.py — E0.5h: Productize the Audit.

Baseline-Free Oracle audit command. Evaluates the quality of an existing test suite
by running it against a target (to record expected behavior) and then against
mutants derived from the OpenAPI spec.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys

import click

from cherenkov.cli.loaders import load_spec
from cherenkov.divergence.mutant_synth import synthesize_mutant_battery
from cherenkov.divergence.self_play import BrokenImplServer
from cherenkov.verdict.traffic_capture import RecordingProxy

_log = logging.getLogger(__name__)


def _run_suite(test_cmd: list[str], url: str) -> tuple[bool, str]:
    """Run the user's test suite, returning (passed, output)."""
    env = os.environ.copy()
    env["API_URL"] = url
    try:
        proc = subprocess.run(
            test_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = proc.returncode == 0
        return passed, proc.stdout + "\n" + proc.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout expired"
    except Exception as exc:
        return False, str(exc)


@click.command("audit")
@click.option(
    "--target",
    "-t",
    required=True,
    help="Base URL of the live server to record baseline from.",
)
@click.option(
    "--spec",
    "-s",
    required=True,
    help="Path or URL to the OpenAPI spec JSON/YAML file.",
)
@click.option(
    "--test-cmd",
    "-c",
    required=True,
    help="Command to run the test suite (e.g. 'npx playwright test tests/'). Will receive API_URL in environment.",
)
@click.option(
    "--proxy-port",
    default=9100,
    help="Port for the recording proxy (default 9100).",
)
@click.option(
    "--mock-port",
    default=9101,
    help="Port for the mutant mock server (default 9101).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit structured JSON instead of text.",
)
def audit_cmd(
    target: str,
    spec: str,
    test_cmd: str,
    proxy_port: int,
    mock_port: int,
    as_json: bool,
) -> None:
    """Audit a test suite for meaningful assertions.

    Evaluates whether the test suite actually catches regressions by:
      1. Recording the baseline against the live target.
      2. Generating spec-derived mutants (status, value, missing, enum).
      3. Replaying the test suite against the mutants.
    """
    if not as_json:
        click.echo("\nCHERENKOV audit (Baseline-Free Oracle)")
        click.echo(f"  Target   : {target}")
        click.echo(f"  Spec     : {spec}")
        click.echo(f"  Test Cmd : {test_cmd}")
        click.echo("")

    spec_dict = load_spec(spec)
    if spec_dict is None:
        sys.exit(2)

    # 1. Record Baseline
    if not as_json:
        click.echo(f"[*] Recording baseline against live target ({target})...")
    with RecordingProxy(port=proxy_port, target=target) as proxy:
        passed, out = _run_suite(test_cmd.split(), proxy.url)
        if not passed:
            if as_json:
                import json as json_lib
                click.echo(json_lib.dumps({"error": "Test suite failed against the live target", "output": out}))
            else:
                click.echo(
                    f"[ERROR] Test suite failed against the live target! Output:\n{out}", err=True
                )
                click.echo("The test suite must pass the baseline to be audited.")
            sys.exit(1)

        interactions = len(proxy.interactions)
        replay_map = proxy.replay_map()
        if not as_json:
            click.echo(f"    ✓ Suite passed baseline. Recorded {interactions} interactions.")

    if not replay_map:
        if as_json:
            import json as json_lib
            click.echo(json_lib.dumps({"error": "No traffic was recorded. Is the test suite using API_URL?"}))
        else:
            click.echo("[ERROR] No traffic was recorded. Is the test suite using API_URL?")
        sys.exit(1)

    # Extract known identifiers from recorded traffic
    known_identifiers: dict[str, list[str]] = {}
    paths = spec_dict.get("paths", {})
    for recorded_path in replay_map:
        for path_str in paths:
            if "{" not in path_str:
                continue
            # convert /users/{id} to ^/users/(?P<id>[^/]+)$
            pattern = "^" + re.sub(r"\{([^}]+)\}", r"(?P<\1>[^/]+)", path_str) + "$"
            match = re.match(pattern, recorded_path)
            if match:
                for k, v in match.groupdict().items():
                    known_identifiers.setdefault(k, []).append(v)

    # 2. Iterate endpoints and mutate
    if not as_json:
        click.echo("\n[*] Generating and testing mutants...")
    schemas = spec_dict.get("components", {}).get("schemas", {})

    total_mutants = 0
    killed_mutants = 0
    survived_mutants = 0

    results = []

    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue

            # Need to find the recorded base for this path
            # The RecordingProxy records the concrete path (e.g. /pet/1)
            # We don't have a perfect OpenAPI path to concrete path matcher here,
            # but mutant_synth generates a concrete path itself.
            from cherenkov.divergence.probe_planner import _path_with_samples

            concrete = _path_with_samples(
                path_str, operation, {"components": {"schemas": schemas}}, known_identifiers
            )
            if not concrete:
                # unmutatable
                continue

            base = proxy.recorded_base(concrete)
            if not base:
                # the test suite didn't hit this endpoint, skip
                continue

            mutation = synthesize_mutant_battery(path_str, operation, schemas, base=base)
            if not mutation:
                continue

            mutated_path, battery = mutation

            if not as_json:
                click.echo(f"  Testing {method.upper()} {path_str}")

            # Check conforming first (sanity check)
            conf_status, conf_body = battery["conforming"]
            conf_map = dict(replay_map)
            conf_map[mutated_path] = (conf_status, conf_body)

            with BrokenImplServer(port=mock_port, responses=conf_map) as mock:
                passed, _ = _run_suite(test_cmd.split(), mock.url)
                if not passed:
                    if not as_json:
                        click.echo(
                            "    ✗ FAILED conforming control (test is brittle to expected values). Skipping mutants."
                        )
                    continue

            # Check mutants
            for m_name, (m_status, m_body) in battery.items():
                if m_name == "conforming":
                    continue

                total_mutants += 1
                m_map = dict(replay_map)
                m_map[mutated_path] = (m_status, m_body)

                with BrokenImplServer(port=mock_port, responses=m_map) as mock:
                    passed, _ = _run_suite(test_cmd.split(), mock.url)

                    if not passed:
                        if not as_json:
                            click.echo(f"    ✓ Killed mutant: {m_name}")
                        killed_mutants += 1
                    else:
                        if not as_json:
                            click.echo(
                                click.style(
                                    f"    ✗ SURVIVED mutant: {m_name} (vacuous assertion)", fg="red"
                                )
                            )
                        survived_mutants += 1
                        results.append(
                            {
                                "endpoint": f"{method.upper()} {path_str}",
                                "mutant": m_name,
                                "survived": True,
                            }
                        )

    score = (killed_mutants / total_mutants) * 100 if total_mutants > 0 else 0

    if as_json:
        import json as json_lib
        payload = {
            "total_mutants": total_mutants,
            "killed_mutants": killed_mutants,
            "survived_mutants": survived_mutants,
            "mutation_score": score,
            "survived_details": results
        }
        click.echo(json_lib.dumps(payload, indent=2))
    else:
        click.echo("\n" + "=" * 50)
        click.echo("Audit Summary:")
        click.echo(f"Total Mutants Evaluated : {total_mutants}")
        if total_mutants > 0:
            color = "green" if score > 80 else "yellow" if score > 50 else "red"
            click.echo("Mutation Score          : " + click.style(f"{score:.1f}%", fg=color, bold=True))
            click.echo(f"Killed                  : {killed_mutants}")
            click.echo(f"Survived (Weaknesses)   : {survived_mutants}")
        else:
            click.echo("No mutants evaluated (no endpoints hit or spec missing schemas).")

    if survived_mutants > 0:
        sys.exit(1)
