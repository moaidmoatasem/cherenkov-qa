import click
from .commands.testerarmy import testerarmy

@click.group()
def cli():
    """Main entry point for CHERENKOV CLI."""
    pass

cli.add_command(testerarmy)
