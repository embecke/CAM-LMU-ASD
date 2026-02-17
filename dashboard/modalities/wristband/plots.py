from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.config import WEARING_COLOR_MAP, WEARING_LABELS


def plot_wristband_stacked(hours_per_bin: pd.DataFrame) -> go.Figure:
    figure = go.Figure()

    for label in WEARING_LABELS[::-1]:
        figure.add_trace(
            go.Bar(
                x=hours_per_bin["Day"],
                y=hours_per_bin[label],
                name=label,
                marker_color=WEARING_COLOR_MAP[label],
            )
        )

    figure.update_layout(
        barmode="stack",
        yaxis={"range": [0, 24]},
        xaxis_title="Day",
        yaxis_title="Hours",
        title="Stacked Hours of Wearing Detection per Day",
        height=420,
    )
    return figure


def plot_wristband_timeline(df_all: pd.DataFrame, wear_col: str) -> go.Figure:
    return px.scatter(
        df_all,
        x="datetime",
        y=wear_col,
        color="day_folder",
        labels={wear_col: "Wearing"},
        title="Wearing Detection Events (All Days)",
    )


__all__ = [
    "plot_wristband_stacked",
    "plot_wristband_timeline",
]
