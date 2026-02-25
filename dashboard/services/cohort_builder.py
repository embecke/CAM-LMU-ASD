from __future__ import annotations

import pandas as pd

from dashboard.data_access.participants import participant_path
from dashboard.services.data_loader import get_meditation_data, get_sleep_reports, get_subjective_data, get_wristband_data
from dashboard.services.data_quality import nights_with_following_wristband_day, wristband_days_with_following_sleep_night
from dashboard.modalities.eeg.processing import summarize_meditation_recordings, summarize_sleep_recordings
from dashboard.modalities.wristband.processing import summarize_wristband_recordings
from dashboard.modalities.subjective.processing import summarize_subjective_data


def _build_cohort_table(
    participants: list[str],
    data_base_path: str,
    coverage_threshold: float,
) -> pd.DataFrame:
    """Return aggregated summary metrics for all participants in base path."""
    records: list[dict[str, object]] = []

    for pid in participants:
        p_dir = participant_path(data_base_path, pid)
        df_wristband, wear_col = get_wristband_data(str(p_dir))
        df_sleep = get_sleep_reports(str(p_dir))
        df_meditation = get_meditation_data(str(p_dir))
        df_subjective = get_subjective_data(str(p_dir))
        wristband_days, wristband_total_hours = summarize_wristband_recordings(df_wristband, wear_col=wear_col)
        sleep_nights, sleep_total_hours = summarize_sleep_recordings(df_sleep)
        meditation_sessions, meditation_total_hours = summarize_meditation_recordings(df_meditation)

        nights_with_day, _ = nights_with_following_wristband_day(
            df_sleep, df_wristband, wear_col=wear_col, coverage_threshold=coverage_threshold
        )
        days_with_night, _ = wristband_days_with_following_sleep_night(
            df_sleep, df_wristband, wear_col=wear_col, coverage_threshold=coverage_threshold
        )

        records.append(
            {
                "participant": pid,
                "wristband_days": wristband_days,
                "wristband_total_hours": wristband_total_hours,
                "wristband_mean": wristband_total_hours / wristband_days if wristband_days > 0 else 0,
                "eeg_company": df_sleep["company"].iloc[0] if not df_sleep.empty else None,
                "sleep_nights": sleep_nights,
                "sleep_total_hours": sleep_total_hours,
                "sleep_mean": sleep_total_hours / sleep_nights if sleep_nights > 0 else 0,
                "meditation_sessions": meditation_sessions,
                "meditation_total_hours": meditation_total_hours,
                "meditation_mean": meditation_total_hours / meditation_sessions if meditation_sessions > 0 else 0,
                "sleep_diary_amount": summarize_subjective_data(df_subjective).get("sleep_diary_sheets_with_data", 0),
                "tet_diary_amount": summarize_subjective_data(df_subjective).get("tet_diary_sheets_with_data", 0),
                "activity_diary_amount": summarize_subjective_data(df_subjective).get("activity_diary_sheets_with_data", 0),
                "tet_meditation_amount": summarize_subjective_data(df_subjective).get("tet_meditation_sheets_with_data", 0),
                "nights_with_following_day": nights_with_day,
                "days_with_following_night": days_with_night,
                "coverage_threshold": coverage_threshold,
            }
        )

    return pd.DataFrame.from_records(records)