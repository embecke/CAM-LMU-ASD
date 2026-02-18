from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

############# Subjective Data Plots #############   
def plot_subjective_timeline(df_subjective: pd.DataFrame) -> go.Figure:
    """Horizontal timeline of subjective recordings shown on a single row.

    Render blue rectangular segments for recording intervals using layout
    shapes so gaps remain empty. Add invisible scatter points at the
    midpoint of each recording to provide hover text.
    """
    df_plot = df_subjective.dropna(subset=["recording_date"]).copy()
    if df_plot.empty:
        return go.Figure()

    df_plot["recording_date"] = pd.to_datetime(df_plot["recording_date"], errors="coerce")
    df_plot.sort_values("recording_date", inplace=True)

    # choose label column for y axis
    label_col = "section" if "section" in df_plot.columns else ("file" if "file" in df_plot.columns else None)
    if label_col is None:
        df_plot = df_plot.reset_index().rename(columns={"index": "record"})
        label_col = "record"

    # prepare recording_date strings for hover
    df_plot["_date_str"] = pd.to_datetime(df_plot["recording_date"]).dt.strftime("%Y-%m-%d %H:%M")

    fig = go.Figure()
    # Color mapping: two browns for diaries (sleep/activity), two oranges for TET (diary/meditation)
    brown_shades = ["#854515", "#A3651F"]
    orange_shades = ["#DF6304", "#FF8827"]
    color_map = {
        "sleep_diary": brown_shades[0],
        "activity_diary": brown_shades[1],
        "tet_diary": orange_shades[0],
        "tet_meditation": orange_shades[1],
    }

    # derive per-point colors based on the section value
    point_colors = [color_map.get(s, "grey") for s in df_plot["section"]]

    fig.add_trace(
        go.Scatter(
            x=df_plot["recording_date"],
            y=df_plot[label_col].astype(str),
            mode="markers",
            marker=dict(color=point_colors, size=10),
            hovertemplate=(
                f"%{{y}}<br>Recording Date: %{{x|%Y-%m-%d %H:%M}}<extra></extra>"
            ),
            showlegend=False,
        )
    )

    # layout
    row_count = max(1, len(df_plot))
    height = min(600, 40 * row_count + 120)
    fig.update_layout(
        title="Subjective Recordings Timeline",
        xaxis_title="Recording Date",
        yaxis_title=None,
        template="plotly_white",
        height=height,
        margin=dict(l=40, r=40, t=80, b=40),
    )

    return fig