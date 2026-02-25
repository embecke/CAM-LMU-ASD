from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.modalities.eeg.plots import plot_sleep_duration


def render_sleep_tab(df_sleep: pd.DataFrame) -> None:
    st.header("🌙 Sleep Data")

    st.subheader("Sleep EEG Recording Intervals")
    if df_sleep.empty:
        st.info("No Dreem sleep EEG reports found for this participant.")
        return

    st.plotly_chart(plot_sleep_duration(df_sleep), width="stretch")
    #display_cols = [col for col in ["night", "start", "stop", "duration_hours", "file"] if col in df_sleep.columns]
    #.dataframe(df_sleep[display_cols], width="stretch")


__all__ = ["render_sleep_tab"]
