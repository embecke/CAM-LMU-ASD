from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.modalities.wristband.processing import timeline_frame
from dashboard.modalities.subjective.plots import plot_subjective_timeline

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

    # Build a fixed 4-row layout (each takes a quarter of the figure):
    # 1: Subjective, 2: Meditation, 3: Sleep, 4: Wristband
    rows = 4
    row_heights = [0.25, 0.25, 0.25, 0.25]
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=-0,
    )

    # flags for which data are present (used later)
    has_sleep = not sleep_df.empty
    has_meditation = not meditation_df.empty
    has_wrist = not timeline_df.empty if isinstance(timeline_df, pd.DataFrame) else False

    ################################## Sleep data processing
    # Subjective row (row 1)
    current_row = 1
    sdf_subjective = pd.DataFrame()
    if not df_subjective.empty:
        sdf_subjective = df_subjective.dropna(subset=["recording_date"]).copy()
    if not sdf_subjective.empty:
        sdf = sdf_subjective.copy()
        sdf["recording_date"] = pd.to_datetime(sdf["recording_date"], errors="coerce")
        sdf.sort_values("recording_date", inplace=True)

        # color mapping consistent with subjective plots
        brown_shades = ["#854515", "#A3651F"]
        orange_shades = ["#DF6304", "#FF8827"]
        color_map = {
            "sleep_diary": brown_shades[0],
            "activity_diary": brown_shades[1],
            "tet_diary": orange_shades[0],
            "tet_meditation": orange_shades[1],
        }
        # determine present sections in order of appearance
        present_sections: list[str] = []
        for sec in sdf.get("section", []):
            sec_label = str(sec) if not pd.isna(sec) else "unknown"
            if sec_label in present_sections:
                continue
            present_sections.append(sec_label)

        # draw one horizontal marker trace per present section, stacked within the subjective row
        n_pres = len(present_sections)
        base_y = row_center_y(row_heights, 0)
        dy = 0.04 if n_pres <= 4 else 0.03
        for idx, sec_label in enumerate(present_sections):
            # pick color
            color = color_map.get(sec_label, "grey")
            # select rows matching this section (handle NaN as 'unknown')
            if sec_label == "unknown":
                sdf_sec = sdf[pd.isna(sdf.get("section"))].copy()
            else:
                sdf_sec = sdf[sdf.get("section") == sec_label].copy()
            if sdf_sec.empty:
                continue
            y_pos = base_y + (idx - (n_pres - 1) / 2) * dy
            fig.add_trace(
                go.Scatter(
                    x=sdf_sec["recording_date"],
                    y=[y_pos] * len(sdf_sec),
                    mode="markers",
                    marker=dict(color=color, size=8),
                    hovertemplate=(
                        f"{sec_label}<br>Recording Date: %{{x|%Y-%m-%d %H:%M}}<extra></extra>"
                    ),
                    name=sec_label,
                    showlegend=False,
                ),
                row=current_row,
                col=1,
            )

        # Create legend proxy shapes+annotations per unique section so legend colors match markers
        n = len(present_sections)
        if n:
            dy_legend = 0.04
            for i, sec_label in enumerate(present_sections):
                color = color_map.get(sec_label, "grey")
                y_center = base_y + (i - (n - 1) / 2) * dy_legend
                # draw a true circle in paper coordinates (equal width and height)
                center_x = 1.01
                half = 0.005
                # use a Unicode dot annotation as a swatch so it's rendered as a perfect circle
                fig.add_annotation(
                    dict(
                        xref="paper",
                        yref="paper",
                        x=1.01,
                        y=y_center,
                        xanchor="center",
                        yanchor="middle",
                        showarrow=False,
                        text="●",
                        font=dict(size=18, color=color),
                    )
                )
                fig.add_annotation(
                    dict(
                        xref="paper",
                        yref="paper",
                        x=1.03,
                        y=y_center,
                        xanchor="left",
                        yanchor="middle",
                        showarrow=False,
                        text=sec_label,
                        font=dict(size=11, color="#333"),
                    )
                )

        fig.update_yaxes(visible=False, row=current_row, col=1)
        # wristband label intentionally removed
    else:
        fig.update_yaxes(visible=False, row=current_row, col=1)
    current_row += 1

    # Meditation (row 2)
    if not meditation_df.empty:
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
                    fillcolor="#6cb5e9",
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


        # Add a small legend swatch centered on the meditation subplot
        y_med = row_center_y(row_heights, 1)
        # meditation legend swatch (dot glyph)
        fig.add_annotation(
            dict(
                xref="paper",
                yref="paper",
                x=1.01,
                y=y_med,
                xanchor="center",
                yanchor="middle",
                showarrow=False,
                text="●",
                font=dict(size=18, color="#6cb5e9"),
            )
        )
        fig.add_annotation(
            dict(
                xref="paper",
                yref="paper",
                x=1.03,
                y=y_med,
                xanchor="left",
                yanchor="middle",
                showarrow=False,
                text="Meditation",
                font=dict(size=11, color="#333"),
            )
        )

        fig.update_yaxes(visible=False, row=current_row, col=1)
    current_row += 1

    ################################# Sleep data processing (row 3)
    if not sleep_df.empty:
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
                    y0=row_center_y(row_heights, 2) - 0.025,
                    y1=row_center_y(row_heights, 2) + 0.025,
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
                    y=[row_center_y(row_heights, 2)] * len(hover_x),
                    mode="markers",
                    marker=dict(opacity=0, size=20),
                    hoverinfo="text",
                    hovertext=hover_text,
                    showlegend=False,
                ),
                row=current_row,
                col=1,
            )

        # Add a small legend swatch centered on the sleep subplot
        y_sleep = row_center_y(row_heights, 2)
        # sleep legend swatch (dot glyph)
        fig.add_annotation(
            dict(
                xref="paper",
                yref="paper",
                x=1.01,
                y=y_sleep,
                xanchor="center",
                yanchor="middle",
                showarrow=False,
                text="●",
                font=dict(size=18, color="#1f77b4"),
            )
        )
        fig.add_annotation(
            dict(
                xref="paper",
                yref="paper",
                x=1.03,
                y=y_sleep,
                xanchor="left",
                yanchor="middle",
                showarrow=False,
                text="Sleep",
                font=dict(size=11, color="#333"),
            )
        )

        fig.update_yaxes(visible=False, row=current_row, col=1)

    ################################# Wristband data processing (row 4)
    current_row += 1
    if has_wrist:
        fig.add_trace(
            go.Scatter(
                x=timeline_df["datetime"],
                y=[row_center_y(row_heights, 3)] * len(timeline_df),
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
                        len=0.2,
                        y=0.1,
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
        height=180 * rows,
        template="plotly_white",
        margin={"l": 120, "r": 120, "t": 30, "b": 40},
        hovermode="closest",
        hoverdistance=8,
        showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.95),
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

        # collect per-day ticks from available data (normalize to dates)
        date_vals: list[pd.Timestamp] = []
        try:
            if has_wrist and not timeline_df.empty:
                date_vals += pd.to_datetime(timeline_df["datetime"]).dt.normalize().dropna().unique().tolist()
        except Exception:
            pass
        try:
            if not sleep_df.empty:
                date_vals += pd.to_datetime(sleep_df["start"]).dt.normalize().dropna().unique().tolist()
                date_vals += pd.to_datetime(sleep_df["stop"]).dt.normalize().dropna().unique().tolist()
        except Exception:
            pass
        try:
            if not meditation_df.empty:
                date_vals += pd.to_datetime(meditation_df["start"]).dt.normalize().dropna().unique().tolist()
                date_vals += pd.to_datetime(meditation_df["stop"]).dt.normalize().dropna().unique().tolist()
        except Exception:
            pass
        try:
            if not df_subjective.empty and "recording_date" in df_subjective.columns:
                date_vals += pd.to_datetime(df_subjective["recording_date"]).dt.normalize().dropna().unique().tolist()
        except Exception:
            pass

        # build unique sorted tick list as date strings (normalize to UTC) to avoid tz-aware/naive comparisons
        tick_dates = sorted({pd.to_datetime(d, utc=True).normalize().strftime("%Y-%m-%d") for d in date_vals})
        if not tick_dates:
            tick_dates = [pd.to_datetime(tmin, utc=True).normalize().strftime("%Y-%m-%d"), pd.to_datetime(tmax, utc=True).normalize().strftime("%Y-%m-%d")]

        # hide tick labels for all rows, then enable/display rotated labels on bottom row only
        for r in range(1, rows + 1):
            fig.update_xaxes(
                showticklabels=False,
                showgrid=True,
                range=[tmin, tmax],
                row=r,
                col=1,
                type="date",
            )

        # bottom row: show every day and rotate labels for readability
        fig.update_xaxes(
            tickformat="%Y-%m-%d",
            tickmode="array",
            tickvals=tick_dates,
            tickangle=45,
            showticklabels=True,
            row=rows,
            col=1,
            type="date",
        )

        # Add alternating day background shading (light grey) across the entire plot area
        try:
            start_day = pd.to_datetime(tmin).normalize()
            end_day = pd.to_datetime(tmax).normalize()
            days = pd.date_range(start=start_day, end=end_day, freq="D")
            for i, d in enumerate(days):
                if i % 2 == 0:
                    x0 = d.isoformat()
                    x1 = (d + pd.Timedelta(days=1)).isoformat()
                    fig.add_shape(
                        dict(
                            type="rect",
                            xref="x",
                            yref="paper",
                            x0=x0,
                            x1=x1,
                            y0=0,
                            y1=1,
                            fillcolor="rgba(200,200,200,0.08)",
                            line=dict(width=0),
                            layer="below",
                        )
                    )
        except Exception:
            pass

        # Add left-side subplot titles (centered vertically at each row)
        try:
            titles = ["Subjective", "Meditation EEG", "Sleep EEG", "Wristband"]
            for idx, title in enumerate(titles):
                y_pos = row_center_y(row_heights, idx)
                fig.add_annotation(
                    dict(
                        xref="paper",
                        yref="paper",
                        x=0,
                        xshift=-20,
                        y=y_pos,
                        xanchor="right",
                        yanchor="middle",
                        showarrow=False,
                        text=f"<b>{title}</b>",
                        font=dict(size=12, color="#111"),
                    )
                )
        except Exception:
            pass

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
