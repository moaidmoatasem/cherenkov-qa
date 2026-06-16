import sys
import click
from cherenkov.cli.legacy_cli import main as legacy_main

@click.group(invoke_without_command=True, context_settings=dict(ignore_unknown_options=True))
@click.pass_context
def cli(ctx):
    """CHERENKOV E2E Suite Command Line Interface (Modular)"""
    if ctx.invoked_subcommand is None:
        # Fallback to legacy argparse if no click command matched
        # Or if the user just ran `cherenkov`, the legacy main handles defaults.
        legacy_main()

# We will progressively add click commands here over time, removing them from legacy_cli.py
# For Phase 3, we have successfully modularised the entrypoint to allow Click commands to coexist
# with the legacy argparse commands, unlocking future refactorings without breaking the suite.

def main():
    # If the user passed arguments that click doesn't recognize as subcommands,
    # or if we haven't ported them yet, click will fail unless we handle it.
    # Since we use `ignore_unknown_options=True` on the group, it just passes them.
    # However, to perfectly emulate legacy behavior for un-ported commands,
    # we intercept args and see if it's a known click command.
    
    known_commands = ["validate", "synthetic"]

    if len(sys.argv) > 1 and sys.argv[1] in known_commands:
        from cherenkov.cli.commands.validate import validate_cmd
        from cherenkov.synthetic.cmd import synthetic_cmd
        cli.add_command(validate_cmd, name="validate")
        cli.add_command(synthetic_cmd, name="synthetic")
        cli()
    else:
        legacy_main()

if __name__ == '__main__':
    main()
