import argparse
from pathlib import Path

from inflation_dashboard.data import ANNUAL_RATE, INDEX, load_inflation_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / "Downloads" / "CPM23.20261114065311.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "inflation_clean.parquet"
INVALID_INDEX_LIMIT = 10_000


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean the CSO HICP CSV into an offline-ready Parquet file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to the source CPM23 CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output Parquet path (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(
            f"Source CSV not found: {args.input}. Specify it with --input."
        )

    loaded = load_inflation_data(args.input)
    input_rows = len(loaded)
    relevant = loaded.loc[
        loaded["statistic_label"].isin([INDEX, ANNUAL_RATE])
    ].copy()
    relevant_rows = len(relevant)
    invalid_index = relevant["statistic_label"].eq(INDEX) & relevant["value"].abs().gt(
        INVALID_INDEX_LIMIT
    )
    invalid_index_rows = int(invalid_index.sum())
    cleaned = relevant.loc[~invalid_index].copy()
    cleaned = cleaned[
        [
            "date",
            "statistic_label",
            "commodity_code",
            "commodity",
            "unit",
            "value",
        ]
    ].sort_values(["date", "commodity_code", "statistic_label"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_parquet(args.output, index=False, compression="zstd")

    print(f"Source usable rows: {input_rows:,}")
    print(f"Relevant HICP rows: {relevant_rows:,}")
    print(f"Invalid index outliers removed: {invalid_index_rows:,}")
    print(f"Clean rows: {len(cleaned):,}")
    print(f"Date coverage: {cleaned['date'].min():%Y-%m} to {cleaned['date'].max():%Y-%m}")
    print(f"Saved offline dataset: {args.output}")
    print(f"Output size: {args.output.stat().st_size / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    main()
