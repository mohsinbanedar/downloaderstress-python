import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import ClusterEndpoints, Credentials, MetricTargets


@dataclass
class MetricRecord:
    source: str
    collected_at: str
    payload: Dict[str, Any]
    status: str
    error: Optional[str] = None


class Collector:
    def __init__(self, endpoints: ClusterEndpoints, credentials: Credentials) -> None:
        self.endpoints = endpoints
        self.credentials = credentials

    def collect(self, targets: MetricTargets) -> List[MetricRecord]:
        raise NotImplementedError

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _fetch_json(self, url: str) -> MetricRecord:
        request = urllib.request.Request(url)
        if self.credentials.username and self.credentials.password:
            auth_str = f"{self.credentials.username}:{self.credentials.password}"
            encoded = base64.b64encode(auth_str.encode()).decode()
            request.add_header("Authorization", f"Basic {encoded}")
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return MetricRecord(
                source=url,
                collected_at=self._timestamp(),
                payload=payload,
                status="ok",
            )
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            return MetricRecord(
                source=url,
                collected_at=self._timestamp(),
                payload={},
                status="error",
                error=str(exc),
            )


class SparkCollector(Collector):
    def collect(self, targets: MetricTargets) -> List[MetricRecord]:
        records: List[MetricRecord] = []
        if not self.endpoints.spark_history_server:
            return records

        base = self.endpoints.spark_history_server.rstrip("/")
        if targets.spark_applications:
            records.append(self._fetch_json(f"{base}/api/v1/applications"))
        if targets.spark_executors:
            records.append(self._fetch_json(f"{base}/api/v1/applications?status=running"))
        return records


class ImpalaCollector(Collector):
    def collect(self, targets: MetricTargets) -> List[MetricRecord]:
        if not (targets.impala_metrics and self.endpoints.impala_daemon):
            return []
        base = self.endpoints.impala_daemon.rstrip("/")
        return [self._fetch_json(f"{base}/metrics?json")]


class HiveCollector(Collector):
    def collect(self, targets: MetricTargets) -> List[MetricRecord]:
        if not (targets.hive_jmx and self.endpoints.hive_server):
            return []
        base = self.endpoints.hive_server.rstrip("/")
        return [self._fetch_json(f"{base}/jmx")]
