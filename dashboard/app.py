from __future__ import annotations

from pathlib import Path

import streamlit as st

from dashboard.config import DEFAULT_DATA_BASE_PATH
from dashboard.data_access.participants import list_participants, participant_path
from dashboard.modalities.eeg.processing import summarize_meditation_recordings, summarize_sleep_recordings
from dashboard.modalities.wristband.processing import summarize_collection
from dashboard.pages.meditation import render_meditation_tab
from dashboard.pages.overview import render_overview_tab
from dashboard.pages.sleep import render_sleep_tab
from dashboard.pages.subjective import render_subjective_tab
from dashboard.pages.wristband import render_wristband_tab
from dashboard.services.data_loader import get_sleep_reports, get_wristband_data, get_meditation_data, get_subjective_data


def _render_summary(days_with_data: int, total_hours: float, sleep_nights: int, sleep_hours: float, meditation_sessions: int, meditation_hours: float) -> None:
    st.subheader("📊 Available Data Summary")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Days with Wristband Data", days_with_data)
    col2.metric("Total Hours Collected", f"{total_hours:.1f}")
    col3.metric("Nights with Sleep EEG", sleep_nights)
    col4.metric("Sleep EEG Hours", f"{sleep_hours:.1f}")
    col5.metric("Meditation Sessions", meditation_sessions)
    col6.metric("Meditation Hours", f"{meditation_hours:.1f}")


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

    # set one participant for testing purposes
    selected_participant = "Stream_LMU_HC_008_2024_30092024"
    
    
    participant_dir = participant_path(data_base_path, selected_participant)

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"Participant: {selected_participant}")

    with st.spinner(f"Loading data for {selected_participant}..."):
        df_wristband, wristband_wear_col = get_wristband_data(str(participant_dir))
        df_sleep = get_sleep_reports(str(participant_dir))
        df_meditation = get_meditation_data(str(participant_dir))
        df_subjective = get_subjective_data(str(participant_dir))
        wristband_summary, wristband_summary_hours = summarize_collection(df_wristband)
        sleep_summary, sleep_summary_hours = summarize_sleep_recordings(df_sleep)
        meditation_summary, meditation_hours = summarize_meditation_recordings(df_meditation)
        

    _render_summary(wristband_summary, wristband_summary_hours, sleep_summary, sleep_summary_hours, meditation_summary, meditation_hours)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Data Overview", "❤️ Wristband Biomarkers", "🌙 Sleep Data", "🧘 Meditation Data", "📝 Subjective Data"])

    with tab1:
        render_overview_tab(df_wristband, wristband_wear_col, df_sleep, df_meditation, df_subjective)

    with tab2:
        render_wristband_tab(df_wristband, wristband_wear_col)

    with tab3:
        render_sleep_tab(df_sleep)

    with tab4:
        render_meditation_tab(df_meditation)

    with tab5:
        render_subjective_tab(df_subjective)

    st.markdown("---")
    st.markdown(
        """
<div style='text-align: center; color: gray; font-size: 12px;'>
    CAM-LMU-STREAM Dashboard | Built with Streamlit | Wristband & Sleep Data |
</div>
""",
        unsafe_allow_html=True,
    )
