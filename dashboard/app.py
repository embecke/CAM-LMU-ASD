from __future__ import annotations

from pathlib import Path

import streamlit as st

from dashboard.config import DEFAULT_DATA_BASE_PATH
from dashboard.data_access.participants import list_participants, participant_path
from dashboard.modalities.eeg.processing import summarize_sleep_recordings
from dashboard.modalities.wristband.processing import summarize_collection
from dashboard.pages.overview import render_overview_tab
from dashboard.pages.sleep import render_sleep_tab
from dashboard.pages.wristband import render_wristband_tab
from dashboard.services.data_loader import get_sleep_reports, get_wearing_data


def _render_summary(days_with_data: int, total_hours: float, sleep_nights: int, sleep_hours: float) -> None:
    st.subheader("📊 Available Data Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Days with Wristband Data", days_with_data)
    col2.metric("Total Hours Collected", f"{total_hours:.1f}")
    col3.metric("Nights with Sleep EEG", sleep_nights)
    col4.metric("Sleep EEG Hours", f"{sleep_hours:.1f}")


def run_dashboard() -> None:
    st.set_page_config(
        page_title="CAM-LMU-ASD Participant Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🏥 CAM-LMU-ASD Participant Data Dashboard")
    st.markdown(
        "Visualize preprocessed Wristband biomarkers and Sleep data for each participant. "
        "*TET data coming soon!*"
    )

    st.sidebar.header("Configuration")
    data_base_path = st.sidebar.text_input(
        "Enter base data folder path:",
        value=DEFAULT_DATA_BASE_PATH,
        help="Path where original participant folders are stored (e.g., LMU_STREAM_HC_001, etc.)",
    )

    if not Path(data_base_path).exists():
        st.warning(f"⚠️ Data path does not exist: {data_base_path}")
        st.stop()

    participants = list_participants(data_base_path)
    if not participants:
        st.error("❌ No participant folders found in the specified path")
        st.stop()

    selected_participant = st.sidebar.selectbox(
        "Select Participant:",
        participants,
        help="Choose a participant to view their data",
    )

    participant_dir = participant_path(data_base_path, selected_participant)

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"Participant: {selected_participant}")

    with st.spinner(f"Loading data for {selected_participant}..."):
        df_all, wear_col = get_wearing_data(str(participant_dir))
        sleep_df = get_sleep_reports(str(participant_dir))
        days_with_data, total_hours = summarize_collection(df_all)
        sleep_nights, sleep_hours = summarize_sleep_recordings(sleep_df)

    _render_summary(days_with_data, total_hours, sleep_nights, sleep_hours)

    tab1, tab2, tab3 = st.tabs(["📅 Data Overview", "❤️ Wristband Biomarkers", "🌙 Sleep Data"])

    with tab1:
        render_overview_tab(df_all, wear_col, sleep_df)

    with tab2:
        render_wristband_tab(df_all, wear_col)

    with tab3:
        render_sleep_tab(sleep_df)

    st.markdown("---")
    st.markdown(
        """
<div style='text-align: center; color: gray; font-size: 12px;'>
    CAM-LMU-STREAM Dashboard | Built with Streamlit | Wristband & Sleep Data |
</div>
""",
        unsafe_allow_html=True,
    )
