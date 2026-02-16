from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from dashboard.config import DEFAULT_DATA_BASE_PATH
from dashboard.data_access.participants import list_participants, participant_path
from dashboard.modalities.wristband.plots import (
    availability_timeline_figure,
    detailed_events_figure,
    generic_aggregated_biomarker_figure,
    stacked_hours_figure,
)
from dashboard.modalities.wristband.processing import (
    detailed_columns,
    hours_per_bin_table,
    load_aggregated_data,
    load_wearing_detection_data,
    summarize_collection,
    timeline_frame,
)


@st.cache_data
def _cached_wearing_data(path_str: str) -> tuple[pd.DataFrame, str | None]:
    return load_wearing_detection_data(path_str)


@st.cache_data
def _cached_aggregated_data(path_str: str) -> dict[str, pd.DataFrame]:
    return load_aggregated_data(path_str)


def _render_summary(days_with_data: int, total_hours: float) -> None:
    st.subheader("📊 Available Data Summary")
    col1, col2 = st.columns(2)
    col1.metric("Days with Wristband Data", days_with_data)
    col2.metric("Total Hours Collected", f"{total_hours:.1f}")


def _render_overview_tab(df_all: pd.DataFrame, wear_col: str | None) -> None:
    st.header("Data Overview")

    if df_all.empty or wear_col is None:
        st.info("No wristband wearing detection data found for timeline plot.")
        return

    timeline_df = timeline_frame(df_all, wear_col)
    if timeline_df.empty:
        st.info("No valid wristband timestamps found for timeline plot.")
        return

    st.subheader("Wristband Data Availability Timeline")
    st.plotly_chart(availability_timeline_figure(timeline_df, wear_col), use_container_width=True)


def _render_wristband_tab(df_all: pd.DataFrame, wear_col: str | None, aggregated_data: dict[str, pd.DataFrame]) -> None:
    st.header("❤️ Wristband Biomarkers")

    if not df_all.empty and wear_col is not None and df_all["datetime"].notna().any():
        valid_df = df_all.sort_values("datetime")
        hours_table = hours_per_bin_table(valid_df, wear_col)

        st.subheader("Hours per Day by Wearing Detection Percentage")
        st.dataframe(hours_table, use_container_width=True)

        st.plotly_chart(stacked_hours_figure(hours_table), use_container_width=True)

        st.subheader("Detailed Wearing Detection Events (All Days)")
        st.plotly_chart(detailed_events_figure(valid_df, wear_col), use_container_width=True)

        show_cols = detailed_columns(valid_df, wear_col)
        st.dataframe(valid_df[show_cols], use_container_width=True)
        return

    if aggregated_data:
        st.info("📊 Displaying aggregated per-minute wristband data (preprocessed)")
        selected_file = st.selectbox("Select aggregated wristband data file:", list(aggregated_data.keys()))
        df = aggregated_data[selected_file]

        st.subheader(f"📊 {selected_file}")
        st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
        st.write(f"**Time Range:** {df.shape[0]} minutes of data")

        with st.expander("View data preview (first 10 rows)"):
            st.dataframe(df.head(10), use_container_width=True)

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.warning("⚠️ No numeric columns found in this file.")
            return

        selected_cols = st.multiselect(
            "Select biomarkers to visualize:",
            numeric_cols,
            default=[numeric_cols[0]],
            help="Select one or more measures to plot",
        )

        if selected_cols:
            st.plotly_chart(generic_aggregated_biomarker_figure(df, selected_cols), use_container_width=True)
            st.subheader("Summary Statistics")
            st.dataframe(df[selected_cols].describe(), use_container_width=True)
        return

    st.warning("No EmbracePlus wearing detection files found for this participant.")


def run_dashboard() -> None:
    st.set_page_config(
        page_title="CAM-LMU-ASD Participant Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🏥 CAM-LMU-ASD Participant Data Dashboard")
    st.markdown(
        "Visualize preprocessed Wristband biomarkers and Sleep data for each participant. "
        "*TET data coming soon!*"
    )

    st.sidebar.header("Configuration")
    data_base_path = st.sidebar.text_input(
        "Enter base data folder path:",
        value=DEFAULT_DATA_BASE_PATH,
        help="Path where original participant folders are stored (e.g., LMU_STREAM_HC_001, etc.)",
    )

    if not Path(data_base_path).exists():
        st.warning(f"⚠️ Data path does not exist: {data_base_path}")
        st.stop()

    participants = list_participants(data_base_path)
    if not participants:
        st.error("❌ No participant folders found in the specified path")
        st.stop()

    selected_participant = st.sidebar.selectbox(
        "Select Participant:",
        participants,
        help="Choose a participant to view their data",
    )

    participant_dir = participant_path(data_base_path, selected_participant)

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"Participant: {selected_participant}")

    with st.spinner(f"Loading data for {selected_participant}..."):
        df_all, wear_col = _cached_wearing_data(str(participant_dir))
        aggregated_data = _cached_aggregated_data(str(participant_dir))
        days_with_data, total_hours = summarize_collection(df_all)

    _render_summary(days_with_data, total_hours)

    tab1, tab2 = st.tabs(["📅 Data Overview", "❤️ Wristband Biomarkers"])

    with tab1:
        _render_overview_tab(df_all, wear_col)

    with tab2:
        _render_wristband_tab(df_all, wear_col, aggregated_data)

    st.markdown("---")
    st.markdown(
        """
<div style='text-align: center; color: gray; font-size: 12px;'>
    CAM-LMU-STREAM Dashboard | Built with Streamlit | Wristband & Sleep Data |
</div>
""",
        unsafe_allow_html=True,
    )
