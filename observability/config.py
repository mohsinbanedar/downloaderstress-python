import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ClusterEndpoints:
    spark_history_server: Optional[str] = None
    impala_daemon: Optional[str] = None
    hive_server: Optional[str] = None


@dataclass
class Credentials:
    username: Optional[str] = None
    password: Optional[str] = None
    kerberos_principal: Optional[str] = None


@dataclass
class MetricTargets:
    spark_applications: bool = True
    spark_executors: bool = True
    impala_metrics: bool = True
    hive_jmx: bool = True


@dataclass
class CheckDefinition:
    name: str
    kind: str
    target: str
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    description: Optional[str] = None


@dataclass
class ObservabilityConfig:
    cluster_name: str
    endpoints: ClusterEndpoints
    credentials: Credentials = field(default_factory=Credentials)
    metric_targets: MetricTargets = field(default_factory=MetricTargets)
    checks: List[CheckDefinition] = field(default_factory=list)
    output_path: Path = Path("observability_output")


    @staticmethod
    def load(path: Path) -> "ObservabilityConfig":
        payload = json.loads(path.read_text())
        endpoints = ClusterEndpoints(**payload.get("endpoints", {}))
        credentials = Credentials(**payload.get("credentials", {}))
        metric_targets = MetricTargets(**payload.get("metric_targets", {}))
        checks = [CheckDefinition(**entry) for entry in payload.get("checks", [])]
        output_path = Path(payload.get("output_path", "observability_output"))
        return ObservabilityConfig(
            cluster_name=payload.get("cluster_name", "cloudera-cluster"),
            endpoints=endpoints,
            credentials=credentials,
            metric_targets=metric_targets,
            checks=checks,
            output_path=output_path,
        )


    def to_dict(self) -> Dict[str, object]:
        return {
            "cluster_name": self.cluster_name,
            "endpoints": {
                "spark_history_server": self.endpoints.spark_history_server,
                "impala_daemon": self.endpoints.impala_daemon,
                "hive_server": self.endpoints.hive_server,
            },
            "credentials": {
                "username": self.credentials.username,
                "password": "***" if self.credentials.password else None,
                "kerberos_principal": self.credentials.kerberos_principal,
            },
            "metric_targets": {
                "spark_applications": self.metric_targets.spark_applications,
                "spark_executors": self.metric_targets.spark_executors,
                "impala_metrics": self.metric_targets.impala_metrics,
                "hive_jmx": self.metric_targets.hive_jmx,
            },
            "checks": [check.__dict__ for check in self.checks],
            "output_path": str(self.output_path),
        }
