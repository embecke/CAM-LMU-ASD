from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

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



def plot_subjective_availability_heatmap(
    df_subjective: pd.DataFrame,
    date_col: str = "recording_date",
) -> go.Figure:
    """Heatmap showing per-day availability of subjective records.
    Missing days appear as 0 and are colored distinctly so gaps are easy to spot.
    """
    if df_subjective is None or df_subjective.empty:
        return go.Figure()

    # for availability by data source, use the 'section' values and show
    # exactly these four rows (sources) so users can easily see which
    # subjective instrument has data per day
    sources = ["sleep_diary", "activity_diary", "tet_diary", "tet_meditation"]

    df = df_subjective.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    if df.empty:
        return go.Figure()
    # normalize to date (midnight) so grouping is by calendar day
    # prefer matched_date if available (computed in processing), otherwise use recording datetime
    if "matched_date" in df.columns:
        df["_date"] = pd.to_datetime(df["matched_date"], errors="coerce").dt.normalize()
    else:
        df["_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()

    if df_subjective is None or df_subjective.empty:
        return go.Figure()

    # full date range (inclusive)
    min_date = df["_date"].min()
    max_date = df["_date"].max()
    date_index = pd.date_range(start=min_date, end=max_date, freq="D")

    # normalize section values to canonical source keys (keep identical logic as other plots)
    def _normalize_section(s: object) -> str:
        if pd.isna(s):
            return ""
        low = str(s).lower()
        if "sleep" in low:
            return "sleep_diary"
        if "activity" in low:
            return "activity_diary"
        if "meditation" in low:
            return "tet_meditation"
        if "tet" in low:
            return "tet_diary"
        return str(s)

    if "section" not in df.columns:
        df["section"] = ""
    df["section"] = df["section"].apply(_normalize_section)

    # ensure color_int exists; derive from textual color if necessary
    color_text_to_int = {"white": 0, "grey": 1, "gray": 1, "green": 2, "red": 3}
    rev_color = {0: "grey", 1: "grey", 2: "green", 3: "red"}  # map 0->grey for display

    if "color_int" in df.columns:
        df["color_int"] = pd.to_numeric(df["color_int"], errors="coerce")
    elif "color" in df.columns:
        df["color_int"] = (
            df["color"].fillna("white").astype(str).str.lower().map(lambda s: color_text_to_int.get(s, 0))
        )
    else:
        df["color_int"] = 0

    # Build explicit grids from dataframe rows so hover shows the exact `color` cell.
    # Initialize with defaults (grey / 1)
    label_grid = pd.DataFrame("grey", index=sources, columns=date_index)
    int_grid = pd.DataFrame(1, index=sources, columns=date_index)

    # fill grids from dataframe rows
    for _, row in df.iterrows():
        sec = row.get("section", "")
        dt = row.get("_date")
        if pd.isna(dt) or sec not in sources:
            continue
        # ensure dt is normalized Timestamp matching our columns
        dt = pd.to_datetime(dt).normalize()
        if dt not in date_index:
            continue
        # textual label from dataframe if present, else map from color_int
        if "color" in row and pd.notna(row.get("color")):
            label = str(row.get("color"))
        else:
            val = int(row.get("color_int") if pd.notna(row.get("color_int")) else 1)
            label = rev_color.get(val, "grey")
        int_val = int(row.get("color_int") if pd.notna(row.get("color_int")) else color_text_to_int.get(label.lower(), 1))
        label_grid.at[sec, dt] = label
        int_grid.at[sec, dt] = int_val

    # convert grids to numpy arrays for plotting
    z = int_grid.values.astype(int)
    custom = label_grid.values.astype(object)

    x_labels = [d.strftime("%Y-%m-%d") for d in date_index]
    y_labels = sources

    # colorscale: map 0/1->grey, 2->green, 3->red
    colorscale = [
        [0.0, "#ffffff"],
        [1 / 3, "#bfbfbf"],
        [2 / 3, "#2ca02c"],
        [1.0, "#d62728"],
    ]

    hovertemplate = "%{y}<br>%{x}<br>Color: %{customdata}<extra></extra>"

    fig = go.Figure(
        data=[
            go.Heatmap(
                z=z,
                x=x_labels,
                y=y_labels,
                customdata=custom,
                hovertemplate=hovertemplate,
                colorscale=colorscale,
                zmin=0,
                zmax=3,
                zauto=False,
                showscale=True,
                colorbar=dict(
                    tickmode="array",
                    tickvals=[1, 2, 3],
                    ticktext=[ "expected missing", "has data", "missing"],
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



def plot_subjective_simple_heatmap(
    df_subjective: pd.DataFrame,
    date_col: str = "recording_date",
) -> go.Figure:
    """Per-day subjective availability heatmap with 3 states:
    0 = expected no data, 1 = data available, 2 = data missing.
    """
    if df_subjective is None or df_subjective.empty:
        return go.Figure()

    sources = ["sleep_diary", "activity_diary", "tet_diary", "tet_meditation"]
    df = df_subjective.copy()
    
    print(df_subjective.columns)

    # Date normalization (prefer matched_date when present)
    if "matched_date" in df.columns:
        df["_date"] = pd.to_datetime(df["matched_date"], errors="coerce").dt.normalize()
    else:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df["_date"] = df[date_col].dt.normalize()

    df = df.dropna(subset=["_date"])
    if df.empty:
        return go.Figure()

    # Normalize section values first (before any filtering/grouping)
    def _normalize_section(s: object) -> str:
        if pd.isna(s):
            return ""
        low = str(s).lower()
        if "sleep" in low:
            return "sleep_diary"
        if "activity" in low:
            return "activity_diary"
        if "meditation" in low:
            return "tet_meditation"
        if "tet" in low:
            return "tet_diary"
        return str(s)

    if "section" not in df.columns:
        df["section"] = ""
    df["section"] = df["section"].apply(_normalize_section)
    df = df[df["section"].isin(sources)]
    if df.empty:
        return go.Figure()

    # Helpers for robust bool parsing
    def _to_bool(v: object) -> bool:
        if pd.isna(v):
            return False
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in {"1", "true", "t", "yes", "y"}
    
    print(df["matched_date"])


    # Build full date range
    min_date = df["matched_date"].min()
    max_date = df["matched_date"].max()
    date_index = pd.date_range(start=min_date, end=max_date, freq="D")
    
    z_new = np.zeros((len(sources), len(date_index)), dtype=int)  # default to 0 (expected no data)
    
    for i, source in enumerate(sources):
        for j, date in enumerate(date_index):
            # print(source, date)
            match = df[(df["section"] == source) & (df["matched_date"] == date)]
            
            
            if match.empty:
                print("No match for", source, date)
                z_new[i, j] = 3  # expected no data
            else:
                row = match.iloc[0]  # take the first matching row
                # print("Match found:", row["section"], row["_date"], row["expected"], row["color_int"])
            # print(row[0:5])
                z_new[i, j] = row["color_int"] # default to expected no data
    print("z_new:")
    print(z_new)
    # Aggregate per (section, date):
    # expected_any: at least one row says data expected
    # has_any: at least one row has data
    grouped = (
        df.groupby(["section", "_date"], as_index=False)
        .agg(
            expected_any=("expected", lambda s: any(_to_bool(v) for v in s) if "expected" in df.columns else False),
            has_any=("has_data", lambda s: any(_to_bool(v) for v in s) if "has_data" in df.columns else False),
        )
    )

    # State encoding:
    # 0 expected no data, 1 data available, 2 data missing
    grouped["state"] = np.where(
        ~grouped["expected_any"],
        0,
        np.where(grouped["has_any"], 1, 2),
    )

    # Initialize grid to "expected no data"
    state_grid = pd.DataFrame(0, index=sources, columns=date_index, dtype=int)
    for _, row in grouped.iterrows():
        state_grid.at[row["section"], row["_date"]] = int(row["state"])

    z = state_grid.values
    print(z)
    x_labels = [d.strftime("%Y-%m-%d") for d in date_index]
    y_labels = sources

    state_label = np.array(["expected no data", "data available", "data missing"], dtype=object)
    custom = state_label[z]

    # 3-state colorscale: white, green, red
    colorscale = [
        [0.0, "#ffffff"],   # expected no data
        [0.5, "#2ca02c"],   # data available
        [1.0, "#d62728"],   # data missing
    ]

    fig = go.Figure(
        data=[
            go.Heatmap(
                z=[[1,2,3,1,1,2,3,1,1,2,3,1,1,2,3,1,],
                   [1,1,1,1,2,2,2,1,1,1,1,1,2,2,2,1],
                    [1,1,1,1,1,1,1,2,2,2,1,1,1,1,1,1],
                    [1,1,1,1,1,1,1,1,1,2,2,2,1,1,1,1],],
                x=x_labels,
                y=y_labels,
                customdata=custom,
                hovertemplate="%{y}<br>%{x}<br>Status: %{customdata}<extra></extra>",
                colorscale=colorscale,
                zmin=1,
                zmax=3,
                zauto=False,
                colorbar=dict(
                    tickmode="array",
                    tickvals=[0, 1, 2],
                    ticktext=["expected no data", "data available", "data missing"],
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

    fig.update_xaxes(tickangle=45, nticks=15 if len(x_labels) > 40 else None)
    return fig