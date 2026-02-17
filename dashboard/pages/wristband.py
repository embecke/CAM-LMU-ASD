from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.modalities.wristband.plots import (
    plot_wristband_timeline,
    plot_wristband_stacked,
)
from dashboard.modalities.wristband.processing import detailed_columns, hours_per_bin_table


def render_wristband_tab(df_all: pd.DataFrame, wear_col: str | None) -> None:
    st.header("❤️ Wristband Biomarkers")

    if not df_all.empty and wear_col is not None and df_all["datetime"].notna().any():
        valid_df = df_all.sort_values("datetime")
        hours_table = hours_per_bin_table(valid_df, wear_col)

        st.plotly_chart(plot_wristband_stacked(hours_table), use_container_width=True)
        st.subheader("Detailed Wearing Detection Events (All Days)")
        st.plotly_chart(plot_wristband_timeline(valid_df, wear_col), use_container_width=True)

        show_cols = detailed_columns(valid_df, wear_col)
        st.dataframe(valid_df[show_cols], use_container_width=True)
        return

    st.warning("No EmbracePlus wearing detection files found for this participant.")


__all__ = ["render_wristband_tab"]
