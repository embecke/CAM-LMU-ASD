from dashboard.modalities.subjective.processing import load_subjective_data

df_subjective = load_subjective_data(r'C:\Users\becke\Documents\PhD_NEVIA\Data_STREAM\Stream_LMU_HC_008_2024_30092024', debug=True)
print(df_subjective[['sheet_name','section','recording_date','expected', 'color', 'color_int']].tail(30))

# print(df["color"].dropna().sum())

# from dashboard.modalities.subjective.plots import plot_subjective_tile_grid
# fig, pivot_color = plot_subjective_tile_grid(df_subjective)
# print(repr(pivot_color.loc['activity_diary','2024-11-10']))
# print(repr(pivot_color.loc['tet_meditation','2024-11-10']))
