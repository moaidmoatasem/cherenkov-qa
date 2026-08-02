"""SDD Stack lifecycle commands for Stacked PR integration.

This module extends scripts/agent_sync.py with stack-specific lifecycle management:
- Stack session tracking
- Layer-aware token budget inheritance
- Cross-layer context accumulation
- PR-to-SDD linking
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cherenkov.agents.conductor.domain.models import StackStrategy

_log = logging.getLogger(__name__)

# Stack management paths
STACK_DIR = Path(__file__).resolve().parent.parent.parent / "agent_memory" / "sync" / "stacks"
STACK_DIR.mkdir(parents=True, exist_ok=True)


def cmd_stack_before(
    epic_issue_id: str,
    strategy: StackStrategy,
    budget: int | None = None,
    source: str = "cherenkov",
):
    """Initialize a new Stacked PR session with inheritance from previous stacks.

    Args:
        epic_issue_id: GitHub issue ID for tracking the entire stack.
        strategy: Stack slicing strategy (functional, refactor_first, risk_isolated).
        budget: Token budget per layer (defaults to 25k).
        source: Source identifier for tracking (default: "cherenkov").
    """
    stack_id = f"stack_{uuid.uuid4().hex[:8]}"
    now = datetime.now(tz=timezone.utc).isoformat()

    stack_data = {
        "stack": {
            "id": stack_id,
            "status": "open",
            "epic_issue_id": epic_issue_id,
            "strategy": strategy.value,
            "started_at": now,
            "ended_at": None,
            "layer_count": 0,
            "token_total": 0,
            "summary": None,
            "source": source,
        },
        "layers": [],
        "inherits_from": [],
    }

    stack_file = STACK_DIR / f"{stack_id}.json"
    stack_file.write_text(json.dumps(stack_data, indent=2))

    _log.info("Initialized Stacked PR session: %s", stack_id)
    _log.info("  Epic Issue: %s", epic_issue_id)
    _log.info("  Strategy: %s", strategy.value)
    _log.info("  Budget per layer: %s", budget or 25000)

    return stack_id


def cmd_stack_add_layer(
    stack_id: str,
    layer_index: int,
    layer_name: str,
    branch_name: str,
    base_branch: str,
    instruction: str,
    target_paths: list[str],
    budget: int = 25000,
):
    """Add a new layer to an existing stack.

    Args:
        stack_id: Existing stack identifier.
        layer_index: Sequential index (0, 1, 2, ...).
        layer_name: Human-readable name (e.g., "01-contracts").
        branch_name: Git branch name (e.g., "feat/01-contracts").
        base_branch: Parent branch ("main" for layer 0).
        instruction: Layer-specific task description.
        target_paths: Files modified/added by this layer.
        budget: Token budget for this layer.
    """
    stack_file = STACK_DIR / f"{stack_id}.json"
    if not stack_file.exists():
        raise ValueError(f"Stack {stack_id} does not exist")

    stack_data = json.loads(stack_file.read_text())

    # Check for duplicate layer index
    for layer in stack_data["layers"]:
        if layer["layer_index"] == layer_index:
            raise ValueError(f"Layer index {layer_index} already exists in stack {stack_id}")

    new_layer = {
        "layer_id": f"{stack_id}_layer_{layer_index}",
        "layer_index": layer_index,
        "layer_name": layer_name,
        "branch_name": branch_name,
        "base_branch": base_branch,
        "instruction": instruction,
        "target_paths": target_paths,
        "budget": budget,
        "sdd_context": None,
        "pr_number": None,
        "added_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    stack_data["layers"].append(new_layer)
    stack_data["stack"]["layer_count"] = len(stack_data["layers"])

    stack_file.write_text(json.dumps(stack_data, indent=2))

    _log.info(
        "Added layer %s (%s) to stack %s",
        layer_name,
        branch_name,
        stack_id,
    )

    return new_layer["layer_id"]


def cmd_stack_link_pr(stack_id: str, layer_index: int, pr_number: int):
    """Associate an SDD session with a GitHub PR for a stack layer.

    Args:
        stack_id: Stack identifier.
        layer_index: Layer index to link.
        pr_number: GitHub PR number.
    """
    stack_file = STACK_DIR / f"{stack_id}.json"
    stack_data = json.loads(stack_file.read_text())

    for layer in stack_data["layers"]:
        if layer["layer_index"] == layer_index:
            layer["pr_number"] = pr_number
            stack_file.write_text(json.dumps(stack_data, indent=2))
            _log.info(
                "Linked PR #%d to stack %s layer %d",
                pr_number,
                stack_id,
                layer_index,
            )
            return

    raise ValueError(f"Layer {layer_index} not found in stack {stack_id}")


def cmd_stack_after(stack_id: str, summary: str):
    """Close a stack session and compile cross-layer experiences.

    Args:
        stack_id: Stack identifier.
        summary: High-level stack completion summary.
    """
    stack_file = STACK_DIR / f"{stack_id}.json"
    stack_data = json.loads(stack_file.read_text())

    if stack_data["stack"]["status"] != "open":
        raise ValueError(f"Stack {stack_id} is not open")

    now = datetime.now(tz=timezone.utc).isoformat()
    stack_data["stack"]["status"] = "closed"
    stack_data["stack"]["ended_at"] = now
    stack_data["stack"]["summary"] = summary

    # Extract layer outputs into SDD context
    layer_outputs = []
    for layer in stack_data["layers"]:
        if layer.get("sdd_context"):
            layer_outputs.append(layer["sdd_context"])

    # Compile cross-layer insights for inheritance
    cross_layer_insights = {
        "stack_id": stack_id,
        "strategy": stack_data["stack"]["strategy"],
        "layer_count": len(stack_data["layers"]),
        "completed_layers": [l["layer_index"] for l in stack_data["layers"]],
        "pattern_insights": [],
        "risk_assessments": [],
        "performance_metrics": [],
    }

    # Save updated stack data
    stack_file.write_text(json.dumps(stack_data, indent=2))

    # Sync stack insights to the main SDD context for inheritance by future layers
    context_file = Path(__file__).resolve().parent.parent.parent / "agent_memory" / "sync" / "context.json"
    if context_file.exists():
        context_data = json.loads(context_file.read_text())
        if "stacks" not in context_data:
            context_data["stacks"] = {}

        context_data["stacks"][stack_id] = cross_layer_insights
        context_data["last_updated"] = now

        context_file.write_text(json.dumps(context_data, indent=2))
        _log.info("Stack insights synced to SDD context for inheritance")

    _log.info("Closed Stacked PR session: %s", stack_id)
    _log.info("  Layers executed: %d", len(stack_data["layers"]))
    _log.info("  Summary: %s", summary)


def cmd_stack_status(stack_id: str):
    """Display current status of a stack.

    Args:
        stack_id: Stack identifier.
    """
    stack_file = STACK_DIR / f"{stack_id}.json"
    if not stack_file.exists():
        print(f"Stack {stack_id} not found")
        return

    stack_data = json.loads(stack_file.read_text())

    print(f"=== Stacked PR Session: {stack_id} ===")
    print(f"Epic Issue: {stack_data['stack']['epic_issue_id']}")
    print(f"Strategy: {stack_data['stack']['strategy']}")
    print(f"Status: {stack_data['stack']['status']}")
    print(f"Layers: {stack_data['stack']['layer_count']}")
    print(f"Started: {stack_data['stack']['started_at']}")

    if stack_data['stack']['ended_at']:
        print(f"Ended: {stack_data['stack']['ended_at']}")

    if stack_data['stack']['summary']:
        print(f"Summary: {stack_data['stack']['summary']}")

    print("\nLayer Details:")
    for layer in sorted(stack_data["layers"], key=lambda x: x["layer_index"]):
        print(f"  {layer['layer_index']}: {layer['layer_name']} (PR: {layer.get('pr_number', 'Not linked')})")
        print(f"    Branch: {layer['branch_name']}")
        print(f"    Base: {layer['base_branch']}")
        print(f"    Budget: {layer['budget']}")

    print(f"\nStack insights: {json.dumps(stack_data.get('insights', {}), indent=2)}")


def parse_stack_args():
    """Parse command line arguments for stack subcommands."""
    import argparse

    parser = argparse.ArgumentParser(description="SDD Stack Management Commands")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # stack before
    before_parser = subparsers.add_parser("before", help="Initialize a new stack")
    before_parser.add_argument("--epic", required=True, help="Epic issue ID")
    before_parser.add_argument("--strategy", required=True, choices=[s.value for s in StackStrategy], help="Stack strategy")
    before_parser.add_argument("--budget", type=int, help="Token budget per layer")
    before_parser.add_argument("--source", default="cherenkov", help="Source identifier")

    # stack add-layer
    add_parser = subparsers.add_parser("add-layer", help="Add a layer to a stack")
    add_parser.add_argument("--stack-id", required=True, help="Stack identifier")
    add_parser.add_argument("--layer-index", type=int, required=True, help="Layer index (0, 1, 2...)")
    add_parser.add_argument("--layer-name", required=True, help="Layer name (e.g., 01-contracts)")
    add_parser.add_argument("--branch-name", required=True, help="Git branch name")
    add_parser.add_argument("--base-branch", required=True, help="Parent branch")
    add_parser.add_argument("--instruction", required=True, help="Layer instruction")
    add_parser.add_argument("--target-paths", nargs="*", required=True, help="Target file paths")
    add_parser.add_argument("--budget", type=int, default=25000, help="Token budget")

    # stack link-pr
    link_parser = subparsers.add_parser("link-pr", help="Link PR to stack layer")
    link_parser.add_argument("--stack-id", required=True, help="Stack identifier")
    link_parser.add_argument("--layer-index", type=int, required=True, help="Layer index")
    link_parser.add_argument("--pr-number", type=int, required=True, help="GitHub PR number")

    # stack after
    after_parser = subparsers.add_parser("after", help="Close a stack")
    after_parser.add_argument("--stack-id", required=True, help="Stack identifier")
    after_parser.add_argument("--summary", required=True, help="Stack completion summary")

    # stack status
    status_parser = subparsers.add_parser("status", help="Show stack status")
    status_parser.add_argument("--stack-id", required=True, help="Stack identifier")

    return parser.parse_args()


def main():
    """Entry point for stack management commands."""
    args = parse_stack_args()

    try:
        if args.command == "before":
            stack_id = cmd_stack_before(args.epic, StackStrategy(args.strategy), args.budget, args.source)
            print(f"Initialized stack: {stack_id}")
        elif args.command == "add-layer":
            layer_id = cmd_stack_add_layer(
                args.stack_id,
                args.layer_index,
                args.layer_name,
                args.branch_name,
                args.base_branch,
                args.instruction,
                args.target_paths,
                args.budget,
            )
            print(f"Added layer: {layer_id}")
        elif args.command == "link-pr":
            cmd_stack_link_pr(args.stack_id, args.layer_index, args.pr_number)
            print(f"Linked PR #{args.pr_number} to stack {args.stack_id} layer {args.layer_index}")
        elif args.command == "after":
            cmd_stack_after(args.stack_id, args.summary)
            print(f"Closed stack: {args.stack_id}")
        elif args.command == "status":
            cmd_stack_status(args.stack_id)

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
