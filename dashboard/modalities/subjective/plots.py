from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import numpy as np

############# Subjective Data Plots #############   

def plot_subjective_availability_heatmap(
    df_subjective: pd.DataFrame,
    date_col: str = "recording_date",
) -> go.Figure:
    """Heatmap showing per-day availability of subjective records."""
    if df_subjective is None or df_subjective.empty:
        return go.Figure()

    sources = ["sleep_diary", "activity_diary", "tet_diary", "tet_meditation"]

    df = df_subjective.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    if df.empty:
        return go.Figure()

    # normalize to calendar days; prefer matched_date if available
    date_source = "matched_date" if "matched_date" in df.columns else date_col
    df["_date"] = pd.to_datetime(df[date_source], errors="coerce").dt.normalize()
    df = df.dropna(subset=["_date"])
    if df.empty:
        return go.Figure()

    # full date range (inclusive)
    min_date = df["_date"].min()
    max_date = df["_date"].max()
    date_index = pd.date_range(start=min_date, end=max_date, freq="D")

    def _normalize_section(value: object) -> str:
        if pd.isna(value):
            return ""
        text = str(value).lower()
        if "sleep" in text:
            return "sleep_diary"
        if "activity" in text:
            return "activity_diary"
        if "meditation" in text:
            return "tet_meditation"
        if "tet" in text:
            return "tet_diary"
        return str(value)

    if "section" not in df.columns:
        df["section"] = ""
    df["section"] = df["section"].apply(_normalize_section)
    df = df[df["section"].isin(sources)]
    if df.empty:
        return go.Figure()

    df["has_data"] = 1
    availability = (
        df.pivot_table(index="section", columns="_date", values="has_data", aggfunc="max", fill_value=0)
        .reindex(index=sources, fill_value=0)
        .reindex(columns=date_index, fill_value=0)
    )

    z = availability.values.astype(int)
    custom = np.where(z == 1, "Available", "No data")

    x_labels = [d.strftime("%Y-%m-%d") for d in date_index]
    y_labels = availability.index.tolist()

    colorscale = [
        [0.0, "#bfbfbf"],
        [0.5, "#bfbfbf"],
        [0.5, "#2ca02c"],
        [1.0, "#2ca02c"],
    ]

    fig = go.Figure(
        data=[
            go.Heatmap(
                z=z,
                x=x_labels,
                y=y_labels,
                customdata=custom,
                hovertemplate="%{y}<br>%{x}<br>%{customdata}<extra></extra>",
                colorscale=colorscale,
                zmin=0,
                zmax=1,
                showscale=True,
                colorbar=dict(
                    tickmode="array",
                    tickvals=[0.25, 0.75],
                    ticktext=["No data", "Available"],
                ),
                xgap=1,
                ygap=1,
            )
        ]
    )

    fig.update_layout(
        title="Subjective Data Availability (per day)",
        xaxis_title="Date",
        yaxis_title="Source",
        template="plotly_white",
        height=min(900, 40 * max(1, len(y_labels)) + 200),
        margin=dict(l=100, r=40, t=80, b=120),
    )

    # make x tick labels sparser if many days
    if len(x_labels) > 40:
        fig.update_xaxes(tickangle=45, nticks=15)
    else:
        fig.update_xaxes(tickangle=45)

    return fig