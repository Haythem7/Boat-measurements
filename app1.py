import streamlit as st
import pandas as pd
import plotly.express as px
import random

# Title
st.title("Boat Measures Visualization")

# Load data
df = pd.read_excel("dataset_janauaca_20210715_OneSpreadsheet.xlsx")
df.columns = df.columns.str.strip()
df["DATE"] = pd.to_datetime(df["DATE"])

# Grouped parameters
parameter_groups = {
    "WaterQuality": [
        "SECCHI", "T(°C)", "SpCOND(uS/cm)", "ODO%", "ODO(mg/l)", "PROBE_CHLO-a(ug/l)",
        "N-NO3+N-NO2(uM)", "N-NO2 (uM)", "No2(mg/l)", "N-NO3corr(uM)", "N03(mg/l)",
        "P-PO4(uM)", "PO4(mg/l)", "Si-SiO4(uM)", "SiO4(mg/l)", "N-DIN (mgN/l )",
        "Ntot(uM)", "Ptot(uM)"
    ],
    "Hydrodynamics": [
        "BottomElevation_Buf50(m)", "SimWaterDepth_Buf50(m)", "SimVelU_Buf50(m.s-1)",
        "SimVelV_Buf50(m.s-1)", "SimVelMag_Buf50(m.s-1)", "SimVelDir_Buf50(Deg)",
        "EffFetch_24h(m)", "WaveFromEffFetch(m)", "FroudeNumber", "ReynoldNumber",
        "ResidenceTime_24h(s)", "SimplifiedResidenceTimek_24h(s)"
    ],
    "Hydro-model": [
        "Water Level (m)", "Volume (m3)", "Surface (m2)", "channel %", "upland %",
        "attz%", "rain %", "seepage %", "v_init %"
    ],
    "Weather": [
        "CumRainTrmm24h_1Day(mm)", "AirTemp_1Day(°)", "CumEvap1h_1Day(mm)",
        "SolarRad_1Day(W/m2)", "RelHum_1Day(%)", "AirPressure_1Day(kPa)"
    ]
}

# Station coordinates
station_coords = df.groupby("NEW_ NAME")[["LATITUDE", "LONGITUDE"]].first().reset_index()

# Station selection
station_names = df["NEW_ NAME"].unique()
selected_station = st.selectbox("Choose a station", station_names)

# Parameter group selection
selected_group = st.selectbox("Choose parameter group", list(parameter_groups.keys()))
selected_param = st.selectbox("Choose a parameter", parameter_groups[selected_group])

# Get selected station coordinates
selected_coords = station_coords[station_coords["NEW_ NAME"] == selected_station].iloc[0]

# Map with selected station highlighted
fig_map = px.scatter_mapbox(
    station_coords,
    lat="LATITUDE",
    lon="LONGITUDE",
    hover_name="NEW_ NAME",
    zoom=5,
    height=500,
    color_discrete_sequence=["blue"]
)

fig_map.add_trace(px.scatter_mapbox(
    pd.DataFrame([selected_coords]),
    lat="LATITUDE",
    lon="LONGITUDE",
    hover_name="NEW_ NAME",
    color_discrete_sequence=["red"],
    zoom=10
).data[0])

fig_map.update_layout(
    mapbox_style="open-street-map",
    mapbox_zoom=10,
    mapbox_center={"lat": selected_coords["LATITUDE"], "lon": selected_coords["LONGITUDE"]},
    margin={"r": 0, "t": 0, "l": 0, "b": 0}
)

st.plotly_chart(fig_map)

# Filter data for selected station
station_df = df[df["NEW_ NAME"] == selected_station].copy()

# Filter out rows where selected parameter is NaN
valid_df = station_df[station_df[selected_param].notna()].copy()

# Extract month-year for grouping
valid_df["MONTH_YEAR"] = valid_df["DATE"].dt.to_period("M")

# Group by month-year and pick one random date from each (to ensure spacing)
grouped = valid_df.groupby("MONTH_YEAR")
one_date_per_month = grouped.apply(lambda g: g.sample(1)).reset_index(drop=True)

# Select up to 6 of them, randomly
selected_dates_df = one_date_per_month.sort_values("DATE")
if len(selected_dates_df) > 6:
    selected_dates_df = selected_dates_df.sample(6).sort_values("DATE")

# Plot the parameter
fig_line = px.line(
    selected_dates_df,
    x="DATE",
    y=selected_param,
    markers=True,
    title=f"{selected_param} over spaced dates for {selected_station}"
)

# Add TOTAL_DEPTH below each point
for i, row in selected_dates_df.iterrows():
    depth = row.get("TOTAL_DEPTH", "NA")
    fig_line.add_annotation(
        x=row["DATE"],
        y=row[selected_param],
        text=f"{depth} m",
        showarrow=False,
        yshift=-30,
        font=dict(size=9, color="gray")
    )

st.plotly_chart(fig_line)
