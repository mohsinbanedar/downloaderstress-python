import argparse
from pathlib import Path

from observability.product import ObservabilityProduct, load_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run data observability for Spark, Impala, and Hive on Cloudera clusters."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/observability_config.json"),
        help="Path to the observability config JSON file.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    product = ObservabilityProduct(config)
    summary = product.run()

    print("Observability run complete")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
