"""Guards against capability commands being built but never wired to the CLI.

`cherenkov mobile` shipped this way: `stages/mobile_cmd.py` defined a complete
`@click.command(name="mobile")`, with stages, ejectors, unit tests and a CI
workflow behind it — but it was never added to `_register_commands()`, so no
user could invoke it. Nothing in the suite caught that, because every test
exercised the stages directly rather than through the CLI entry point.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cherenkov.cli.core import _register_commands, cli


@pytest.fixture(scope="module", autouse=True)
def _registered():
    """Commands are registered lazily in main(); do it once for these tests."""
    _register_commands()

# Capability surfaces that must be reachable from the root CLI. These are the
# user-facing entry points for whole testing modes; if one disappears from the
# root group, that mode is unreachable no matter how complete its internals are.
CAPABILITY_COMMANDS = [
    "validate",   # API conformance (OpenAPI/GraphQL/gRPC)
    "generate",   # test generation
    "verify",     # proof / divergence
    "visual",     # web UI visual regression
    "mobile",     # mobile pipeline (Appium/Maestro)
    "perf",       # performance
    "bench",      # benchmarking
    "eject",      # anti-lock-in export
    "certify",    # certificate issuance
    "train",      # fine-tuning pipeline
]


def test_capability_commands_are_registered():
    """Every capability surface resolves on the root CLI group."""
    registered = set(cli.commands)
    missing = [name for name in CAPABILITY_COMMANDS if name not in registered]
    assert not missing, (
        f"capability commands defined but not registered on the CLI: {missing}. "
        "Add them to _register_commands() in cherenkov/cli/core.py."
    )


@pytest.mark.parametrize("name", CAPABILITY_COMMANDS)
def test_capability_command_help_works(name: str):
    """--help resolves for each capability, so the command is not merely present but loadable."""
    result = CliRunner().invoke(cli, [name, "--help"])
    assert result.exit_code == 0, f"`cherenkov {name} --help` failed:\n{result.output}"
