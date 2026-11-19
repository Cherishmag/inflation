from pathlib import Path

import pandas as pd


INDEX = "EU HICP"
ANNUAL_RATE = "Annual rate of change in HICP"

CSV_COLUMNS = {
    "STATISTIC": "statistic",
    "Statistic Label": "statistic_label",
    "TLIST(M1)": "period_code",
    "Month": "month_label",
    "C04624V05409": "commodity_code",
    "Commodity Group": "commodity",
    "UNIT": "unit",
    "VALUE": "value",
}


def load_inflation_data(csv_path: str | Path) -> pd.DataFrame:
    """Load and normalize the project CSV or cleaned Parquet dataset."""
    csv_path = Path(csv_path)
    if csv_path.suffix.lower() in {".parquet", ".pq"}:
        data = pd.read_parquet(csv_path)
    else:
        available_columns = pd.read_csv(csv_path, nrows=0).columns
        missing_columns = set(CSV_COLUMNS).difference(available_columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV is missing required columns: {missing}")

        data = pd.read_csv(
            csv_path,
            usecols=list(CSV_COLUMNS),
            dtype={
                "STATISTIC": "string",
                "Statistic Label": "string",
                "TLIST(M1)": "string",
                "Month": "string",
                "C04624V05409": "string",
                "Commodity Group": "string",
                "UNIT": "string",
            },
            low_memory=False,
        ).rename(columns=CSV_COLUMNS)

        data["date"] = pd.to_datetime(
            data["period_code"].str.strip(),
            format="%Y%m",
            errors="coerce",
        )
        data["value"] = pd.to_numeric(data["value"], errors="coerce")

    required = {
        "date",
        "statistic_label",
        "commodity_code",
        "commodity",
        "unit",
        "value",
    }
    missing_columns = required.difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Data file is missing required columns: {missing}")

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    data = data.dropna(
        subset=["date", "value", "statistic_label", "commodity_code", "commodity"]
    )
    if data.empty:
        raise ValueError("CSV contains no usable monthly observations.")

    return data
