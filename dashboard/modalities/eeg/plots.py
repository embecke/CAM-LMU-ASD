from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


############# Sleep EEG Plots #############
def plot_sleep_duration(df_sleep: pd.DataFrame) -> go.Figure:
    """Horizontal timeline of sleep EEG recordings shown on a single row.

    Render blue rectangular segments for recording intervals using layout
    shapes so gaps remain empty. Add invisible scatter points at the
    midpoint of each recording to provide hover text.
    """
    df_plot = df_sleep.dropna(subset=["start", "stop"]).copy()
    if df_plot.empty:
        return go.Figure()

    df_plot["start"] = pd.to_datetime(df_plot["start"], errors="coerce")
    df_plot["stop"] = pd.to_datetime(df_plot["stop"], errors="coerce")
    df_plot.sort_values("start", inplace=True)

    # compute durations in hours
    df_plot["duration_hours"] = (df_plot["stop"] - df_plot["start"]).dt.total_seconds() / 3600.0
    df_plot = df_plot.sort_values("start")

    # choose label column for y axis
    label_col = "night" if "night" in df_plot.columns else ("file" if "file" in df_plot.columns else None)
    if label_col is None:
        df_plot = df_plot.reset_index().rename(columns={"index": "record"})
        label_col = "record"

    # prepare start/stop strings for hover
    df_plot["_start_str"] = pd.to_datetime(df_plot["start"]).dt.strftime("%Y-%m-%d %H:%M")
    df_plot["_stop_str"] = pd.to_datetime(df_plot["stop"]).dt.strftime("%Y-%m-%d %H:%M")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_plot["duration_hours"],
            y=df_plot[label_col].astype(str),
            orientation="h",
            marker=dict(color="#1f77b4"),
            hovertemplate=(
                f"%{{y}}<br>Duration: %{{x:.2f}} h<br>Start: %{{customdata[0]}}<br>Stop: %{{customdata[1]}}<extra></extra>"
            ),
            customdata=df_plot[["_start_str", "_stop_str"]].values,
            showlegend=False,
        )
    )

    # layout
    row_count = max(1, len(df_plot))
    height = min(600, 40 * row_count + 120)
    fig.update_layout(
        title="Sleep Duration per Night",
        xaxis_title="Duration (hours)",
        yaxis_title=None,
        template="plotly_white",
        height=height,
        margin={"l": 160, "r": 40, "t": 60, "b": 60},
    )

    # show most recent at top
    fig.update_yaxes(autorange="reversed")

    return fig


############## Meditation EEG Plots #############
def plot_meditation_duration(df_meditation: pd.DataFrame) -> go.Figure:
    """Horizontal timeline of meditation EEG recordings shown on a single row.
    Add invisible scatter points at the
    midpoint of each recording to provide hover text.
    """
    df_plot = df_meditation.dropna(subset=["start", "stop"]).copy()
    if df_plot.empty:
        return go.Figure()

    df_plot["start"] = pd.to_datetime(df_plot["start"], errors="coerce")
    df_plot["stop"] = pd.to_datetime(df_plot["stop"], errors="coerce")
    df_plot.sort_values("start", inplace=True)

    # compute durations in hours
    df_plot["duration_hours"] = (df_plot["stop"] - df_plot["start"]).dt.total_seconds() / 3600.0
    df_plot = df_plot.sort_values("start")

    # choose label column for y axis
    label_col = "session" if "session" in df_plot.columns else ("file" if "file" in df_plot.columns else None)
    if label_col is None:
        df_plot = df_plot.reset_index().rename(columns={"index": "record"})
        label_col = "record"

    # prepare start/stop strings for hover
    df_plot["_start_str"] = pd.to_datetime(df_plot["start"]).dt.strftime("%Y-%m-%d %H:%M")
    df_plot["_stop_str"] = pd.to_datetime(df_plot["stop"]).dt.strftime("%Y-%m-%d %H:%M")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_plot["duration_hours"],
            y=df_plot[label_col].astype(str),
            orientation="h",
            marker=dict(color="#6cb5e9"),
            hovertemplate=(
                f"%{{y}}<br>Duration: %{{x:.2f}} h<br>Start: %{{customdata[0]}}<br>Stop: %{{customdata[1]}}<extra></extra>"
            ),
            customdata=df_plot[["_start_str", "_stop_str"]].values,
            showlegend=False,
        )
    )

    # layout
    row_count = max(1, len(df_plot))
    height = min(600, 40 * row_count + 120)
    fig.update_layout(
        title="Meditation Duration per Session",
        xaxis_title="Duration (hours)",
        yaxis_title=None,
        template="plotly_white",
        height=height,
        margin={"l": 160, "r": 40, "t": 60, "b": 60},
    )

    # show most recent at top
    fig.update_yaxes(autorange="reversed")

    return fig


__all__ = [
    "plot_sleep_duration",
    "plot_meditation_duration",
]
