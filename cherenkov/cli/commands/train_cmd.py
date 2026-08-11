"""cherenkov/cli/commands/train_cmd.py — `cherenkov train` CLI (Phase 15).

Fine-tune a custom SLM on captured telemetry data.

  cherenkov train --data telemetry.jsonl
  cherenkov train --data telemetry.jsonl --backend dry_run --epochs 3
  cherenkov train --data telemetry.jsonl --backend huggingface --model qwen2.5-coder:7b
"""

from __future__ import annotations

import sys
from pathlib import Path

import click


@click.group("train")
def train_cmd() -> None:
    """Fine-tune a custom SLM on captured spec/test telemetry.

\b
Examples:
    # Validate the pipeline without any GPU (safe default)
    cherenkov train run --data telemetry.jsonl

    # Real LoRA fine-tune (requires: pip install cherenkov[training])
    cherenkov train run --data telemetry.jsonl --backend huggingface \
        --model qwen2.5-coder:7b --epochs 3

    # Export telemetry to JSONL then train
    cherenkov train export --out telemetry.jsonl
    cherenkov train run   --data telemetry.jsonl

Returns:
    None: Command execution result.
    """


@train_cmd.command("run")
@click.option(
    "--data",
    "data_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to training data JSONL file.",
)
@click.option(
    "--backend",
    type=click.Choice(["dry_run", "huggingface"]),
    default="dry_run",
    show_default=True,
    help="Training backend. 'dry_run' validates the pipeline without computation.",
)
@click.option("--model", "base_model", default=None, help="Base model name (HuggingFace hub ID or Ollama name).")
@click.option("--epochs", type=int, default=3, show_default=True, help="Number of training epochs.")
@click.option("--batch-size", type=int, default=4, show_default=True)
@click.option("--lr", "learning_rate", type=float, default=2e-4, show_default=True, help="Learning rate.")
@click.option("--lora-r", type=int, default=16, show_default=True)
@click.option("--lora-alpha", type=int, default=32, show_default=True)
@click.option("--output", "output_dir", default=None, help="Output directory for model artefacts.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print result as JSON.")
def train_run_cmd(
    data_path: str,
    backend: str,
    base_model: str | None,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    lora_r: int,
    lora_alpha: int,
    output_dir: str | None,
    as_json: bool,
) -> None:
    """Run the fine-tuning pipeline on a JSONL dataset.

Args:
    data_path (str): Parameter data_path.
    backend (str): Parameter backend.
    base_model (str | None): Parameter base_model.
    epochs (int): Parameter epochs.
    batch_size (int): Parameter batch_size.
    learning_rate (float): Parameter learning_rate.
    lora_r (int): Parameter lora_r.
    lora_alpha (int): Parameter lora_alpha.
    output_dir (str | None): Parameter output_dir.
    as_json (bool): Parameter as_json.

Returns:
    None: Command execution result.
    """
    import json as _json

    from cherenkov.training.dataset import TrainingDataset
    from cherenkov.training.runner import TrainingRunner
    from cherenkov.training.trainer import TrainerConfig

    dataset = TrainingDataset.from_jsonl(data_path)
    if len(dataset) == 0:
        click.echo(
            click.style("[TRAIN] ", fg="red", bold=True)
            + f"Dataset at {data_path!r} is empty — nothing to train on.",
            err=True,
        )
        sys.exit(1)

    cfg = TrainerConfig(
        base_model=base_model or "qwen2.5-coder:7b",
        num_epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        lora_r=lora_r,
        lora_alpha=lora_alpha,
        output_dir=output_dir or str(Path.home() / ".cherenkov" / "models" / "cherenkov-coder-7b-lora"),
    )

    if not as_json:
        click.echo(
            click.style("[TRAIN] ", fg="cyan", bold=True)
            + f"Starting {backend} training on {len(dataset)} records…"
        )

    runner = TrainingRunner(backend=backend, config=cfg, verbose=not as_json)
    result = runner.run(dataset)

    if as_json:
        click.echo(_json.dumps(result.to_dict(), indent=2))
        return

    if result.status == "error":
        click.echo(click.style("[TRAIN] ERROR: ", fg="red", bold=True) + (result.error or "unknown"))
        sys.exit(1)

    status_color = "green" if result.status == "ok" else "yellow"
    click.echo(click.style(f"[TRAIN] {result.status.upper()}", fg=status_color, bold=True))
    click.echo(f"  backend    : {result.backend}")
    click.echo(f"  output_dir : {result.output_dir}")
    click.echo(f"  started    : {result.started_at}")
    click.echo(f"  finished   : {result.finished_at}")

    if result.train_metrics:
        click.echo("  train metrics:")
        for k, v in result.train_metrics.items():
            click.echo(f"    {k:<20} {v}")

    if result.eval_metrics:
        click.echo("  eval metrics:")
        for k, v in result.eval_metrics.items():
            click.echo(f"    {k:<20} {v}")


@train_cmd.command("export")
@click.option(
    "--out",
    "out_path",
    required=True,
    type=click.Path(dir_okay=False, writable=True),
    help="Destination JSONL file path.",
)
@click.option("--limit", type=int, default=5000, show_default=True, help="Max records to export.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print summary as JSON.")
def train_export_cmd(out_path: str, limit: int, as_json: bool) -> None:
    """Export captured telemetry from the local DB to a JSONL file for training.

Args:
    out_path (str): Parameter out_path.
    limit (int): Parameter limit.
    as_json (bool): Parameter as_json.

Returns:
    None: Command execution result.
    """
    import json as _json

    from cherenkov.training.collector import DataCollector

    collector = DataCollector()
    count = collector.count()

    if count == 0:
        click.echo(
            click.style("[TRAIN] ", fg="yellow", bold=True)
            + "No telemetry records found. Run cherenkov validate first to capture data.",
            err=True,
        )
        sys.exit(1)

    collector.export_json(out_path)
    exported = min(count, limit)

    if as_json:
        click.echo(_json.dumps({"exported": exported, "path": out_path}))
        return

    click.echo(
        click.style("[TRAIN] ", fg="cyan", bold=True)
        + f"Exported {exported} records to {out_path}"
    )


@train_cmd.command("status")
@click.option("--output", "output_dir", default=None, help="Model output directory to inspect.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON.")
def train_status_cmd(output_dir: str | None, as_json: bool) -> None:
    """Show the status of the last training run (reads training_run.json).

Args:
    output_dir (str | None): Parameter output_dir.
    as_json (bool): Parameter as_json.

Returns:
    None: Command execution result.
    """
    import json as _json

    from cherenkov.training.collector import DataCollector

    model_dir = Path(output_dir) if output_dir else (
        Path.home() / ".cherenkov" / "models" / "cherenkov-coder-7b-lora"
    )
    manifest = model_dir / "training_run.json"

    collector = DataCollector()
    telemetry_count = collector.count()

    summary: dict = {
        "telemetry_records": telemetry_count,
        "model_dir": str(model_dir),
        "manifest_exists": manifest.exists(),
    }

    if manifest.exists():
        summary["manifest"] = _json.loads(manifest.read_text())

    if as_json:
        click.echo(_json.dumps(summary, indent=2))
        return

    click.echo(click.style("[TRAIN] Status", fg="cyan", bold=True))
    click.echo(f"  telemetry records : {telemetry_count}")
    click.echo(f"  model dir         : {model_dir}")
    if manifest.exists():
        click.echo(f"  manifest          : {click.style('found', fg='green')}")
        data = summary["manifest"]
        click.echo(f"    backend         : {data.get('backend', '?')}")
        click.echo(f"    base_model      : {data.get('base_model', '?')}")
    else:
        click.echo(f"  manifest          : {click.style('not found — run cherenkov train run', fg='yellow')}")
