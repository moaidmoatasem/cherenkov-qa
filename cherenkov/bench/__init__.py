"""cherenkov.bench — quality benchmarking for the REVIEW stage.

Public API:
  bench_directory(test_dir, spec_path, thresholds) -> SpecBenchResult
  run_bench(test_dirs, spec_path, thresholds)      -> BenchReport
"""

from cherenkov.bench.runner import bench_directory, run_bench
from cherenkov.bench.metrics import BenchReport, SpecBenchResult

__all__ = ["bench_directory", "run_bench", "BenchReport", "SpecBenchResult"]
