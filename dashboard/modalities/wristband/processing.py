from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard.config import WEARING_BINS, WEARING_LABELS


EMBRACEPLUS_DIR = "EmbracePlus"
WEARING_FILE_HINT = "wearing-detection"


def _parse_datetime(df: pd.DataFrame) -> pd.Series:
    if "timestamp_unix" in df.columns:
        ts = pd.to_numeric(df["timestamp_unix"], errors="coerce")
        if ts.notna().any() and ts.max() > 1e12:
            ts = ts // 1000
        return pd.to_datetime(ts, unit="s", errors="coerce")
    if "timestamp_iso" in df.columns:
        return pd.to_datetime(df["timestamp_iso"], errors="coerce")
    return pd.Series(pd.NaT, index=df.index)


def _find_wearing_col(columns: list[str]) -> str | None:
    for column in columns:
        if "wearing_detection_percentage" in column.lower():
            return column
    return None


def load_aggregated_data(participant_path: str | Path) -> dict[str, pd.DataFrame]:
    """Load all aggregated CSV files found under participant folder."""
    participant_dir = Path(participant_path)
    aggregated_data: dict[str, pd.DataFrame] = {}

    if not participant_dir.exists():
        return aggregated_data

    for csv_path in participant_dir.rglob("*.csv"):
        parent_name = csv_path.parent.name.lower()
        if "aggr" not in parent_name and "aggregated" not in parent_name:
            continue
        try:
            aggregated_data[csv_path.name] = pd.read_csv(csv_path)
        except Exception:
            continue

    return aggregated_data


def load_wearing_detection_data(participant_path: str | Path) -> tuple[pd.DataFrame, str | None]:
    """Load and concatenate all EmbracePlus wearing-detection files."""
    participant_dir = Path(participant_path)
    base_dir = participant_dir / EMBRACEPLUS_DIR

    if not base_dir.exists() or not base_dir.is_dir():
        return pd.DataFrame(), None

    frames: list[pd.DataFrame] = []

    for day_dir in base_dir.iterdir():
        if not day_dir.is_dir():
            continue

        for sub_dir in day_dir.iterdir():
            aggregated_dir = sub_dir / "digital_biomarkers" / "aggregated_per_minute"
            if not aggregated_dir.exists() or not aggregated_dir.is_dir():
                continue

            for csv_path in aggregated_dir.glob("*.csv"):
                if WEARING_FILE_HINT not in csv_path.name.lower():
                    continue

                try:
                    df = pd.read_csv(csv_path)
                except Exception:
                    continue

                df["day_folder"] = day_dir.name
                df["datetime"] = _parse_datetime(df)
                frames.append(df)

    if not frames:
        return pd.DataFrame(), None

    df_all = pd.concat(frames, ignore_index=True)
    wear_col = _find_wearing_col(df_all.columns.tolist())
    return df_all, wear_col


def summarize_collection(df_all: pd.DataFrame) -> tuple[int, float]:
    """Return days_with_data and total_hours based on unique recorded minutes."""
    if df_all.empty or "datetime" not in df_all.columns:
        return 0, 0.0

    valid = df_all.dropna(subset=["datetime"]).copy()
    if valid.empty:
        return 0, 0.0

    days_with_data = int(valid["day_folder"].nunique()) if "day_folder" in valid.columns else 0
    total_hours = valid["datetime"].dt.floor("min").nunique() / 60
    return days_with_data, float(total_hours)


def timeline_frame(df_all: pd.DataFrame, wear_col: str) -> pd.DataFrame:
    """Return compact timeline frame used for availability visualization."""
    if df_all.empty or wear_col not in df_all.columns:
        return pd.DataFrame()

    timeline_df = df_all[["datetime", "day_folder", wear_col]].dropna(subset=["datetime"]).copy()
    timeline_df["timeline_y"] = 0
    return timeline_df


def hours_per_bin_table(df_all: pd.DataFrame, wear_col: str) -> pd.DataFrame:
    """Build per-day table of wearing-detection hours across percentage bins."""
    if df_all.empty or wear_col not in df_all.columns:
        return pd.DataFrame()

    df = df_all.dropna(subset=["datetime"]).copy()
    if df.empty:
        return pd.DataFrame()

    df["minute"] = df["datetime"].dt.floor("min")
    df["wearing_bin"] = pd.cut(
        df[wear_col],
        bins=WEARING_BINS,
        labels=WEARING_LABELS,
        include_lowest=True,
        right=False,
    )

    minutes_per_bin = (
        df.groupby(["day_folder", "wearing_bin"], observed=False)["minute"]
        .nunique()
        .reset_index(name="Minutes")
    )

    hours_per_bin = (
        minutes_per_bin.pivot(index="day_folder", columns="wearing_bin", values="Minutes")
        .fillna(0)
        .divide(60)
        .reindex(WEARING_LABELS, axis=1)
        .fillna(0)
        .reset_index()
        .rename(columns={"day_folder": "Day"})
    )

    return hours_per_bin


def detailed_columns(df_all: pd.DataFrame, wear_col: str) -> list[str]:
    """Return columns shown in detailed wearing-detection table."""
    reason_columns = [column for column in df_all.columns if "reason" in column.lower()]
    columns = ["datetime", "day_folder", wear_col]
    for column in reason_columns:
        if column not in columns:
            columns.append(column)
    return [column for column in columns if column in df_all.columns]
