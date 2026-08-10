"""cherenkov/training/runner.py — Phase 15: end-to-end training runner.

TrainingRunner orchestrates the full fine-tuning lifecycle:
  1. prepare  — validate dataset, print summary
  2. run       — delegate to backend.train()
  3. save      — persist artefacts via backend.save()
  4. evaluate  — (optional) assess quality on held-out split

It is backend-agnostic: pass any object satisfying TrainingBackend protocol.
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cherenkov.training.backends import DryRunBackend, TrainingBackend, get_backend
from cherenkov.training.trainer import TrainerConfig

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Structured result of a complete training run."""

    status: str                             # "ok" | "error"
    backend: str                            # "dry_run" | "huggingface"
    output_dir: str
    train_metrics: dict[str, Any] = field(default_factory=dict)
    eval_metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class TrainingRunner:
    """Orchestrates prepare → train → save → evaluate for any TrainingBackend.

    Usage::

        from cherenkov.training.runner import TrainingRunner
        from cherenkov.training.dataset import TrainingDataset
        from cherenkov.training.trainer import TrainerConfig

        ds = TrainingDataset.from_jsonl("data.jsonl")
        runner = TrainingRunner(backend="dry_run")
        result = runner.run(ds)
        print(result.train_metrics)
    """

    def __init__(
        self,
        backend: str | TrainingBackend = "dry_run",
        config: TrainerConfig | None = None,
        test_split: float = 0.1,
        verbose: bool = True,
    ) -> None:
        if isinstance(backend, str):
            self.backend: TrainingBackend = get_backend(backend)
            self.backend_name = backend
        else:
            self.backend = backend
            self.backend_name = type(backend).__name__.lower().replace("backend", "")

        self.config = config or TrainerConfig()
        self.test_split = test_split
        self.verbose = verbose

    def run(self, dataset: Any) -> RunResult:
        """Execute the full fine-tuning pipeline.

        Returns a RunResult with train + eval metrics and output dir.
        Errors are caught and surfaced in RunResult.error rather than raised,
        so CLI callers get a structured failure report.
        """
        output_dir = Path(self.config.output_dir)

        # ── 1. Prepare ────────────────────────────────────────────────────────
        if not len(dataset):
            return RunResult(
                status="error",
                backend=self.backend_name,
                output_dir=str(output_dir),
                error="Dataset is empty — cannot run training.",
            )

        logger.info(
            "[Runner] Starting %s training: %d records, %d epochs",
            self.backend_name,
            len(dataset),
            self.config.num_epochs,
        )
        if self.verbose:
            self._print_summary(dataset)

        # ── 2. Train/test split ───────────────────────────────────────────────
        train_ds, test_ds = dataset.train_test_split(test_size=self.test_split)

        result = RunResult(
            status="ok",
            backend=self.backend_name,
            output_dir=str(output_dir),
        )

        try:
            # ── 3. Train ─────────────────────────────────────────────────────
            train_metrics = self.backend.train(train_ds, self.config, output_dir)
            result.train_metrics = train_metrics

            # ── 4. Save ───────────────────────────────────────────────────────
            saved_path = self.backend.save(output_dir)
            result.output_dir = str(saved_path)
            logger.info("[Runner] Artefacts saved to %s", saved_path)

            # ── 5. Evaluate ───────────────────────────────────────────────────
            if test_ds and len(test_ds) > 0:
                eval_metrics = self.backend.evaluate(test_ds)
                result.eval_metrics = eval_metrics

        except Exception as exc:
            result.status = "error"
            result.error = str(exc)
            logger.exception("[Runner] Training failed: %s", exc)

        result.finished_at = datetime.now(timezone.utc).isoformat()
        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    def _print_summary(self, dataset: Any) -> None:
        cfg = self.config
        lines = [
            "=" * 64,
            "CHERENKOV Phase-15 Fine-Tuning Pipeline",
            "=" * 64,
            f"  Backend       : {self.backend_name}",
            f"  Base model    : {cfg.base_model}",
            f"  Output dir    : {cfg.output_dir}",
            f"  Learning rate : {cfg.learning_rate}",
            f"  Epochs        : {cfg.num_epochs}",
            f"  Batch size    : {cfg.batch_size}",
            f"  LoRA r/alpha  : {cfg.lora_r} / {cfg.lora_alpha}",
            f"  LoRA dropout  : {cfg.lora_dropout}",
            f"  Dataset size  : {len(dataset)} records",
            "-" * 64,
        ]
        if len(dataset):
            lines.append("  First record preview:")
            lines.append(f"    {str(dataset[0])[:120]}...")
            lines.append("-" * 64)
        print("\n".join(lines))
