from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.modalities.wristband.processing import timeline_frame

def row_center_y(row_heights: list[float], row_index: int) -> float:
    return 1.0 - (sum(row_heights[:row_index]) + row_heights[row_index] / 2.0)


def build_combined_overview(df_all: pd.DataFrame, wear_col: str | None, df_sleep: pd.DataFrame, df_meditation: pd.DataFrame, df_subjective: pd.DataFrame) -> go.Figure | None:
    """Return stacked timeline combining wristband wearing and sleep intervals."""
    timeline_df = pd.DataFrame()
    if wear_col is not None and not df_all.empty:
        timeline_df = timeline_frame(df_all, wear_col)

    #################################### Setting up dataframes for sleep, meditation, and wristband
    sleep_df = pd.DataFrame()
    if not df_sleep.empty:
        sleep_df = df_sleep.dropna(subset=["start", "stop"]).copy()
        if not sleep_df.empty:
            sleep_df["start"] = pd.to_datetime(sleep_df["start"], errors="coerce")
            sleep_df["stop"] = pd.to_datetime(sleep_df["stop"], errors="coerce")
            sleep_df.sort_values("start", inplace=True)
        
    meditation_df = pd.DataFrame() 
    if not df_meditation.empty:
        meditation_df = df_meditation.dropna(subset=["start", "stop"]).copy()
        if not meditation_df.empty:
            meditation_df["start"] = pd.to_datetime(meditation_df["start"], errors="coerce")
            meditation_df["stop"] = pd.to_datetime(meditation_df["stop"], errors="coerce")
            meditation_df.sort_values("start", inplace=True)

    if (isinstance(timeline_df, pd.DataFrame) and timeline_df.empty) and sleep_df.empty:
        return None

    has_sleep = not sleep_df.empty
    has_wrist = not timeline_df.empty if isinstance(timeline_df, pd.DataFrame) else False
    has_meditation = not meditation_df.empty
    rows = int(has_sleep) + int(has_wrist) + int(has_meditation)
    row_heights = [0.25, 0.25, 0.5] if has_sleep and has_meditation and has_wrist else [1.0]
    fig = make_subplots(
        rows=rows or 1,
        cols=1,
        shared_xaxes=True,
        row_heights=row_heights[: rows or 1],
        vertical_spacing=0.02,
    )

    ################################## Sleep data processing
    current_row = 1
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

            shapes.append(
                dict(
                    type="rect",
                    xref="x",
                    x0=start,
                    x1=stop,
                    yref="paper",
                    y0=row_center_y(row_heights, 0) - 0.025,
                    y1=row_center_y(row_heights, 0) + 0.025,
                    fillcolor="#1f77b4",
                    line=dict(width=0),
                )
            )

            mid = start + (stop - start) / 2
            hover_x.append(mid)
            try:
                start_iso = pd.to_datetime(start).isoformat()
                stop_iso = pd.to_datetime(stop).isoformat()
            except Exception:
                start_iso = str(start)
                stop_iso = str(stop)

            hover_text.append(f"Start: {start_iso}<br>Stop: {stop_iso}<br>Night: {row.get('night','')}")

        for shape in shapes:
            fig.add_shape(shape)

        if hover_x:
            fig.add_trace(
                go.Scatter(
                    x=hover_x,
                    y=[0.62] * len(hover_x),
                    mode="markers",
                    marker=dict(opacity=0, size=20),
                    hoverinfo="text",
                    hovertext=hover_text,
                    showlegend=False,
                ),
                row=current_row,
                col=1,
            )

            legend_extra = " (Dreem)" if any("dreem" in str(f).lower() for f in sdf.get("file", [])) else ""
            legend_text = f"Sleep{legend_extra}"


            fig.add_shape(
                dict(
                    type="circle",
                    xref="paper",
                    yref="paper",
                    x0=1.005,
                    x1=1.015,
                    y0=row_center_y(row_heights, 0) - 0.03,
                    y1=row_center_y(row_heights, 0) + 0.03,
                    fillcolor="#1f77b4",
                    line=dict(width=0),
                )
            )

            fig.add_annotation(
                dict(
                    xref="paper",
                    yref="paper",
                    x=1.02,
                    y=row_center_y(row_heights, 0),
                    xanchor="left",
                    yanchor="middle",
                    showarrow=False,
                    text=legend_text,
                    font=dict(size=11, color="#333"),
                )
            )

        fig.update_yaxes(visible=False, row=current_row, col=1)
        current_row += 1
        
    # add Meditation row (if present)
    if has_meditation:
        mdf = meditation_df.copy()
        m_shapes: list[dict] = []
        m_hover_x: list[pd.Timestamp] = []
        m_hover_text: list[str] = []
        for _, mrow in mdf.iterrows():
            mstart = mrow["start"]
            mstop = mrow["stop"]
            if pd.isna(mstart) or pd.isna(mstop):
                continue
            m_shapes.append(
                dict(
                    type="rect",
                    xref="x",
                    x0=mstart,
                    x1=mstop,
                    yref="paper",
                    y0=row_center_y(row_heights, 1) - 0.025,
                    y1=row_center_y(row_heights, 1) + 0.025,
                    fillcolor="#6cb5e9",    # blue-ish color for meditation
                    line=dict(width=0),
                )
            )
            mid = mstart + (mstop - mstart) / 2
            m_hover_x.append(mid)
            try:
                s_iso = pd.to_datetime(mstart).isoformat()
                e_iso = pd.to_datetime(mstop).isoformat()
            except Exception:
                s_iso = str(mstart)
                e_iso = str(mstop)
            m_hover_text.append(f"Start: {s_iso}<br>Stop: {e_iso}<br>Session: {mrow.get('session','')}")
        for sh in m_shapes:
            fig.add_shape(sh)
        if m_hover_x:
            fig.add_trace(
                go.Scatter(
                    x=m_hover_x,
                    y=[row_center_y(row_heights, 1)] * len(m_hover_x),
                    mode="markers",
                    marker=dict(opacity=0, size=20),
                    hoverinfo="text",
                    hovertext=m_hover_text,
                    showlegend=False,
                ),
                row=current_row,
                col=1,
            )
            
            legend_extra = " (Dreem)" if any("dreem" in str(f).lower() for f in sdf.get("file", [])) else ""
            legend_text = f"Meditation{legend_extra}"

            # small legend swatch for meditation
            fig.add_shape(
                dict(
                    type="circle",
                    xref="paper",
                    yref="paper",
                    x0=1.005,
                    x1=1.015,
                    y0=row_center_y(row_heights, 1) - 0.03,
                    y1=row_center_y(row_heights, 1) + 0.03,
                    fillcolor="#6cb5e9",
                    line=dict(width=0),
                )
            )
            fig.add_annotation(
                dict(
                    xref="paper",
                    yref="paper",
                    x=1.02,
                    y=row_center_y(row_heights, 1),
                    xanchor="left",
                    yanchor="middle",
                    showarrow=False,
                    text=legend_text,
                    font=dict(size=11, color="#333"),
                )
            )

        fig.update_yaxes(visible=False, row=current_row, col=1)
        current_row += 1
    

    ################################# Wristband data processing
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
                    colorbar=dict(
                        title="Wearing %",
                        thickness=10,
                        len=0.4,
                        y=0.2,
                        yanchor="middle",
                        x=1.02,
                        xanchor="left",
                        tickmode="array",
                        tickvals=[0, 100],
                        ticktext=["0%", "100%"],
                        tickfont=dict(size=10),
                    ),
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

    ################################# Layout update
    fig.update_layout(
        height=180 * (rows or 1),
        template="plotly_white",
        margin={"l": 60, "r": 80, "t": 30, "b": 40},
        hovermode="closest",
        hoverdistance=8,
        showlegend=False,
    )

    fig.update_xaxes(title_text="Time", row=(rows or 1), col=1)

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
            fig.update_xaxes(
                tickformat="%Y-%m-%d\n%H:%M",
                showgrid=True,
                tickangle=0,
                range=[tmin, tmax],
                row=r,
                col=1,
                type="date",
            )

    return fig


def render_overview_tab(df_all: pd.DataFrame, wear_col: str | None, df_sleep: pd.DataFrame, df_meditation: pd.DataFrame, df_subjective: pd.DataFrame) -> None:
    st.header("Data Overview")
    st.subheader("Combined Timeline: Wristband + Sleep + Meditation + Subjective")
    combined = build_combined_overview(df_all, wear_col, df_sleep, df_meditation, df_subjective)
    if combined:
        st.plotly_chart(combined, use_container_width=True)
    else:
        st.info("No timeline data available to plot a combined view.")


__all__ = ["build_combined_overview", "render_overview_tab"]
