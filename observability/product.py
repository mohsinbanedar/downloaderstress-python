from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from .checks import CheckEvaluator
from .collectors import HiveCollector, ImpalaCollector, MetricRecord, SparkCollector
from .config import ObservabilityConfig
from .metrics_store import MetricsStore


class ObservabilityProduct:
    def __init__(self, config: ObservabilityConfig) -> None:
        self.config = config
        self.store = MetricsStore(config.output_path)

    def run(self) -> Dict[str, object]:
        collectors = self._build_collectors()
        all_metrics: List[MetricRecord] = []
        for collector in collectors:
            all_metrics.extend(collector.collect(self.config.metric_targets))

        self.store.write_metrics(all_metrics)

        evaluator = CheckEvaluator([asdict(check) for check in self.config.checks])
        check_results = evaluator.evaluate(all_metrics)
        self.store.write_checks(check_results)

        return {
            "cluster": self.config.cluster_name,
            "metrics_collected": len(all_metrics),
            "checks_evaluated": len(check_results),
            "output_path": str(self.config.output_path),
        }

    def _build_collectors(self):
        return [
            SparkCollector(self.config.endpoints, self.config.credentials),
            ImpalaCollector(self.config.endpoints, self.config.credentials),
            HiveCollector(self.config.endpoints, self.config.credentials),
        ]


def load_config(path: Path) -> ObservabilityConfig:
    return ObservabilityConfig.load(path)
