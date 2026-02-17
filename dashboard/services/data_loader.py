from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.modalities.eeg.processing import load_sleep_reports
from dashboard.modalities.wristband.processing import load_wearing_detection_data


@st.cache_data
def get_wearing_data(path_str: str) -> tuple[pd.DataFrame, str | None]:
    return load_wearing_detection_data(path_str)


@st.cache_data
def get_sleep_reports(path_str: str) -> pd.DataFrame:
    return load_sleep_reports(path_str, debug=False)


__all__ = ["get_wearing_data", "get_sleep_reports"]
