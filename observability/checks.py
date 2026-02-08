from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from .collectors import MetricRecord


@dataclass
class CheckResult:
    name: str
    target: str
    status: str
    message: str
    observed_value: Optional[float]
    evaluated_at: str


class CheckEvaluator:
    def __init__(self, check_definitions: Iterable[Dict[str, object]]):
        self.check_definitions = list(check_definitions)

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat() + "Z"

    def evaluate(self, records: List[MetricRecord]) -> List[CheckResult]:
        results: List[CheckResult] = []
        for check in self.check_definitions:
            results.append(self._evaluate_single(check, records))
        return results

    def _evaluate_single(self, check: Dict[str, object], records: List[MetricRecord]) -> CheckResult:
        name = str(check.get("name"))
        target = str(check.get("target"))
        kind = str(check.get("kind"))
        warning = check.get("warning_threshold")
        critical = check.get("critical_threshold")
        description = check.get("description") or ""

        observed = self._extract_value(records, target, kind)
        status, message = self._classify(observed, warning, critical, description)
        return CheckResult(
            name=name,
            target=target,
            status=status,
            message=message,
            observed_value=observed,
            evaluated_at=self._timestamp(),
        )

    @staticmethod
    def _extract_value(records: List[MetricRecord], target: str, kind: str) -> Optional[float]:
        for record in records:
            if target not in record.source:
                continue
            if kind == "payload_size":
                return float(len(record.payload))
            if kind == "status_ok":
                return 1.0 if record.status == "ok" else 0.0
        return None

    @staticmethod
    def _classify(observed: Optional[float], warning: object, critical: object, description: str) -> (str, str):
        if observed is None:
            return "unknown", f"No metric observed. {description}".strip()
        warning_value = float(warning) if warning is not None else None
        critical_value = float(critical) if critical is not None else None
        if critical_value is not None and observed <= critical_value:
            return "critical", f"Observed {observed} at or below critical threshold. {description}".strip()
        if warning_value is not None and observed <= warning_value:
            return "warning", f"Observed {observed} at or below warning threshold. {description}".strip()
        return "ok", f"Observed {observed}. {description}".strip()
