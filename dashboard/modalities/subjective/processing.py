from __future__ import annotations

from pathlib import Path

import pandas as pd
import re


# Base folders relative to the participant directory (use Path for reliable joins)
SUBJECTIVE_DIR = Path("App")
DAILY_HINT = "App"
TEMP_PREFIX = "~$"


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

    # We expect up to 4 relevant sheets per file in the following order/indexes
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

        # iterate expected sheet positions
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
            }

            # If the workbook has fewer sheets than expected, skip that section
            if idx >= len(xl.sheet_names):
                if debug:
                    print(f"[SUBJECTIVE] missing_sheet idx={idx} for {excel_path.name}")
                records.append(record)
                continue

            sheet_name = xl.sheet_names[idx]
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
                last_row = df_clean.iloc[-1]
                # pick the first non-null entry in the last row (safer than iloc[0])
                first_entry = None
                for v in last_row:
                    if pd.notna(v) and str(v).strip() != "":
                        first_entry = v
                        break

                if first_entry is None:
                    record["recording_date"] = pd.NaT
                    record["recording_date_iso"] = None
                    records.append(record)
                    continue
                
                # If it's a string like "2024-09-30 21:03:13.560 nachm.", extract the date/time substring
                if isinstance(first_entry, str):
                    
                    # regex allows fractional seconds (dot or comma) and stops before trailing text
                    m = re.search(r"\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?", first_entry)
                    if m:
                        first_entry = m.group(0).replace(",", ".")
                        if debug:
                            print(f"[SUBJECTIVE] extracted_datetime: {first_entry} from sheet {sheet_name}")

                recording_date = pd.to_datetime(first_entry, errors="coerce")
                record["recording_date"] = recording_date
                if debug:
                    print(f"[SUBJECTIVE] parsed_recording_date: {recording_date} (type={type(recording_date)}) from sheet {sheet_name} in {excel_path.name}")
                # store ISO string for easier downstream consumption
                try:
                    record["recording_date_iso"] = recording_date.isoformat() if pd.notna(recording_date) else None
                except Exception:
                    record["recording_date_iso"] = None
            except Exception:
                record["recording_date"] = pd.NaT
                record["recording_date_iso"] = None

            # add before records.append(record)
            
            #print("DEBUG APPEND:", record['section'], record['sheet_name'], record['recording_date'], record.get('recording_date_iso'))
            records.append(record)

    df = pd.DataFrame.from_records(records)
    # Ensure both columns exist and have stable types
    if "recording_date_iso" not in df.columns:
        df["recording_date_iso"] = None
    # Coerce recording_date to datetime dtype
    df["recording_date"] = pd.to_datetime(df["recording_date"], errors="coerce")
    return df