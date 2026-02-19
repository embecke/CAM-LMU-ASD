from dashboard.modalities.subjective.processing import load_subjective_data

df = load_subjective_data(r'C:\Users\becke\Documents\PhD_NEVIA\Data_STREAM\Stream_LMU_HC_008_2024_30092024', debug=True)
print(df[['sheet_name','section','first_entry_raw','recording_date','recording_date_iso']])