from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def sleep_duration(df_sleep: pd.DataFrame) -> go.Figure:
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

def sleep_availability_overview(df_sleep: pd.DataFrame) -> go.Figure:
    """Compact availability overview shown on one horizontal row.

    Uses the same single-row layout as `sleep_recording_timeline` but kept
    as a separate helper for overview contexts.
    """
    df_plot = df_sleep.dropna(subset=["start", "stop"]).copy()
    if df_plot.empty:
        return go.Figure()

    df_plot["start"] = pd.to_datetime(df_plot["start"], errors="coerce")
    df_plot["stop"] = pd.to_datetime(df_plot["stop"], errors="coerce")
    df_plot.sort_values("start", inplace=True)
    df_plot["_row"] = "recordings"

    fig = go.Figure()
    shapes = []
    hover_x = []
    hover_text = []
    for _, row in df_plot.iterrows():
        start = row["start"]
        stop = row["stop"]
        if pd.isna(start) or pd.isna(stop):
            continue

        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="paper",
                x0=start,
                x1=stop,
                y0=0.4,
                y1=0.6,
                fillcolor="#1f77b4",
                line=dict(width=0),
            )
        )

        mid = start + (stop - start) / 2
        hover_x.append(mid)
        hover_text.append(f"Night: {row.get('night', '')}<br>File: {row.get('file', '')}<br>Duration: {row.get('duration_hours', ''):.2f} h")

    fig.update_layout(shapes=shapes)

    if hover_x:
        fig.add_trace(
            go.Scatter(
                x=hover_x,
                y=[0.5] * len(hover_x),
                mode="markers",
                marker=dict(opacity=0, size=20),
                hoverinfo="text",
                hovertext=hover_text,
                showlegend=False,
            )
        )

    fig.update_yaxes(visible=False)
    fig.update_xaxes(title_text="Time", tickformat="%Y-%m-%d\n%H:%M")
    fig.update_layout(height=120, margin={"l": 60, "r": 20, "t": 30, "b": 30}, template="plotly_white")

    return fig


def sleep_recordings_overview(
    df_sleep: pd.DataFrame,
    show_timeline: bool = True,
    height: int = 300,
    legend_x: float = 1.02,
    legend_y: float = 0.5,
) -> go.Figure:
    """Overview plot: all nights on a single horizontal row with legend on the right.

    If `show_timeline` is True a shared x-axis timeline is added as a second
    (small) subplot row to provide a consistent bottom timeline that can be
    aligned with other modalities (e.g. wristband overview).
    """
    df_plot = df_sleep.dropna(subset=["start", "stop"]).copy()
    if df_plot.empty:
        return go.Figure()

    df_plot.sort_values("start", inplace=True)
    # single row value so all bars line up
    df_plot["_row"] = "recordings"

    # top: bars (one row) colored by night
    top = px.timeline(
        df_plot,
        x_start="start",
        x_end="stop",
        y="_row",
        color="night" if "night" in df_plot.columns else "file",
        hover_data={"file": True, "duration_hours": ":.2f"},
        title="Sleep EEG Overview (all nights)",
    )

    # create subplots: top = bars, bottom = compact timeline axis
    rows = 2 if show_timeline else 1
    row_heights = [0.78, 0.22] if show_timeline else [1.0]
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=row_heights, vertical_spacing=0.02)

    # move top traces into subplot row 1
    for trace in top.data:
        fig.add_trace(trace, row=1, col=1)

    # bottom: small timeline built from start/stop markers (invisible markers,
    # only x-axis ticks/labels are used). This ensures a consistent datetime
    # axis that can be shared across modalities.
    if show_timeline:
        times = sorted({pd.to_datetime(t) for t in pd.concat([df_plot["start"], df_plot["stop"]]).tolist()})
        # invisible markers to force x-axis tick placement
        fig.add_trace(
            go.Scatter(
                x=times,
                y=[0] * len(times),
                mode="markers",
                marker=dict(opacity=0),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=2,
            col=1,
        )

    # layout tweaks: legend on the right, tidy margins, white template
    fig.update_layout(
        height=height,
        template="plotly_white",
        margin={"l": 60, "r": 140, "t": 50, "b": 40},
        legend=dict(title="Night", orientation="v", x=legend_x, y=legend_y),
    )

    # hide y-axis labels (single row)
    fig.update_yaxes(visible=False, row=1, col=1)
    if show_timeline:
        fig.update_yaxes(visible=False, row=2, col=1)

    # keep a compact x-axis label
    fig.update_xaxes(title_text="Time", row=rows, col=1)

    return fig
