from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.modalities.subjective.plots import (
    plot_subjective_availability_heatmap,
)



def render_subjective_tab(df_subjective: pd.DataFrame) -> None:
    st.header(" Subjective Data")

    if df_subjective.empty:
        st.info("No rating data found for this participant.")
        return
    # work on a local copy so we can augment columns for display without
    # relying on cached loading code to have been re-run
    df_display = df_subjective.copy()
    #print("DF Display columns:", df_display.columns)

    # compute matched_date locally if not present (same heuristic as processing)
    # if "matched_date" not in df_display.columns:
    #     CUTOFF_HOUR = 6

    #     def _compute_matched_date_local(row: pd.Series):
    #         dt = row.get("recording_date")
    #         if pd.isna(dt):
    #             return pd.NaT
    #         section = row.get("section")
    #         try:
    #             hour = int(pd.to_datetime(dt).hour)
    #         except Exception:
    #             hour = None
    #         if section in ("activity_diary", "tet_diary") and hour is not None and hour < CUTOFF_HOUR:
    #             return (pd.to_datetime(dt).normalize() - pd.Timedelta(days=1))
    #         return pd.to_datetime(dt).normalize()

    #     df_display["matched_date"] = df_display.apply(_compute_matched_date_local, axis=1)
    #     df_display["matched_date_iso"] = df_display["matched_date"].apply(lambda d: d.isoformat() if pd.notna(d) else None)

    #st.plotly_chart(plot_subjective_timeline(df_display), width='stretch')
    
    #st.plotly_chart(plot_subjective_simple_heatmap(df_display), width='stretch', key="test")

    # availability heatmap: shows which days have subjective records (per participant/file)
    st.plotly_chart(plot_subjective_availability_heatmap(df_display), width='stretch')


    display_cols = [
        col
        for col in [
            #"participant",
            "file",
            "section",
            "sheet_index",
            "sheet_name",
            "has_data",
            "recording_date",
            #"recording_date_iso",
            "matched_date",
            #"matched_date_iso",
            "first_entry_raw",
            "expected",
            "color",            
            "color_int",
        ]
        if col in df_display.columns
    ]
    #st.dataframe(df_display[display_cols], width='stretch')
    
__all__ = ["render_subjective_tab"]