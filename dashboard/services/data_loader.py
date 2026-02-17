from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.modalities.eeg.processing import load_meditation_reports, load_sleep_reports
from dashboard.modalities.wristband.processing import load_wearing_detection_data


@st.cache_data
def get_wristband_data(path_str: str) -> tuple[pd.DataFrame, str | None]:
    return load_wearing_detection_data(path_str)


@st.cache_data
def get_sleep_reports(path_str: str) -> pd.DataFrame:
    return load_sleep_reports(path_str, debug=False)

@st.cache_data
def get_meditation_data(path_str: str) -> pd.DataFrame:
    return load_meditation_reports(path_str, debug=False)


__all__ = ["get_wristband_data", "get_sleep_reports", "get_meditation_data"]
