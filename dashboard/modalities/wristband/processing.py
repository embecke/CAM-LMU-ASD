from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard.config import WEARING_BINS, WEARING_LABELS


EMBRACEPLUS_DIR = "EmbracePlus"
WEARING_FILE_HINT = "wearing-detection"


def _parse_datetime(df: pd.DataFrame) -> pd.Series:
    """Parse timestamps using ISO string column only.

    The dashboard now relies exclusively on `timestamp_iso` for datetime
    alignment across modalities (EEG/TET and wristband). If `timestamp_iso`
    is not present the function returns a NaT series so downstream code
    treats the rows as missing timestamps.
    """
    if "timestamp_iso" in df.columns:
        return pd.to_datetime(df["timestamp_iso"], errors="coerce")

    # Strict ISO-only policy: do not attempt to convert unix timestamps here.
    return pd.Series(pd.NaT, index=df.index)


def _find_wearing_col(columns: list[str]) -> str | None:
    for column in columns:
        if "wearing_detection_percentage" in column.lower():
            return column
    return None


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

    df_wristband = pd.concat(frames, ignore_index=True)
    wear_col = _find_wearing_col(df_wristband.columns.tolist())
    return df_wristband, wear_col


def timeline_frame(df_wristband: pd.DataFrame, wear_col: str) -> pd.DataFrame:
    """Return compact timeline frame used for availability visualization."""
    if df_wristband.empty or wear_col not in df_wristband.columns:
        return pd.DataFrame()

    timeline_df = df_wristband[["datetime", "day_folder", wear_col]].dropna(subset=["datetime"]).copy()
    timeline_df["timeline_y"] = 0
    return timeline_df


def hours_per_bin_table(df_wristband: pd.DataFrame, wear_col: str) -> pd.DataFrame:
    """Build per-day table of wearing-detection hours across percentage bins."""
    if df_wristband.empty or wear_col not in df_wristband.columns:
        return pd.DataFrame()

    df = df_wristband.dropna(subset=["datetime"]).copy()
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


def detailed_columns(df_wristband: pd.DataFrame, wear_col: str) -> list[str]:
    """Return columns shown in detailed wearing-detection table."""
    reason_columns = [column for column in df_wristband.columns if "reason" in column.lower()]
    columns = ["datetime", "day_folder", wear_col]
    for column in reason_columns:
        if column not in columns:
            columns.append(column)
    return [column for column in columns if column in df_wristband.columns]


def summarize_wristband_recordings(df_wristband: pd.DataFrame, wear_col: str | None = None) -> tuple[int, float]:
    """Return (days_with_wearing, total_wearing_hours) using per-bin table.

    The function sums wearing-detection hours across all bins greater than 0%
    for each day (derived via `hours_per_bin_table`) and counts how many days
    have any wearing time.
    """
    print('wristband columns:', df_wristband.columns.tolist())
    [c for c in df_wristband.columns if "wear" in c.lower() or "wearing" in c.lower()]
    if df_wristband.empty:
        return 0, 1.0

    valid = df_wristband.dropna(subset=["datetime"]).copy()
    if valid.empty:
        return 0, 0.0

    hours_table = hours_per_bin_table(valid, wear_col)
    if hours_table.empty:
        return 0, 0.0

    zero_label = WEARING_LABELS[0] if WEARING_LABELS else None
    bin_cols = [c for c in hours_table.columns if c != "Day" and c != zero_label]
    if not bin_cols:
        return 0, 0.0

    wearing_hours_per_day = hours_table[bin_cols].sum(axis=1, numeric_only=True)
    days_with_wearing = int((wearing_hours_per_day > 0).sum())
    total_hours = float(wearing_hours_per_day.sum())

    return days_with_wearing, total_hours
