# CAM-LMU-ASD
Code files built for the CAM-LMU-ASD project

For the old workflow of the project developed in 2023 as part of my first research project:
As described in the video guide, run code block 1 from the MATLAB file first (Explorations_and_visualisation.m), and then the python code (Sleep_Stat_Gen.py), and then back again to the matlab file code block 2 and proceed.

For work during the mastewr thesis and beyond: Use files from the "framework" folder

## Streamlit dashboard (modularized)

The dashboard entrypoint remains:

`streamlit run participant_dashboard.py`

Dashboard source is now modularized under `dashboard/` with separate modules for:
- app orchestration,
- participant data access,
- modality-specific processing,
- modality-specific plotting.

Design principles, implementation rationale, and extension guidance are documented in:

`docs/dashboard_modularization.md`
