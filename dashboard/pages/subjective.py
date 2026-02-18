from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.modalities.subjective.plots import plot_subjective_timeline



def render_subjective_tab(df_subjective: pd.DataFrame) -> None:
    st.header(" Subjective Data")

    if df_subjective.empty:
        st.info("No rating data found for this participant.")
        return
    
    st.plotly_chart(plot_subjective_timeline(df_subjective), use_container_width=True)

    display_cols = [col for col in ["participant", "file", "section", "sheet_index", "sheet_name", "has_data", "recording_date", "recording_date_iso"] if col in df_subjective.columns]
    st.dataframe(df_subjective[display_cols], use_container_width=True)
    
__all__ = ["render_subjective_tab"]