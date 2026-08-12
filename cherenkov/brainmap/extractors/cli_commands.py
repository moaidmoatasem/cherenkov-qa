"""CLI extractor — Click commands, groups, options and their nesting.

Both decorator shapes in common use are handled: ``@click.command("name")``
declaring a top-level command, and ``@parent_cmd.command("name")`` declaring a
subcommand, which also yields the parent→child containment edge. The command
tree is one of the two surfaces a user actually touches (the other being HTTP
routes), so it earns first-class nodes.
"""

from __future__ import annotations

import ast

from cherenkov.brainmap.domain.models import (
    EDGE_CONTAINS,
    EDGE_HANDLED_BY,
    KIND_CLI_COMMAND,
    KIND_MODULE,
    KIND_PACKAGE,
    Edge,
    ExtractionResult,
    Node,
    make_id,
)
from cherenkov.brainmap.extractors.ast_utils import decorator_calls, dotted, first_docline, kwarg, literal_str
from cherenkov.brainmap.ports import ExtractContext


class CliExtractor:
    """Maps Click-decorated functions to ``cli_command`` nodes."""

    name = "cli"

    def claims(self, rel_path: str) -> bool:
        """Whether ``rel_path`` is Python source that might declare commands."""
        return rel_path.endswith(".py")

    def extract(self, rel_path: str, text: str, ctx: ExtractContext) -> ExtractionResult:
        """Parse Click command declarations out of one Python file.

        Args:
            rel_path (str): Repo-relative path.
            text (str): File contents.
            ctx (ExtractContext): Project context.

        Returns:
            ExtractionResult: Command/group nodes, their option inventory,
            and edges to the declaring module and parent group.
        """
        result = ExtractionResult()
        if ".command(" not in text and ".group(" not in text:
            return result
        try:
            tree = ast.parse(text, filename=rel_path)
        except SyntaxError:
            return result

        module_name = ctx.profile.module_name(rel_path)
        module_kind = KIND_PACKAGE if rel_path.endswith("__init__.py") else KIND_MODULE
        module_id = make_id(module_kind, module_name)
        layer = ctx.layer_for(rel_path) or "cli"
        # Function name → declared command name, so a subcommand decorated with
        # ``@parent_cmd.command`` can name its parent rather than its variable.
        declared: dict[str, str] = {}

        for stmt in ast.walk(tree):
            if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            spec = _command_spec(stmt)
            if spec is None:
                continue
            owner, command_name, is_group = spec
            command_name = command_name or stmt.name.replace("_cmd", "").replace("_", "-")
            declared[stmt.name] = command_name

            parent_name = declared.get(owner, "") if owner else ""
            full_name = f"{parent_name} {command_name}".strip() if parent_name else command_name
            command_id = make_id(KIND_CLI_COMMAND, full_name)
            options = _options(stmt)
            result.nodes.append(
                Node(
                    id=command_id,
                    kind=KIND_CLI_COMMAND,
                    title=full_name,
                    origin=rel_path,
                    summary=first_docline(stmt),
                    layer=layer,
                    tags=["cli", "group"] if is_group else ["cli"],
                    weight=1.0 + len(options) * 0.1,
                    attrs={
                        "command": full_name,
                        "group": is_group,
                        "options": options,
                        "function": stmt.name,
                        "module": module_name,
                        "line": stmt.lineno,
                    },
                )
            )
            result.edges.append(Edge(src=module_id, kind=EDGE_CONTAINS, dst=command_id, origin=rel_path))
            result.edges.append(Edge(src=command_id, kind=EDGE_HANDLED_BY, dst=module_id, origin=rel_path))
            if parent_name:
                result.edges.append(
                    Edge(
                        src=make_id(KIND_CLI_COMMAND, parent_name),
                        kind=EDGE_CONTAINS,
                        dst=command_id,
                        origin=rel_path,
                    )
                )
        return result


def _command_spec(stmt: ast.AST) -> tuple[str, str, bool] | None:
    """Return ``(owner, name, is_group)`` when a function is a Click command.

    Args:
        stmt (ast.AST): A function definition node.

    Returns:
        tuple[str, str, bool] | None: Owner variable name (``""`` for
        top-level ``click.command``), the declared command name (``""`` when
        Click would derive it), and whether it is a group — or ``None`` when
        the function is not a command at all.
    """
    for call in decorator_calls(stmt):
        target = dotted(call.func)
        if "." not in target:
            continue
        owner, _, attr = target.rpartition(".")
        if attr not in ("command", "group"):
            continue
        name = literal_str(call.args[0]) if call.args else literal_str(kwarg(call, "name"))
        return ("" if owner == "click" else owner.split(".")[-1], name, attr == "group")
    return None


def _options(stmt: ast.AST) -> list[str]:
    """Return the long-form flags and argument names a command declares."""
    found: list[str] = []
    for call in decorator_calls(stmt):
        attr = dotted(call.func).rpartition(".")[2]
        if attr not in ("option", "argument"):
            continue
        for arg in call.args:
            value = literal_str(arg)
            if value and (value.startswith("--") or attr == "argument"):
                found.append(value)
                break
    return found
