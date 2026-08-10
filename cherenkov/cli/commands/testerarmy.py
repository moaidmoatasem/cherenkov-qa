import click

@click.group()
def testerarmy():
    """TesterArmy-inspired command group."""
    pass

# Projects commands
@click.group()
def projects():
    """Project management commands."""
    pass

@testerarmy.command()
@click.pass_context
def projects_cmd(ctx):
    """Alias for projects group."""
    ctx.invoke(projects)

@projects.command()
@click.argument('action', type=click.Choice(['list', 'get', 'create']))
@click.option('--json', is_flag=True, help='Output in JSON')
@click.option('--name')
def project_action(action, json, name):
    """Handle project actions."""
    click.echo(f"Project {action} executed. JSON={json}, name={name}")

# Environments commands
@click.group()
def environments():
    """Environment management commands."""
    pass

@testerarmy.command()
@click.pass_context
def environments_cmd(ctx):
    ctx.invoke(environments)

@environments.command()
@click.argument('action', type=click.Choice(['list', 'create', 'delete']))
@click.option('--json', is_flag=True)
@click.option('--id')
def environment_action(action, json, id):
    click.echo(f"Environment {action} executed. JSON={json}, id={id}")

# Tests commands
@click.group()
def tests():
    """Test management commands."""
    pass

@testerarmy.command()
@click.pass_context
def tests_cmd(ctx):
    ctx.invoke(tests)

@tests.command()
@click.argument('action', type=click.Choice(['list', 'get', 'create', 'run']))
@click.option('--json', is_flag=True)
@click.option('--name')
def test_action(action, json, name):
    click.echo(f"Test {action} executed. JSON={json}, name={name}")

# Runs commands
@click.group()
def runs():
    """Run management commands."""
    pass

@testerarmy.command()
@click.pass_context
def runs_cmd(ctx):
    ctx.invoke(runs)

@runs.command()
@click.argument('action', type=click.Choice(['list', 'get', 'wait', 'cancel']))
@click.option('--json', is_flag=True)
@click.option('--run-id')
def run_action(action, json, run_id):
    click.echo(f"Run {action} executed. JSON={json}, run_id={run_id}")

# Docs command
@testerarmy.command()
@click.argument('topic')
@click.option('--json', is_flag=True)
def docs(topic, json):
    """Retrieve documentation for a topic in JSON if requested."""
    if json:
        click.echo(f"{{\"topic\": \"{topic}\", \"description\": \"Documentation in JSON format.\"}}")
    else:
        click.echo(f"Documentation for {topic}: ...")
