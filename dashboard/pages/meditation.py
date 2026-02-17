from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.modalities.eeg.plots import plot_meditation_duration



def render_meditation_tab(df_meditation: pd.DataFrame) -> None:
    st.header("🧘 Meditation Data")

    if df_meditation.empty:
        st.info("No meditation data found for this participant.")
        return
    
    st.plotly_chart(plot_meditation_duration(df_meditation), use_container_width=True)

    display_cols = [col for col in ["session", "start", "stop", "duration_minutes", "file"] if col in df_meditation.columns]
    st.dataframe(df_meditation[display_cols], use_container_width=True)
    
__all__ = ["render_meditation_tab"]
