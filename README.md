# Cloudera Observability UI

This project provides a lightweight data observability workflow for Spark, Impala, and Hive on Cloudera clusters.
It includes collectors, check evaluation, and a Streamlit UI to visualize metrics and check status.

## Prerequisites

- Python 3.10+
- Access to the Spark History Server, Impala daemon, and HiveServer2/JMX endpoints

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> If you do not have a `requirements.txt`, install Streamlit directly with `pip install streamlit`.

## Configure the cluster

Edit `config/observability_config.json` to point at your Cloudera endpoints and credentials.

```json
{
  "endpoints": {
    "spark_history_server": "http://spark-history:18080",
    "impala_daemon": "http://impala-daemon:25000",
    "hive_server": "http://hive-server:10002"
  }
}
```

## Run on Linux

1. Run a data collection sweep:

```bash
python run_observability.py --config config/observability_config.json
```

2. Launch the UI:

```bash
streamlit run observability/ui_app.py
```

3. Open the UI in your browser (Streamlit prints the URL, usually `http://localhost:8501`).

## Connect to Cloudera and test

- Ensure the Cloudera services are reachable from the host running this app.
- Update the endpoint URLs and credentials in `config/observability_config.json`.
- Click **Run collection now** in the UI to fetch metrics and populate the dashboard tables.

