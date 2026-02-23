from __future__ import annotations

from pathlib import Path

import pandas as pd

import streamlit as st

from dashboard.config import DEFAULT_DATA_BASE_PATH
from dashboard.data_access.participants import list_participants, participant_path
from dashboard.modalities.eeg.processing import summarize_meditation_recordings, summarize_sleep_recordings
from dashboard.modalities.wristband.processing import summarize_collection
from dashboard.modalities.subjective.processing import summarize_subjective_data
from dashboard.pages.meditation import render_meditation_tab
from dashboard.pages.overview import build_combined_overview, render_overview_tab
from dashboard.pages.sleep import render_sleep_tab
from dashboard.pages.subjective import render_subjective_tab
from dashboard.pages.wristband import render_wristband_tab
from dashboard.services.data_loader import get_sleep_reports, get_wristband_data, get_meditation_data, get_subjective_data
from dashboard.services.data_quality import wristband_days_with_following_sleep_night, nights_with_following_wristband_day


def _render_summary(days_with_data: int, total_hours: float, sleep_nights: int, sleep_hours: float, meditation_sessions: int, meditation_hours: float, 
                    sleep_diary_sheets: int, tet_diary_sheets: int, activity_diary_sheets: int, tet_meditation_sheets: int) -> None:
    st.subheader("📊 Available Data Summary")
    col1, col2, col3, col4, col5, col6, = st.columns(6)
    col1.metric("Days with Wristband Data", days_with_data)
    col2.metric("Wristband Total Hours", f"{total_hours:.1f}")
    col3.metric("Nights with Sleep EEG", sleep_nights)
    col4.metric("Sleep EEG Total Hours", f"{sleep_hours:.1f}")
    col5.metric("Meditation Sessions", meditation_sessions)
    col6.metric("Meditation Total Hours", f"{meditation_hours:.1f}")
    
    col7, col8, col9, col10, col11, col12 = st.columns(6)
    col9.metric("Sleep Diary Amount", sleep_diary_sheets)
    col8.metric("TET Diary Amount", tet_diary_sheets)
    col7.metric("Activity Diary Amount", activity_diary_sheets)
    col11.metric("TET Meditation Amount", tet_meditation_sheets)


def _build_cohort_table(
    participants: list[str],
    data_base_path: str,
    coverage_threshold: float,
) -> pd.DataFrame:
    """Return aggregated summary metrics for all participants in base path."""
    records: list[dict[str, object]] = []

    for pid in participants:
        p_dir = participant_path(data_base_path, pid)
        df_wristband, wear_col = get_wristband_data(str(p_dir))
        df_sleep = get_sleep_reports(str(p_dir))
        df_meditation = get_meditation_data(str(p_dir))
        df_subjective = get_subjective_data(str(p_dir))
        wristband_days, wristband_total_hours = summarize_collection(df_wristband)
        sleep_nights, sleep_total_hours = summarize_sleep_recordings(df_sleep)
        meditation_sessions, meditation_total_hours = summarize_meditation_recordings(df_meditation)

        nights_with_day, _ = nights_with_following_wristband_day(
            df_sleep, df_wristband, wear_col=wear_col, coverage_threshold=coverage_threshold
        )
        days_with_night, _ = wristband_days_with_following_sleep_night(
            df_sleep, df_wristband, wear_col=wear_col, coverage_threshold=coverage_threshold
        )

        records.append(
            {
                "participant": pid,
                "wristband_days": wristband_days,
                "wristband_total_hours": wristband_total_hours,
                "wristband_mean": wristband_total_hours / wristband_days if wristband_days > 0 else 0,
                "eeg_company": df_sleep["company"].iloc[0] if not df_sleep.empty else None,
                "sleep_nights": sleep_nights,
                "sleep_total_hours": sleep_total_hours,
                "sleep_mean": sleep_total_hours / sleep_nights if sleep_nights > 0 else 0,
                "meditation_sessions": meditation_sessions,
                "meditation_total_hours": meditation_total_hours,
                "meditation_mean": meditation_total_hours / meditation_sessions if meditation_sessions > 0 else 0,
                "sleep_diary_amount": summarize_subjective_data(df_subjective).get("sleep_diary_sheets_with_data", 0),
                "tet_diary_amount": summarize_subjective_data(df_subjective).get("tet_diary_sheets_with_data", 0),
                "activity_diary_amount": summarize_subjective_data(df_subjective).get("activity_diary_sheets_with_data", 0),
                "tet_meditation_amount": summarize_subjective_data(df_subjective).get("tet_meditation_sheets_with_data", 0),
                "nights_with_following_day": nights_with_day,
                "days_with_following_night": days_with_night,
                "coverage_threshold": coverage_threshold,
            }
        )

    return pd.DataFrame.from_records(records)


def run_dashboard() -> None:
    st.set_page_config(
        page_title="CAM-LMU-ASD Participant Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🏥 CAM-LMU-ASD Participant Data Dashboard")
    st.markdown(
        "Visualize timeline of Wristband wear times, Sleep data, Meditation sessions, and Subjective reports for each participant. "
    )

    st.sidebar.header("Configuration")
    data_base_path = st.sidebar.text_input(
        "Enter base data folder path:",
        value=DEFAULT_DATA_BASE_PATH,
        help="Path where original participant folders are stored (e.g., LMU_STREAM_HC_001, etc.)",
    )

    # view mode toggle stored in session state
    if "view_mode" not in st.session_state:
        st.session_state["view_mode"] = "participant"

    if not Path(data_base_path).exists():
        st.warning(f"⚠️ Data path does not exist: {data_base_path}")
        st.stop()

    participants = list_participants(data_base_path)
    if not participants:
        st.error("❌ No participant folders found in the specified path")
        st.stop()

    # participant selection (only in participant view)
    selected_participant = None
    if st.session_state.get("view_mode") == "participant":
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

    st.sidebar.markdown("---")
    # Coverage threshold slider (percentage)
    threshold_pct = st.sidebar.slider(
        "Wristband coverage threshold (%)",
        min_value=0,
        max_value=100,
        value=70,
        step=5,
        help="Minimum fraction of minutes in the defined day period required to count the day as available (shown as percent).",
    )
    coverage_threshold = float(threshold_pct) / 100.0

    st.sidebar.markdown("---")
    # cohort navigation buttons at bottom
    if st.session_state.get("view_mode") == "cohort":
        if st.sidebar.button("Back to participant page"):
            st.session_state["view_mode"] = "participant"
            st.rerun()
    else:
        if st.sidebar.button("Open cohort summary page"):
            st.session_state["view_mode"] = "cohort"
            st.rerun()

    if st.session_state.get("view_mode") == "participant":
        with st.spinner(f"Loading data for {selected_participant}..."):
            df_wristband, wristband_wear_col = get_wristband_data(str(participant_dir))
            df_sleep = get_sleep_reports(str(participant_dir))
            df_meditation = get_meditation_data(str(participant_dir))
            df_subjective = get_subjective_data(str(participant_dir))
            wristband_summary, wristband_summary_hours = summarize_collection(df_wristband)
            sleep_summary, sleep_summary_hours = summarize_sleep_recordings(df_sleep)
            meditation_summary, meditation_hours = summarize_meditation_recordings(df_meditation)
            # compute cross-modality counts based on chosen coverage threshold
            nights_with_day_cnt, _ = nights_with_following_wristband_day(
                df_sleep, df_wristband, wear_col=wristband_wear_col, coverage_threshold=coverage_threshold
            )
            days_with_night_cnt, _ = wristband_days_with_following_sleep_night(
                df_sleep, df_wristband, wear_col=wristband_wear_col, coverage_threshold=coverage_threshold
            )

        _render_summary(wristband_summary, wristband_summary_hours, sleep_summary, sleep_summary_hours, meditation_summary, meditation_hours,
                        sleep_diary_sheets=summarize_subjective_data(df_subjective).get("sleep_diary_sheets_with_data", 0),
                        tet_diary_sheets=summarize_subjective_data(df_subjective).get("tet_diary_sheets_with_data", 0),
                        activity_diary_sheets=summarize_subjective_data(df_subjective).get("activity_diary_sheets_with_data", 0),
                        tet_meditation_sheets=summarize_subjective_data(df_subjective).get("tet_meditation_sheets_with_data", 0))

        # show additional cross-modality availability metrics based on threshold
        st.subheader("🔗 Cross-Modality Data Quality Metrics")
        col7, col8, col9, col10, col11, col12 = st.columns(6)
        col7.metric(f"Nights with following day (≥{threshold_pct}%)", nights_with_day_cnt)
        col8.metric(f"Days (with ≥{threshold_pct}%) with following night", days_with_night_cnt)

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📅 Data Overview",
            "❤️ Wristband Biomarkers",
            "🌙 Sleep Data",
            "🧘 Meditation Data",
            "📝 Subjective Data",
        ])

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


    else:
        st.title("👥 Cohort Summary")
        

        tab_table, tab_overviews = st.tabs([
            "Summary Table",
            "Participant Overviews",
        ])

        with tab_table:
            st.caption("Uses the coverage threshold from the sidebar slider.")
            if st.button("Build cohort summary table"):
                with st.spinner("Building cohort summary across all participants..."):
                    cohort_df = _build_cohort_table(participants, data_base_path, coverage_threshold)
                    st.session_state["cohort_df"] = cohort_df

            cohort_df = st.session_state.get("cohort_df") if "cohort_df" in st.session_state else None
            if cohort_df is not None and not cohort_df.empty:
                st.dataframe(cohort_df, use_container_width=True)
                csv_bytes = cohort_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download CSV",
                    data=csv_bytes,
                    file_name="cohort_summary.csv",
                    mime="text/csv",
                )
            else:
                st.info("Click the button to build the cohort summary table.")

        with tab_overviews:
            st.subheader("All Participant Overviews")
            st.caption("Renders each participant's combined timeline for side-by-side visual comparison. May take a few seconds for many participants.")

            selected_for_overview = st.multiselect(
                "Choose participants to render",
                options=participants,
                default=participants,
            )

            if not selected_for_overview:
                st.info("Select at least one participant to render their overview plot.")
            else:
                for pid in selected_for_overview:
                    p_dir = participant_path(data_base_path, pid)
                    with st.spinner(f"Rendering overview for {pid}..."):
                        df_wristband, wristband_wear_col = get_wristband_data(str(p_dir))
                        df_sleep = get_sleep_reports(str(p_dir))
                        df_meditation = get_meditation_data(str(p_dir))
                        df_subjective = get_subjective_data(str(p_dir))
                        fig = build_combined_overview(df_wristband, wristband_wear_col, df_sleep, df_meditation, df_subjective)

                    st.markdown(f"**{pid}**")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                        html_bytes = fig.to_html(full_html=False, include_plotlyjs="cdn").encode("utf-8")
                        st.download_button(
                            label="Download interactive HTML",
                            data=html_bytes,
                            file_name=f"{pid}_overview.html",
                            mime="text/html",
                            key=f"dl-{pid}",
                        )
                    else:
                        st.info("No timeline data available for this participant.")

    st.markdown("---")
    st.markdown(
        """
<div style='text-align: center; color: gray; font-size: 12px;'>
    CAM-LMU-STREAM Dashboard | Built with Streamlit | Wristband & Sleep Data |
</div>
""",
        unsafe_allow_html=True,
    )
