# Dashboard Modularization Guide

## Objectives
- Separate data processing from UI rendering.
- Organize code by modality/source so each stream can evolve independently.
- Keep `participant_dashboard.py` as a stable Streamlit entrypoint.
- Enable gradual expansion (Sleep, TET, additional wearables) without a full rewrite.

## New Layout
- `participant_dashboard.py`: thin launcher that calls `dashboard.app.run_dashboard()`.
- `dashboard/app.py`: Streamlit orchestration layer (sidebar, tabs, high-level flow).
- `dashboard/config.py`: shared constants (defaults, bins, color mapping).
- `dashboard/data_access/participants.py`: participant discovery and path resolution.
- `dashboard/modalities/wristband/processing.py`: wristband data loading + transformations.
- `dashboard/modalities/wristband/plots.py`: wristband Plotly figure factories.

## Development Principles
1. **Single Responsibility per Module**
   - Data loading/parsing lives in processing modules.
   - Plot construction lives in plot modules.
   - Streamlit widget orchestration stays in `dashboard/app.py`.

2. **Separation of Concerns**
   - Processing functions return DataFrames/tables, independent of Streamlit widgets.
   - Plot functions return `plotly.graph_objects.Figure` instances.
   - UI layer decides when/how to render and what fallback to show.

3. **Composable Feature Slices by Modality**
   - Wristband is now an explicit modality package.
   - New modalities should follow the same `processing.py` + `plots.py` pattern.

4. **Thin and Stable Entrypoint**
   - `participant_dashboard.py` intentionally contains minimal code.
   - This reduces merge conflicts and keeps Streamlit startup command unchanged.

5. **Pragmatic Performance**
   - Caching is centralized in the app layer via `@st.cache_data` wrappers.
   - Pure processing functions remain testable and reusable outside Streamlit.

## Why These Decisions
- The previous file had duplicated loops and timestamp parsing in multiple tabs.
- Repeated logic increased bug risk when adding new visualizations.
- Centralized processing functions provide one source of truth for:
  - wearing-detection file discovery,
  - timestamp normalization,
  - summary metrics,
  - bin-based daily aggregation.
- Figure factories decouple chart details from dashboard flow, making redesigns low-risk.

## Extending the Dashboard

### Add Sleep Modality
1. Create `dashboard/modalities/sleep/processing.py`.
2. Create `dashboard/modalities/sleep/plots.py`.
3. Add a Sleep tab in `dashboard/app.py` that calls those modules.

### Add TET/EEG Modality
1. Follow the same modality package pattern.
2. Reuse participant path helpers from `dashboard/data_access/participants.py`.
3. Keep any expensive transforms behind cached wrappers in `dashboard/app.py`.

### Add Shared Utilities (When Needed)
- Only introduce `dashboard/utils/` when duplication appears across modalities.
- Prefer explicit imports from modality modules over early abstraction.

## Quality and Maintenance Notes
- Keep processing functions free of Streamlit side effects.
- Add tests first for pure transformation logic (`hours_per_bin_table`, timestamp parsing).
- Avoid introducing modality-specific code directly in `dashboard/app.py`; call modality APIs instead.
- Keep constants in `dashboard/config.py` to avoid hidden magic values.

## How to Run
```bash
streamlit run participant_dashboard.py
```

The startup command is unchanged after modularization.
