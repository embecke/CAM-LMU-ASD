from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.config import DEFAULT_DATA_BASE_PATH
from dashboard.data_access.participants import list_participants, participant_path
from dashboard.modalities.eeg.plots import sleep_availability_overview, sleep_duration
from dashboard.modalities.eeg.processing import load_sleep_reports, summarize_sleep_recordings
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


@st.cache_data
def _cached_sleep_reports(path_str: str) -> pd.DataFrame:
    return load_sleep_reports(path_str)


def _render_summary(days_with_data: int, total_hours: float, sleep_nights: int, sleep_hours: float) -> None:
    st.subheader("📊 Available Data Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Days with Wristband Data", days_with_data)
    col2.metric("Total Hours Collected", f"{total_hours:.1f}")
    col3.metric("Nights with Sleep EEG", sleep_nights)
    col4.metric("Sleep EEG Hours", f"{sleep_hours:.1f}")


def _combined_overview_figure(df_all: pd.DataFrame, wear_col: str | None, df_sleep: pd.DataFrame) -> go.Figure | None:
    # Build timeline dataframes (wristband timeline is preferred x-axis reference)
    timeline_df = pd.DataFrame()
    if wear_col is not None and not df_all.empty:
        timeline_df = timeline_frame(df_all, wear_col)

    sleep_df = pd.DataFrame()
    if not df_sleep.empty:
        sleep_df = df_sleep.dropna(subset=["start", "stop"]).copy()
        if not sleep_df.empty:
            sleep_df["start"] = pd.to_datetime(sleep_df["start"], errors="coerce")
            sleep_df["stop"] = pd.to_datetime(sleep_df["stop"], errors="coerce")
            sleep_df.sort_values("start", inplace=True)

    # nothing to show
    if (timeline_df.empty if not isinstance(timeline_df, pd.DataFrame) else timeline_df.empty) and (sleep_df.empty):
        return None

    # determine rows: EEG on top, wristband below
    has_sleep = not sleep_df.empty
    has_wrist = not timeline_df.empty if isinstance(timeline_df, pd.DataFrame) else False
    rows = int(has_sleep) + int(has_wrist)
    row_heights = [0.25, 0.75] if has_sleep and has_wrist else [1.0]
    fig = make_subplots(rows=rows or 1, cols=1, shared_xaxes=True, row_heights=row_heights[: rows or 1], vertical_spacing=0.02)

    current_row = 1
    # add EEG row (top)
    if has_sleep:
        sdf = sleep_df.copy()
        shapes: list[dict] = []
        hover_x: list[pd.Timestamp] = []
        hover_text: list[str] = []
        for _, row in sdf.iterrows():
            start = row["start"]
            stop = row["stop"]
            if pd.isna(start) or pd.isna(stop):
                continue

            # rectangle in paper coords so it appears as a horizontal bar
            shapes.append(
                dict(
                    type="rect",
                    xref="x",
                    x0=start,
                    x1=stop,
                    yref="paper",
                    y0=0.85,
                    y1=0.9,
                    fillcolor="#1f77b4",
                    line=dict(width=0),
                )
            )

            mid = start + (stop - start) / 2
            hover_x.append(mid)
            # include ISO timestamps in hover text
            try:
                start_iso = pd.to_datetime(start).isoformat()
                stop_iso = pd.to_datetime(stop).isoformat()
            except Exception:
                start_iso = str(start)
                stop_iso = str(stop)

            hover_text.append(f"Start: {start_iso}<br>Stop: {stop_iso}<br>Night: {row.get('night','')}")

        for sh in shapes:
            fig.add_shape(sh)

        if hover_x:
            fig.add_trace(
                go.Scatter(
                    x=hover_x,
                    y= [0.62] * len(hover_x),
                    mode="markers",
                    marker=dict(opacity=0, size=20),
                    hoverinfo="text",
                    hovertext=hover_text,
                    showlegend=False,
                ),
                row=current_row,
                col=1,
            )

            # Add a small legend on the right side of the EEG subplot.
            # Determine if any EEG file indicates Dreem processing to adjust label.
            legend_extra = " (Dreem)" if any("dreem" in str(f).lower() for f in sdf.get("file", [])) else ""
            legend_text = f"Sleep{legend_extra}"

            # y position in paper coordinates for the center of the EEG subplot row.
            if has_sleep and has_wrist:
                top_row_height = row_heights[0]
                eeg_y = 1.0 - top_row_height / 2.0
            else:
                eeg_y = 0.5

            # Small blue box shape as legend swatch and text annotation to its right.
            fig.add_shape(
                dict(
                    type="circle",
                    xref="paper",
                    yref="paper",
                    x0=1.005,
                    x1=1.015,
                    y0=eeg_y - 0.03,
                    y1=eeg_y + 0.03,
                    fillcolor="#1f77b4",
                    line=dict(width=0),
                )
            )

            fig.add_annotation(
                dict(
                    xref="paper",
                    yref="paper",
                    x=1.02,
                    y=eeg_y,
                    xanchor="left",
                    yanchor="middle",
                    showarrow=False,
                    text=legend_text,
                    font=dict(size=11, color="#333"),
                )
            )

        fig.update_yaxes(visible=False, row=current_row, col=1)
        current_row += 1

    # add wristband row (below)
    if has_wrist:
        fig.add_trace(
            go.Scatter(
                x=timeline_df["datetime"],
                y=[0] * len(timeline_df),
                mode="markers",
                marker=dict(
                    size=10,
                    color=timeline_df[wear_col],
                    colorscale=["#ff4136", "#ffe066", "#b6e63e", "#2ecc40"],
                    cmin=0,
                    cmax=100,
                    colorbar=dict(title="Wearing %", thickness=10, len=0.4, y=0.4, yanchor="middle", x=1.02, xanchor="left", tickmode="array", tickvals=[0, 100], ticktext=["0%", "100%"], tickfont=dict(size=10)),
                    showscale=True,
                ),
                name="Wristband",
                hovertemplate="Time: %{x|%Y-%m-%d %H:%M}<br>Wearing: %{marker.color:.0f}%<extra></extra>",
                showlegend=False,
            ),
            row=current_row,
            col=1,
        )
        fig.update_yaxes(visible=False, row=current_row, col=1)

    # finalize layout
    fig.update_layout(
        height=180 * (rows or 1),
        template="plotly_white",
        margin={"l": 60, "r": 80, "t": 30, "b": 40},
        hovermode="closest",
        hoverdistance=8,
        showlegend=False,
    )

    # bottom x-axis label
    fig.update_xaxes(title_text="Time", row=(rows or 1), col=1)

    # derive base times for axis range: prefer wristband timeline, fall back to sleep extremes
    base_times = None
    if has_wrist:
        base_times = sorted(timeline_df["datetime"].dropna().unique().tolist())
    elif has_sleep:
        starts = sleep_df["start"].dropna().tolist()
        stops = sleep_df["stop"].dropna().tolist()
        if starts or stops:
            base_times = [min(starts)] if starts else []
            if stops:
                base_times.append(max(stops))

    if base_times:
        tmin = min(base_times)
        tmax = max(base_times)
        for r in range(1, (rows or 1) + 1):
            fig.update_xaxes(tickformat="%Y-%m-%d\n%H:%M", showgrid=True, tickangle=0, range=[tmin, tmax], row=r, col=1, type='date')

    return fig


def _render_overview_tab(df_all: pd.DataFrame, wear_col: str | None, df_sleep: pd.DataFrame) -> None:
    st.header("Data Overview")

    st.subheader("Combined Timeline: Wristband + Sleep")
    combined = _combined_overview_figure(df_all, wear_col, df_sleep)
    if combined:
        st.plotly_chart(combined, use_container_width=True)
    else:
        st.info("No timeline data available to plot a combined view.")



def _render_wristband_tab(df_all: pd.DataFrame, wear_col: str | None, aggregated_data: dict[str, pd.DataFrame]) -> None:
    st.header("❤️ Wristband Biomarkers")

    if not df_all.empty and wear_col is not None and df_all["datetime"].notna().any():
        valid_df = df_all.sort_values("datetime")
        hours_table = hours_per_bin_table(valid_df, wear_col)
        
        st.plotly_chart(stacked_hours_figure(hours_table), use_container_width=True)

        #st.subheader("Hours per Day by Wearing Detection Percentage")
        #st.dataframe(hours_table, use_container_width=True)
        st.subheader("Detailed Wearing Detection Events (All Days)")
        st.plotly_chart(detailed_events_figure(valid_df, wear_col), use_container_width=True)

        show_cols = detailed_columns(valid_df, wear_col)
        #st.dataframe(valid_df[show_cols], use_container_width=True)
        return

    st.warning("No EmbracePlus wearing detection files found for this participant.")
    
def _render_sleep_tab(df_sleep: pd.DataFrame) -> None:
    st.header("🌙 Sleep Data")

    st.subheader("Sleep EEG Recording Intervals")
    if df_sleep.empty:
        st.info("No Dreem sleep EEG reports found for this participant.")
    else:
        st.plotly_chart(sleep_duration(df_sleep), use_container_width=True)
        display_cols = [col for col in ["night", "start", "stop", "duration_hours", "file"] if col in df_sleep.columns]
        st.dataframe(df_sleep[display_cols], use_container_width=True)


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
    # overwrite selected_participant for testing
    selected_participant = "Stream_LMU_HC_008_2024_30092024"

    participant_dir = participant_path(data_base_path, selected_participant)

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"Participant: {selected_participant}")

    with st.spinner(f"Loading data for {selected_participant}..."):
        df_all, wear_col = _cached_wearing_data(str(participant_dir))
        aggregated_data = _cached_aggregated_data(str(participant_dir))
        sleep_df = _cached_sleep_reports(str(participant_dir))
        days_with_data, total_hours = summarize_collection(df_all)
        sleep_nights, sleep_hours = summarize_sleep_recordings(sleep_df)

    _render_summary(days_with_data, total_hours, sleep_nights, sleep_hours)

    tab1, tab2, tab3 = st.tabs(["📅 Data Overview", "❤️ Wristband Biomarkers", "🌙 Sleep Data"])

    with tab1:
        _render_overview_tab(df_all, wear_col, sleep_df)

    with tab2:
        _render_wristband_tab(df_all, wear_col, aggregated_data)

    with tab3:
        _render_sleep_tab(sleep_df)

    st.markdown("---")
    st.markdown(
        """
<div style='text-align: center; color: gray; font-size: 12px;'>
    CAM-LMU-STREAM Dashboard | Built with Streamlit | Wristband & Sleep Data |
</div>
""",
        unsafe_allow_html=True,
    )
