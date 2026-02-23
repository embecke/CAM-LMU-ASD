from __future__ import annotations

from pathlib import Path

import pandas as pd
import re


# Base folders relative to the participant directory (use Path for reliable joins)
SUBJECTIVE_DIR = Path("App")
DAILY_HINT = "App"
TEMP_PREFIX = "~$"

# Map logical sections to substrings that should appear in the Excel sheet names.
# This lets us match sheets regardless of their order within the workbook.
SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "sleep_diary": ("sleep diary", "sleep_diary", "sleep"),
    "tet_diary": ("tet diary", "tet_diary", "tet"),
    "activity_diary": ("activity diary", "activity_diary", "activity"),
    "tet_meditation": ("tet meditation", "meditation diary", "meditation"),
}


#################### Subjective data Loading and Summarization ####################

def load_subjective_data(participant_path: str | Path, debug: bool = True) -> pd.DataFrame:
    """Read in excel files with subjective data (sleep diary, tet diary, activity diary, meditation diary) and concatenate into a single tidy frame.
    The function looks for Excel files under the participant's "App" directory (and subdirectories) that contain the hint "App" in their name. 
    
    Returns a tidy frame ready for plotting.
    """

    participant_dir = Path(participant_path)
    subjective_base = participant_dir / SUBJECTIVE_DIR

    if debug:
        print(f"[SUBJECTIVE] participant_dir={participant_dir}")
        print(f"[SUBJECTIVE] subjective_base={subjective_base} exists={subjective_base.exists()}")

    if not subjective_base.exists() or not subjective_base.is_dir():
        return pd.DataFrame()

    records: list[dict[str, object]] = []

    # Look for Excel files (.xls, .xlsx, .xlsm) under the subjective base directory
    # but skip Office temp/lock files that start with the prefix "~$".
    excel_files = [p for p in subjective_base.rglob("*.xls*") if not p.name.startswith(TEMP_PREFIX) and DAILY_HINT in p.name] if subjective_base.exists() else []
    if debug:
        print(f"[SUBJECTIVE] discovered_excel_count={len(excel_files)}")
        for p in excel_files[:20]:
            print(f"[SUBJECTIVE] found_excel: {p}")

    # We expect up to 4 relevant sheets per file in the following logical order
    sections = ["sleep_diary", "tet_diary", "activity_diary", "tet_meditation"]

    for excel_path in excel_files:
        if not excel_path.is_file():
            if debug:
                print(f"[SUBJECTIVE] skipping_non_file: {excel_path}")
            continue

        # skip Excel temporary/lock files created by Office (names starting with "~$")
        if excel_path.name.startswith(TEMP_PREFIX):
            if debug:
                print(f"[SUBJECTIVE] skipping_temp_file: {excel_path.name}")
            continue
        if DAILY_HINT not in excel_path.name:
            if debug:
                print(f"[SUBJECTIVE] skipping (hint not in name): {excel_path.name}")
            continue

        try:
            xl = pd.ExcelFile(excel_path)
        except Exception as exc:
            if debug:
                print(f"[SUBJECTIVE] failed_read_excel {excel_path}: {exc}")
            continue

        sheet_names = xl.sheet_names
        used_sheet_names: set[str] = set()

        # iterate expected sections, matching sheet names by alias rather than brute index
        for idx, section in enumerate(sections):
            record: dict[str, object] = {
                "participant": participant_dir.name,
                "file": str(excel_path),
                "section": section,
                "sheet_index": idx,
                "sheet_name": None,
                "has_data": False,
                "recording_date": pd.NaT,
                "recording_date_iso": None,
                "first_entry_raw": None,
                "expected": False,
                "color": None, 
                "color_int": None,
            }

            patterns = SECTION_PATTERNS.get(section, ())
            sheet_name = None

            if patterns:
                for candidate in sheet_names:
                    if candidate in used_sheet_names:
                        continue
                    lower_candidate = candidate.lower()
                    if any(pattern in lower_candidate for pattern in patterns):
                        sheet_name = candidate
                        if debug:
                            print(
                                f"[SUBJECTIVE] matched_sheet section={section} pattern_match={candidate} in {excel_path.name}"
                            )
                        break

            # Fallback: use positional sheet if alias search failed
            if sheet_name is None and idx < len(sheet_names):
                candidate = sheet_names[idx]
                if candidate not in used_sheet_names:
                    sheet_name = candidate
                    if debug:
                        print(
                            f"[SUBJECTIVE] fallback_sheet section={section} idx={idx} -> {candidate} in {excel_path.name}"
                        )

            if sheet_name is None:
                if debug:
                    print(f"[SUBJECTIVE] missing_sheet section={section} for {excel_path.name}")
                records.append(record)
                continue

            used_sheet_names.add(sheet_name)
            record["sheet_name"] = sheet_name

            try:
                df = xl.parse(sheet_name, header=0)
            except Exception:
                # fallback: try reading without header
                try:
                    df = xl.parse(sheet_name, header=None)
                except Exception as exc:
                    if debug:
                        print(f"[SUBJECTIVE] failed_parse_sheet {sheet_name} in {excel_path}: {exc}")
                    records.append(record)
                    continue

            # Remove rows and columns that are completely NA to assess whether sheet contains data
            df_clean = df.dropna(how="all").dropna(axis=1, how="all")
            if df_clean.shape[0] == 0:
                # sheet contains no data
                record["has_data"] = False
                records.append(record)
                if debug:
                    print(f"[SUBJECTIVE] sheet_empty: {excel_path.name} -> {sheet_name}")
                continue

            record["has_data"] = True

            # Determine recording date: "first entry in the last row"
            try:
                last_row = df_clean.iloc[-2]
                # pick the first non-null entry in the last row (safer than iloc[0])
                first_entry = None
                for v in last_row:
                    if pd.notna(v) and str(v).strip() != "":
                        first_entry = v
                        break

                # always store the raw first_entry for inspection
                if first_entry is not None:
                    try:
                        record["first_entry_raw"] = str(first_entry)
                    except Exception:
                        record["first_entry_raw"] = None
                
                # If it's a string like "2024-09-30 21:03:13.560 nachm.", extract the date/time substring
                if isinstance(first_entry, str):
                    
                    # regex allows fractional seconds (dot or comma) and stops before trailing text
                    m = re.search(r"\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?", first_entry)
                    if m:
                        first_entry = m.group(0).replace(",", ".")
                        if debug:
                            print(f"[SUBJECTIVE] extracted_datetime: {first_entry} from sheet {sheet_name}")

                # prefer regex-extracted timestamp; otherwise try parsing the raw value
                if isinstance(first_entry, str):
                    m = re.search(r"\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?", first_entry)
                    if m:
                        parsed_candidate = m.group(0).replace(",", ".")
                        if debug:
                            print(f"[SUBJECTIVE] extracted_datetime: {parsed_candidate} from sheet {sheet_name}")
                    else:
                        # no regex match — keep the raw string in first_entry_raw for inspection
                        parsed_candidate = first_entry
                else:
                    parsed_candidate = first_entry
                
                print(f"[SUBJECTIVE] parsing_candidate: {parsed_candidate} (type={type(parsed_candidate)}) from sheet {sheet_name} in {excel_path.name}")

                recording_date = pd.to_datetime(parsed_candidate, errors="coerce") if parsed_candidate is not None else pd.NaT
                record["recording_date"] = recording_date
                if debug:
                    print(
                        f"[SUBJECTIVE] parsed_recording_date: {recording_date} (type={type(recording_date)}) from sheet {sheet_name} in {excel_path.name}"
                    )
                # store ISO string for easier downstream consumption
                try:
                    record["recording_date_iso"] = recording_date.isoformat() if pd.notna(recording_date) else None
                except Exception:
                    record["recording_date_iso"] = None
            except Exception:
                record["recording_date"] = pd.NaT
                record["recording_date_iso"] = None

            records.append(record)

    df = pd.DataFrame.from_records(records)
    # Ensure both columns exist and have stable types
    if "recording_date_iso" not in df.columns:
        df["recording_date_iso"] = None
    # Coerce recording_date to datetime dtype
    df["recording_date"] = pd.to_datetime(df["recording_date"], errors="coerce")

    # Matched date: assign entries that were recorded after midnight to the
    # previous calendar day when they conceptually belong to the prior evening.
    # Default heuristic: for activity and TET diaries, timestamps between
    # 00:00 and 06:00 are attributed to the previous day.
    CUTOFF_HOUR = 6

    def _compute_matched_date(row: pd.Series) -> pd.Timestamp | pd.NaT:
        dt = row.get("recording_date")
        if pd.isna(dt):
            return pd.NaT
        section = row.get("section")
        try:
            hour = int(dt.hour)
        except Exception:
            hour = None
        # apply heuristic to these diary types
        if section in ("activity_diary", "tet_diary") and hour is not None and hour < CUTOFF_HOUR:
            return (pd.to_datetime(dt).normalize() - pd.Timedelta(days=1))
        return pd.to_datetime(dt).normalize()

    df["matched_date"] = df.apply(_compute_matched_date, axis=1)
    # ISO string for convenience
    df["matched_date_iso"] = df["matched_date"].apply(lambda d: d.isoformat() if pd.notna(d) else None)
    
    
    
    # --- Determine where missing data is expected vs unexpected ---
    # Per-file matched date (many sheets come from the same workbook/file)
    def _file_max(dt_series: pd.Series) -> pd.Timestamp | pd.NaT:
        s = dt_series.dropna()
        return s.max() if not s.empty else pd.NaT

    df["file_matched_date"] = df.groupby("file")["matched_date"].transform(_file_max)

    # Participant-level first/last observation dates
    participant_last = df.loc[df["has_data"], "matched_date"].groupby(df["participant"]).max()
    df["participant_last_date"] = df["participant"].map(participant_last)

    tet_first = (
        df.loc[(df["section"] == "tet_meditation") & (df["has_data"]), "matched_date"]
        .groupby(df["participant"])
        .min()
    )
    df["tet_first_date"] = df["participant"].map(tet_first)

    # Default: missing data is unexpected
    df["expected"] = False

    # Work on missing records only
    missing_mask = ~df["has_data"]

    # Case 1: it's expected that TET meditation only starts after some days —
    # so for files dated before the participant's first observed tet_meditation, mark expected
    mask_tet_early = (
        missing_mask
        & (df["section"] == "tet_meditation")
        & df["file_matched_date"].notna()
        & df["tet_first_date"].notna()
        & (df["file_matched_date"] < df["tet_first_date"])
    )
    df.loc[mask_tet_early, "expected"] = True

    # Case 2: it's expected that there is no tet meditation, tet diary or activity diary
    # on the last day of data collection for the participant
    last_day_sections = ("tet_meditation", "tet_diary", "activity_diary")
    mask_last_day = (
        missing_mask
        & df["section"].isin(last_day_sections)
        & df["file_matched_date"].notna()
        & df["participant_last_date"].notna()
        & (df["file_matched_date"] == df["participant_last_date"])
    )
    df.loc[mask_last_day, "expected"] = True

    # Populate `color` column with clear, deterministic states so plotting
    # and downstream logic can rely on a single source of truth.
    # States (strings):
    # - 'white' = unknown / initialized
    # - 'green' = has_data == True
    # - 'grey'  = has_data == False but expected == True (missing but expected)
    # - 'red'   = has_data == False and expected == False (unexpected missing)
    df["color"] = "white"

    # mark rows where data is present
    df.loc[df["has_data"] == True, "color"] = "green"

    # missing but expected -> grey
    df.loc[(df["has_data"] == False) & (df["expected"] == True), "color"] = "grey"

    # missing and unexpected -> red
    df.loc[(df["has_data"] == False) & (df["expected"] == False), "color"] = "red"

    # Add integer mapping for colors for easier downstream processing/plotting
    _color_map = {"white": 0, "grey": 1, "green": 2, "red": 3}
    df["color_int"] = df["color"].map(_color_map).fillna(0).astype(int)

    return df


def summarize_subjective_data(df: pd.DataFrame) -> dict[str, object]:
    """Summarize subjective data availability and coverage for a participant based on the tidy dataframe produced by load_subjective_data."""
    summary = {}
    if df.empty:
        return summary

    # Count how many sheets of each section have data
    for section in df["section"].unique():
        section_df = df[df["section"] == section]
        summary[f"{section}_sheets_with_data"] = int(section_df["has_data"].sum())
        summary[f"{section}_total_sheets"] = len(section_df)

    return summary