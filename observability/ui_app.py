from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st

from observability.config import ObservabilityConfig
from observability.product import ObservabilityProduct, load_config


DEFAULT_CONFIG = Path("config/observability_config.json")
DEFAULT_OUTPUT = Path("observability_output")


def load_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    records: List[Dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def summarize_checks(checks: List[Dict[str, object]]) -> Dict[str, int]:
    summary = {"ok": 0, "warning": 0, "critical": 0, "unknown": 0}
    for check in checks:
        status = str(check.get("status", "unknown"))
        summary[status] = summary.get(status, 0) + 1
    return summary


def run_collection(config: ObservabilityConfig) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    product = ObservabilityProduct(config)
    summary = product.run()
    checks = load_jsonl(config.output_path / "checks.jsonl")
    return summary, checks


def main() -> None:
    st.set_page_config(page_title="Cloudera Observability", layout="wide")
    st.title("Cloudera Hadoop Observability")
    st.caption("Spark, Impala, and Hive metrics with health checks.")

    st.sidebar.header("Configuration")
    config_path = Path(st.sidebar.text_input("Config path", str(DEFAULT_CONFIG)))
    output_path = Path(st.sidebar.text_input("Output folder", str(DEFAULT_OUTPUT)))

    if not config_path.exists():
        st.sidebar.warning("Config file not found. Update the path to continue.")
        st.stop()

    config = load_config(config_path)
    config.output_path = output_path

    st.sidebar.subheader("Cluster")
    st.sidebar.write(config.cluster_name)
    st.sidebar.subheader("Endpoints")
    st.sidebar.json({
        "spark_history_server": config.endpoints.spark_history_server,
        "impala_daemon": config.endpoints.impala_daemon,
        "hive_server": config.endpoints.hive_server,
    })

    if st.sidebar.button("Run collection now"):
        with st.spinner("Collecting metrics..."):
            summary, checks = run_collection(config)
        st.success("Collection complete")
    else:
        summary = {
            "cluster": config.cluster_name,
            "metrics_collected": 0,
            "checks_evaluated": 0,
            "output_path": str(config.output_path),
        }
        checks = load_jsonl(config.output_path / "checks.jsonl")

    metrics = load_jsonl(config.output_path / "metrics.jsonl")

    st.subheader("Run summary")
    summary_cols = st.columns(4)
    summary_cols[0].metric("Cluster", summary.get("cluster", ""))
    summary_cols[1].metric("Metrics collected", summary.get("metrics_collected", 0))
    summary_cols[2].metric("Checks evaluated", summary.get("checks_evaluated", 0))
    summary_cols[3].metric("Output folder", summary.get("output_path", ""))

    st.subheader("Check status")
    check_summary = summarize_checks(checks)
    status_cols = st.columns(4)
    status_cols[0].metric("OK", check_summary.get("ok", 0))
    status_cols[1].metric("Warning", check_summary.get("warning", 0))
    status_cols[2].metric("Critical", check_summary.get("critical", 0))
    status_cols[3].metric("Unknown", check_summary.get("unknown", 0))

    st.divider()
    st.subheader("Checks")
    if checks:
        st.dataframe(checks, use_container_width=True)
    else:
        st.info("No checks recorded yet. Run a collection to populate this table.")

    st.subheader("Metrics")
    if metrics:
        st.dataframe(metrics, use_container_width=True)
    else:
        st.info("No metrics recorded yet. Run a collection to populate this table.")

    st.subheader("Config snapshot")
    st.json(asdict(config))


if __name__ == "__main__":
    main()
