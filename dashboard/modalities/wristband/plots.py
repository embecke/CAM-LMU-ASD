from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.config import WEARING_COLOR_MAP, WEARING_LABELS


def availability_timeline_figure(df_timeline: pd.DataFrame, wear_col: str) -> go.Figure:
    figure = px.scatter(
        df_timeline,
        x="datetime",
        y="timeline_y",
        color=wear_col,
        color_continuous_scale=["#ff4136", "#ffe066", "#b6e63e", "#2ecc40"],
        labels={wear_col: "Wearing %"},
        title="Wristband Wearing Detection Timeline",
        height=170,
    )
    figure.update_traces(marker={"size": 6})
    figure.update_layout(
        yaxis={"showticklabels": False, "showgrid": False, "zeroline": False, "title": None},
        xaxis_title="Date/Time",
        coloraxis_colorbar={"title": "Wearing %"},
        margin={"l": 20, "r": 20, "t": 45, "b": 20},
    )
    return figure


def stacked_hours_figure(hours_per_bin: pd.DataFrame) -> go.Figure:
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


def detailed_events_figure(df_all: pd.DataFrame, wear_col: str) -> go.Figure:
    return px.scatter(
        df_all,
        x="datetime",
        y=wear_col,
        color="day_folder",
        labels={wear_col: "Wearing"},
        title="Wearing Detection Events (All Days)",
    )


def generic_aggregated_biomarker_figure(df: pd.DataFrame, selected_cols: list[str]) -> go.Figure:
    figure = go.Figure()
    for column in selected_cols:
        figure.add_trace(
            go.Scatter(
                x=list(range(len(df))),
                y=df[column],
                mode="lines",
                name=column,
                line={"width": 1},
            )
        )

    figure.update_layout(
        title="Wristband Biomarkers - Aggregated File",
        xaxis_title="Time (minutes)",
        yaxis_title="Value",
        height=500,
        template="plotly_white",
        hovermode="x unified",
    )
    return figure
