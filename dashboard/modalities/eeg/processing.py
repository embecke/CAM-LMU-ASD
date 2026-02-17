from __future__ import annotations

from pathlib import Path

import pandas as pd


# Base folders relative to the participant directory (use Path for reliable joins)
SLEEP_DIR = Path("EEG") / "Night"
MEDITATION_DIR = Path("EEG") / "Meditation"
REPORT_FILE_HINT = "report"
DREEM_HINT = "dreem"


#################### Sleep Loading and Summarization ####################
def _read_key_value_csv(csv_path: Path, debug: bool = False) -> dict:
    """Read CSVs that contain key,value rows and return a dict of values.

    This attempts several separators and fallback strategies so it works for
    slightly different report formats.
    """
    text = None
    try:
        text = csv_path.read_text(encoding="utf-8")
    except Exception:
        try:
            text = csv_path.read_text(encoding="latin1")
        except Exception:
            if debug:
                print(f"[EEG] cannot read file as text: {csv_path}")
            return {}

    # Try common separators in order
    for sep in [",", ";", "\t"]:
        try:
            df_kv = pd.read_csv(csv_path, header=None, names=["key", "value"], sep=sep, engine="python", dtype=str, comment="#")
        except Exception:
            df_kv = None

        if df_kv is None or df_kv.shape[1] < 2:
            # try manual splitting of lines
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            pairs = []
            for l in lines:
                if sep in l:
                    k, v = l.split(sep, 1)
                    pairs.append((k.strip(), v.strip()))
                else:
                    # fallback: try whitespace separation
                    parts = l.split()
                    if len(parts) >= 2:
                        pairs.append((parts[0].strip(), " ".join(parts[1:]).strip()))
            if pairs:
                df_kv = pd.DataFrame(pairs, columns=["key", "value"])

        if df_kv is not None and not df_kv.empty:
            try:
                df_kv = df_kv.dropna(how="all")
                keys = df_kv.iloc[:, 0].astype(str).str.strip().str.lower()
                vals = df_kv.iloc[:, 1].astype(str).str.strip()
                mapping = {k: v for k, v in zip(keys.tolist(), vals.tolist())}
                if debug:
                    print(f"[EEG] parsed {len(mapping)} key-value pairs using sep='{sep}'")
                return mapping
            except Exception:
                continue

    if debug:
        print(f"[EEG] no key/value pairs found in {csv_path}")
    return {}


def load_sleep_reports(participant_path: str | Path, debug: bool = True) -> pd.DataFrame:
    """Collect record start/stop times from Dreem sleep report CSVs.

    For each night folder under the participant's EEG sleep directory, the
    function searches for CSV files whose names contain both "report" and
    "dreem". It extracts the first valid `record_start_iso` and
    `record_stop_iso` values and returns a tidy frame ready for plotting.
    """

    participant_dir = Path(participant_path)
    sleep_base = participant_dir / SLEEP_DIR

    if debug:
        print(f"[EEG] participant_dir={participant_dir}")
        print(f"[EEG] sleep_base={sleep_base} exists={sleep_base.exists()}")

    if not sleep_base.exists() or not sleep_base.is_dir():
        return pd.DataFrame()

    records: list[dict[str, object]] = []

    # Recursively search for CSV files under the sleep base directory so that
    # CSVs stored in deeper subfolders are also discovered.
    all_csvs = list(sleep_base.rglob("*.csv")) if sleep_base.exists() else []
    if debug:
        print(f"[EEG] discovered_csv_count={len(all_csvs)}")
        for p in all_csvs[:20]:
            print(f"[EEG] found_csv: {p}")

    for csv_path in all_csvs:
        if not csv_path.is_file():
            if debug:
                print(f"[EEG] skipping_non_file: {csv_path}")
            continue

        name_lower = csv_path.name.lower()
        has_report = REPORT_FILE_HINT in name_lower
        has_dreem = DREEM_HINT in name_lower
        if debug:
            print(f"[EEG] checking: {csv_path.name} report={has_report} dreem={has_dreem}")

        if not has_report:
            continue
        if not has_dreem:
            # Placeholder for future Bitbrain handling: skip for now
            if debug:
                print(f"[EEG] skipping (not Dreem): {csv_path.name}")
            continue

        # Derive the top-level night folder name relative to the sleep base.
        try:
            rel = csv_path.relative_to(sleep_base)
            night_name = rel.parts[0] if rel.parts else csv_path.parent.name
        except Exception:
            night_name = csv_path.parent.name

        if debug:
            print(f"[EEG] night_name derived: {night_name}")

        # Prefer key/value parsing for Dreem report files which list rows as
        # `key,value` pairs (no header). Fall back to table parsing if needed.
        start = pd.NaT
        stop = pd.NaT

        # Try key/value parsing first (matches provided example CSV)
        kv = _read_key_value_csv(csv_path, debug=debug)
        if kv:
            record_start_iso = kv.get("record_start_iso")
            record_stop_iso = kv.get("record_stop_iso")
            if record_start_iso:
                try:
                    start = pd.to_datetime(record_start_iso, errors="coerce")
                except Exception:
                    start = pd.NaT
            if record_stop_iso:
                try:
                    stop = pd.to_datetime(record_stop_iso, errors="coerce")
                except Exception:
                    stop = pd.NaT

            if debug:
                print(f"[EEG] kv parsed start={start} stop={stop} for file={csv_path.name}")


        if pd.isna(start) or pd.isna(stop):
            if debug:
                print(f"Still [EEG] missing start/stop for {csv_path.name}, skipping")
            continue

        duration_hours = (stop - start).total_seconds() / 3600 if stop > start else 0.0

        records.append(
            {
                "night": night_name,
                "file": csv_path.name,
                "start": start,
                "stop": stop,
                "duration_hours": duration_hours,
            }
        )

    return pd.DataFrame.from_records(records)


def summarize_sleep_recordings(df_sleep: pd.DataFrame) -> tuple[int, float]:
    """Return (nights_with_data, total_hours_recorded)."""
    if df_sleep.empty:
        return 0, 0.0

    nights = int(df_sleep["night"].nunique()) if "night" in df_sleep.columns else 0
    total_hours = float(df_sleep.get("duration_hours", pd.Series(dtype=float)).sum())
    return nights, total_hours



####################### Meditation Loading and Summarization #######################
def load_meditation_reports(participant_path: str | Path, debug: bool = True) -> pd.DataFrame:
    """Collect record start/stop times from Dreem meditation report CSVs.

    For each meditation folder under the participant's EEG meditation directory, the
    function searches for CSV files whose names contain both "report" and
    "dreem". It extracts the first valid `record_start_iso` and
    `record_stop_iso` values and returns a tidy frame ready for plotting.
    """

    participant_dir = Path(participant_path)
    meditation_base = participant_dir / MEDITATION_DIR

    if debug:
        print(f"[Meditation] participant_dir={participant_dir}")
        print(f"[Meditation] meditation_base={meditation_base} exists={meditation_base.exists()}")

    if not meditation_base.exists() or not meditation_base.is_dir():
        return pd.DataFrame()

    records: list[dict[str, object]] = []

    # Recursively search for CSV files under the meditation base directory so that
    # CSVs stored in deeper subfolders are also discovered.
    all_csvs = list(meditation_base.rglob("*.csv")) if meditation_base.exists() else []
    if debug:
        print(f"[Meditation] discovered_csv_count={len(all_csvs)}")
        for p in all_csvs[:20]:
            print(f"[Meditation] found_csv: {p}")

    for csv_path in all_csvs:
        if not csv_path.is_file():
            if debug:
                print(f"[Meditation] skipping_non_file: {csv_path}")
            continue

        name_lower = csv_path.name.lower()
        has_report = REPORT_FILE_HINT in name_lower
        has_dreem = DREEM_HINT in name_lower
        if debug:
            print(f"[Meditation] checking: {csv_path.name} report={has_report} dreem={has_dreem}")

        if not has_report:
            continue
        if not has_dreem:
            # Placeholder for future Bitbrain handling: skip for now
            if debug:
                print(f"[Meditation] skipping (not Dreem): {csv_path.name}")
            continue

        # Derive the top-level night folder name relative to the meditation base.
        try:
            rel = csv_path.relative_to(meditation_base)
            session = rel.parts[0] if rel.parts else csv_path.parent.name
        except Exception:
            session = csv_path.parent.name

        if debug:
            print(f"[Meditation] session derived: {session}")

        # Prefer key/value parsing for Dreem report files which list rows as
        # `key,value` pairs (no header). Fall back to table parsing if needed.
        start = pd.NaT
        stop = pd.NaT

        # Try key/value parsing first (matches provided example CSV)
        kv = _read_key_value_csv(csv_path, debug=debug)
        if kv:
            record_start_iso = kv.get("record_start_iso")
            record_stop_iso = kv.get("record_stop_iso")
            if record_start_iso:
                try:
                    start = pd.to_datetime(record_start_iso, errors="coerce")
                except Exception:
                    start = pd.NaT
            if record_stop_iso:
                try:
                    stop = pd.to_datetime(record_stop_iso, errors="coerce")
                except Exception:
                    stop = pd.NaT

            if debug:
                print(f"[Meditation] kv parsed start={start} stop={stop} for file={csv_path.name}")


        if pd.isna(start) or pd.isna(stop):
            if debug:
                print(f"Still [Meditation] missing start/stop for {csv_path.name}, skipping")
            continue

        duration_hours = (stop - start).total_seconds() / 3600 if stop > start else 0.0

        records.append(
            {
                "session": session,
                "file": csv_path.name,
                "start": start,
                "stop": stop,
                "duration_minutes": duration_hours * 60,
            }
        )

    return pd.DataFrame.from_records(records)

def summarize_meditation_recordings(df_meditation: pd.DataFrame) -> tuple[int, float]:
    """Return (sessions_with_data, total_minutes_recorded)."""
    if df_meditation.empty:
        return 0, 0.0

    sessions = int(df_meditation["session"].nunique()) if "session" in df_meditation.columns else 0
    total_hours = float(df_meditation.get("duration_minutes", pd.Series(dtype=float)).sum()) / 60
    return sessions, total_hours