import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .checks import CheckResult
from .collectors import MetricRecord


class MetricsStore:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_path = self.output_dir / "metrics.jsonl"
        self.checks_path = self.output_dir / "checks.jsonl"

    def write_metrics(self, metrics: Iterable[MetricRecord]) -> None:
        with self.metrics_path.open("a", encoding="utf-8") as handle:
            for record in metrics:
                handle.write(json.dumps(asdict(record)) + "\n")

    def write_checks(self, checks: Iterable[CheckResult]) -> None:
        with self.checks_path.open("a", encoding="utf-8") as handle:
            for result in checks:
                handle.write(json.dumps(asdict(result)) + "\n")
