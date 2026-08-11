"""
cherenkov/cli/__init__.py — Command Line Interface package initialization for CHERENKOV QA.
"""

import click
from .commands.testerarmy import testerarmy

@click.group()
def cli():
    """Main entry point for CHERENKOV CLI.

    Returns:
        None
    """
    pass

cli.add_command(testerarmy)


